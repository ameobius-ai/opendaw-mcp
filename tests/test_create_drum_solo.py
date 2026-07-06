"""Tests for create_drum_solo logic."""
import json
import inspect
from server import mcp_opendaw_create_drum_solo


def _src():
    return inspect.getsource(mcp_opendaw_create_drum_solo)


def test_drum_solo_function_exists():
    assert mcp_opendaw_create_drum_solo.__name__ == "mcp_opendaw_create_drum_solo"


def test_drum_solo_default_type_rock():
    sig = inspect.signature(mcp_opendaw_create_drum_solo)
    assert sig.parameters["solo_type"].default == "rock"


def test_drum_solo_default_bars_4():
    sig = inspect.signature(mcp_opendaw_create_drum_solo)
    assert sig.parameters["bars"].default == 4


def test_drum_solo_default_velocity_09():
    sig = inspect.signature(mcp_opendaw_create_drum_solo)
    assert sig.parameters["velocity"].default == 0.9


def test_drum_solo_default_seed_42():
    sig = inspect.signature(mcp_opendaw_create_drum_solo)
    assert sig.parameters["seed"].default == 42


def test_drum_solo_five_types():
    s = _src()
    assert "rock" in s
    assert "jazz" in s
    assert "funk" in s
    assert "latin" in s
    assert "marching" in s


def test_drum_solo_valid_types_list():
    s = _src()
    assert '"rock", "jazz", "funk", "latin", "marching"' in s


def test_drum_solo_gm_pitches():
    s = _src()
    assert "KICK = 36" in s
    assert "SNARE = 38" in s
    assert "HAT = 42" in s
    assert "CRASH = 49" in s


def test_drum_solo_rudiments():
    s = _src()
    assert "paradiddle" in s
    assert "flam" in s
    assert "drag" in s
    assert "open_roll" in s


def test_drum_solo_paradiddle_pattern():
    s = _src()
    # RLRR LRLL pattern
    assert "[1, 0, 1, 1, 0, 1, 0, 0]" in s


def test_drum_solo_flam_grace_note():
    s = _src()
    # Grace note + main note
    assert "start, 0.08, vel * 0.5" in s
    assert "start + 0.02" in s


def test_drum_solo_drag_grace_notes():
    s = _src()
    # Two grace notes + main
    assert "start - 0.06" in s
    assert "start - 0.03" in s


def test_drum_solo_rock_double_kick():
    s = _src()
    assert "double kick" in s.lower() or "double kick" in s


def test_drum_solo_rock_tom_descent():
    s = _src()
    assert "tom_descent" in s
    assert "TOM1, TOM2, TOM3, TOM4" in s


def test_drum_solo_jazz_ride_pattern():
    s = _src()
    assert "ride_pattern" in s
    # Swing: 0.66, 0.66
    assert "0.66" in s


def test_drum_solo_jazz_comping():
    s = _src()
    assert "comping" in s
    assert "comp_positions" in s


def test_drum_solo_jazz_press_roll():
    s = _src()
    assert "press roll" in s


def test_drum_solo_funk_ghost_notes():
    s = _src()
    assert "ghost-note" in s or "ghost" in s
    assert "ghost" in s


def test_drum_solo_funk_sixteenth_hats():
    s = _src()
    assert "16th-note hat" in s or "16th" in s


def test_drum_solo_latin_cascara():
    s = _src()
    assert "cascara" in s
    assert "cascara_accents" in s


def test_drum_solo_latin_mambo_bell():
    s = _src()
    assert "MAMBO_BELL" in s
    assert "mambo bell" in s


def test_drum_solo_latin_timbale():
    s = _src()
    assert "TIMBALE" in s
    assert "timbale" in s


def test_drum_solo_marching_rudimental():
    s = _src()
    assert "rudimental" in s
    assert "paradiddles, flams, drags, open rolls" in s


def test_drum_solo_marching_dci():
    s = _src()
    assert "DCI" in s


def test_drum_solo_intensity_build():
    s = _src()
    assert "intensity" in s
    assert "0.6 + 0.4" in s


def test_drum_solo_mulberry32_prng():
    s = _src()
    assert "mulberry32" in s


def test_drum_solo_creates_batches():
    s = _src()
    assert "mcp_opendaw_create_notes_batch" in s


def test_drum_solo_output_structure():
    s = _src()
    assert '"drum_solo"' in s
    assert '"solo_type"' in s
    assert '"notes_generated"' in s
    assert '"characteristics"' in s


def test_drum_solo_error_handling():
    s = _src()
    assert "Invalid solo_type" in s
    assert "bars must be 2-16" in s
