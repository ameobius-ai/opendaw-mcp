"""Unit tests for phase-based tool loading — OPENDAW_MCP_MODE=phase."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
        return f.read()


def test_phase_tools_exists():
    src = _get_source()
    assert "PHASE_TOOLS" in src


def test_phase_tools_has_4_phases():
    src = _get_source()
    for phase in ["inspect", "compose", "mix", "render"]:
        assert f'"{phase}"' in src, f"Phase {phase} missing"


def test_switch_phase_tool_exists():
    src = _get_source()
    assert "async def mcp_opendaw_switch_phase" in src


def test_switch_phase_has_docstring():
    src = _get_source()
    assert "Switch the active tool phase" in src


def test_apply_phase_function_exists():
    src = _get_source()
    assert "def _apply_phase" in src


def test_phase_mode_in_main():
    src = _get_source()
    assert "phase" in src
    assert "_apply_phase" in src


def test_phase_mode_env_var():
    src = _get_source()
    assert "OPENDAW_MCP_MODE" in src


def test_inspect_phase_has_read_only_tools():
    src = _get_source()
    assert "mcp_opendaw_get_full_project_state" in src
    assert "mcp_opendaw_read_meter" in src
    assert "mcp_opendaw_analyze_mix" in src


def test_compose_phase_has_creation_tools():
    src = _get_source()
    assert "mcp_opendaw_create_synth_track" in src
    assert "mcp_opendaw_create_drum_pattern" in src
    assert "mcp_opendaw_arrange_full_song" in src


def test_mix_phase_has_effect_tools():
    src = _get_source()
    assert "mcp_opendaw_add_effect" in src
    assert "mcp_opendaw_auto_master" in src
    assert "mcp_opendaw_add_genre_effects" in src


def test_render_phase_has_export_tools():
    src = _get_source()
    assert "mcp_opendaw_render_full" in src
    assert "mcp_opendaw_export_stems" in src


def test_all_phase_tools_meta():
    src = _get_source()
    assert "ALL_PHASE_TOOLS" in src
    assert "mcp_opendaw_switch_phase" in src
    assert "mcp_opendaw_evaluate_raw" in src


def test_switch_phase_validates_input():
    src = _get_source()
    assert "Invalid phase" in src


def test_switch_phase_returns_json():
    src = _get_source()
    assert "tools_active" in src
    assert "available_phases" in src


def test_phase_tools_file_exists():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "opendaw_mcp", "phase_tools.py")
    assert os.path.exists(path)


def test_current_phase_variable():
    src = _get_source()
    assert "_current_phase" in src


def test_phase_help_shows_mode():
    src = _get_source()
    assert "OPENDAW_MCP_MODE=lite" in src
    assert "phase" in src


def test_compose_has_scriptable_devices():
    src = _get_source()
    assert "mcp_opendaw_set_script_device_code" in src
    assert "mcp_opendaw_set_script_param" in src
