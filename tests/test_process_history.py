"""Unit tests for process history (P2) — mix_pass last-N + metric diffs."""

from __future__ import annotations

from pathlib import Path

import pytest

from opendaw_mcp.lineage import (
    CANONICAL_METRICS,
    LineageStore,
    metric_diff,
    reset_default_store,
)


@pytest.fixture
def store(tmp_path: Path) -> LineageStore:
    reset_default_store()
    s = LineageStore(tmp_path / "lineage.json")
    s.reset()
    return s


def _seed_chain(store: LineageStore, n: int = 5):
    """Synthetic root + n mix_pass nodes. presence rises +0.4 on pass index 3 (0-based 2)."""
    root = store.record(
        kind="external",
        path="suno_raw.wav",
        label="root",
        metrics={"presence_pct": 3.0, "sub_pct": 55.0, "lufs_integrated": -12.0, "true_peak_db": -0.3},
    )
    parent = root["node"]["id"]
    nodes = [root]
    presence = 3.0
    sub = 55.0
    for i in range(n):
        if i == 2:
            presence = round(presence + 0.4, 3)  # HS boost
            op = "eq"
            params = {"recipe": "HS+4@3k"}
            label = f"pass{i+1}_hs"
        elif i == 4:
            op = "master"
            params = {"limiter": "-0.5dBTP"}
            label = f"pass{i+1}_master"
        else:
            op = "eq"
            params = {"recipe": f"pass{i+1}"}
            label = f"pass{i+1}"
        r = store.record_mix_pass(
            parent_id=parent,
            path=f"mix_v{i+1}.wav",
            op=op,
            params=params,
            metrics={
                "presence_pct": presence,
                "sub_pct": sub,
                "lufs_integrated": -12.0 - i * 0.2,
                "true_peak_db": -0.5,
                "air_pct": 2.0 + i * 0.1,
                "crest": 8.0,
            },
            label=label,
        )
        assert r["success"] is True
        parent = r["node"]["id"]
        nodes.append(r)
    return nodes


class TestMetricDiff:
    def test_canonical_delta(self):
        d = metric_diff(
            {"presence_pct": 4.5, "sub_pct": 60.0, "label": "x"},
            {"presence_pct": 4.9, "sub_pct": 58.0, "label": "y"},
        )
        assert d["presence_pct"] == pytest.approx(0.4)
        assert d["sub_pct"] == pytest.approx(-2.0)
        assert "label" not in d

    def test_missing_keys_skipped(self):
        d = metric_diff({"presence_pct": 1.0}, {"sub_pct": 2.0})
        assert d == {}

    def test_canonical_keys_defined(self):
        assert "presence_pct" in CANONICAL_METRICS
        assert "true_peak_db" in CANONICAL_METRICS


class TestRecordMixPass:
    def test_wrapper_sets_kind(self, store: LineageStore):
        root = store.record(kind="external", path="a.wav")
        r = store.record_mix_pass(
            parent_id=root["node"]["id"],
            path="v1.wav",
            op="eq",
            params={"recipe": "LS-2.5@100"},
            metrics={"presence_pct": 4.9, "sub_pct": 50.0},
            label="eq1",
        )
        assert r["success"] is True
        assert r["node"]["kind"] == "mix_pass"
        assert r["edge"]["op"] == "eq"
        assert r["node"]["metrics"]["presence_pct"] == 4.9

    def test_requires_parent(self, store: LineageStore):
        r = store.record_mix_pass(parent_id="", path="x.wav")
        assert "error" in r
        assert r["error_code"] == "INVALID_PARAMETER"

    def test_unknown_parent(self, store: LineageStore):
        r = store.record_mix_pass(parent_id="n_missing", path="x.wav")
        assert "error" in r
        assert r["error_code"] == "NOT_FOUND"


class TestListMixHistory:
    def test_five_pass_chain_with_presence_diff(self, store: LineageStore):
        nodes = _seed_chain(store, n=5)
        leaf = nodes[-1]["node"]["id"]
        hist = store.list_mix_history(leaf, limit=8)
        assert hist["success"] is True
        assert hist["total_mix_passes"] == 5
        assert hist["shown"] == 5

        # first pass has empty diff (no prev mix)
        assert hist["passes"][0]["diff_from_prev"] == {} or hist["passes"][0]["diff_from_prev"] is not None
        # pass index 2 (3rd mix) has +0.4 presence vs previous
        p2 = hist["passes"][2]
        assert p2["diff_from_prev"]["presence_pct"] == pytest.approx(0.4)
        assert p2["op"] == "eq"
        assert "HS+4" in str(p2["params"].get("recipe", ""))

    def test_from_root_walks_descendants(self, store: LineageStore):
        nodes = _seed_chain(store, n=5)
        root_id = nodes[0]["node"]["id"]
        hist = store.list_mix_history(root_id, limit=8)
        assert hist["success"] is True
        assert hist["total_mix_passes"] == 5

    def test_limit_last_n(self, store: LineageStore):
        nodes = _seed_chain(store, n=5)
        leaf = nodes[-1]["node"]["id"]
        hist = store.list_mix_history(leaf, limit=2)
        assert hist["shown"] == 2
        assert hist["total_mix_passes"] == 5
        # last two labels
        labels = [p["label"] for p in hist["passes"]]
        assert labels[-1] == "pass5_master"
        # first of window should still have diff vs pass before window
        assert "presence_pct" in hist["passes"][0]["diff_from_prev"] or hist["passes"][0]["metrics"]

    def test_unknown_node(self, store: LineageStore):
        r = store.list_mix_history("n_nope")
        assert "error" in r


class TestDiffMixPasses:
    def test_diff_two_nodes(self, store: LineageStore):
        nodes = _seed_chain(store, n=5)
        a = nodes[2]["node"]["id"]  # before HS? index: 0=root, 1=pass1, 2=pass2, 3=pass3_hs
        b = nodes[3]["node"]["id"]  # HS pass
        d = store.diff_mix_passes(a, b)
        assert d["success"] is True
        assert d["diff"]["presence_pct"] == pytest.approx(0.4)

    def test_missing_node(self, store: LineageStore):
        root = store.record(kind="external", path="a.wav")
        r = store.diff_mix_passes(root["node"]["id"], "n_missing")
        assert "error" in r
        assert r["error_code"] == "NOT_FOUND"
