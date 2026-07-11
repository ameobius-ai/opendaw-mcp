# E2E Pivot Spike — Complete

## Result: Prototype Validated ✓

Full E2E smoke path passes locally through the minimal test host:

```
1/8 set_bpm(128)              ✓
2/8 create_synth(Vaporisateur)  ✓ unit=1
3/8 add_effect(Delay)          ✓
4/8 create_note(C4)            ✓
5/8 fix_region_duration        ✓ dur=7680
6/8 project_state              ✓ bpm=128
7/8 render_full                ✓ 2ch, 33.75s, max=0.461, rms=0.196
8/8 verify finite+non-silent   ✓ PASS
```

LUFS ≈ -14.83 (near Spotify -14 target), finite=true, has_audio=true, WAV 12.9MB.

## Architecture

```
test_host (Vite + @opendaw/studio-core)
  → main.ts boots: Workers → AudioWorklets → Project.new() → engine.isReady
  → exposes window.opendaw.service (shim wrapping Project)
  → exposes 54 window.DAW_* globals for server.py tool functions
  → no React, no dashboard, no clicks, no routes

bridge.py
  → goto(DAW_URL)
  → wait_for_function("window.opendaw.service")
  → inject DAW_HELPERS (box navigation helpers)
  → server.py MCP tools use DAW_HELPERS + DAW_* globals
```

## Bugs Found & Fixed (locally, not committed)

1. **bridge.py uuid bug**: `uuid: p.rootBox.address.toString()` → `uuid: window.DAW_UUID`
   - server.py calls `h.uuid.generate()` — needs UUID module, not string

2. **Vite dual instantiation**: `optimizeDeps.exclude` must include all @opendaw/* packages
   - Without this, AudioUnitBox class identity breaks (two instances in memory)

3. **OfflineEngineRenderer "Already connected"**: needs `project.copy()` before render
   - server.py render_full skips copy → AudioWorkletNode already connected to live context

4. **NoteRegionBox.create() duration=0**: `duration.setValue()` inside create callback has no effect
   - Workaround: set duration + loopDuration in separate `h.modify()` call after creation
   - Root cause likely: box not yet in graph when callback runs

## Key Files (local, not committed)

- `tests/e2e/test_host/main.ts` — boot script, 54 DAW_* globals
- `tests/e2e/test_host/vite.config.ts` — COOP/COEP + WASM middleware
- `tests/e2e/test_host/package.json` — @opendaw/studio-sdk ^0.0.157
- `tests/e2e/test_host/tsconfig.json`
- `tests/e2e/test_host/index.html`
- `tests/e2e/test_host/localhost.pem` + `localhost-key.pem`
- `opendaw_mcp/bridge.py` — uuid fix + dashboard hacks removed

## Next Steps (before commit/push)

1. Fix server.py `render_full` to use `project.copy()` before OfflineEngineRenderer.start()
2. Fix server.py `create_note` to set region duration/loopDuration after creation (outside create callback)
3. Commit test_host + bridge.py fixes
4. Update CI workflow to build test_host instead of full openDAW studio
5. Run CI headless-e2e-smoke → should pass now
