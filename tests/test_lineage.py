"""Unit tests for opendaw_mcp.lineage — provenance store + graph walks."""

from __future__ import annotations

from pathlib import Path

import pytest

from opendaw_mcp.lineage import (
    LineageStore,
    VALID_KINDS,
    VALID_OPS,
    chain_hash,
    empty_store,
    reset_default_store,
)


@pytest.fixture
def store(tmp_path: Path) -> LineageStore:
    reset_default_store()
    s = LineageStore(tmp_path / "lineage.json")
    s.reset()
    return s


class TestSchema:
    def test_empty_store_version(self):
        d = empty_store()
        assert d["version"] == 1
        assert d["nodes"] == {}
        assert d["edges"] == []

    def test_chain_hash_stable(self):
        a = chain_hash({"eq": "HS+4@3k"}, "eq")
        b = chain_hash({"eq": "HS+4@3k"}, "eq")
        c = chain_hash({"eq": "HS+3@3k"}, "eq")
        assert a == b
        assert a != c
        assert len(a) == 16


class TestRecord:
    def test_record_root_node(self, store: LineageStore):
        r = store.record(
            kind="external",
            path="suno_raw.wav",
            label="suno v1",
            provenance={"source": "suno", "model": "chirp-v5-5"},
        )
        assert r["success"] is True
        assert r["node"]["kind"] == "external"
        assert r["node"]["path"] == "suno_raw.wav"
        assert "edge" not in r
        assert r["node"]["id"] in store.load()["nodes"]

    def test_record_with_parent_edge(self, store: LineageStore):
        root = store.record(kind="external", path="src.wav")
        child = store.record(
            kind="stem",
            path="vocals.wav",
            parent_id=root["node"]["id"],
            op="stem_split",
            params={"model": "bs-roformer"},
            metrics={"lufs_integrated": -18.2},
        )
        assert child["success"] is True
        assert child["edge"]["parent_id"] == root["node"]["id"]
        assert child["edge"]["op"] == "stem_split"
        assert child["node"]["metrics"]["lufs_integrated"] == -18.2
        assert "chain_hash" in child["node"]["provenance"]

    def test_unknown_parent(self, store: LineageStore):
        r = store.record(kind="audio", parent_id="n_missing", op="eq")
        assert "error" in r
        assert r["error_code"] == "NOT_FOUND"

    def test_invalid_kind(self, store: LineageStore):
        r = store.record(kind="banana")
        assert "error" in r
        assert r["error_code"] == "INVALID_PARAMETER"

    def test_invalid_op(self, store: LineageStore):
        r = store.record(kind="audio", parent_id=None, op="teleport")
        # no parent — still validates op when? we validate always
        r = store.record(kind="audio", op="teleport")
        assert "error" in r

    def test_persist_reload(self, store: LineageStore, tmp_path: Path):
        r = store.record(kind="render", path="mix.wav", label="v1")
        store2 = LineageStore(tmp_path / "lineage.json")
        node = store2.get_node(r["node"]["id"])
        assert node is not None
        assert node["label"] == "v1"


class TestTrace:
    def _chain(self, store: LineageStore):
        a = store.record(kind="external", path="suno.wav", label="root")
        b = store.record(
            kind="stem",
            path="stems/vox.wav",
            parent_id=a["node"]["id"],
            op="stem_split",
        )
        c = store.record(
            kind="mix_pass",
            path="mix_eq.wav",
            parent_id=b["node"]["id"],
            op="eq",
            params={"recipe": "LS-2.5@100"},
            metrics={"presence_pct": 4.9},
        )
        d = store.record(
            kind="export",
            path="spotify.wav",
            parent_id=c["node"]["id"],
            op="export",
            params={"platform": "spotify"},
        )
        return a, b, c, d

    def test_trace_ancestors(self, store: LineageStore):
        a, b, c, d = self._chain(store)
        t = store.trace_ancestors(d["node"]["id"])
        assert t["success"] is True
        assert t["nodes_visited"] == 4
        ops = [step["edge"]["op"] for step in t["ancestors"]]
        assert "export" in ops
        assert "eq" in ops
        assert "stem_split" in ops
        assert t["roots"][0]["id"] == a["node"]["id"]

    def test_list_descendants(self, store: LineageStore):
        a, b, c, d = self._chain(store)
        t = store.list_descendants(a["node"]["id"])
        assert t["success"] is True
        child_ids = {step["child"]["id"] for step in t["descendants"]}
        assert b["node"]["id"] in child_ids
        assert d["node"]["id"] in child_ids
        leaf_ids = {n["id"] for n in t["leaves"]}
        assert d["node"]["id"] in leaf_ids

    def test_unknown_trace(self, store: LineageStore):
        t = store.trace_ancestors("n_nope")
        assert "error" in t


class TestList:
    def test_list_filter_kind(self, store: LineageStore):
        store.record(kind="stem", path="a.wav")
        store.record(kind="export", path="b.wav")
        store.record(kind="stem", path="c.wav")
        r = store.list_nodes(kind="stem", limit=10)
        assert r["success"] is True
        assert r["total"] == 2
        assert all(n["kind"] == "stem" for n in r["nodes"])


class TestValidSets:
    def test_kinds_nonempty(self):
        assert "mix_pass" in VALID_KINDS
        assert "export" in VALID_KINDS

    def test_ops_nonempty(self):
        assert "stem_split" in VALID_OPS
        assert "master" in VALID_OPS
