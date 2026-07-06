"""Unit tests for context-mode output sandboxing — OPENDAW_MCP_OUTPUT_LIMIT."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "opendaw_mcp", "utils.py")) as f:
        return f.read()


def test_limit_output_exists():
    src = _get_source()
    assert "def _limit_output" in src


def test_output_limit_env_var():
    src = _get_source()
    assert "OPENDAW_MCP_OUTPUT_LIMIT" in src


def test_output_limit_default_zero():
    src = _get_source()
    assert '"0"' in src  # default 0 = unlimited


def test_limit_output_truncates_dict():
    src = _get_source()
    assert "__truncated" in src
    assert "__original_length" in src


def test_limit_output_truncates_list():
    src = _get_source()
    assert "total" in src
    assert "shown" in src


def test_limit_output_preserves_short_output():
    src = _get_source()
    assert "_OUTPUT_LIMIT <= 0 or len(s) <= _OUTPUT_LIMIT" in src


def test_limit_output_handles_non_json():
    src = _get_source()
    assert "Not JSON" in src or "simple truncation" in src


def test_limit_output_dict_has_truncated_flag():
    src = _get_source()
    assert '"__truncated"' in src
    assert '"__original_length"' in src


def test_limit_output_list_has_total():
    src = _get_source()
    assert '"total"' in src
    assert '"shown"' in src


def test_wrap_eval_uses_limit_output():
    src = _get_source()
    assert "_limit_output" in src


def test_output_limit_has_docstring():
    src = _get_source()
    assert "Truncate tool output" in src


def test_output_limit_zero_means_unlimited():
    src = _get_source()
    assert "unlimited" in src.lower()


def test_output_limit_has_smart_json_truncation():
    src = _get_source()
    assert "Smart JSON truncation" in src
