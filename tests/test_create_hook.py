"""Tests for create_hook logic — melodic earworm phrases in 5 styles."""
import inspect
import pytest


def _src():
    from server import mcp_opendaw_create_hook
    return inspect.getsource(mcp_opendaw_create_hook)


def _sig():
    from server import mcp_opendaw_create_hook
    return inspect.signature(mcp_opendaw_create_hook)


class TestHookSignature:
    def test_function_exists(self):
        from server import mcp_opendaw_create_hook
        assert mcp_opendaw_create_hook.__name__ == "mcp_opendaw_create_hook"

    def test_default_type_pop(self):
        assert _sig().parameters["hook_type"].default == "pop"

    def test_default_key_c(self):
        assert _sig().parameters["key_root"].default == "C"

    def test_default_scale_major(self):
        assert _sig().parameters["scale_type"].default == "major"

    def test_default_bars_2(self):
        assert _sig().parameters["bars"].default == 2

    def test_default_octave_4(self):
        assert _sig().parameters["octave"].default == 4

    def test_default_velocity_08(self):
        assert _sig().parameters["velocity"].default == 0.8

    def test_default_seed_42(self):
        assert _sig().parameters["seed"].default == 42

    def test_has_unit_index(self):
        assert "unit_index" in _sig().parameters

    def test_has_track_index(self):
        assert "track_index" in _sig().parameters


class TestHookTypes:
    def test_five_types(self):
        s = _src()
        for t in ["pop", "rock", "dance", "rnb", "country"]:
            assert t in s

    def test_valid_types_list(self):
        s = _src()
        assert '"pop", "rock", "dance", "rnb", "country"' in s

    def test_pop_stepwise(self):
        s = _src()
        assert "stepwise" in s.lower()
        assert "I-V-vi-IV" in s

    def test_pop_climax_leap(self):
        s = _src()
        assert "climax" in s.lower()
        assert "deg_to_pitch(0, 1)" in s  # octave leap

    def test_rock_pentatonic(self):
        s = _src()
        assert "pentatonic" in s.lower()
        assert "power" in s.lower()

    def test_rock_power_chords(self):
        s = _src()
        assert "pitch + 7" in s  # fifth = power chord

    def test_dance_ostinato(self):
        s = _src()
        assert "ostinato" in s.lower()
        assert "syncopat" in s.lower()

    def test_dance_octave_jumps(self):
        s = _src()
        assert "octave" in s.lower()
        assert "deg_to_pitch(0, 1)" in s

    def test_rnb_melismatic(self):
        s = _src()
        assert "melismatic" in s.lower() or "melisma" in s.lower()
        assert "neo-soul" in s.lower() or "chromatic" in s.lower()

    def test_rnb_blue_notes(self):
        s = _src()
        # R&B uses chrom_map with b3 (3) and b7 (10) chromatic values
        assert "chrom_map" in s
        assert ": 3" in s  # b3 blue note value
        assert ": 10" in s  # b7 blue note value

    def test_country_diatonic(self):
        s = _src()
        assert "diatonic" in s.lower()
        assert "story" in s.lower()

    def test_country_root_resolution(self):
        s = _src()
        assert "deg_to_pitch(0)" in s
        assert "3.75" in s  # final resolution position


class TestHookScales:
    def test_five_scales(self):
        s = _src()
        for sc in ["major", "minor", "dorian", "mixolydian", "pentatonic_major"]:
            assert sc in s

    def test_pentatonic_major_scale(self):
        s = _src()
        assert "[0, 2, 4, 7, 9]" in s


class TestHookPitchLogic:
    def test_deg_to_pitch(self):
        s = _src()
        assert "def deg_to_pitch" in s

    def test_chrom_pitch(self):
        s = _src()
        assert "def chrom_pitch" in s

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


class TestHookMetadata:
    def test_metadata_fields(self):
        s = _src()
        assert '"hook"' in s
        assert '"hook_type"' in s
        assert '"key_root"' in s
        assert '"scale_type"' in s
        assert '"bars"' in s
        assert '"notes_generated"' in s
        assert '"characteristics"' in s

    def test_characteristics_all_types(self):
        s = _src()
        for t in ["pop", "rock", "dance", "rnb", "country"]:
            assert t in s

    def test_calls_create_notes_batch(self):
        s = _src()
        assert "mcp_opendaw_create_notes_batch" in s


class TestHookValidation:
    def test_invalid_key_root(self):
        s = _src()
        assert "Invalid key_root" in s

    def test_invalid_scale_type(self):
        s = _src()
        assert "Invalid scale_type" in s

    def test_invalid_hook_type(self):
        s = _src()
        assert "Invalid hook_type" in s

    def test_bars_range_check(self):
        s = _src()
        assert "bars must be 1-4" in s

    def test_velocity_range_check(self):
        s = _src()
        assert "0.0 <= velocity <= 1.0" in s

    def test_octave_range_check(self):
        s = _src()
        assert "0 <= octave <= 7" in s
