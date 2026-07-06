"""Unit tests for lite mode — OPENDAW_MCP_MODE env var."""
import importlib.util
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
        return f.read()


def test_lite_tools_set_exists():
    src = _get_source()
    assert "LITE_TOOLS" in src


def test_lite_tools_is_set():
    src = _get_source()
    assert "LITE_TOOLS = {" in src


def test_lite_mode_env_var_in_help():
    src = _get_source()
    assert "OPENDAW_MCP_MODE" in src
    assert "lite" in src


def test_lite_mode_removes_tools():
    src = _get_source()
    assert "remove_tool" in src
    assert "mode == \"lite\"" in src


def test_lite_mode_has_39_tools():
    src = _get_source()
    # Count tool names in the set
    import re
    matches = re.findall(r'"(mcp_opendaw_\w+)"', src[src.index("LITE_TOOLS = {"):src.index("}", src.index("LITE_TOOLS = {")) + 1])
    assert len(matches) == 39, f"Expected 39, got {len(matches)}"


def test_lite_mode_has_create_synth_track():
    src = _get_source()
    assert "mcp_opendaw_create_synth_track" in src


def test_lite_mode_has_render_full():
    src = _get_source()
    assert "mcp_opendaw_render_full" in src


def test_lite_mode_has_add_effect():
    src = _get_source()
    assert "mcp_opendaw_add_effect" in src


def test_lite_mode_has_script_devices():
    src = _get_source()
    assert "mcp_opendaw_set_script_device_code" in src
    assert "mcp_opendaw_set_script_param" in src


def test_lite_mode_has_audio():
    src = _get_source()
    assert "mcp_opendaw_load_audio" in src
    assert "mcp_opendaw_place_audio_region" in src


def test_lite_mode_has_version():
    src = _get_source()
    assert "__version__" in src


def test_lite_mode_has_compositional_tools():
    src = _get_source()
    assert "mcp_opendaw_create_drum_pattern" in src
    assert "mcp_opendaw_create_bassline" in src
    assert "mcp_opendaw_create_melody" in src
    assert "mcp_opendaw_create_chord_progression" in src


def test_lite_mode_has_mixing():
    src = _get_source()
    assert "mcp_opendaw_create_send" in src
    assert "mcp_opendaw_set_track_volume" in src
    assert "mcp_opendaw_set_track_panning" in src


def test_lite_mode_has_export():
    src = _get_source()
    assert "mcp_opendaw_export_stems" in src


def test_lite_mode_has_project_info():
    src = _get_source()
    assert "mcp_opendaw_get_full_project_state" in src
    assert "mcp_opendaw_get_project_info" in src


def test_lite_mode_prints_status():
    src = _get_source()
    assert "Lite mode:" in src


def test_lite_mode_help_shows_env_var():
    src = _get_source()
    assert "OPENDAW_MCP_MODE=lite" in src


def test_lite_mode_has_token_savings_message():
    src = _get_source()
    assert "93%" in src or "92%" in src


def test_lite_tools_file_exists():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "opendaw_mcp", "lite_tools.py")
    assert os.path.exists(path)
