"""Agent-native lineage / provenance store for openDAW pipelines.

Inspired by theDAW LEARN genealogy — but lightweight, file-backed, no UI.
Tracks: source → op → result across suno → stems → eq → bounce → export.

Storage: JSON file (default exports/lineage/lineage.json).
Env:
  OPENDAW_LINEAGE_PATH  — full path to lineage.json
  OPENDAW_EXPORT_DIR    — used for default location under exports/lineage/
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from opendaw_mcp.errors import enrich_error

SCHEMA_VERSION = 1

VALID_KINDS = frozenset(
    {
        "audio",
        "render",
        "stem",
        "mix_pass",
        "export",
        "prompt",
        "external",
        "analysis",
    }
)

VALID_OPS = frozenset(
    {
        "import",
        "generate",
        "stem_split",
        "eq",
        "compress",
        "saturate",
        "reverb",
        "delay",
        "master",
        "bounce",
        "export",
        "cover",
        "remix",
        "inpaint",
        "extend",
        "analyze",
        "prompt_infer",
        "other",
    }
)

_lock = threading.RLock()

CANONICAL_METRICS = (
    "lufs_integrated",
    "true_peak_db",
    "sub_pct",
    "presence_pct",
    "air_pct",
    "crest",
)


def metric_diff(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, float]:
    """Compute numeric deltas (after - before) for overlapping numeric keys.

    Prefers CANONICAL_METRICS order; includes other shared numeric keys after.
    """
    before = before or {}
    after = after or {}
    keys: list[str] = []
    for k in CANONICAL_METRICS:
        if k in before or k in after:
            keys.append(k)
    for k in sorted(set(before) | set(after)):
        if k not in keys:
            keys.append(k)

    out: dict[str, float] = {}
    for k in keys:
        if k not in before or k not in after:
            continue
        try:
            bv = float(before[k])
            av = float(after[k])
        except (TypeError, ValueError):
            continue
        out[k] = round(av - bv, 6)
    return out


def _default_path() -> Path:
    env = os.environ.get("OPENDAW_LINEAGE_PATH")
    if env:
        return Path(env).expanduser().resolve()
    export_dir = os.environ.get(
        "OPENDAW_EXPORT_DIR",
        str(Path(__file__).resolve().parent.parent / "exports"),
    )
    return Path(export_dir).expanduser().resolve() / "lineage" / "lineage.json"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id(prefix: str = "n") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def empty_store() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "nodes": {},
        "edges": [],
    }


def chain_hash(params: dict | None = None, *parts: str) -> str:
    """Stable short hash for mix/render chains."""
    payload = json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256("|".join([payload, *parts]).encode("utf-8")).hexdigest()
    return h[:16]


class LineageStore:
    """Thread-safe JSON lineage store."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else _default_path()
        self._data: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        with _lock:
            if self._data is not None:
                return self._data
            if self.path.exists():
                try:
                    raw = json.loads(self.path.read_text(encoding="utf-8"))
                    if not isinstance(raw, dict):
                        raw = empty_store()
                    raw.setdefault("version", SCHEMA_VERSION)
                    raw.setdefault("nodes", {})
                    raw.setdefault("edges", [])
                    self._data = raw
                except (json.JSONDecodeError, OSError):
                    self._data = empty_store()
            else:
                self._data = empty_store()
            return self._data

    def save(self) -> None:
        with _lock:
            data = self.load()
            data["updated_at"] = _now_iso()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            tmp.replace(self.path)

    def reset(self) -> None:
        """In-memory reset (tests). Does not delete file unless save()."""
        with _lock:
            self._data = empty_store()

    def record(
        self,
        *,
        kind: str = "audio",
        path: str | None = None,
        parent_id: str | None = None,
        op: str = "other",
        params: dict | None = None,
        metrics: dict | None = None,
        provenance: dict | None = None,
        node_id: str | None = None,
        label: str | None = None,
        auto_save: bool = True,
    ) -> dict[str, Any]:
        """Create a node and optional parent→child edge.

        Returns {success, node, edge?}.
        """
        kind = (kind or "audio").strip().lower()
        if kind not in VALID_KINDS:
            return enrich_error({
                "error": f"Invalid kind: {kind}",
                "error_code": "INVALID_PARAMETER",
                "hint": f"Valid kinds: {sorted(VALID_KINDS)}",
            })
        op = (op or "other").strip().lower()
        if op not in VALID_OPS:
            return enrich_error({
                "error": f"Invalid op: {op}",
                "error_code": "INVALID_PARAMETER",
                "hint": f"Valid ops: {sorted(VALID_OPS)}",
            })

        with _lock:
            data = self.load()
            if parent_id and parent_id not in data["nodes"]:
                return enrich_error({
                    "error": f"Unknown parent_id: {parent_id}",
                    "error_code": "NOT_FOUND",
                    "hint": "Record parent first or omit parent_id",
                })

            nid = node_id or _new_id("n")
            if nid in data["nodes"]:
                return enrich_error({
                    "error": f"Node already exists: {nid}",
                    "error_code": "INVALID_PARAMETER",
                    "hint": "Use a new node_id or omit to auto-generate",
                })

            prov = dict(provenance or {})
            if params and "chain_hash" not in prov:
                prov["chain_hash"] = chain_hash(params, op, path or "")

            node = {
                "id": nid,
                "kind": kind,
                "path": path,
                "label": label,
                "created_at": _now_iso(),
                "metrics": dict(metrics or {}),
                "provenance": prov,
            }
            data["nodes"][nid] = node

            edge = None
            if parent_id:
                edge = {
                    "id": _new_id("e"),
                    "parent_id": parent_id,
                    "child_id": nid,
                    "op": op,
                    "params": dict(params or {}),
                    "created_at": _now_iso(),
                }
                data["edges"].append(edge)

            if auto_save:
                self.save()

            out: dict[str, Any] = {"success": True, "node": node}
            if edge:
                out["edge"] = edge
            return out

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with _lock:
            return deepcopy(self.load()["nodes"].get(node_id))

    def trace_ancestors(
        self, node_id: str, *, max_depth: int = 32
    ) -> dict[str, Any]:
        """Walk parent chain(s) from node_id toward roots."""
        with _lock:
            data = self.load()
            if node_id not in data["nodes"]:
                return enrich_error({
                    "error": f"Unknown node_id: {node_id}",
                    "error_code": "NOT_FOUND",
                })

            # parent_id -> edges from parent to child where child is current
            parents_of: dict[str, list[dict]] = {}
            for e in data["edges"]:
                parents_of.setdefault(e["child_id"], []).append(e)

            chain: list[dict] = []
            visited: set[str] = set()
            frontier = [node_id]
            depth = 0
            while frontier and depth < max_depth:
                nxt: list[str] = []
                for cid in frontier:
                    if cid in visited:
                        continue
                    visited.add(cid)
                    for e in parents_of.get(cid, []):
                        pid = e["parent_id"]
                        chain.append(
                            {
                                "depth": depth + 1,
                                "edge": e,
                                "parent": data["nodes"].get(pid),
                                "child": data["nodes"].get(cid),
                            }
                        )
                        if pid not in visited:
                            nxt.append(pid)
                frontier = nxt
                depth += 1

            # nodes with no parent edges among visited
            rooted = []
            for nid in visited:
                if not parents_of.get(nid):
                    rooted.append(data["nodes"][nid])

            return {
                "success": True,
                "node_id": node_id,
                "node": data["nodes"][node_id],
                "ancestors": chain,
                "roots": rooted,
                "depth": depth,
                "nodes_visited": len(visited),
            }

    def list_descendants(
        self, node_id: str, *, max_depth: int = 32
    ) -> dict[str, Any]:
        """Walk children from node_id toward leaves."""
        with _lock:
            data = self.load()
            if node_id not in data["nodes"]:
                return enrich_error({
                    "error": f"Unknown node_id: {node_id}",
                    "error_code": "NOT_FOUND",
                })

            children_of: dict[str, list[dict]] = {}
            for e in data["edges"]:
                children_of.setdefault(e["parent_id"], []).append(e)

            chain: list[dict] = []
            visited: set[str] = set()
            frontier = [node_id]
            depth = 0
            while frontier and depth < max_depth:
                nxt: list[str] = []
                for pid in frontier:
                    if pid in visited and depth > 0:
                        continue
                    visited.add(pid)
                    for e in children_of.get(pid, []):
                        cid = e["child_id"]
                        chain.append(
                            {
                                "depth": depth + 1,
                                "edge": e,
                                "parent": data["nodes"].get(pid),
                                "child": data["nodes"].get(cid),
                            }
                        )
                        if cid not in visited:
                            nxt.append(cid)
                frontier = nxt
                depth += 1

            leaves = []
            all_seen = {node_id} | {
                step["child"]["id"]
                for step in chain
                if step.get("child") and step["child"].get("id")
            }
            for nid in all_seen:
                if not children_of.get(nid):
                    node = data["nodes"].get(nid)
                    if node:
                        leaves.append(node)

            return {
                "success": True,
                "node_id": node_id,
                "node": data["nodes"][node_id],
                "descendants": chain,
                "leaves": leaves,
                "depth": depth,
                "nodes_visited": len(all_seen),
            }

    def list_nodes(
        self,
        *,
        kind: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        with _lock:
            data = self.load()
            nodes = list(data["nodes"].values())
            if kind:
                kind = kind.strip().lower()
                nodes = [n for n in nodes if n.get("kind") == kind]
            nodes.sort(key=lambda n: n.get("created_at") or "", reverse=True)
            limit = max(1, min(int(limit), 500))
            return {
                "success": True,
                "total": len(nodes),
                "shown": min(limit, len(nodes)),
                "nodes": nodes[:limit],
                "path": str(self.path),
            }

    # --- Process history (P2) — mix_pass chain + metric diffs ---

    def record_mix_pass(
        self,
        *,
        parent_id: str,
        path: str | None = None,
        op: str = "eq",
        params: dict | None = None,
        metrics: dict | None = None,
        label: str | None = None,
        node_id: str | None = None,
        provenance: dict | None = None,
        auto_save: bool = True,
    ) -> dict[str, Any]:
        """Wrapper: record kind=mix_pass under parent with mix op/metrics."""
        if not parent_id:
            return enrich_error({
                "error": "parent_id required for mix_pass",
                "error_code": "INVALID_PARAMETER",
                "hint": "Pass the previous mix/root node id",
            })
        op = (op or "eq").strip().lower()
        if op not in VALID_OPS:
            return enrich_error({
                "error": f"Invalid op: {op}",
                "error_code": "INVALID_PARAMETER",
                "hint": f"Valid ops: {sorted(VALID_OPS)}",
            })
        metrics = dict(metrics or {})
        # Keep only known metric keys when present; allow extras but prefer canonical
        return self.record(
            kind="mix_pass",
            path=path,
            parent_id=parent_id,
            op=op,
            params=params,
            metrics=metrics,
            provenance=provenance,
            node_id=node_id,
            label=label,
            auto_save=auto_save,
        )

    def _edge_to_child(self, child_id: str) -> dict[str, Any] | None:
        data = self.load()
        for e in data["edges"]:
            if e.get("child_id") == child_id:
                return e
        return None

    def _mix_chain_from(self, node_id: str) -> dict[str, Any]:
        """Collect ordered mix_pass chain through node_id (ancestors + descendants).

        Returns {success, chain:[{node, edge?}]} oldest→newest, or error dict.
        When multiple children exist, follows the longest mix_pass spine.
        """
        data = self.load()
        if node_id not in data["nodes"]:
            return enrich_error({
                "error": f"Unknown node_id: {node_id}",
                "error_code": "NOT_FOUND",
            })

        parents_of: dict[str, list[dict]] = {}
        children_of: dict[str, list[dict]] = {}
        for e in data["edges"]:
            parents_of.setdefault(e["child_id"], []).append(e)
            children_of.setdefault(e["parent_id"], []).append(e)

        # Ancestors: node → root
        up_ids: list[str] = []
        cur = node_id
        visited: set[str] = set()
        while cur and cur not in visited:
            visited.add(cur)
            up_ids.append(cur)
            pe = parents_of.get(cur)
            if not pe:
                break
            pe_sorted = sorted(pe, key=lambda x: x.get("created_at") or "")
            cur = pe_sorted[0]["parent_id"]
        up_ids.reverse()  # root → node

        # Descendants from node along longest mix_pass spine (exclude node itself)
        def _longest_mix_spine(start: str) -> list[str]:
            best: list[str] = []

            def dfs(nid: str, path: list[str]) -> None:
                nonlocal best
                kids = children_of.get(nid, [])
                mix_kids = [
                    e
                    for e in kids
                    if (data["nodes"].get(e["child_id"]) or {}).get("kind") == "mix_pass"
                ]
                if not mix_kids:
                    if len(path) > len(best):
                        best = list(path)
                    return
                # Prefer earliest created among equal branches after exploring all
                for e in sorted(mix_kids, key=lambda x: x.get("created_at") or ""):
                    cid = e["child_id"]
                    if cid in path:
                        continue
                    dfs(cid, path + [cid])
                if not mix_kids and len(path) > len(best):
                    best = list(path)

            dfs(start, [])
            return best

        down_ids = _longest_mix_spine(node_id)
        lineage_ids = up_ids + down_ids

        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        for nid in lineage_ids:
            if nid in seen:
                continue
            node = data["nodes"].get(nid)
            if not node or node.get("kind") != "mix_pass":
                continue
            seen.add(nid)
            edge = self._edge_to_child(nid)
            chain.append(
                {"node": deepcopy(node), "edge": deepcopy(edge) if edge else None}
            )

        return {
            "success": True,
            "node_id": node_id,
            "chain": chain,
            "count": len(chain),
        }

    def list_mix_history(
        self,
        node_id: str,
        *,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Last-N mix_pass nodes on the chain through node_id, with metric diffs.

        node_id may be a root, intermediate, or leaf. Diffs are consecutive
        (pass_n vs pass_n-1) for canonical metric keys.
        """
        if not node_id:
            return enrich_error({
                "error": "node_id required",
                "error_code": "INVALID_PARAMETER",
            })
        limit = max(1, min(int(limit), 100))

        with _lock:
            base = self._mix_chain_from(node_id)
            if "error" in base:
                return base

            chain = base["chain"]
            # If node itself is not mix and chain empty, try descendants mix_pass
            if not chain:
                desc = self.list_descendants(node_id, max_depth=64)
                if "error" in desc:
                    return desc
                mix_steps = [
                    step
                    for step in desc.get("descendants", [])
                    if step.get("child") and step["child"].get("kind") == "mix_pass"
                ]
                # order by depth then created_at
                mix_steps.sort(
                    key=lambda s: (
                        s.get("depth", 0),
                        (s.get("child") or {}).get("created_at") or "",
                    )
                )
                chain = [
                    {
                        "node": deepcopy(s["child"]),
                        "edge": deepcopy(s.get("edge")),
                    }
                    for s in mix_steps
                ]

            # Keep last N
            total = len(chain)
            shown_chain = chain[-limit:]

            passes: list[dict[str, Any]] = []
            prev_metrics: dict[str, Any] | None = None
            # For diffs we need the pass immediately before the window too
            pre_window = chain[: max(0, total - limit)]
            if pre_window:
                prev_metrics = dict(pre_window[-1]["node"].get("metrics") or {})

            for step in shown_chain:
                node = step["node"]
                metrics = dict(node.get("metrics") or {})
                diff = metric_diff(prev_metrics, metrics) if prev_metrics is not None else {}
                passes.append(
                    {
                        "id": node.get("id"),
                        "label": node.get("label"),
                        "path": node.get("path"),
                        "created_at": node.get("created_at"),
                        "op": (step.get("edge") or {}).get("op"),
                        "params": (step.get("edge") or {}).get("params") or {},
                        "metrics": metrics,
                        "diff_from_prev": diff,
                    }
                )
                prev_metrics = metrics

            return {
                "success": True,
                "node_id": node_id,
                "total_mix_passes": total,
                "shown": len(passes),
                "limit": limit,
                "passes": passes,
                "metric_keys": list(CANONICAL_METRICS),
            }

    def diff_mix_passes(self, node_a: str, node_b: str) -> dict[str, Any]:
        """Numeric delta of metrics between two nodes (b - a)."""
        if not node_a or not node_b:
            return enrich_error({
                "error": "node_a and node_b required",
                "error_code": "INVALID_PARAMETER",
            })
        with _lock:
            a = self.get_node(node_a)
            b = self.get_node(node_b)
            if a is None:
                return enrich_error({
                    "error": f"Unknown node_id: {node_a}",
                    "error_code": "NOT_FOUND",
                })
            if b is None:
                return enrich_error({
                    "error": f"Unknown node_id: {node_b}",
                    "error_code": "NOT_FOUND",
                })
            ma = dict(a.get("metrics") or {})
            mb = dict(b.get("metrics") or {})
            return {
                "success": True,
                "node_a": node_a,
                "node_b": node_b,
                "metrics_a": ma,
                "metrics_b": mb,
                "diff": metric_diff(ma, mb),
                "label_a": a.get("label"),
                "label_b": b.get("label"),
            }


# Process-wide default store (path resolved lazily)
_default_store: LineageStore | None = None


def get_store(path: str | Path | None = None) -> LineageStore:
    global _default_store
    if path is not None:
        return LineageStore(path)
    if _default_store is None:
        _default_store = LineageStore()
    return _default_store


def reset_default_store() -> None:
    """Test helper: drop process-wide store handle."""
    global _default_store
    with _lock:
        _default_store = None
