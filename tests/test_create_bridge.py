"""Tests for create_bridge — bridge section generator.

Uses inspect.getsource() pattern (no bridge needed).
"""

import inspect
from server import mcp_opendaw_create_bridge


def _src():
    return inspect.getsource(mcp_opendaw_create_bridge)


class TestCreateBridgeStructure:

    def test_has_5_types(self):
        src = _src()
        for t in ["breakdown", "modulation", "solo", "atmospheric", "surprise"]:
            assert t in src, f"Missing bridge type: {t}"

    def test_has_3_scales(self):
        src = _src()
        for s in ["major", "minor", "harmonic_minor"]:
            assert s in src, f"Missing scale: {s}"

    def test_has_valid_types_list(self):
        assert 'VALID_TYPES = ["breakdown", "modulation", "solo", "atmospheric", "surprise"]' in _src()

    def test_has_mulberry32(self):
        assert "mulberry32" in _src()

    def test_has_deg_to_pitch(self):
        assert "deg_to_pitch" in _src()

    def test_calls_create_notes_batch(self):
        assert "create_notes_batch" in _src()

    def test_has_bridge_flag(self):
        assert 'data["bridge"] = True' in _src()

    def test_has_characteristics_dict(self):
        src = _src()
        for t in ["breakdown", "modulation", "solo", "atmospheric", "surprise"]:
            assert f'"{t}"' in src


class TestCreateBridgeValidation:

    def test_bars_validation(self):
        assert "bars must be 2-8" in _src()

    def test_velocity_validation(self):
        assert "velocity must be 0-1" in _src()

    def test_octave_validation(self):
        assert "octave must be 0-7" in _src()

    def test_bridge_type_validation(self):
        assert "Invalid bridge_type" in _src()


class TestCreateBridgeBreakdown:

    def test_bass_low_octave(self):
        assert "deg_to_pitch(0, -1)" in _src()

    def test_bass_on_beats_1_and_3(self):
        src = _src()
        assert "bar_start" in src
        assert "bar_start + 2.0" in src  # beat 3

    def test_occasional_stabs(self):
        assert "stab_deg" in _src()

    def test_intentionally_quiet(self):
        assert "velocity * 0.5" in _src()


class TestCreateBridgeModulation:

    def test_minor_third_shift(self):
        assert "shift = 3" in _src()

    def test_half_bar_split(self):
        assert "bars // 2" in _src()

    def test_current_base(self):
        assert "current_base" in _src()


class TestCreateBridgeSolo:

    def test_i_iv_v_i_cycle(self):
        assert "chord_deg = bar % 4" in _src()

    def test_dense_8th_notes(self):
        assert "range(8)" in _src()
        assert "i * 0.5" in _src()

    def test_occasional_skips(self):
        assert "next(rng) > 0.7" in _src()


class TestCreateBridgeAtmospheric:

    def test_chromatic_not_diatonic(self):
        assert "int(next(rng) * 12)" in _src()

    def test_sustained_tones(self):
        assert "dur = 2.0" in _src()

    def test_2_to_3_tones(self):
        assert "2 + int(next(rng) * 2)" in _src()


class TestCreateBridgeSurprise:

    def test_irregular_positions(self):
        assert "burst_positions" in _src()
        assert "0.75" in _src()  # odd position

    def test_staccato_duration(self):
        assert '"duration": 0.25' in _src()

    def test_low_bass_anchor(self):
        assert "deg_to_pitch(0, -1)" in _src()


class TestCreateBridgeMIDI:

    def test_base_formula(self):
        assert "base = (octave + 1) * 12 + root_pc" in _src()

    def test_scale_intervals(self):
        src = _src()
        assert "[0, 2, 4, 5, 7, 9, 11]" in src
        assert "[0, 2, 3, 5, 7, 8, 10]" in src


class TestCreateBridgeSorting:

    def test_notes_sorted(self):
        assert 'notes.sort(key=lambda n: (n["start"], n["pitch"]))' in _src()

    def test_velocity_clamped(self):
        assert 'max(0.0, min(1.0, n["velocity"]))' in _src()
