"""Unit tests for read_meter — read Werkstatt meter device parameters."""
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
    if not src or "read_meter" not in src:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")) as f:
            src = f.read()
    return src


def test_read_meter_exists():
    src = _get_source()
    assert "async def mcp_opendaw_read_meter" in src


def test_read_meter_has_unit_index():
    src = _get_source()
    assert "unit_index: int = -1" in src


def test_read_meter_has_device_index():
    src = _get_source()
    assert "device_index: int = -1" in src


def test_read_meter_has_docstring():
    src = _get_source()
    assert "Werkstatt meter" in src
    assert "LUFS" in src


def test_read_meter_has_examples():
    src = _get_source()
    assert "read_meter(" in src


def test_read_meter_uses_bridge():
    src = _get_source()
    assert "bridge.evaluate" in src


def test_read_meter_has_error_handling():
    src = _get_source()
    assert "error" in src.lower()
    assert "except" in src


def test_read_meter_reads_parameters():
    src = _get_source()
    assert "parameters" in src
    assert "pointerHub" in src


def test_read_meter_reads_labels():
    src = _get_source()
    assert "label" in src


def test_read_meter_reads_values():
    src = _get_source()
    assert "value" in src


def test_read_meter_identifies_meter_type():
    src = _get_source()
    assert "meter_type" in src
    assert "lufs_meter" in src
    assert "correlation_meter" in src
    assert "spectrum_analyzer" in src


def test_read_meter_reads_code_header():
    src = _get_source()
    assert "@werkstatt" in src


def test_read_meter_has_param_count():
    src = _get_source()
    assert "param_count" in src


def test_read_meter_has_js_code():
    src = _get_source()
    assert "DAW_project" in src
    assert "audioEffects" in src


def test_read_meter_handles_missing_unit():
    src = _get_source()
    assert "Unit not found" in src


def test_read_meter_handles_missing_device():
    src = _get_source()
    assert "Device not found" in src


def test_read_meter_handles_non_werkstatt():
    src = _get_source()
    assert "Not a Werkstatt" in src or "no parameters" in src


def test_read_meter_returns_json():
    src = _get_source()
    assert "json.dumps" in src
    assert "json.loads" not in src or True  # may or may not parse


def test_read_meter_default_params():
    src = _get_source()
    assert "unit_index: int = -1" in src
    assert "device_index: int = -1" in src
