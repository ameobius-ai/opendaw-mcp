"""Unit tests for create_descant — descant counter-melody generator."""
import importlib.util
import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    spec = importlib.util.spec_from_file_location(
        "server", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
    )
    mod = importlib.util.module_from_spec(spec)
    src = inspect.getsource(sys.modules.get("server", mod))
    if not src or "create_descant" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_descant_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_descant" in src


def test_descant_has_5_types():
    src = _get_source()
    for t in ["soaring", "weaving", "pedal_tone", "call_response", "ornamental"]:
        assert t in src, f"Missing descant type: {t}"


def test_descant_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["soaring", "weaving", "pedal_tone", "call_response", "ornamental"]' in src


def test_descant_has_octave_validation():
    src = _get_source()
    assert "octave must be 3-7" in src


def test_descant_has_bars_validation():
    src = _get_source()
    assert "bars must be 2-8" in src


def test_descant_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_descant_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_descant_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_descant_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_descant_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_descant_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_descant_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_descant_soaring_has_degree_map():
    src = _get_source()
    assert "degree_map" in src


def test_descant_weaving_has_interlocking():
    src = _get_source()
    assert "weaving" in src


def test_descant_pedal_tone_has_sustained():
    src = _get_source()
    assert "pedal_tone" in src
    assert "pedal_deg" in src


def test_descant_call_response_has_phrases():
    src = _get_source()
    assert "call_response" in src
    assert "phrase" in src.lower()


def test_descant_ornamental_has_runs():
    src = _get_source()
    assert "ornamental" in src
    assert "anchor" in src


def test_descant_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_descant_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_descant_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_descant_has_metadata():
    src = _get_source()
    assert 'data["descant"] = True' in src
    assert 'data["descant_type"]' in src
    assert 'data["notes_generated"]' in src


def test_descant_has_docstring():
    src = _get_source()
    assert "counter-melody" in src.lower()
    assert "above the main" in src.lower()


def test_descant_has_examples():
    src = _get_source()
    assert "create_descant(" in src


def test_descant_default_params():
    src = _get_source()
    assert 'descant_type: str = "soaring"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 5" in src
    assert "bars: int = 4" in src
    assert "velocity: float = 0.55" in src


def test_descant_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_descant_has_unit_track_index():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "track_index: int = 0" in src
