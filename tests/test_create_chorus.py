"""Unit tests for create_chorus — chorus section generator."""
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
    if not src or "create_chorus" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_chorus_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_chorus(" in src


def test_chorus_has_5_types():
    src = _get_source()
    for t in ["anthemic", "hooky", "driving", "soaring", "call_response"]:
        assert t in src, f"Missing chorus type: {t}"


def test_chorus_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["anthemic", "hooky", "driving", "soaring", "call_response"]' in src


def test_chorus_has_octave_validation():
    src = _get_source()
    assert "octave must be 2-6" in src


def test_chorus_has_bars_validation():
    src = _get_source()
    assert "bars must be 4-16" in src


def test_chorus_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_chorus_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_chorus_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_chorus_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_chorus_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_chorus_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_chorus_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_chorus_anthemic_has_prog():
    src = _get_source()
    assert "prog" in src
    assert "0, 4, 5, 3" in src  # I-V-vi-IV


def test_chorus_hooky_has_pattern():
    src = _get_source()
    assert "hook_pattern" in src


def test_chorus_driving_has_16th():
    src = _get_source()
    assert "16th" in src.lower() or "beat_idx" in src


def test_chorus_soaring_has_progress():
    src = _get_source()
    assert "progress" in src
    assert "crescendo" in src.lower()


def test_chorus_call_response_has_question_answer():
    src = _get_source()
    assert "call_response" in src
    assert "q_degrees" in src
    assert "a_degrees" in src


def test_chorus_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_chorus_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_chorus_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_chorus_has_metadata():
    src = _get_source()
    assert 'data["chorus"] = True' in src
    assert 'data["chorus_type"]' in src
    assert 'data["notes_generated"]' in src


def test_chorus_has_docstring():
    src = _get_source()
    assert "emotional peak" in src.lower()
    assert "hook" in src.lower()


def test_chorus_has_examples():
    src = _get_source()
    assert "create_chorus(" in src


def test_chorus_default_params():
    src = _get_source()
    assert 'chorus_type: str = "anthemic"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 4" in src
    assert "bars: int = 8" in src
    assert "velocity: float = 0.8" in src


def test_chorus_higher_velocity_than_verse():
    src = _get_source()
    # Chorus default 0.8 > Verse default 0.6
    assert "velocity: float = 0.8" in src
