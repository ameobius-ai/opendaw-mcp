"""Unit tests for produce_full_track — ultimate meta-tool."""
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
    if not src or "produce_full_track" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_produce_exists():
    src = _get_source()
    assert "async def mcp_opendaw_produce_full_track" in src


def test_produce_has_structure_param():
    src = _get_source()
    assert "structure: str" in src


def test_produce_has_genre_param():
    src = _get_source()
    assert "genre: str" in src


def test_produce_has_bpm_param():
    src = _get_source()
    assert "bpm: float" in src


def test_produce_has_render_param():
    src = _get_source()
    assert "render: bool" in src


def test_produce_calls_set_bpm():
    src = _get_source()
    assert "mcp_opendaw_set_bpm" in src


def test_produce_calls_arrange_full_song():
    src = _get_source()
    assert "mcp_opendaw_arrange_full_song" in src


def test_produce_calls_create_drum_pattern():
    src = _get_source()
    assert "mcp_opendaw_create_drum_pattern" in src


def test_produce_calls_create_bassline():
    src = _get_source()
    assert "mcp_opendaw_create_bassline" in src


def test_produce_calls_apply_mix_preset():
    src = _get_source()
    assert "mcp_opendaw_apply_mix_preset" in src


def test_produce_calls_render_full():
    src = _get_source()
    assert "mcp_opendaw_render_full" in src


def test_produce_has_6_steps():
    src = _get_source()
    assert "Step 1" in src
    assert "Step 2" in src
    assert "Step 3" in src
    assert "Step 4" in src
    assert "Step 5" in src
    assert "Step 6" in src


def test_produce_has_error_handling():
    src = _get_source()
    assert "drum_error" in src
    assert "bass_error" in src


def test_produce_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_produce_has_key_root():
    src = _get_source()
    assert "key_root: str = " in src


def test_produce_has_scale_type():
    src = _get_source()
    assert "scale_type: str = " in src


def test_produce_has_docstring():
    src = _get_source()
    assert "ultimate meta-tool" in src
    assert "One call replaces" in src


def test_produce_has_examples():
    src = _get_source()
    assert "produce_full_track(" in src


def test_produce_has_total_notes():
    src = _get_source()
    assert "total_notes" in src


def test_produce_has_next_steps():
    src = _get_source()
    assert "next_steps" in src


def test_produce_has_genre_list():
    src = _get_source()
    assert "house" in src
    assert "dnb" in src
    assert "trap" in src


def test_produce_default_structure():
    src = _get_source()
    assert "intro:4,verse:8,prechorus:2,chorus:8" in src
