"""Unit tests for create_jpop_arrangement — J-pop genre arrangement."""
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
    if not src or "jpop_arrangement" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_jpop_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_jpop_arrangement" in src


def test_jpop_has_key_root():
    src = _get_source()
    assert 'key_root: str = "C"' in src


def test_jpop_has_bpm():
    src = _get_source()
    assert "bpm: int = 140" in src


def test_jpop_has_4_tracks():
    src = _get_source()
    assert "track_index + 1" in src
    assert "track_index + 2" in src
    assert "track_index + 3" in src


def test_jpop_has_kick():
    src = _get_source()
    assert "KICK = 36" in src


def test_jpop_has_snare():
    src = _get_source()
    assert "SNARE = 38" in src


def test_jpop_has_crash():
    src = _get_source()
    assert "CRASH = 49" in src


def test_jpop_has_double_time_hats():
    src = _get_source()
    assert "double-time" in src.lower() or "32" in src


def test_jpop_has_modal_mixture():
    src = _get_source()
    assert "modal mixture" in src.lower() or "minor iv" in src.lower()


def test_jpop_has_prog_minor():
    src = _get_source()
    assert "prog_minor" in src


def test_jpop_has_iv_v_vi_iv():
    src = _get_source()
    assert "IV-V-vi-iv" in src or "3, 4, 5, 3" in src


def test_jpop_has_octave_jumping_bass():
    src = _get_source()
    assert "octave" in src.lower()
    assert "16th" in src.lower()


def test_jpop_has_fast_runs():
    src = _get_source()
    assert "fast run" in src.lower() or "fast 16th" in src.lower()


def test_jpop_has_arpeggiated_picks():
    src = _get_source()
    assert "arpeggiated" in src.lower()


def test_jpop_has_major_scale():
    src = _get_source()
    assert "major_scale" in src


def test_jpop_has_create_notes_batch():
    src = _get_source()
    assert "mcp_opendaw_create_notes_batch" in src


def test_jpop_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_jpop_has_docstring():
    src = _get_source()
    assert "j-pop" in src.lower() or "J-pop" in src


def test_jpop_has_references():
    src = _get_source()
    assert "references" in src
    assert "One Ok Rock" in src or "YOASOBI" in src or "BABYMETAL" in src


def test_jpop_has_next_steps():
    src = _get_source()
    assert "next_steps" in src


def test_jpop_has_characteristics():
    src = _get_source()
    assert "characteristics" in src


def test_jpop_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_jpop_default_velocity():
    src = _get_source()
    assert "velocity: float = 0.78" in src
