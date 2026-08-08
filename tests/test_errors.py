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
