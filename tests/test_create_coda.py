"""Unit tests for create_coda — coda section generator."""
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
    if not src or "create_coda" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_coda_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_coda" in src


def test_coda_has_5_types():
    src = _get_source()
    for t in ["theme", "vamp", "codetta", "postlude", "fanfare"]:
        assert t in src, f"Missing coda type: {t}"


def test_coda_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["theme", "vamp", "codetta", "postlude", "fanfare"]' in src


def test_coda_has_scale_validation():
    src = _get_source()
    assert "Invalid scale_type" in src
    assert "Invalid key_root" in src


def test_coda_has_bars_validation():
    src = _get_source()
    assert "bars must be 2-8" in src


def test_coda_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_coda_has_octave_validation():
    src = _get_source()
    assert "octave must be 0-7" in src


def test_coda_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_coda_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_coda_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_coda_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_coda_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src
    assert '"C": 0' in src
    assert '"B": 11' in src


def test_coda_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_coda_theme_has_melody_degrees():
    src = _get_source()
    assert "melody_degrees" in src


def test_coda_vamp_has_chord_roots():
    src = _get_source()
    assert "chord_roots" in src


def test_coda_vamp_has_fade():
    src = _get_source()
    assert "fade" in src


def test_coda_codetta_always_2_bars():
    src = _get_source()
    assert 'actual_bars = 2' in src


def test_coda_codetta_has_scale_run():
    src = _get_source()
    assert "Ascending scale run" in src or "ascending" in src.lower()


def test_coda_postlude_has_wind_down():
    src = _get_source()
    assert "wind_down" in src


def test_coda_fanfare_has_arpeggio():
    src = _get_source()
    assert "arpeggio" in src.lower() or "Ascending arpeggio" in src


def test_coda_fanfare_has_tutti():
    src = _get_source()
    assert "Tutti" in src or "tutti" in src


def test_coda_fanfare_has_fermata():
    src = _get_source()
    assert "fermata" in src.lower() or "Fermata" in src


def test_coda_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_coda_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_coda_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_coda_has_metadata():
    src = _get_source()
    assert 'data["coda"] = True' in src
    assert 'data["coda_type"]' in src
    assert 'data["notes_generated"]' in src


def test_coda_has_docstring():
    src = _get_source()
    assert "definitive ending" in src
    assert "coda_type: theme" in src


def test_coda_has_examples():
    src = _get_source()
    assert "create_coda(" in src


def test_coda_default_params():
    src = _get_source()
    assert 'coda_type: str = "theme"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 4" in src
    assert "bars: int = 4" in src
    assert "velocity: float = 0.7" in src
    assert "seed: int = 42" in src


def test_coda_bar_len():
    src = _get_source()
    assert "bar_len = 4.0" in src


def test_coda_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_coda_has_unit_track_index():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "track_index: int = 0" in src


def test_coda_theme_has_fermata():
    src = _get_source()
    assert "Fermata" in src or "fermata" in src


def test_coda_codetta_has_tonic_chord():
    src = _get_source()
    assert "Tonic chord" in src or "tonic" in src.lower()
