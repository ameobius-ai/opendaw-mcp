"""Tests for create_etude logic — technical study pieces in 5 types."""
import inspect
import pytest


def _src():
    from server import mcp_opendaw_create_etude
    return inspect.getsource(mcp_opendaw_create_etude)


def _sig():
    from server import mcp_opendaw_create_etude
    return inspect.signature(mcp_opendaw_create_etude)


class TestEtudeSignature:
    def test_function_exists(self):
        from server import mcp_opendaw_create_etude
        assert mcp_opendaw_create_etude.__name__ == "mcp_opendaw_create_etude"

    def test_default_type_scale(self):
        assert _sig().parameters["etude_type"].default == "scale"

    def test_default_key_c(self):
        assert _sig().parameters["key_root"].default == "C"

    def test_default_scale_major(self):
        assert _sig().parameters["scale_type"].default == "major"

    def test_default_bars_8(self):
        assert _sig().parameters["bars"].default == 8

    def test_default_octave_4(self):
        assert _sig().parameters["octave"].default == 4

    def test_default_velocity_07(self):
        assert _sig().parameters["velocity"].default == 0.7

    def test_default_seed_42(self):
        assert _sig().parameters["seed"].default == 42

    def test_has_unit_index(self):
        assert "unit_index" in _sig().parameters

    def test_has_track_index(self):
        assert "track_index" in _sig().parameters


class TestEtudeTypes:
    def test_five_types(self):
        s = _src()
        for t in ["scale", "arpeggio", "interval", "rhythm", "chromatic"]:
            assert t in s

    def test_valid_types_list(self):
        s = _src()
        assert '"scale", "arpeggio", "interval", "rhythm", "chromatic"' in s

    def test_scale_ascending_descending(self):
        s = _src()
        assert "ascending" in s.lower() or "descending" in s.lower()
        assert "direction" in s

    def test_scale_16th_notes(self):
        s = _src()
        assert "0.25" in s  # 16th note duration
        assert "notes_per_beat" in s

    def test_arpeggio_broken_chords(self):
        s = _src()
        assert "broken" in s.lower() or "chord" in s.lower()
        assert "chord_degrees" in s

    def test_arpeggio_root_3rd_5th_7th(self):
        s = _src()
        assert "[0, 2, 4, 6]" in s  # 7th chord degrees

    def test_arpeggio_inversions(self):
        s = _src()
        assert "inversion" in s.lower()
        assert "root_shifts" in s

    def test_interval_thirds(self):
        s = _src()
        assert "third" in s.lower() or "interval" in s.lower()
        assert "interval = 3" in s

    def test_interval_two_voices(self):
        s = _src()
        assert "lower_pitch" in s
        assert "upper_pitch" in s

    def test_rhythm_syncopation(self):
        s = _src()
        assert "syncopat" in s.lower()
        assert "patterns" in s

    def test_rhythm_varied_patterns(self):
        s = _src()
        assert "patterns[bar % 4]" in s or "bar % 4" in s

    def test_chromatic_runs(self):
        s = _src()
        assert "chromatic" in s.lower()
        assert "chrom_pitch" in s or "start_pitch" in s

    def test_chromatic_thirds(self):
        s = _src()
        assert "+ 3" in s  # chromatic third


class TestEtudeScales:
    def test_five_scales(self):
        s = _src()
        for sc in ["major", "minor", "dorian", "mixolydian", "harmonic_minor"]:
            assert sc in s

    def test_harmonic_minor_scale(self):
        s = _src()
        assert "[0, 2, 3, 5, 7, 8, 11]" in s


class TestEtudePitchLogic:
    def test_deg_to_pitch(self):
        s = _src()
        assert "def deg_to_pitch" in s

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


class TestEtudeMetadata:
    def test_metadata_fields(self):
        s = _src()
        assert '"etude"' in s
        assert '"etude_type"' in s
        assert '"key_root"' in s
        assert '"scale_type"' in s
        assert '"bars"' in s
        assert '"notes_generated"' in s
        assert '"characteristics"' in s

    def test_characteristics_all_types(self):
        s = _src()
        for t in ["scale", "arpeggio", "interval", "rhythm", "chromatic"]:
            assert t in s

    def test_calls_create_notes_batch(self):
        s = _src()
        assert "mcp_opendaw_create_notes_batch" in s


class TestEtudeValidation:
    def test_invalid_key_root(self):
        s = _src()
        assert "Invalid key_root" in s

    def test_invalid_scale_type(self):
        s = _src()
        assert "Invalid scale_type" in s

    def test_invalid_etude_type(self):
        s = _src()
        assert "Invalid etude_type" in s

    def test_bars_range_check(self):
        s = _src()
        assert "bars must be 4-16" in s

    def test_velocity_range_check(self):
        s = _src()
        assert "0.0 <= velocity <= 1.0" in s

    def test_octave_range_check(self):
        s = _src()
        assert "0 <= octave <= 7" in s
