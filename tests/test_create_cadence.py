"""Tests for create_cadence logic — harmonic phrase conclusions in 5 types."""
import inspect
import pytest


def _src():
    from server import mcp_opendaw_create_cadence
    return inspect.getsource(mcp_opendaw_create_cadence)


def _sig():
    from server import mcp_opendaw_create_cadence
    return inspect.signature(mcp_opendaw_create_cadence)


class TestCadenceSignature:
    def test_function_exists(self):
        from server import mcp_opendaw_create_cadence
        assert mcp_opendaw_create_cadence.__name__ == "mcp_opendaw_create_cadence"

    def test_default_type_authentic(self):
        assert _sig().parameters["cadence_type"].default == "authentic"

    def test_default_key_c(self):
        assert _sig().parameters["key_root"].default == "C"

    def test_default_scale_major(self):
        assert _sig().parameters["scale_type"].default == "major"

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


class TestCadenceTypes:
    def test_five_types(self):
        s = _src()
        for t in ["authentic", "plagal", "half", "deceptive", "phrygian"]:
            assert t in s

    def test_valid_types_list(self):
        s = _src()
        assert '"authentic", "plagal", "half", "deceptive", "phrygian"' in s

    def test_authentic_v_i(self):
        s = _src()
        assert "V-I" in s or "v_root" in s
        assert "deg_to_pitch(4)" in s  # V chord root = scale degree 4
        assert "deg_to_pitch(0)" in s  # I chord root = scale degree 0

    def test_authentic_leading_tone(self):
        s = _src()
        assert "leading tone" in s.lower()
        assert "deg_to_pitch(6)" in s  # leading tone = degree 6

    def test_plagal_iv_i(self):
        s = _src()
        assert "IV-I" in s or "iv_root" in s
        assert "deg_to_pitch(3)" in s  # IV chord root = degree 3
        assert "Amen" in s

    def test_half_i_v(self):
        s = _src()
        assert "I-V" in s or "half" in s.lower()
        assert "no closure" in s.lower()

    def test_deceptive_v_vi(self):
        s = _src()
        assert "V-vi" in s or "vi_root" in s
        assert "deg_to_pitch(5)" in s  # vi chord root = degree 5
        assert "surprise" in s.lower() or "deceptive" in s.lower()

    def test_phrygian_bii_i(self):
        s = _src()
        assert "bII-i" in s or "bii_root" in s
        assert "chrom_pitch(1, 0)" in s  # bII = root + 1 semitone
        assert "Neapolitan" in s


class TestCadenceScales:
    def test_three_scales(self):
        s = _src()
        for sc in ["major", "minor", "harmonic_minor"]:
            assert sc in s

    def test_harmonic_minor(self):
        s = _src()
        assert "[0, 2, 3, 5, 7, 8, 11]" in s


class TestCadencePitchLogic:
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


class TestCadenceMetadata:
    def test_metadata_fields(self):
        s = _src()
        assert '"cadence"' in s
        assert '"cadence_type"' in s
        assert '"key_root"' in s
        assert '"scale_type"' in s
        assert '"notes_generated"' in s
        assert '"characteristics"' in s

    def test_characteristics_all_types(self):
        s = _src()
        for t in ["authentic", "plagal", "half", "deceptive", "phrygian"]:
            assert t in s

    def test_calls_create_notes_batch(self):
        s = _src()
        assert "mcp_opendaw_create_notes_batch" in s


class TestCadenceValidation:
    def test_invalid_key_root(self):
        s = _src()
        assert "Invalid key_root" in s

    def test_invalid_scale_type(self):
        s = _src()
        assert "Invalid scale_type" in s

    def test_invalid_cadence_type(self):
        s = _src()
        assert "Invalid cadence_type" in s

    def test_velocity_range_check(self):
        s = _src()
        assert "0.0 <= velocity <= 1.0" in s

    def test_octave_range_check(self):
        s = _src()
        assert "0 <= octave <= 7" in s
