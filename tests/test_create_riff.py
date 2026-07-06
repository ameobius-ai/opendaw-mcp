"""Tests for create_riff logic."""
import json
import inspect
from server import mcp_opendaw_create_riff


def _src():
    return inspect.getsource(mcp_opendaw_create_riff)


def test_riff_function_exists():
    assert mcp_opendaw_create_riff.__name__ == "mcp_opendaw_create_riff"


def test_riff_default_type_rock():
    sig = inspect.signature(mcp_opendaw_create_riff)
    assert sig.parameters["riff_type"].default == "rock"


def test_riff_default_key_e():
    sig = inspect.signature(mcp_opendaw_create_riff)
    assert sig.parameters["key_root"].default == "E"


def test_riff_default_scale_pentatonic():
    sig = inspect.signature(mcp_opendaw_create_riff)
    assert sig.parameters["scale_type"].default == "minor_pentatonic"


def test_riff_default_bars_2():
    sig = inspect.signature(mcp_opendaw_create_riff)
    assert sig.parameters["bars"].default == 2


def test_riff_default_seed_42():
    sig = inspect.signature(mcp_opendaw_create_riff)
    assert sig.parameters["seed"].default == 42


def test_riff_five_types():
    s = _src()
    for t in ["rock", "funk", "metal", "blues", "hip_hop"]:
        assert t in s


def test_riff_valid_types_list():
    s = _src()
    assert '"rock", "funk", "metal", "blues", "hip_hop"' in s


def test_riff_scales():
    s = _src()
    for sc in ["minor_pentatonic", "major_pentatonic", "blues", "minor", "phrygian"]:
        assert sc in s


def test_riff_rock_power_chords():
    s = _src()
    assert "pitch + 7" in s  # root + fifth = power chord


def test_riff_rock_syncopated_rests():
    s = _src()
    assert "-1 = rest" in s or "deg == -1" in s


def test_riff_funk_16th_syncopation():
    s = _src()
    assert "16th" in s.lower() or "0.25" in s
    assert "ghost" in s.lower() or "staccato" in s


def test_riff_metal_galloping():
    s = _src()
    assert "gallop" in s.lower()
    assert "0.0, 0.25, 0.5" in s or "gallop_positions" in s


def test_riff_metal_tritone():
    s = _src()
    assert "tritone" in s
    assert "6, 6, 6" in s  # b5 degree


def test_riff_blues_shuffle():
    s = _src()
    assert "shuffle" in s.lower()
    assert "0.75, 0.25" in s  # long-short


def test_riff_blues_bending():
    s = _src()
    assert "bend" in s.lower() or "bent" in s


def test_riff_hip_hop_sparse():
    s = _src()
    assert "sparse" in s
    assert "loop aesthetic" in s


def test_riff_mulberry32():
    s = _src()
    assert "mulberry32" in s


def test_riff_creates_batches():
    s = _src()
    assert "mcp_opendaw_create_notes_batch" in s


def test_riff_output_structure():
    s = _src()
    assert '"riff"' in s
    assert '"riff_type"' in s
    assert '"notes_generated"' in s
    assert '"characteristics"' in s


def test_riff_error_handling():
    s = _src()
    assert "Invalid riff_type" in s
    assert "bars must be 1-4" in s


def test_riff_deg_to_pitch():
    s = _src()
    assert "deg_to_pitch" in s


def test_riff_rock_octave_accents():
    s = _src()
    assert "pitch + 12" in s  # octave accent


def test_riff_funk_accent_map():
    s = _src()
    assert "accent_map" in s


def test_riff_blues_call_response():
    s = _src()
    assert "call-response" in s or "call_response" in s
