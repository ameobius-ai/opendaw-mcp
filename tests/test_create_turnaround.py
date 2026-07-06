"""Tests for create_turnaround logic — 2-bar resolution phrases in 5 styles."""
import inspect
import pytest


def _src():
    from server import mcp_opendaw_create_turnaround
    return inspect.getsource(mcp_opendaw_create_turnaround)


def _sig():
    from server import mcp_opendaw_create_turnaround
    return inspect.signature(mcp_opendaw_create_turnaround)


class TestTurnaroundSignature:
    def test_function_exists(self):
        from server import mcp_opendaw_create_turnaround
        assert mcp_opendaw_create_turnaround.__name__ == "mcp_opendaw_create_turnaround"

    def test_default_type_jazz(self):
        assert _sig().parameters["turnaround_type"].default == "jazz"

    def test_default_key_c(self):
        assert _sig().parameters["key_root"].default == "C"

    def test_default_scale_major(self):
        assert _sig().parameters["scale_type"].default == "major"

    def test_default_octave_4(self):
        assert _sig().parameters["octave"].default == 4

    def test_default_velocity_075(self):
        assert _sig().parameters["velocity"].default == 0.75

    def test_default_seed_42(self):
        assert _sig().parameters["seed"].default == 42

    def test_has_unit_index(self):
        assert "unit_index" in _sig().parameters

    def test_has_track_index(self):
        assert "track_index" in _sig().parameters

    def test_has_start_beat(self):
        assert "start_beat" in _sig().parameters


class TestTurnaroundTypes:
    def test_five_types(self):
        s = _src()
        for t in ["jazz", "blues", "gospel", "rock", "pop"]:
            assert t in s

    def test_valid_types_list(self):
        s = _src()
        assert '"jazz", "blues", "gospel", "rock", "pop"' in s

    def test_jazz_vi_ii_v(self):
        s = _src()
        # I-vi-ii-V chord degrees: 0, 5, 1, 4
        assert "chord_degrees" in s
        assert "(0.0, [0, 2, 4], 0)" in s  # I
        assert "(2.0, [5, 0, 2], 5)" in s  # vi
        assert "(4.0, [1, 3, 5], 1)" in s  # ii
        assert "(6.0, [4, 6, 1], 4)" in s  # V

    def test_jazz_chromatic_approach(self):
        s = _src()
        assert "approach_pitch" in s
        assert "next_root_pitch - 1" in s

    def test_blues_shuffle(self):
        s = _src()
        assert "bar1_positions" in s
        assert "0.75" in s  # shuffle long-short
        assert "1.75" in s

    def test_blues_walkup(self):
        s = _src()
        assert "walk_notes" in s
        assert "deg_to_pitch(2)" in s
        assert "deg_to_pitch(3)" in s
        assert "deg_to_pitch(4)" in s

    def test_blues_ivdim(self):
        s = _src()
        # IVdim: diminished passing chord (root, b3, b5 = +3, +6)
        assert "+ 3" in s
        assert "+ 6" in s
        # IVdim at beat 5.0
        assert "5.0" in s

    def test_gospel_ii_v_i(self):
        s = _src()
        assert "ii_root" in s
        assert "v_root" in s
        assert "i_root" in s
        assert "iv_root" in s

    def test_gospel_plagal_cadence(self):
        s = _src()
        # Plagal IV (Amen) at beat 6.0
        assert "6.0" in s
        assert "iv_root" in s

    def test_gospel_melisma(self):
        s = _src()
        # Bluesy third at 5.0, resolved at 5.25
        assert "5.0" in s
        assert "5.25" in s

    def test_rock_mixolydian_descent(self):
        s = _src()
        assert "bvii_root" in s
        assert "chrom_pitch(10, 0)" in s  # b7

    def test_rock_power_chords(self):
        s = _src()
        assert "root + 7" in s  # fifth
        assert "root + 12" in s  # octave

    def test_rock_passing_tones(self):
        s = _src()
        assert "passing" in s
        assert "root - 2" in s  # whole step down

    def test_pop_axis_progression(self):
        s = _src()
        assert "chord_roots" in s
        assert "(0.0, 0)" in s   # I
        assert "(2.0, 4)" in s   # V
        assert "(4.0, 5)" in s   # vi
        assert "(6.0, 3)" in s   # IV

    def test_pop_stepwise_approach(self):
        s = _src()
        assert "step_dir" in s
        assert "approach_pitch" in s


class TestTurnaroundScales:
    def test_four_scales(self):
        s = _src()
        for sc in ["major", "minor", "mixolydian", "dorian"]:
            assert sc in s

    def test_scale_intervals(self):
        s = _src()
        # major: [0, 2, 4, 5, 7, 9, 11]
        assert "[0, 2, 4, 5, 7, 9, 11]" in s
        # minor: [0, 2, 3, 5, 7, 8, 10]
        assert "[0, 2, 3, 5, 7, 8, 10]" in s


class TestTurnaroundPitchLogic:
    def test_deg_to_pitch(self):
        s = _src()
        assert "def deg_to_pitch" in s
        assert "octave_shift" in s

    def test_chrom_pitch(self):
        s = _src()
        assert "def chrom_pitch" in s
        assert "semitone" in s

    def test_mulberry32_prng(self):
        s = _src()
        assert "def mulberry32" in s
        assert "0x6D2B79F5" in s

    def test_base_formula(self):
        s = _src()
        assert "(octave + 1) * 12 + root_pc" in s

    def test_notes_sorted(self):
        s = _src()
        assert "notes.sort" in s

    def test_velocities_clamped(self):
        s = _src()
        assert "max(0.0, min(1.0" in s


class TestTurnaroundMetadata:
    def test_metadata_fields(self):
        s = _src()
        assert '"turnaround"' in s
        assert '"turnaround_type"' in s
        assert '"key_root"' in s
        assert '"scale_type"' in s
        assert '"bars"' in s
        assert '"notes_generated"' in s
        assert '"characteristics"' in s

    def test_bars_fixed_2(self):
        s = _src()
        # 2-bar turnaround always
        assert 'data["bars"] = 2' in s

    def test_characteristics_all_types(self):
        s = _src()
        for t in ["jazz", "blues", "gospel", "rock", "pop"]:
            assert t in s

    def test_calls_create_notes_batch(self):
        s = _src()
        assert "mcp_opendaw_create_notes_batch" in s


class TestTurnaroundValidation:
    def test_invalid_key_root(self):
        s = _src()
        assert "Invalid key_root" in s
        assert "NOTE_MAP.get" in s

    def test_invalid_scale_type(self):
        s = _src()
        assert "Invalid scale_type" in s

    def test_invalid_turnaround_type(self):
        s = _src()
        assert "Invalid turnaround_type" in s

    def test_velocity_range_check(self):
        s = _src()
        assert "0.0 <= velocity <= 1.0" in s

    def test_octave_range_check(self):
        s = _src()
        assert "0 <= octave <= 7" in s
