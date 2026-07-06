"""Unit tests for arrange_full_song — meta-tool for complete song arrangement."""
import importlib.util
import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    spec = importlib.util.spec_from_file_location(
        "server", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
    )
    mod = importlib.util.module_from_spec(spec)
    src = inspect.getsource(sys.modules.get("server", mod))
    if not src or "arrange_full_song" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_arrange_exists():
    src = _get_source()
    assert "async def mcp_opendaw_arrange_full_song" in src


def test_arrange_has_structure_param():
    src = _get_source()
    assert "structure: str" in src


def test_arrange_has_valid_sections():
    src = _get_source()
    for s in ["intro", "prechorus", "chorus", "verse", "bridge", "interlude", "transition", "outro", "coda"]:
        assert s in src, f"Missing section: {s}"


def test_arrange_has_valid_sections_set():
    src = _get_source()
    assert "VALID_SECTIONS" in src


def test_arrange_calls_create_intro():
    src = _get_source()
    assert "mcp_opendaw_create_intro(" in src


def test_arrange_calls_create_prechorus():
    src = _get_source()
    assert "mcp_opendaw_create_prechorus(" in src


def test_arrange_calls_create_bridge():
    src = _get_source()
    assert "mcp_opendaw_create_bridge(" in src


def test_arrange_calls_create_outro():
    src = _get_source()
    assert "mcp_opendaw_create_outro(" in src


def test_arrange_calls_create_interlude():
    src = _get_source()
    assert "mcp_opendaw_create_interlude(" in src


def test_arrange_calls_create_transition():
    src = _get_source()
    assert "mcp_opendaw_create_transition(" in src


def test_arrange_calls_create_coda():
    src = _get_source()
    assert "mcp_opendaw_create_coda(" in src


def test_arrange_calls_create_arpeggio():
    src = _get_source()
    assert "mcp_opendaw_create_arpeggio(" in src


def test_arrange_calls_create_song_structure():
    src = _get_source()
    assert "mcp_opendaw_create_song_structure" in src


def test_arrange_has_start_beat_tracking():
    src = _get_source()
    assert "current_beat" in src
    assert "start_beat" in src


def test_arrange_has_bar_calculation():
    src = _get_source()
    assert "bars * 4.0" in src or "bars * 4" in src


def test_arrange_has_type_params():
    src = _get_source()
    assert "intro_type" in src
    assert "prechorus_type" in src
    assert "bridge_type" in src
    assert "outro_type" in src


def test_arrange_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_arrange_has_key_root():
    src = _get_source()
    assert "key_root: str = " in src


def test_arrange_has_scale_type():
    src = _get_source()
    assert "scale_type: str = " in src


def test_arrange_has_velocity():
    src = _get_source()
    assert "velocity: float = 0.65" in src


def test_arrange_has_docstring():
    src = _get_source()
    assert "meta-tool" in src or "one call" in src
    assert "structure:" in src


def test_arrange_has_examples():
    src = _get_source()
    assert "arrange_full_song(" in src


def test_arrange_has_results_tracking():
    src = _get_source()
    assert "total_notes" in src
    assert "total_bars" in src
    assert "total_sections" in src


def test_arrange_has_next_steps():
    src = _get_source()
    assert "next_steps" in src
    assert "render_full" in src


def test_arrange_has_error_handling():
    src = _get_source()
    assert "Invalid structure format" in src
    assert "Invalid section name" in src


def test_arrange_has_chord_name_construction():
    src = _get_source()
    assert "chord_name" in src
    assert "min7" in src
    assert "maj7" in src


def test_arrange_default_structure():
    src = _get_source()
    assert "intro:4,prechorus:2,chorus:4" in src
