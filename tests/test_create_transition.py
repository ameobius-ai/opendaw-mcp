"""Unit tests for create_transition — transition section generator."""
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
    if not src or "create_transition" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_transition_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_transition" in src


def test_transition_has_5_types():
    src = _get_source()
    for t in ["key_shift", "tempo_ramp", "texture_build", "texture_thin", "drop"]:
        assert t in src, f"Missing transition type: {t}"


def test_transition_has_valid_types_check():
    src = _get_source()
    assert 'VALID_TYPES = ["key_shift", "tempo_ramp", "texture_build", "texture_thin", "drop"]' in src


def test_transition_has_direction():
    src = _get_source()
    assert "direction: str" in src
    assert 'direction: str = "up"' in src
    assert "VALID_DIRECTIONS" in src


def test_transition_has_interval():
    src = _get_source()
    assert "interval: int = 5" in src
    assert "interval must be 1-7" in src


def test_transition_has_scale_validation():
    src = _get_source()
    assert "Invalid scale_type" in src
    assert "Invalid key_root" in src


def test_transition_has_bars_validation():
    src = _get_source()
    assert "bars must be 2-8" in src


def test_transition_has_velocity_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src


def test_transition_has_octave_validation():
    src = _get_source()
    assert "octave must be 0-7" in src


def test_transition_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_transition_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_transition_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_transition_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_transition_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src
    assert '"C": 0' in src
    assert '"B": 11' in src


def test_transition_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_transition_key_shift_has_pivot():
    src = _get_source()
    assert "pivot_bar" in src or "pivot" in src


def test_transition_key_shift_has_shift():
    src = _get_source()
    assert "shift = interval" in src
    assert "dir_mult" in src


def test_transition_tempo_ramp_has_dur_factor():
    src = _get_source()
    assert "dur_factor" in src


def test_transition_texture_build_has_voices():
    src = _get_source()
    assert "num_voices" in src
    assert "texture_build" in src


def test_transition_texture_thin_has_voices():
    src = _get_source()
    assert "texture_thin" in src
    assert "4 - bar" in src


def test_transition_drop_has_silence():
    src = _get_source()
    assert "drop" in src
    assert "silence" in src.lower() or "Silence" in src


def test_transition_has_characteristics_dict():
    src = _get_source()
    assert "characteristics" in src


def test_transition_has_notes_sort():
    src = _get_source()
    assert 'notes.sort' in src


def test_transition_has_velocity_clamp():
    src = _get_source()
    assert "max(0.0, min(1.0" in src


def test_transition_has_metadata():
    src = _get_source()
    assert 'data["transition"] = True' in src
    assert 'data["transition_type"]' in src
    assert 'data["notes_generated"]' in src


def test_transition_has_docstring():
    src = _get_source()
    assert "active" in src.lower() or "movement" in src.lower()
    assert "transition_type: key_shift" in src


def test_transition_has_examples():
    src = _get_source()
    assert "create_transition(" in src


def test_transition_default_params():
    src = _get_source()
    assert 'transition_type: str = "key_shift"' in src
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "major"' in src
    assert "octave: int = 4" in src
    assert "bars: int = 4" in src
    assert "velocity: float = 0.6" in src
    assert "seed: int = 42" in src


def test_transition_bar_len():
    src = _get_source()
    assert "bar_len = 4.0" in src


def test_transition_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src


def test_transition_has_unit_track_index():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "track_index: int = 0" in src


def test_transition_key_shift_has_pitch_offset():
    src = _get_source()
    assert "pitch_offset" in src
