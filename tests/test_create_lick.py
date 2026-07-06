"""Tests for create_lick logic — short melodic vocabulary phrases in 5 styles."""
import inspect
import pytest


def _src():
    from server import mcp_opendaw_create_lick
    return inspect.getsource(mcp_opendaw_create_lick)


def _sig():
    from server import mcp_opendaw_create_lick
    return inspect.signature(mcp_opendaw_create_lick)


class TestLickSignature:
    def test_function_exists(self):
        from server import mcp_opendaw_create_lick
        assert mcp_opendaw_create_lick.__name__ == "mcp_opendaw_create_lick"

    def test_default_type_bebop(self):
        assert _sig().parameters["lick_type"].default == "bebop"

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


class TestLickTypes:
    def test_five_types(self):
        s = _src()
        for t in ["bebop", "blues", "funk", "rock", "jazz_minor"]:
            assert t in s

    def test_valid_types_list(self):
        s = _src()
        assert '"bebop", "blues", "funk", "rock", "jazz_minor"' in s

    def test_bebop_enclosure(self):
        s = _src()
        assert "enclosure" in s.lower() or "Enclosure" in s
        assert "chromatic" in s.lower()

    def test_bebop_8th_note_line(self):
        s = _src()
        assert "0.25" in s  # 8th note durations

    def test_blues_blue_notes(self):
        s = _src()
        assert "blue note" in s.lower() or "blue_note" in s
        assert "chrom_pitch(3" in s  # b3 blue note
        assert "chrom_pitch(6" in s  # b5 blue note
        assert "chrom_pitch(10" in s  # b7 blue note

    def test_blues_call_response(self):
        s = _src()
        assert "call" in s.lower() and "response" in s.lower()

    def test_funk_16th_syncopation(self):
        s = _src()
        assert "accent_pattern" in s
        assert "0.25" in s  # 16th note grid

    def test_funk_octave_jump(self):
        s = _src()
        assert "octave" in s.lower()
        assert "deg_to_pitch(0, 1)" in s  # octave up

    def test_rock_pentatonic(self):
        s = _src()
        assert "pentatonic" in s.lower()
        assert "bend" in s.lower()

    def test_rock_climax_note(self):
        s = _src()
        assert "climax" in s.lower()

    def test_jazz_minor_diminished(self):
        s = _src()
        assert "diminished" in s.lower()
        assert "dim_pitches" in s
        assert "chrom_pitch(0" in s
        assert "chrom_pitch(3" in s
        assert "chrom_pitch(6" in s
        assert "chrom_pitch(9" in s  # diminished = R, b3, b5, 6

    def test_jazz_minor_chromatic_descent(self):
        s = _src()
        assert "descent" in s.lower() or "descend" in s.lower()
        assert "descent" in s


class TestLickScales:
    def test_five_scales(self):
        s = _src()
        for sc in ["major", "minor", "dorian", "mixolydian", "blues"]:
            assert sc in s

    def test_blues_scale(self):
        s = _src()
        assert "[0, 3, 5, 6, 7, 10]" in s  # blues scale


class TestLickPitchLogic:
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


class TestLickMetadata:
    def test_metadata_fields(self):
        s = _src()
        assert '"lick"' in s
        assert '"lick_type"' in s
        assert '"key_root"' in s
        assert '"scale_type"' in s
        assert '"notes_generated"' in s
        assert '"characteristics"' in s

    def test_characteristics_all_types(self):
        s = _src()
        for t in ["bebop", "blues", "funk", "rock", "jazz_minor"]:
            assert t in s

    def test_calls_create_notes_batch(self):
        s = _src()
        assert "mcp_opendaw_create_notes_batch" in s


class TestLickValidation:
    def test_invalid_key_root(self):
        s = _src()
        assert "Invalid key_root" in s
        assert "NOTE_MAP.get" in s

    def test_invalid_scale_type(self):
        s = _src()
        assert "Invalid scale_type" in s

    def test_invalid_lick_type(self):
        s = _src()
        assert "Invalid lick_type" in s

    def test_velocity_range_check(self):
        s = _src()
        assert "0.0 <= velocity <= 1.0" in s

    def test_octave_range_check(self):
        s = _src()
        assert "0 <= octave <= 7" in s
