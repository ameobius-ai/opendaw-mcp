"""Unit tests for create_industrial_arrangement — industrial genre arrangement."""
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
    if not src or "industrial_arrangement" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_industrial_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_industrial_arrangement" in src


def test_industrial_has_key_root():
    src = _get_source()
    assert "key_root: str = " in src
    assert '"D"' in src  # default D minor


def test_industrial_has_bpm():
    src = _get_source()
    assert "bpm: int = 135" in src


def test_industrial_has_bars():
    src = _get_source()
    assert "bars: int = 16" in src


def test_industrial_has_4_tracks():
    src = _get_source()
    assert "track_index" in src
    assert "track_index + 1" in src
    assert "track_index + 2" in src
    assert "track_index + 3" in src


def test_industrial_has_kick():
    src = _get_source()
    assert "KICK = 36" in src or "KICK = 36" in src


def test_industrial_has_metallic_percussion():
    src = _get_source()
    assert "SNARE = 38" in src
    assert "RIDE = 59" in src  # metallic shimmer


def test_industrial_has_4_on_floor():
    src = _get_source()
    assert "4-on-floor" in src.lower() or "4_on_floor" in src.lower()


def test_industrial_has_dissonant_stabs():
    src = _get_source()
    assert "tritone" in src.lower()
    assert "b5" in src or "interval" in src


def test_industrial_has_drone():
    src = _get_source()
    assert "drone" in src.lower()
    assert "DRONE" in src


def test_industrial_has_minor_scale():
    src = _get_source()
    assert "minor_scale" in src


def test_industrial_has_chromatic_bass():
    src = _get_source()
    assert "chromatic" in src.lower()


def test_industrial_has_create_notes_batch():
    src = _get_source()
    assert "mcp_opendaw_create_notes_batch" in src


def test_industrial_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_industrial_has_docstring():
    src = _get_source()
    assert "industrial" in src.lower()
    assert "NIN" in src or "Nine Inch Nails" in src


def test_industrial_has_references():
    src = _get_source()
    assert "references" in src
    assert "Ministry" in src or "Skinny Puppy" in src


def test_industrial_has_next_steps():
    src = _get_source()
    assert "next_steps" in src


def test_industrial_has_characteristics():
    src = _get_source()
    assert "characteristics" in src


def test_industrial_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_industrial_default_velocity():
    src = _get_source()
    assert "velocity: float = 0.85" in src
