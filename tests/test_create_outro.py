"""Tests for create_outro — outro section generator.

Uses inspect.getsource() pattern (no bridge needed).
"""

import inspect
from server import mcp_opendaw_create_outro


def _src():
    return inspect.getsource(mcp_opendaw_create_outro)


class TestCreateOutroStructure:
    """Verify tool signature and docstring."""

    def test_has_5_types(self):
        src = _src()
        for t in ["fade", "ritardando", "recap", "pedal", "cadential"]:
            assert t in src, f"Missing outro type: {t}"

    def test_has_3_scales(self):
        src = _src()
        for s in ["major", "minor", "harmonic_minor"]:
            assert s in src, f"Missing scale: {s}"

    def test_has_valid_types_list(self):
        assert 'VALID_TYPES = ["fade", "ritardando", "recap", "pedal", "cadential"]' in _src()

    def test_has_mulberry32(self):
        assert "mulberry32" in _src()

    def test_has_deg_to_pitch(self):
        assert "deg_to_pitch" in _src()

    def test_calls_create_notes_batch(self):
        assert "create_notes_batch" in _src()

    def test_has_outro_flag_in_result(self):
        assert 'data["outro"] = True' in _src()

    def test_has_characteristics_dict(self):
        src = _src()
        for t in ["fade", "ritardando", "recap", "pedal", "cadential"]:
            assert f'"{t}"' in src


class TestCreateOutroValidation:
    """Verify parameter validation logic."""

    def test_bars_validation(self):
        assert "bars must be 2-8" in _src()

    def test_velocity_validation(self):
        assert "velocity must be 0-1" in _src()

    def test_octave_validation(self):
        assert "octave must be 0-7" in _src()

    def test_key_root_validation(self):
        assert "Invalid key_root" in _src()

    def test_scale_type_validation(self):
        assert "Invalid scale_type" in _src()

    def test_outro_type_validation(self):
        assert "Invalid outro_type" in _src()


class TestCreateOutroFade:
    """Verify fade style logic."""

    def test_uses_fade_factor(self):
        assert "fade_factor" in _src()

    def test_texture_thins(self):
        src = _src()
        # Fifth removed in last bar
        assert "bar < bars - 1" in src
        # Third removed in last 2 bars
        assert "bar < bars - 2" in src

    def test_decreasing_melody_density(self):
        assert "melody_notes = max(1, bars - bar)" in _src()


class TestCreateOutroRitardando:
    """Verify ritardando style logic."""

    def test_duration_multiplier(self):
        assert "dur_mult = 1.0 + bar * 0.5" in _src()

    def test_fewer_notes_per_bar(self):
        assert "notes_per_bar = max(1, 4 - bar)" in _src()

    def test_final_fermata_note(self):
        src = _src()
        assert "final_pitch" in src
        assert "bar_len * 1.5" in src  # longer than one bar


class TestCreateOutroRecap:
    """Verify recap style logic."""

    def test_descending_swell(self):
        src = _src()
        assert "1.0 - 0.5 * progress" in src

    def test_root_and_fifth(self):
        src = _src()
        assert "deg_to_pitch(0)" in src
        assert "deg_to_pitch(4)" in src

    def test_descending_melodic_line(self):
        assert "ns - 1 - i - bar" in _src()


class TestCreateOutroPedal:
    """Verify pedal style logic."""

    def test_v_chord_before_resolution(self):
        src = _src()
        assert "v_root = deg_to_pitch(4)" in src
        assert "v_third = deg_to_pitch(6)" in src
        assert "v_fifth = deg_to_pitch(8)" in src

    def test_i_chord_resolution(self):
        src = _src()
        assert "root_pitch" in src
        assert "third_pitch" in src
        assert "fifth_pitch" in src

    def test_octave_for_finality(self):
        assert "deg_to_pitch(0, 1)" in _src()

    def test_crescendo_to_final(self):
        assert "0.6 + 0.4 * bar" in _src()


class TestCreateOutroCadential:
    """Verify cadential style logic."""

    def test_running_notes(self):
        src = _src()
        assert "run_steps" in src
        assert "run_beats" in src

    def test_fermata_chord(self):
        src = _src()
        assert "fermata_start" in src
        assert "chord_pitches" in src

    def test_crescendo_in_run(self):
        assert "0.5 + 0.4 * i / run_steps" in _src()

    def test_fermata_at_last_bar(self):
        assert "total_beats - bar_len" in _src()


class TestCreateOutroMIDI:
    """Verify MIDI note formula."""

    def test_base_formula(self):
        assert "base = (octave + 1) * 12 + root_pc" in _src()

    def test_scale_intervals(self):
        src = _src()
        assert "[0, 2, 4, 5, 7, 9, 11]" in src
        assert "[0, 2, 3, 5, 7, 8, 10]" in src
        assert "[0, 2, 3, 5, 7, 8, 11]" in src


class TestCreateOutroSorting:
    """Verify notes are sorted and velocity clamped."""

    def test_notes_sorted(self):
        assert 'notes.sort(key=lambda n: (n["start"], n["pitch"]))' in _src()

    def test_velocity_clamped(self):
        assert 'max(0.0, min(1.0, n["velocity"]))' in _src()
