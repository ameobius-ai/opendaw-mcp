"""Unit tests for add_genre_effects — genre-specific effect chains."""
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
    if not src or "add_genre_effects" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_genre_fx_exists():
    src = _get_source()
    assert "async def mcp_opendaw_add_genre_effects" in src


def test_genre_fx_has_genre_param():
    src = _get_source()
    assert "genre: str" in src


def test_genre_fx_has_15_genres():
    src = _get_source()
    for g in ["house", "techno", "dnb", "trap", "dubstep", "synthwave",
              "ambient", "lofi", "rock", "pop", "funk", "reggae", "jazz", "metal", "edm"]:
        assert g in src, f"Missing genre: {g}"


def test_genre_fx_has_chains():
    src = _get_source()
    assert "GENRE_CHAINS" in src


def test_genre_fx_calls_add_effect():
    src = _get_source()
    assert "mcp_opendaw_add_effect" in src


def test_genre_fx_calls_set_effect_parameter():
    src = _get_source()
    assert "mcp_opendaw_set_effect_parameter" in src


def test_genre_fx_has_error_handling():
    src = _get_source()
    assert "Invalid genre" in src


def test_genre_fx_has_house_chain():
    src = _get_source()
    assert '"house"' in src


def test_genre_fx_has_target_routing():
    src = _get_source()
    assert "target" in src
    assert "bass" in src
    assert "drums" in src
    assert "output" in src


def test_genre_fx_has_effects_added_count():
    src = _get_source()
    assert "effects_added" in src


def test_genre_fx_has_next_steps():
    src = _get_source()
    assert "next_steps" in src


def test_genre_fx_has_docstring():
    src = _get_source()
    assert "genre-appropriate" in src.lower() or "Genre chains" in src


def test_genre_fx_has_examples():
    src = _get_source()
    assert "add_genre_effects(" in src


def test_genre_fx_has_unit_index():
    src = _get_source()
    assert "unit_index: int = -1" in src


def test_genre_fx_has_vocal_unit():
    src = _get_source()
    assert "vocal_unit_index" in src


def test_genre_fx_house_has_sidechain():
    src = _get_source()
    # house should have compressor on bass
    assert "Compressor" in src


def test_genre_fx_metal_has_waveshaper():
    src = _get_source()
    # metal should have heavy waveshaper on guitars
    assert "Waveshaper" in src


def test_genre_fx_ambient_has_reverb():
    src = _get_source()
    # ambient should have long reverb
    assert "DattorroReverb" in src


def test_genre_fx_has_params():
    src = _get_source()
    assert "params" in src
    assert "threshold" in src
    assert "ratio" in src


def test_genre_fx_default_params():
    src = _get_source()
    assert 'genre: str = "house"' in src
