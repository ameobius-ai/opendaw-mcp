"""Unit tests for create_kpop_arrangement — K-pop genre arrangement."""
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
    if not src or "kpop_arrangement" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_kpop_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_kpop_arrangement" in src


def test_kpop_has_key_root():
    src = _get_source()
    assert "key_root: str = " in src
    assert '"C"' in src  # default C major


def test_kpop_has_bpm():
    src = _get_source()
    assert "bpm: int = 128" in src


def test_kpop_has_4_tracks():
    src = _get_source()
    assert "track_index + 1" in src
    assert "track_index + 2" in src
    assert "track_index + 3" in src


def test_kpop_has_kick():
    src = _get_source()
    assert "KICK = 36" in src


def test_kpop_has_snare():
    src = _get_source()
    assert "SNARE = 38" in src


def test_kpop_has_clap():
    src = _get_source()
    assert "CLAP = 39" in src  # K-pop layers claps


def test_kpop_has_4_on_floor():
    src = _get_source()
    assert "4-on-floor" in src.lower() or "4_on_floor" in src.lower()


def test_kpop_has_pop_progression():
    src = _get_source()
    assert "I-V-vi-IV" in src
    assert "prog_degrees" in src


def test_kpop_has_wide_intervals():
    src = _get_source()
    assert "wide interval" in src.lower() or "wide" in src.lower()


def test_kpop_has_chord_stabs():
    src = _get_source()
    assert "stab" in src.lower()


def test_kpop_has_major_scale():
    src = _get_source()
    assert "major_scale" in src


def test_kpop_has_create_notes_batch():
    src = _get_source()
    assert "mcp_opendaw_create_notes_batch" in src


def test_kpop_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_kpop_has_docstring():
    src = _get_source()
    assert "k-pop" in src.lower() or "K-pop" in src


def test_kpop_has_references():
    src = _get_source()
    assert "references" in src
    assert "BTS" in src or "Blackpink" in src


def test_kpop_has_next_steps():
    src = _get_source()
    assert "next_steps" in src


def test_kpop_has_characteristics():
    src = _get_source()
    assert "characteristics" in src


def test_kpop_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_kpop_default_velocity():
    src = _get_source()
    assert "velocity: float = 0.8" in src


def test_kpop_has_call_response():
    src = _get_source()
    assert "call-response" in src or "call_response" in src
