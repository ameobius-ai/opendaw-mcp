"""
Integration tests for opendaw-mcp — end-to-end through the Playwright bridge.

These tests require a running Vite dev server (openDAW) on localhost:5174.
They exercise the real MCP tools against the live DAW instance.

Run: pytest tests/test_integration.py -v --timeout=180
Skip if DAW_URL is not reachable.
"""
import asyncio
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Check if DAW is reachable before collecting
import httpx
DAW_URL = "http://localhost:5174"
_daw_reachable = False
try:
    r = httpx.get(DAW_URL, timeout=3)
    _daw_reachable = r.status_code == 200
except Exception:
    pass

# Check if a Playwright-compatible chromium is available
_chrome_env = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "")
_chrome_ok = False
if _chrome_env and os.path.exists(_chrome_env):
    _chrome_ok = True
else:
    # Check Playwright's bundled browser
    from pathlib import Path
    _pw_cache = Path.home() / ".cache" / "ms-playwright"
    if _pw_cache.exists():
        _chrome_ok = any(_pw_cache.glob("chromium*"))

# These tests share a global Playwright bridge + live DAW state — skip under
# pytest-xdist (parallel workers corrupt each other's state).
_running_under_xdist = "PYTEST_XDIST_WORKER" in os.environ

pytestmark = pytest.mark.skipif(
    not (_daw_reachable and _chrome_ok) or _running_under_xdist,
    reason=(
        "Skipped under xdist (requires serial execution)"
        if _running_under_xdist
        else f"Need DAW at {DAW_URL} and Playwright chromium"
    ),
)

_bridge = None
_started = False


def _get_bridge():
    global _bridge, _started
    if _bridge is None:
        from server import bridge
        _bridge = bridge
    return _bridge


def _run_async(coro):
    """Run an async coroutine in the current event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _ensure_started():
    global _started
    if not _started:
        from server import mcp_opendaw_start_engine
        _run_async(mcp_opendaw_start_engine())
        _started = True


class TestBridgeStartup:
    """Verify bridge connects and DAW globals are available."""

    def test_globals_loaded(self):
        _ensure_started()
        b = _get_bridge()

        async def _check():
            return await b.evaluate('''() => ({
                hasDAW: typeof window.DAW !== 'undefined',
                hasHelpers: typeof window.DAW_HELPERS !== 'undefined',
                hasIF: typeof window.DAW_InstrumentFactories !== 'undefined',
                hasEF: typeof window.DAW_EffectFactories !== 'undefined',
                hasSC: typeof window.DAW_ScriptCompiler !== 'undefined',
                hasSD: typeof window.DAW_ScriptDeclaration !== 'undefined',
            })''')
        r = _run_async(_check())
        assert r["hasDAW"] is True
        assert r["hasHelpers"] is True
        assert r["hasIF"] is True
        assert r["hasEF"] is True
        assert r["hasSC"] is True
        assert r["hasSD"] is True

    def test_project_state(self):
        _ensure_started()
        b = _get_bridge()

        async def _check():
            return await b.evaluate('''() => {
                const h = window.DAW_HELPERS;
                const eng = h.engine;
                return {bpm: eng ? eng.bpm : null, playing: eng ? eng.playing : null};
            }''')
        r = _run_async(_check())
        assert r["bpm"] is not None


class TestTrackOperations:
    """E2E: create tracks, verify they exist."""

    def test_create_audio_track(self):
        _ensure_started()
        from server import mcp_opendaw_create_audio_track
        b = _get_bridge()

        async def _do():
            r = await mcp_opendaw_create_audio_track()
            d = json.loads(r)
            assert d["success"] is True

            # Verify track exists via direct bridge query
            r2 = await b.evaluate('''() => {
                const h = window.DAW_HELPERS;
                const aus = h.allAUBoxes();
                return {au_count: aus.length};
            }''')
            assert r2["au_count"] > 0
        _run_async(_do())


class TestScriptableDevices:
    """E2E: compile scriptable device code, verify params with mapping info."""

    def test_werkstatt_compile_and_params(self):
        _ensure_started()
        from server import (mcp_opendaw_create_audio_track, mcp_opendaw_add_effect,
            mcp_opendaw_set_script_device_code, mcp_opendaw_list_script_params)
        b = _get_bridge()

        async def _do():
            await mcp_opendaw_create_audio_track()
            await mcp_opendaw_add_effect(0, "Werkstatt")

            r = await b.evaluate('''() => {
                const h = window.DAW_HELPERS;
                const au = h.allAUBoxes()[0];
                const fx = h.effectBoxes(au);
                return fx.findIndex(bx => bx.constructor.name === "WerkstattDeviceBox");
            }''')
            werk_idx = r
            assert werk_idx >= 0

            code = '''// @werkstatt test_e2e 1 1
// @param cutoff 1000 20 20000 exp Hz
// @param mode 2 0 4 int
// @param bypass false

class Processor {
  processAudio(inputs, outputs, parameters) {
    const out = outputs[0];
    for (let c = 0; c < out.length; c++) {
      const ch = out[c];
      for (let i = 0; i < ch.length; i++) ch[i] = 0;
    }
  }
}'''
            r = await mcp_opendaw_set_script_device_code("Werkstatt", 0, werk_idx, code)
            d = json.loads(r)
            assert d["success"] is True
            assert d["params_created"] == 3

            r = await mcp_opendaw_list_script_params("Werkstatt", 0, werk_idx)
            d = json.loads(r)
            assert d["success"] is True

            cutoff = next(p for p in d["params"] if p["label"] == "cutoff")
            assert cutoff["mapping"] == "exp"
            assert cutoff["min"] == 20
            assert cutoff["max"] == 20000
            assert cutoff["unit"] == "Hz"

            mode = next(p for p in d["params"] if p["label"] == "mode")
            assert mode["mapping"] == "int"

            bypass = next(p for p in d["params"] if p["label"] == "bypass")
            assert bypass["mapping"] == "bool"
        _run_async(_do())


class TestParamClamping:
    """E2E: set_script_param clamps values correctly."""

    def test_clamp_exp(self):
        _ensure_started()
        from server import (mcp_opendaw_create_audio_track, mcp_opendaw_add_effect,
            mcp_opendaw_set_script_device_code, mcp_opendaw_set_script_param)
        b = _get_bridge()

        async def _do():
            await mcp_opendaw_create_audio_track()
            await mcp_opendaw_add_effect(0, "Werkstatt")
            r = await b.evaluate('''() => {
                const h = window.DAW_HELPERS;
                const au = h.allAUBoxes()[0];
                const fx = h.effectBoxes(au);
                return fx.findIndex(bx => bx.constructor.name === "WerkstattDeviceBox");
            }''')
            werk_idx = r

            code = '''// @werkstatt clamp_e2e 1 1
// @param freq 1000 20 20000 exp Hz

class Processor { processAudio(i,o,p) {} }'''
            await mcp_opendaw_set_script_device_code("Werkstatt", 0, werk_idx, code)

            r = await mcp_opendaw_set_script_param("Werkstatt", 0, werk_idx, "freq", 99999)
            d = json.loads(r)
            assert d["success"] is True
            assert d["clamped"] is True
            assert d["new_value"] == 20000.0

            r = await mcp_opendaw_set_script_param("Werkstatt", 0, werk_idx, "freq", 500)
            d = json.loads(r)
            assert d["success"] is True
            assert d["clamped"] is False
            assert d["new_value"] == 500.0
        _run_async(_do())


class TestBenchmark:
    """Measure round-trip latency of bridge.evaluate()."""

    def test_eval_latency(self):
        _ensure_started()
        b = _get_bridge()

        async def _bench():
            # Warm up
            for _ in range(3):
                await b.evaluate("() => 1 + 1")

            times = []
            for _ in range(20):
                t0 = time.perf_counter()
                await b.evaluate("() => ({ ok: true, value: 42 })")
                times.append((time.perf_counter() - t0) * 1000)

            avg = sum(times) / len(times)
            p95 = sorted(times)[int(len(times) * 0.95)]
            return avg, p95

        avg, p95 = _run_async(_bench())
        print(f"\n  bridge.evaluate latency: avg={avg:.1f}ms p95={p95:.1f}ms (n=20)")
        assert avg < 500, f"Average latency {avg:.1f}ms is too high"
