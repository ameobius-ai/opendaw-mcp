"""Unit tests for produce_and_master — ultimate one-call pipeline."""
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
    if not src or "produce_and_master" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_pipeline_exists():
    src = _get_source()
    assert "async def mcp_opendaw_produce_and_master" in src


def test_pipeline_has_7_steps():
    src = _get_source()
    for i in range(1, 8):
        assert f"Step {i}" in src


def test_pipeline_calls_set_bpm():
    src = _get_source()
    assert "mcp_opendaw_set_bpm" in src


def test_pipeline_calls_arrange():
    src = _get_source()
    assert "mcp_opendaw_arrange_full_song" in src


def test_pipeline_calls_drum_pattern():
    src = _get_source()
    assert "mcp_opendaw_create_drum_pattern" in src


def test_pipeline_calls_bassline():
    src = _get_source()
    assert "mcp_opendaw_create_bassline" in src


def test_pipeline_calls_genre_effects():
    src = _get_source()
    assert "mcp_opendaw_add_genre_effects" in src


def test_pipeline_calls_auto_master():
    src = _get_source()
    assert "mcp_opendaw_auto_master" in src


def test_pipeline_calls_render():
    src = _get_source()
    assert "mcp_opendaw_render_full" in src


def test_pipeline_has_structure():
    src = _get_source()
    assert "structure: str" in src


def test_pipeline_has_genre():
    src = _get_source()
    assert "genre: str" in src


def test_pipeline_has_platform():
    src = _get_source()
    assert "platform: str" in src


def test_pipeline_has_master_style():
    src = _get_source()
    assert "master_style: str" in src


def test_pipeline_has_render_bool():
    src = _get_source()
    assert "render: bool" in src


def test_pipeline_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_pipeline_has_error_handling():
    src = _get_source()
    assert "bpm_error" in src
    assert "arrange_error" in src
    assert "drum_error" in src


def test_pipeline_has_total_notes():
    src = _get_source()
    assert "total_notes" in src


def test_pipeline_has_steps_count():
    src = _get_source()
    assert "steps_completed" in src
    assert "steps_total" in src


def test_pipeline_has_pipeline_string():
    src = _get_source()
    assert "set_bpm" in src
    assert "auto_master" in src
    assert "render" in src


def test_pipeline_has_docstring():
    src = _get_source()
    assert "single most powerful" in src or "one call" in src.lower()


def test_pipeline_has_examples():
    src = _get_source()
    assert "produce_and_master(" in src


def test_pipeline_default_params():
    src = _get_source()
    assert 'platform: str = "spotify"' in src
    assert 'master_style: str = "balanced"' in src
    assert 'genre: str = "house"' in src
    assert "bpm: float = 124" in src
