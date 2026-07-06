"""Unit tests for auto_master — adaptive mastering meta-tool."""
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
    if not src or "auto_master" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_auto_master_exists():
    src = _get_source()
    assert "async def mcp_opendaw_auto_master" in src


def test_auto_master_has_platform():
    src = _get_source()
    assert "platform: str" in src
    assert "spotify" in src
    assert "apple" in src
    assert "youtube" in src


def test_auto_master_has_style():
    src = _get_source()
    assert "style: str" in src
    assert "balanced" in src
    assert "warm" in src
    assert "loud" in src
    assert "transparent" in src


def test_auto_master_has_target_lufs():
    src = _get_source()
    assert "target_lufs: float" in src
    assert "-23 to -8" in src


def test_auto_master_has_ceiling():
    src = _get_source()
    assert "ceiling_dbtp" in src


def test_auto_master_has_platform_lufs_map():
    src = _get_source()
    assert "PLATFORM_LUFS" in src


def test_auto_master_has_valid_platforms():
    src = _get_source()
    assert "VALID_PLATFORMS" in src


def test_auto_master_has_valid_styles():
    src = _get_source()
    assert "VALID_STYLES" in src


def test_auto_master_calls_analyze_mix():
    src = _get_source()
    assert "mcp_opendaw_analyze_mix" in src


def test_auto_master_calls_add_mastering_chain():
    src = _get_source()
    assert "mcp_opendaw_add_mastering_chain" in src


def test_auto_master_calls_auto_gain():
    src = _get_source()
    assert "mcp_opendaw_auto_gain" in src


def test_auto_master_has_3_steps():
    src = _get_source()
    assert "Step 1" in src
    assert "Step 2" in src
    assert "Step 3" in src


def test_auto_master_has_error_handling():
    src = _get_source()
    assert "analysis_error" in src
    assert "chain_error" in src
    assert "gain_error" in src


def test_auto_master_has_docstring():
    src = _get_source()
    assert "Adaptive mastering" in src
    assert "meta-tool" in src


def test_auto_master_has_examples():
    src = _get_source()
    assert "auto_master(" in src


def test_auto_master_has_next_steps():
    src = _get_source()
    assert "next_steps" in src
    assert "LUFS" in src


def test_auto_master_has_metadata():
    src = _get_source()
    assert 'results["auto_master"] = True' in src
    assert 'results["platform"]' in src


def test_auto_master_default_params():
    src = _get_source()
    assert 'platform: str = "spotify"' in src
    assert 'style: str = "balanced"' in src
    assert "target_lufs: float = -14.0" in src
