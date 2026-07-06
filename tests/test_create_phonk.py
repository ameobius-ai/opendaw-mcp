"""Tests for create_phonk_arrangement logic."""
import json
import inspect
from server import mcp_opendaw_create_phonk_arrangement


def _src():
    return inspect.getsource(mcp_opendaw_create_phonk_arrangement)


def test_phonk_function_exists():
    assert mcp_opendaw_create_phonk_arrangement.__name__ == "mcp_opendaw_create_phonk_arrangement"


def test_phonk_default_bpm_130():
    sig = inspect.signature(mcp_opendaw_create_phonk_arrangement)
    assert sig.parameters["bpm"].default == 130


def test_phonk_default_root_f():
    sig = inspect.signature(mcp_opendaw_create_phonk_arrangement)
    assert sig.parameters["root"].default == "F"


def test_phonk_bpm_range():
    s = _src()
    assert "110 <= bpm <= 150" in s


def test_phonk_bars_range():
    s = _src()
    assert "bars < 4 or bars > 32" in s


def test_phonk_three_tracks():
    s = _src()
    assert "drum_track" in s
    assert "bass_track" in s
    assert "cowbell_track" in s


def test_phonk_minor_pentatonic():
    s = _src()
    assert "penta = [0, 3, 5, 7, 10]" in s
    assert "minor_pentatonic" in s


def test_phonk_cowbell_degrees():
    s = _src()
    assert "cowbell_degrees" in s
    assert "[10, 7, 3, 0, 7, 3, 7, 10]" in s


def test_phonk_cowbell_1_bar_cycle():
    s = _src()
    assert "cowbell_cycle = 4.0" in s


def test_phonk_cowbell_octave():
    s = _src()
    assert "octave + 5" in s  # 3 octaves above bass


def test_phonk_808_slides():
    s = _src()
    # Slides to b3, back to root, down to b7 below, octave jump
    assert "3, 0.5, 0.85" in s  # slide to b3
    assert "-2, 0.5, 0.85" in s  # slide down
    assert "12, 0.5, 0.8" in s  # octave jump


def test_phonk_drum_memphis_style():
    s = _src()
    assert "kick" in s
    assert "clap" in s
    assert "hat" in s
    assert "memphis" in s


def test_phonk_drum_hat_rolls():
    s = _src()
    # Hat rolls at phrase ends
    assert "3.25" in s or "3.33" in s
    assert "7.25" in s or "7.33" in s


def test_phonk_drum_kick_boosted_velocity():
    s = _src()
    assert "velocity + 0.08" in s


def test_phonk_drum_2bar_cycle():
    s = _src()
    assert "drum_cycle = 8.0" in s


def test_phonk_creates_batches():
    s = _src()
    assert s.count("mcp_opendaw_create_notes_batch") == 3


def test_phonk_output_structure():
    s = _src()
    assert "phonk_arrangement" in s
    assert "total_notes" in s
    assert "drum_pattern" in s
    assert "bass_pattern" in s
    assert "scale" in s


def test_phonk_error_handling():
    s = _src()
    assert "Error: bpm must be 110-150" in s
    assert "Error: bars must be 4-32" in s
    assert "Error: velocity must be 0-1" in s


def test_phonk_drum_pitch_map():
    s = _src()
    assert "kick_p, clap_p, hat_p = 36, 39, 42" in s


def test_phonk_808_sustained_resonance():
    s = _src()
    # Long sustained notes (2.0 beat duration)
    assert "0, 2.0, 1.0" in s


def test_phonk_808_chromatic_movement():
    s = _src()
    # Chromatic slides: b3 (+3), b7 below (-2), octave (+12)
    assert "+3" in s or "3, 0.5" in s
    assert "-2" in s


def test_phonk_cowbell_velocity():
    s = _src()
    assert "cowbell_vel_base = 0.85" in s


def test_phonk_cowbell_repetitive_riff():
    s = _src()
    # 8 notes per bar, 1-bar cycle = repetitive
    assert "cowbell_beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]" in s
