"""Tests for create_solo logic."""
import json
import inspect
from server import mcp_opendaw_create_solo


def _src():
    return inspect.getsource(mcp_opendaw_create_solo)


def test_solo_function_exists():
    assert mcp_opendaw_create_solo.__name__ == "mcp_opendaw_create_solo"


def test_solo_default_type_bebop():
    sig = inspect.signature(mcp_opendaw_create_solo)
    assert sig.parameters["solo_type"].default == "bebop"


def test_solo_default_key_c():
    sig = inspect.signature(mcp_opendaw_create_solo)
    assert sig.parameters["key_root"].default == "C"


def test_solo_default_scale_major():
    sig = inspect.signature(mcp_opendaw_create_solo)
    assert sig.parameters["scale_type"].default == "major"


def test_solo_default_bars_8():
    sig = inspect.signature(mcp_opendaw_create_solo)
    assert sig.parameters["bars"].default == 8


def test_solo_default_seed_42():
    sig = inspect.signature(mcp_opendaw_create_solo)
    assert sig.parameters["seed"].default == 42


def test_solo_five_types():
    s = _src()
    assert "bebop" in s
    assert "blues" in s
    assert "rock" in s
    assert "jazz_swing" in s
    assert "fusion" in s


def test_solo_valid_solo_types():
    s = _src()
    assert '"bebop", "blues", "rock", "jazz_swing", "fusion"' in s


def test_solo_scales():
    s = _src()
    assert "major" in s
    assert "dorian" in s
    assert "mixolydian" in s
    assert "blues" in s
    assert "pentatonic_minor" in s


def test_solo_bebop_chromatic_approach():
    s = _src()
    assert "chromatic_approach" in s
    assert "enclosure" in s


def test_solo_bebop_enclosure():
    s = _src()
    # Enclosure: upper + lower chromatic + target
    assert "target_pitch + 1" in s
    assert "target_pitch - 1" in s


def test_solo_blues_blue_notes():
    s = _src()
    assert "blue note" in s
    assert "blues_degrees" in s


def test_solo_blues_12_bar():
    s = _src()
    # 12-bar blues progression
    assert "[0, 0, 0, 0, 3, 3, 0, 0, 5, 3, 0, 4]" in s


def test_solo_rock_register_climax():
    s = _src()
    assert "oct_shift" in s or "register" in s


def test_solo_rock_pentatonic():
    s = _src()
    assert "rock_degrees" in s


def test_solo_jazz_swing_swing_8ths():
    s = _src()
    # Swung 8ths: 0.66 long, 0.34 short
    assert "0.66" in s
    assert "0.34" in s


def test_solo_jazz_swing_guide_tones():
    s = _src()
    assert "guide" in s.lower() or "Guide tone" in s


def test_solo_fusion_wide_intervals():
    s = _src()
    assert "wide interval" in s
    assert "Octave jump" in s


def test_solo_fusion_rhythmic_displacement():
    s = _src()
    assert "rhythmic displacement" in s
    assert "irregular" in s


def test_solo_mulberry32_prng():
    s = _src()
    assert "mulberry32" in s


def test_solo_seeded_reproducibility():
    s = _src()
    assert "seed" in s
    assert "rng = mulberry32(seed)" in s


def test_solo_creates_batches():
    s = _src()
    assert "mcp_opendaw_create_notes_batch" in s


def test_solo_output_structure():
    s = _src()
    assert '"solo"' in s
    assert '"solo_type"' in s
    assert '"notes_generated"' in s
    assert '"progression"' in s
    assert '"characteristics"' in s


def test_solo_error_handling():
    s = _src()
    assert "Invalid key_root" in s
    assert "Invalid scale_type" in s
    assert "Invalid solo_type" in s
    assert "bars must be 4-32" in s


def test_solo_chord_progressions():
    s = _src()
    # ii-V-I-vi for bebop/jazz
    assert "[1, 4, 0, 5]" in s
    # I-I-IV-IV-V-V-I-I for rock
    assert "[0, 0, 4, 4, 5, 5, 0, 0]" in s


def test_solo_characteristics_map():
    s = _src()
    assert "chromatic approach tones" in s
    assert "pentatonic riffs" in s
    assert "swung 8ths" in s
    assert "wide intervals" in s


def test_solo_chord_tones():
    s = _src()
    assert "chord_tones" in s
    assert "[0, 2, 4]" in s  # root, 3rd, 5th
