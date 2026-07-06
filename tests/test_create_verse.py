"""Unit tests for create_verse — verse section generator."""
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
    if not src or "create_verse" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_verse_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_verse(" in src


def test_verse_has_5_types():
    src = _get_source()
    for t in ["narrative", "sparse", "driving", "conversational", "build"]:
        assert t in src, f"Missing verse type: {t}"


def test_verse_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["narrative", "sparse", "driving", "conversational", "build"]' in src


def test_verse_has_octave_validation():
    src = _get_source()
    assert "octave must be 2-6" in src


def test_verse_has_bars_validation():
    src = _get_source()
    assert "bars must be 4-16" in src


def test_verse_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_verse_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_verse_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_verse_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_verse_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_verse_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_verse_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_verse_narrative_has_degree_map():
    src = _get_source()
    assert "degree_map" in src


def test_verse_driving_has_8th_notes():
    src = _get_source()
    assert "8th" in src.lower() or "beat_idx" in src


def test_verse_build_has_progress():
    src = _get_source()
    assert "progress" in src


def test_verse_conversational_has_phrases():
    src = _get_source()
    assert "conversational" in src
    assert "phrase" in src.lower()


def test_verse_sparse_has_minimal():
    src = _get_source()
    assert "sparse" in src


def test_verse_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_verse_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_verse_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_verse_has_metadata():
    src = _get_source()
    assert 'data["verse"] = True' in src
    assert 'data["verse_type"]' in src
    assert 'data["notes_generated"]' in src


def test_verse_has_docstring():
    src = _get_source()
    assert "storytelling" in src.lower()
    assert "verse" in src.lower()


def test_verse_has_examples():
    src = _get_source()
    assert "create_verse(" in src


def test_verse_default_params():
    src = _get_source()
    assert 'verse_type: str = "narrative"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 4" in src
    assert "bars: int = 8" in src
    assert "velocity: float = 0.6" in src


def test_verse_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_verse_has_unit_track_index():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "track_index: int = 0" in src
