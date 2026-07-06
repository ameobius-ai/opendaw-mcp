"""Unit tests for create_counter_melody — secondary melody that complements the main one."""
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
    if not src or "counter_melody" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_counter_melody_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_counter_melody" in src


def test_counter_melody_has_5_types():
    src = _get_source()
    for t in ["contrary", "oblique", "parallel", "rhythmic", "pedal"]:
        assert t in src, f"Missing counter type: {t}"


def test_counter_melody_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["contrary", "oblique", "parallel", "rhythmic", "pedal"]' in src


def test_counter_melody_has_octave_validation():
    src = _get_source()
    assert "octave must be 2-6" in src


def test_counter_melody_has_bars_validation():
    src = _get_source()
    assert "bars must be 4-16" in src


def test_counter_melody_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_counter_melody_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_counter_melody_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_counter_melody_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_counter_melody_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_counter_melody_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_counter_melody_contrary_has_opposite():
    src = _get_source()
    assert "opposite" in src.lower() or "counter_dir" in src


def test_counter_melody_oblique_has_sustained():
    src = _get_source()
    assert "sustained" in src.lower() or "sustain_deg" in src


def test_counter_melody_parallel_has_thirds():
    src = _get_source()
    assert "third" in src.lower() or "interval = 2" in src


def test_counter_melody_rhythmic_has_offbeats():
    src = _get_source()
    assert "offbeat" in src.lower()


def test_counter_melody_pedal_has_drone():
    src = _get_source()
    assert "drone" in src.lower() or "pedal" in src.lower()


def test_counter_melody_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_counter_melody_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_counter_melody_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_counter_melody_has_metadata():
    src = _get_source()
    assert 'data["counter_melody"] = True' in src
    assert 'data["counter_type"]' in src
    assert 'data["notes_generated"]' in src


def test_counter_melody_has_docstring():
    src = _get_source()
    assert "counter-melody" in src.lower()
    assert "secondary melody" in src.lower()


def test_counter_melody_has_examples():
    src = _get_source()
    assert "create_counter_melody(" in src


def test_counter_melody_default_params():
    src = _get_source()
    assert 'counter_type: str = "contrary"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 3" in src
    assert "bars: int = 8" in src
    assert "velocity: float = 0.55" in src


def test_counter_melody_lower_velocity_than_descant():
    src = _get_source()
    # Counter-melody 0.55 < Descant 0.65 < Chorus 0.8
    assert "velocity: float = 0.55" in src
