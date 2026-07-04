# DAW_HELPERS Refactoring — 2026-07-03 (updated)

## Goal
Convert 180 tools from `const p = window.DAW;` to `const h = window.DAW_HELPERS;` for shorter, cleaner code.

## DAW_HELPERS extensions

Added to `bridge.start()` injection block across two sessions:

```js
rootBox: p.rootBox,                  // raw box access (not adapter)
timelineBox: p.timelineBox,          // timeline fields (bpm, signature, loopArea, markerTrack, signatureTrack, tempoTrack)
engine: p.engine,                    // transport (play/stop/setPosition)
primaryAudioUnitBox: p.primaryAudioUnitBox,  // for create_audio_track, create_note_track
primaryAudioBusBox: p.primaryAudioBusBox,    // for create_synth_track, create_instrument_track
uuid: window.DAW_UUID,               // UUID.generate()
ppqn: window.DAW_PPQN,              // PPQN.Quarter = 960
```

Previously had: `au(i)`, `track(au,track)`, `region(au,track,reg)`, `allAUs()`, `instrumentAU()`, `modify(fn)`, `project` (=p), `api`, `boxGraph`, `editing`, `tempoMap`, `audioUnitFreeze`, `rootBoxAdapter`.

## Full conversion table

| Old | New | Notes |
|-----|-----|-------|
| `const p = window.DAW;` | `const h = window.DAW_HELPERS;` | One line replacement |
| `const UUID = window.DAW_UUID;` | (remove — use `h.uuid`) | |
| `const PPQN = window.DAW_PPQN;` or `const Quarter = 960;` | (remove — use `h.ppqn.Quarter`) | Hardcoded `960` → `h.ppqn.Quarter` |
| `p.editing.modify(fn)` | `h.modify(fn)` | Direct shortcut |
| `p.api.X()` | `h.api.X()` | **VERIFY method exists!** setPosition lives on engine, not api |
| `p.timelineBox` | `h.timelineBox` | |
| `p.rootBox` | `h.rootBox` | |
| `p.engine` | `h.engine` | |
| `p.primaryAudioUnitBox` | `h.primaryAudioUnitBox` | |
| `p.primaryAudioBusBox` | `h.primaryAudioBusBox` | |
| `p.rootBox.audioUnits.pointerHub.incoming()` | `h.rootBox.audioUnits.pointerHub.incoming()` | **Keep raw box access** — just replace `p.` with `h.`. DO NOT switch to `h.au(i)`. |
| `p.boxGraph` | `h.boxGraph` | |
| `window.DAW_PPQN` | `h.ppqn` | |
| `window.DAW_UUID` | `h.uuid` | |

## Pre-existing bugs found during refactoring

The refactoring exposed 3 classes of latent bugs that the old `const p = window.DAW;` pattern masked:

### 1. set_position — wrong API method
```js
// OLD — p.api.setPosition() does NOT exist!
p.editing.modify(() => { p.api.setPosition(pos); });
// NEW — eng.setPosition() is the correct method
h.modify(() => { h.engine.setPosition(pos); });
```
Found by checking `Object.getOwnPropertyNames(Object.getPrototypeOf(p.engine))` → `['setPosition', 'position', ...]`. Latent from .pyc recovery era.

### 2. set_track_volume/panning/mute/solo — missing AU sort
```js
// OLD — no .sort(), AU ordering is nondeterministic
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
// NEW — sorted by index (systemic bug fix from pattern #41)
const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
```
These 4 tools were missed in the original 80+ site AU sort fix. Refactoring caught them.

### 3. delete_marker — hardcoded PPQN
```js
// OLD — hardcoded 960
deleted_position_beats: pos / 960,
// NEW — use h.ppqn.Quarter
deleted_position_beats: pos / h.ppqn.Quarter,
```

## Packages converted (28 tools total)

### Package 1: Transport (5 tools) — previous session
- transport, set_position, set_bpm, set_loop_region, set_time_signature
- E2E ✅. Found+fixed `set_position` bug.

### Package 2: Markers (5 tools)
- add_marker, list_markers, delete_marker, set_marker_position, set_marker_label
- Pattern: `p.timelineBox?.markerTrack` → `h.timelineBox?.markerTrack`, `p.boxGraph` → `h.boxGraph`, `UUID.generate()` → `h.uuid.generate()`
- E2E ✅. Found+fixed `delete_marker` /960 hardcode.
- Commit: `c536fc3`

### Package 3: Groove/Tuning (2 tools)
- set_groove_shuffle, set_tuning
- Pattern: `p.rootBox?.groove?.targetVertex` → `h.rootBox?.groove?.targetVertex`, `p.rootBox?.baseFrequency` → `h.rootBox?.baseFrequency`
- E2E ✅. Commit: `c536fc3`

### Package 4: Tempo/Signature (5 tools)
- add_signature_change, add_tempo_change, list_tempo_changes, list_signature_changes, delete_signature_change
- Pattern: `const Quarter = 960` → `h.ppqn.Quarter`, `p.timelineBox` → `h.timelineBox`, `p.boxGraph` → `h.boxGraph`, `UUID.generate()` → `h.uuid.generate()`, `ValueEventCollectionBox.create(p.boxGraph, UUID.generate())` → `ValueEventCollectionBox.create(h.boxGraph, h.uuid.generate())`
- E2E ✅. Commit: `c95f8a4`

### Package 5: Track/Instrument (8 tools)
- create_audio_track, create_note_track, rename_unit, replace_instrument, set_track_volume, set_track_panning, set_track_mute, set_track_solo
- Pattern: `p.primaryAudioUnitBox` → `h.primaryAudioUnitBox`, `p.rootBox.audioUnits.pointerHub.incoming()` → `h.rootBox.audioUnits.pointerHub.incoming()`, `p.api.createAudioTrack/createNoteTrack/replaceMIDIInstrument` → `h.api.X`
- E2E ✅. Found+fixed missing `.sort()` on 4 tools (volume/panning/mute/solo).
- Commit: `c95f8a4`

### Package 6: Synth (1 tool)
- create_synth_track
- Required adding `primaryAudioBusBox` to DAW_HELPERS
- Pattern: `p.rootBox`, `p.primaryAudioBusBox`, `p.boxGraph`, `UUID.generate()`, `p.api.createNoteTrack`, `p.editing.modify` → all `h.*`
- E2E ✅. Commit: `c95f8a4`

### Package 7: Project/Audio (3 tools) — NOT YET COMMITTED
- get_project_state, create_instrument_track, place_audio_region
- `get_project_state`: `p.engine`, `p.rootBox.audioUnits.pointerHub.incoming()`, `p.timelineBox`, `p.boxGraph.boxes()` → all `h.*`
- `create_instrument_track`: same as create_synth_track but with TapeDeviceBox. Required `primaryAudioBusBox`.
- `place_audio_region`: `p.rootBox.audioUnits.pointerHub.incoming()`, `p.api.createNotStretchedRegion`, `p.boxGraph`, `UUID.generate()`, `PPQN.Quarter` → all `h.*`
- E2E ✅ (signature+tempo verified in batch test; synth/track/createNote verified in direct evaluate test)
- Commit: `ea6c706`

### Package 8: Effects + Sends + Buses (13 tools)
- add_effect, clone_effect_chain, move_effect, create_send, set_send_level, list_sends, remove_send, set_send_routing, list_audio_buses, set_send_pan, set_bus_enabled, remove_audio_bus, list_effect_parameters
- Pattern: `p.rootBox.audioUnits.pointerHub.incoming()` → `h.rootBox.audioUnits.pointerHub.incoming()`, `p.rootBox.audioBusses.pointerHub.incoming()` → `h.rootBox.audioBusses.pointerHub.incoming()`, `p.primaryAudioBusBox` → `h.primaryAudioBusBox`, `p.api.insertEffect` → `h.api.insertEffect`, `p.boxGraph` → `h.boxGraph`, `UUID.generate()` → `h.uuid.generate()`
- Found+fixed missing `.sort()` on `add_effect` and `list_effect_parameters` (same systemic AU ordering bug, pattern #41)
- **Patch tool pitfall**: when converting `create_send`, the patch introduced a duplicate `return _wrap_eval(result)` line — the old_string had a unique context but the new_string included the closing differently. Always verify lint after patches to large evaluate blocks.
- Commit: `40e7eff`

## E2E test methodology — MCP tool function calls

When testing refactored tools, prefer calling the actual MCP tool function (`mcp_opendaw_tool_name.fn(args)`) rather than replicating JS in `bridge.evaluate()`. The tool function already contains the exact JS logic that was refactored. However, some tools (like `create_synth_track`) have complex setup logic that may timeout when called through FastMCP's `.fn()` — in that case, use `bridge.evaluate()` with the EXACT JS from the tool body (not a simplified version). Using `api.createInstrument` instead of `factory.create()` is a common mistake when writing test code by hand.

## Commits across all sessions

| Commit | Package | Tools | Notes |
|--------|---------|-------|-------|
| (prev session) | Transport | 5 | set_position bug found |
| `c536fc3` | Markers+Groove+Tuning | 7 | delete_marker /960 hardcode |
| `c95f8a4` | Tempo/Signature/Track/Instrument/Synth | 14 | 4× missing .sort() found |
| `ea6c706` | Project/Audio | 3 | |
| `40e7eff` | Effects+Sends+Buses | 13 | 2× missing .sort() found |

**Total: 40/180 converted, 140 remaining** (line 49 DAW_HELPERS definition excluded from count).

## E2E test methodology for refactoring

1. Start Vite: `cd headless-daw && node node_modules/vite/bin/vite.js --port 5174 --strictPort` (background, 15s warmup)
2. Verify: `sleep 15 && curl -s -o /dev/null -w "%{http_code}" http://localhost:5174` → 200
3. Run batch test: single `asyncio.run()` with `bridge.start()` + multiple `bridge.evaluate()` calls + `bridge.stop()`
4. Each test exercises the DAW_HELPERS path (h.* instead of p.*)
5. Kill Vite: `process(action='kill')`

**Key**: test with REAL tool logic (not simplified mock) — the `create_synth_track` test initially failed because the test script used `api.createInstrument` (wrong API) instead of `factory.create()` (correct API used by the actual tool). When testing refactored tools, either call the MCP tool function directly (`mcp_opendaw_tool_name.fn(args)`) or replicate the EXACT JS from the tool body.

## Remaining work

140 tools still use `const p = window.DAW;`. Next packages by priority:
1. **Effects (~15)** — add_effect, set_effect_parameter, list_effect_parameters, clone_effect_chain, etc.
2. **Notes (~12)** — create_note, delete_note, duplicate_note_event, etc.
3. **Regions (~10)** — create_note_region, duplicate_region, copy_region_to_track, etc.
4. **Clips (~11)** — create_note_clip, clone_clip, consolidate_clip, etc.
5. **Sends (6)**, **Buses (5)**, **Automation (8)**, **Export (7)**, **MIDI (2)**, **MIDI Effects (6)**, **Modular (7)**, **PianoMode (6)**, **Scriptable (5)**, **Transfer (2)**, **Presets (5)**, and others.

**Track progress**: `grep -c 'const p = window.DAW;' server.py` — subtract 1 for the DAW_HELPERS definition line (line 49). Target: 0 (excluding line 49).
