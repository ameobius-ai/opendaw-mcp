"""Unit tests for create_breakbeat_arrangement — breakbeat/big beat genre arrangement."""
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
    if not src or "breakbeat_arrangement" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_breakbeat_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_breakbeat_arrangement" in src


def test_breakbeat_has_key_root():
    src = _get_source()
    assert "key_root: str = " in src
    assert '"E"' in src  # default E minor


def test_breakbeat_has_bpm():
    src = _get_source()
    assert "bpm: int = 130" in src


def test_breakbeat_has_4_tracks():
    src = _get_source()
    assert "track_index + 1" in src
    assert "track_index + 2" in src
    assert "track_index + 3" in src


def test_breakbeat_has_kick():
    src = _get_source()
    assert "KICK = 36" in src


def test_breakbeat_has_snare():
    src = _get_source()
    assert "SNARE = 38" in src


def test_breakbeat_has_ghost_snare():
    src = _get_source()
    assert "GHOST_SNARE = 37" in src


def test_breakbeat_has_amen_style():
    src = _get_source()
    assert "Amen" in src or "amen" in src


def test_breakbeat_has_rolling_bass():
    src = _get_source()
    assert "rolling" in src.lower()
    assert "bass_pattern" in src


def test_breakbeat_has_acid_riff():
    src = _get_source()
    assert "acid" in src.lower()
    assert "lead_pattern" in src


def test_breakbeat_has_stabs():
    src = _get_source()
    assert "stab" in src.lower()


def test_breakbeat_has_minor_scale():
    src = _get_source()
    assert "minor_scale" in src


def test_breakbeat_has_create_notes_batch():
    src = _get_source()
    assert "mcp_opendaw_create_notes_batch" in src


def test_breakbeat_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_breakbeat_has_docstring():
    src = _get_source()
    assert "breakbeat" in src.lower()
    assert "Prodigy" in src or "Chemical Brothers" in src


def test_breakbeat_has_references():
    src = _get_source()
    assert "references" in src
    assert "Fatboy Slim" in src


def test_breakbeat_has_next_steps():
    src = _get_source()
    assert "next_steps" in src


def test_breakbeat_has_characteristics():
    src = _get_source()
    assert "characteristics" in src


def test_breakbeat_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_breakbeat_default_velocity():
    src = _get_source()
    assert "velocity: float = 0.85" in src
