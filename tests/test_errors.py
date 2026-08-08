"""Tests for the central error catalog (issue #31 foundation slice)."""
from opendaw_mcp.errors import ERROR_CATALOG, enrich_error
from opendaw_mcp import prompt_inference, smart_export


def test_catalog_entries_complete_and_unique():
    refs = set()
    for code, entry in ERROR_CATALOG.items():
        assert entry["ref"].startswith("E"), code
        assert entry["ref"] not in refs, f"duplicate ref {entry['ref']}"
        refs.add(entry["ref"])
        assert entry["hint"].strip(), code
        assert entry["category"].strip(), code
        assert entry["docs"].startswith("http"), code


def test_enrich_fills_guidance():
    err = enrich_error({"error": "nope", "error_code": "NOT_FOUND"})
    assert err["error_ref"] == "E4001"
    assert err["hint"]
    assert "error-codes.md" in err["docs"]


def test_enrich_keeps_specific_hint():
    err = enrich_error({"error": "x", "error_code": "INVALID_PARAMETER", "hint": "custom"})
    assert err["hint"] == "custom"
    assert err["error_ref"] == "E3001"


def test_enrich_passthrough():
    assert enrich_error({"success": True}) == {"success": True}
    assert enrich_error({"error": "x"}) == {"error": "x"}
    assert enrich_error({"error": "x", "error_code": "SOMETHING_NEW"}) == {
        "error": "x",
        "error_code": "SOMETHING_NEW",
    }


def test_smart_export_errors_are_enriched():
    res = smart_export.export_for_platform("nope", "x")
    assert res["error_code"] == "INVALID_PARAMETER"
    assert res["error_ref"] == "E3001"
    assert res["hint"]  # specific platform list wins over catalog default


def test_prompt_inference_errors_are_enriched():
    res = prompt_inference.infer_suno_prompt()
    assert res["error_code"] == "INVALID_PARAMETER"
    assert res["error_ref"] == "E3001"
    assert res["hint"]  # catalog default filled in


def test_lineage_errors_are_enriched(tmp_path):
    from opendaw_mcp.lineage import LineageStore

    store = LineageStore(tmp_path / "lineage.json")

    bad_kind = store.record(kind="nope")
    assert bad_kind["error_ref"] == "E3001"
    assert "Valid kinds" in bad_kind["hint"]  # specific hint wins

    missing = store.trace_ancestors("n_missing")
    assert missing["error_code"] == "NOT_FOUND"
    assert missing["error_ref"] == "E4001"
    assert missing["hint"]  # catalog default filled in

    desc = store.list_descendants("n_missing")
    assert desc["error_ref"] == "E4001"

    diff = store.diff_mix_passes("", "x")
    assert diff["error_ref"] == "E3001"
    assert diff["hint"]

    hist = store.list_mix_history("")
    assert hist["error_ref"] == "E3001"

    dup_a = store.record(kind="export", path="/tmp/a.wav", node_id="n_dup")
    assert dup_a.get("success")
    dup_b = store.record(kind="export", path="/tmp/b.wav", node_id="n_dup")
    assert dup_b["error_ref"] == "E3001"
