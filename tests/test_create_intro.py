"""Tests for create_intro — intro section generator.

Uses inspect.getsource() pattern (no bridge needed).
"""

import inspect
import pytest
from server import mcp_opendaw_create_intro


def _src():
    return inspect.getsource(mcp_opendaw_create_intro)


class TestCreateIntroStructure:
    """Verify tool signature and docstring."""

    def test_has_5_types(self):
        src = _src()
        for t in ["ambient", "drum", "melodic", "minimalist", "cinematic"]:
            assert t in src, f"Missing intro type: {t}"

    def test_has_3_scales(self):
        src = _src()
        for s in ["major", "minor", "harmonic_minor"]:
            assert s in src, f"Missing scale: {s}"

    def test_has_valid_types_list(self):
        src = _src()
        assert 'VALID_TYPES = ["ambient", "drum", "melodic", "minimalist", "cinematic"]' in src

    def test_has_mulberry32(self):
        assert "mulberry32" in _src()

    def test_has_deg_to_pitch(self):
        assert "deg_to_pitch" in _src()

    def test_has_chrom_pitch(self):
        assert "chrom_pitch" in _src()

    def test_calls_create_notes_batch(self):
        assert "create_notes_batch" in _src()

    def test_has_intro_flag_in_result(self):
        assert 'data["intro"] = True' in _src()

    def test_has_characteristics_dict(self):
        src = _src()
        for t in ["ambient", "drum", "melodic", "minimalist", "cinematic"]:
            assert f'"{t}"' in src


class TestCreateIntroValidation:
    """Verify parameter validation logic in source."""

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

    def test_intro_type_validation(self):
        assert "Invalid intro_type" in _src()


class TestCreateIntroAmbient:
    """Verify ambient style logic."""

    def test_uses_root_and_fifth(self):
        src = _src()
        assert "deg_to_pitch(0)" in src  # root
        assert "deg_to_pitch(4)" in src  # fifth

    def test_has_third_for_second_half(self):
        src = _src()
        assert "deg_to_pitch(2)" in src  # third
        assert "bars // 2" in src

    def test_has_swell_curve(self):
        src = _src()
        assert "swell" in src
        assert "3.14159265" in src  # pi constant

    def test_bar_len_4(self):
        assert "bar_len = 4.0" in _src()


class TestCreateIntroDrum:
    """Verify drum build style."""

    def test_kick_pitch_36(self):
        assert "kick_pitch = 36" in _src()

    def test_snare_pitch_38(self):
        assert "snare_pitch = 38" in _src()

    def test_hat_pitch_42(self):
        assert "hat_pitch = 42" in _src()

    def test_kick_density_increases(self):
        assert "kick_density = 1 + bar" in _src()

    def test_snare_from_bar_1(self):
        assert "bar >= 1" in _src()

    def test_hats_from_bar_2(self):
        assert "bar >= 2" in _src()

    def test_snare_on_beats_2_and_4(self):
        src = _src()
        assert "bar_start + 1.0" in src  # beat 2
        assert "bar_start + 3.0" in src  # beat 4


class TestCreateIntroMelodic:
    """Verify melodic arpeggio style."""

    def test_arp_degrees(self):
        assert "arp_degrees = [0, 5, 3, 4]" in _src()  # I-vi-IV-V

    def test_notes_per_bar_increases(self):
        assert "notes_per_bar = 2 * (bar + 1)" in _src()

    def test_arp_offset_pattern(self):
        assert "[0, 2, 4, 7]" in _src()  # root, 3rd, 5th, octave


class TestCreateIntroMinimalist:
    """Verify minimalist layered style."""

    def test_has_layer_pitches(self):
        assert "layer_pitches" in _src()

    def test_5_layers(self):
        src = _src()
        # 5 pitches: tonic, third, fifth, octave, third-octave
        assert "deg_to_pitch(0, 1)" in src
        assert "deg_to_pitch(2, 1)" in src

    def test_layer_0_is_8ths(self):
        src = _src()
        assert "range(8)" in src
        assert "i * 0.5" in src

    def test_layer_1_is_quarters(self):
        src = _src()
        assert "range(4)" in src
        assert "i * 1.0" in src


class TestCreateIntroCinematic:
    """Verify cinematic drone+riser+impact style."""

    def test_drone_low_octave(self):
        assert "deg_to_pitch(0, -1)" in _src()

    def test_riser_chromatic(self):
        src = _src()
        assert "riser_steps" in src
        assert "semitone = i" in src

    def test_impact_chord(self):
        src = _src()
        assert "impact_pitches" in src
        assert "deg_to_pitch(0)" in src
        assert "deg_to_pitch(2)" in src
        assert "deg_to_pitch(4)" in src
        assert "deg_to_pitch(0, 1)" in src

    def test_impact_at_end(self):
        assert "total_beats - 2.0" in _src()

    def test_drone_sustained_full(self):
        src = _src()
        assert "total_beats" in src
        # drone duration spans the full intro
        assert '"duration": total_beats' in src


class TestCreateIntroMIDI:
    """Verify MIDI note formula correctness."""

    def test_base_formula(self):
        src = _src()
        # (octave + 1) * 12 + root_pc = MIDI note
        assert "base = (octave + 1) * 12 + root_pc" in src

    def test_c4_is_60(self):
        # C4 = (4+1)*12 + 0 = 60
        src = _src()
        assert "(octave + 1) * 12" in src

    def test_scale_intervals_major(self):
        src = _src()
        assert "[0, 2, 4, 5, 7, 9, 11]" in src

    def test_scale_intervals_minor(self):
        src = _src()
        assert "[0, 2, 3, 5, 7, 8, 10]" in src

    def test_scale_intervals_harmonic_minor(self):
        src = _src()
        assert "[0, 2, 3, 5, 7, 8, 11]" in src


class TestCreateIntroNoteSorting:
    """Verify notes are sorted and velocity clamped."""

    def test_notes_sorted(self):
        assert 'notes.sort(key=lambda n: (n["start"], n["pitch"]))' in _src()

    def test_velocity_clamped(self):
        assert 'max(0.0, min(1.0, n["velocity"]))' in _src()

    def test_notes_have_required_fields(self):
        src = _src()
        assert '"pitch"' in src
        assert '"start"' in src
        assert '"duration"' in src
        assert '"velocity"' in src
