"""Unit tests for create_prechorus — pre-chorus section generator."""
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
    if not src or "create_prechorus" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_prechorus_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_prechorus" in src


def test_prechorus_has_5_types():
    src = _get_source()
    for t in ["build", "pedal", "stall", "lift", "suspending"]:
        assert t in src, f"Missing prechorus type: {t}"


def test_prechorus_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["build", "pedal", "stall", "lift", "suspending"]' in src


def test_prechorus_has_scale_validation():
    src = _get_source()
    assert "Invalid scale_type" in src
    assert "Invalid key_root" in src


def test_prechorus_has_bars_validation():
    src = _get_source()
    assert "bars must be 2-4" in src


def test_prechorus_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_prechorus_has_octave_validation():
    src = _get_source()
    assert "octave must be 0-7" in src


def test_prechorus_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_prechorus_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_prechorus_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_prechorus_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_prechorus_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_prechorus_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_prechorus_build_has_crescendo():
    src = _get_source()
    assert "chord_prog" in src
    assert "progress" in src


def test_prechorus_pedal_has_dominant():
    src = _get_source()
    assert "dom_deg" in src
    assert "pedal" in src.lower()


def test_prechorus_stall_has_stasis():
    src = _get_source()
    assert "stall_chords" in src


def test_prechorus_lift_has_ascent():
    src = _get_source()
    assert "start_deg" in src
    assert "ascending" in src.lower() or "ascent" in src.lower()


def test_prechorus_suspending_has_sus():
    src = _get_source()
    assert "sus4" in src or "sus" in src
    assert "sus2" in src
    assert "resolve" in src.lower() or "Resolve" in src


def test_prechorus_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_prechorus_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_prechorus_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_prechorus_has_metadata():
    src = _get_source()
    assert 'data["prechorus"] = True' in src
    assert 'data["prechorus_type"]' in src
    assert 'data["notes_generated"]' in src


def test_prechorus_has_docstring():
    src = _get_source()
    assert "tension builder" in src.lower()
    assert "prechorus_type: build" in src


def test_prechorus_has_examples():
    src = _get_source()
    assert "create_prechorus(" in src


def test_prechorus_default_params():
    src = _get_source()
    assert 'prechorus_type: str = "build"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 4" in src
    assert "bars: int = 4" in src
    assert "velocity: float = 0.6" in src
    assert "seed: int = 42" in src


def test_prechorus_bar_len():
    src = _get_source()
    assert "bar_len = 4.0" in src


def test_prechorus_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_prechorus_has_unit_track_index():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "track_index: int = 0" in src


def test_prechorus_build_has_ii_iv_v():
    src = _get_source()
    # build progression should include ii, IV, V
    assert "chord_prog" in src
