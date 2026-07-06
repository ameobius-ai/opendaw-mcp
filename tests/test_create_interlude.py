"""Unit tests for create_interlude — interlude section generator."""
import importlib.util
import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_source():
    """Get source code of create_interlude without importing server.py."""
    spec = importlib.util.spec_from_file_location(
        "server", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
    )
    mod = importlib.util.module_from_spec(spec)
    src = inspect.getsource(sys.modules.get("server", mod))
    # Fallback: read file directly
    if not src or "create_interlude" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_interlude_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_interlude" in src


def test_interlude_has_5_types():
    src = _get_source()
    for t in ["instrumental", "atmospheric", "breakdown", "reprise", "contrapuntal"]:
        assert t in src, f"Missing interlude type: {t}"


def test_interlude_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["instrumental", "atmospheric", "breakdown", "reprise", "contrapuntal"]' in src


def test_interlude_has_scale_validation():
    src = _get_source()
    assert "Invalid scale_type" in src
    assert "Invalid key_root" in src


def test_interlude_has_bars_validation():
    src = _get_source()
    assert "bars must be 2-4" in src


def test_interlude_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_interlude_has_octave_validation():
    src = _get_source()
    assert "octave must be 0-7" in src


def test_interlude_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_interlude_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_interlude_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_interlude_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_interlude_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src
    assert '"C": 0' in src
    assert '"B": 11' in src


def test_interlude_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_interlude_instrumental_has_bass():
    src = _get_source()
    # instrumental type should have bass root
    assert "bass_pitch" in src


def test_interlude_atmospheric_has_chord_roots():
    src = _get_source()
    # atmospheric should have I-IV-V-I chord roots
    assert "chord_roots" in src


def test_interlude_breakdown_has_layers():
    src = _get_source()
    assert "layer_threshold" in src
    assert "Layer" in src or "layer" in src


def test_interlude_reprise_has_motif():
    src = _get_source()
    assert "motif_degrees" in src


def test_interlude_contrapuntal_has_voices():
    src = _get_source()
    assert "num_voices" in src
    assert "voice_starts" in src


def test_interlude_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src
    assert "instrumental" in src
    assert "atmospheric" in src


def test_interlude_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_interlude_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_interlude_has_metadata():
    src = _get_source()
    assert 'data["interlude"] = True' in src
    assert 'data["interlude_type"]' in src
    assert 'data["notes_generated"]' in src


def test_interlude_has_docstring():
    src = _get_source()
    assert "connective passage" in src
    assert "interlude_type: instrumental" in src


def test_interlude_has_examples():
    src = _get_source()
    assert "create_interlude(" in src


def test_interlude_default_params():
    src = _get_source()
    assert 'interlude_type: str = "instrumental"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 4" in src
    assert "bars: int = 4" in src
    assert "velocity: float = 0.6" in src
    assert "seed: int = 42" in src


def test_interlude_bar_len():
    src = _get_source()
    assert "bar_len = 4.0" in src


def test_interlude_contrapuntal_contrary_motion():
    src = _get_source()
    # contrapuntal should have step_dir for contrary motion
    assert "step_dir" in src


def test_interlude_breakdown_growths():
    src = _get_source()
    # breakdown should add layers progressively
    assert "0.3" in src  # layer 2 threshold
    assert "0.6" in src  # layer 3 threshold


def test_interlude_reprise_octave_shift():
    src = _get_source()
    assert "oct_shift" in src


def test_interlude_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_interlude_has_unit_track_index():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "track_index: int = 0" in src
