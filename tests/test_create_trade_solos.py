"""Unit tests for create_trade_solos — two soloists trading phrases."""
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
    if not src or "trade_solos" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_trade_solos_exists():
    src = _get_source()
    assert "async def mcp_opendaw_create_trade_solos" in src


def test_trade_solos_has_trade_length():
    src = _get_source()
    assert "trade_length: int = 4" in src


def test_trade_solos_has_two_tracks():
    src = _get_source()
    assert "track_index_a: int = 0" in src
    assert "track_index_b: int = 1" in src


def test_trade_solos_has_divisibility_check():
    src = _get_source()
    assert "divisible by trade_length" in src


def test_trade_solos_has_intensity():
    src = _get_source()
    assert "intensity" in src


def test_trade_solos_has_mulberry32():
    src = _get_source()
    assert "mulberry32" in src


def test_trade_solos_has_deg_to_pitch():
    src = _get_source()
    assert "deg_to_pitch" in src


def test_trade_solos_has_create_notes_batch():
    src = _get_source()
    assert "create_notes_batch" in src


def test_trade_solos_has_note_map():
    src = _get_source()
    assert "NOTE_MAP" in src


def test_trade_solos_has_scales():
    src = _get_source()
    assert '"major"' in src
    assert '"minor"' in src
    assert '"harmonic_minor"' in src


def test_trade_solos_has_chromatic_passing():
    src = _get_source()
    assert "chromatic" in src.lower() or "half-step" in src.lower()


def test_trade_solos_has_alternation():
    src = _get_source()
    assert "is_a" in src
    assert "trade_idx % 2" in src


def test_trade_solos_has_octave_shift_for_b():
    src = _get_source()
    assert "oct_shift" in src


def test_trade_solos_has_validation():
    src = _get_source()
    assert "velocity must be 0-1" in src
    assert "octave must be 2-6" in src
    assert "trade_length must be 2-16" in src


def test_trade_solos_has_trade_type():
    src = _get_source()
    assert "trading_" in src


def test_trade_solos_has_num_trades():
    src = _get_source()
    assert "num_trades" in src


def test_trade_solos_has_characteristics():
    src = _get_source()
    assert "characteristics" in src
    assert "conversation" in src.lower()


def test_trade_solos_has_references():
    src = _get_source()
    assert "references" in src
    assert "Coltrane" in src or "Miles" in src


def test_trade_solos_has_docstring():
    src = _get_source()
    assert "trading fours" in src.lower() or "trading eights" in src.lower()


def test_trade_solos_has_examples():
    src = _get_source()
    assert "create_trade_solos(" in src


def test_trade_solos_has_seed():
    src = _get_source()
    assert "seed: int = 42" in src


def test_trade_solos_default_params():
    src = _get_source()
    assert 'key_root: str = "C"' in src
    assert 'scale_type: str = "minor"' in src
    assert "bars: int = 16" in src


def test_trade_solos_has_start_beat():
    src = _get_source()
    assert "start_beat: float = 0" in src
