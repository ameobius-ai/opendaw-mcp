# E2E Integration Tests — 2026-07-04

## Setup

Integration tests live in `tests/test_integration.py`. They auto-skip if DAW is not reachable at `localhost:5174`.

### Running
```bash
# Start Vite first
cd headless-daw && node node_modules/vite/bin/vite.js --port 5174 &
# Run tests
cd opendaw-mcp && source venv/bin/activate
python3 -m pytest tests/test_integration.py -v -s
```

### No pytest-asyncio needed
Tests use `_run_async(coro)` helper that manages its own event loop. No `pytest-asyncio` dependency required (it's not installed and NO install is allowed).

## Test classes

### TestBridgeStartup
- `test_globals_loaded` — verifies DAW, DAW_HELPERS, InstrumentFactories, EffectFactories, ScriptCompiler, ScriptDeclaration all loaded
- `test_project_state` — checks engine.bpm is not null

### TestTrackOperations
- `test_create_audio_track` — creates track, verifies AU count > 0 via direct bridge query (NOT via list_tracks — that returns different key names)

### TestScriptableDevices
- `test_werkstatt_compile_and_params` — compiles code with exp/int/bool params, verifies mapping metadata (cutoff=exp/Hz, mode=int, bypass=bool)

### TestParamClamping
- `test_clamp_exp` — over-range (99999→20000, clamped=True) and in-range (500→500, clamped=False)

### TestBenchmark
- `test_eval_latency` — 20 iterations of `bridge.evaluate("() => ({ ok: true, value: 42 })")` after 3 warmup rounds
- **Result: avg=4.0ms, p95=4.4ms** (n=20, localhost)
- Assert: avg < 500ms

## Pitfalls

### bridge.evaluate returns dict, not string
`bridge.evaluate()` returns Python dict/list/None directly. MCP tools wrap with `_wrap_eval()` → `json.dumps()` → string. In tests, when calling tools directly, use `json.loads(r)` to parse. When calling `bridge.evaluate()` directly, handle the dict.

### Bridge state doesn't persist across Python processes
Each `python3 -c "..."` or `python3 script.py` starts a fresh bridge. The DAW page state (tracks, effects) is lost. All test operations must happen in a single asyncio.run() call.

### list_tracks key name varies
`mcp_opendaw_list_tracks()` returns JSON with keys that may not include `"tracks"`. Use direct bridge query to verify AU count instead:
```python
r = await bridge.evaluate('''() => {
    const h = window.DAW_HELPERS;
    return {au_count: h.allAUBoxes().length};
}''')
```

### Integration test pattern
```python
_daw_reachable = False
try:
    r = httpx.get("http://localhost:5174", timeout=3)
    _daw_reachable = r.status_code == 200
except Exception:
    pass

pytestmark = pytest.mark.skipif(not _daw_reachable, reason="DAW not reachable")

def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed(): raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
```
