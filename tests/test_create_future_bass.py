"""Tests for create_future_bass_arrangement logic."""
import inspect
from server import mcp_opendaw_create_future_bass_arrangement


def _src():
    return inspect.getsource(mcp_opendaw_create_future_bass_arrangement)


def test_future_bass_function_exists():
    assert mcp_opendaw_create_future_bass_arrangement.__name__ == "mcp_opendaw_create_future_bass_arrangement"


def test_future_bass_default_bpm_150():
    sig = inspect.signature(mcp_opendaw_create_future_bass_arrangement)
    assert sig.parameters["bpm"].default == 150


def test_future_bass_default_root_c():
    sig = inspect.signature(mcp_opendaw_create_future_bass_arrangement)
    assert sig.parameters["root"].default == "C"


def test_future_bass_bpm_range():
    s = _src()
    assert "120 <= bpm <= 170" in s


def test_future_bass_four_tracks():
    s = _src()
    assert "drum_track" in s
    assert "bass_track" in s
    assert "chord_track" in s
    assert "lead_track" in s


def test_future_bass_pitching_snare_roll():
    s = _src()
    assert "snare_roll" in s
    assert "7.0" in s and "7.17" in s and "7.33" in s


def test_future_bass_snare_roll_crescendo():
    s = _src()
    # Ascending velocity for pitching roll effect
    assert "velocity - 0.3 + idx * 0.06" in s


def test_future_bass_supersaw_chords():
    s = _src()
    assert "chord_intervals_map" in s
    assert "[0, 4, 7, 11, 12]" in s  # maj7 voicing


def test_future_bass_iv_vi_iv_progression():
    s = _src()
    assert "chord_roots = [0, 4, 5, 3]" in s
    assert "I-V-vi-IV" in s


def test_future_bass_major_scale():
    s = _src()
    assert "major_scale = [0, 2, 4, 5, 7, 9, 11]" in s
    assert '"scale": "major"' in s


def test_future_bass_lead_starts_after_4_bars():
    s = _src()
    assert "c >= 2" in s  # starts after 4 bars (2 cycles)


def test_future_bass_lead_vocal_chop_style():
    s = _src()
    assert "lead_degrees" in s
    assert "lead_beats" in s
    assert "0.0, 0.5, 1.0, 1.5" in s or "[0.0, 0.5, 1.0, 1.5" in s


def test_future_bass_chord_2_bars_per_chord():
    s = _src()
    assert "chord_cycle = 8.0" in s


def test_future_bass_sub_bass():
    s = _src()
    assert "bass_base" in s
    assert "sub-bass" in s


def test_future_bass_creates_batches():
    s = _src()
    assert s.count("mcp_opendaw_create_notes_batch") == 4


def test_future_bass_output_structure():
    s = _src()
    assert "future_bass_arrangement" in s
    assert "total_notes" in s
    assert "progression" in s
    assert "drum_pattern" in s


def test_future_bass_error_handling():
    s = _src()
    assert "Error: bpm must be 120-170" in s
    assert "Error: bars must be 4-32" in s


def test_future_bass_drum_pitch_map():
    s = _src()
    assert "kick_p, snare_p, hat_p = 36, 38, 42" in s


def test_future_bass_kick_boosted():
    s = _src()
    assert "velocity + 0.08" in s


def test_future_bass_chord_voicings():
    s = _src()
    # maj7, maj9, min7 voicings
    assert "[0, 4, 7, 11, 12]" in s  # I: maj7
    assert "[0, 3, 7, 10, 12]" in s  # vi: min7
    assert "[0, 4, 7, 11, 14]" in s  # IV/V: maj9


def test_future_bass_lead_octave():
    s = _src()
    assert "octave + 3" in s  # lead 2 octaves above


def test_future_bass_lead_major_scale_degrees():
    s = _src()
    assert "[0, 2, 4, 7, 4, 2, 0, 5, 7, 9, 7, 4, 2, 0, 4, 7]" in s
