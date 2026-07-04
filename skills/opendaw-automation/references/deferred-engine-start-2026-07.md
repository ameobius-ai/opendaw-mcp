# Deferred Engine Start — July 2, 2026

## Problem
`EngineWorklet` (AudioWorkletNode) serializes the project state via `project.toArrayBuffer()` at construction time (EngineWorklet.ts:111, `processorOptions.project`). After that, `SyncSource` (EngineWorklet.ts:236, `initialize=false`) propagates only NEW boxGraph changes to the processor via MessagePort.

In headless/automation context, regions created via `editing.modify()` AFTER `startAudioWorklet()` may not reach the EngineProcessor — SyncSource updates can fail to propagate, leaving the processor with an empty processQueue and producing silence.

## Solution: Deferred Engine Start
Delay `project.startAudioWorklet()` until AFTER all boxes (tracks, regions, audio files) are created. This way they're included in the serialized project buffer and the processor sees them immediately — no SyncSource dependency.

### main.ts Changes
```typescript
// BEFORE (broken for automation):
const engineWorklet = project.startAudioWorklet();  // serializes EMPTY project
await project.engine.isReady();
// ... later: create tracks, regions via editing.modify() → SyncSource may not propagate

// AFTER (working):
// 1. Expose globals BEFORE starting worklet
w.DAW = project;
w.DAW_audioContext = audioContext;
// ... all other globals ...

// 2. Deferred engine start — MCP calls DAW_startEngine() after setup
let engineWorklet = null;
w.DAW_startEngine = async () => {
    if (engineWorklet) return;
    console.log("[engine] serializing project with", project.boxGraph.boxes().length, "boxes");
    engineWorklet = project.startAudioWorklet();
    w.DAW_engineWorklet = engineWorklet;
    await project.engine.isReady();
};
w.DAW_engineStarted = () => engineWorklet !== null;
```

### MCP server.py Changes
- New tool `mcp_opendaw_start_engine` — calls `DAW_startEngine()` explicitly
- `export_mix` — checks `DAW_engineStarted()` before `releaseWorklet()`, only restores if was running
- Bridge `wait_for_function` checks `window.DAW` and `window.DAW_EffectFactories` (both set before engine start)

### Verified Working Sequence
```
1. Boot: main.ts creates Project, exposes globals, does NOT start engine
2. load_audio: fetch WAV → decodeAudioData → store in localAudioBuffers + fileNameToAudioBuffer
3. create track + place region: editing.modify() → createAudioTrack + createNotStretchedRegion
4. start_engine: DAW_startEngine() → startAudioWorklet() → serializes project WITH all boxes
5. queryLoadingComplete: poll until true (~10s for sample data to load in processor)
6. engine.play() → position advances, isPlaying=true, bpm=120
```

### Verification Results (July 2)
- ✅ `loadingComplete = true` after polling
- ✅ `filePointer` connected: `box.file.nonEmpty() = true`, `box.file.targetAddress = Option.Some(uuid)`
- ✅ `pointerHubCount = 1` on AudioFileBox (AudioRegionBox.file points to it)
- ✅ Region in serialized project: `AudioRegionBox` and `AudioFileBox` logged at engine start
- ✅ sampleProvider resolves by fileName (exact UUID match)
- ✅ position advances (0→5628 PPQN), isPlaying=true, bpm=120
- ❌ **Audio output still silence** (maxAmplitude=0) — see "Remaining Blocker" below

## SyncSource Internals (for reference)

| Component | Location | Role |
|-----------|----------|------|
| `SyncSource` | `lib/box/src/sync-source.ts` | Main thread: subscribes to boxGraph, sends updates via MessagePort |
| `createSyncTarget` | `lib/box/src/sync-target.ts` | Processor: receives updates, applies to processor's boxGraph |
| `project.toArrayBuffer()` | `EngineWorklet.ts:111` | Serializes project into processorOptions at worklet creation |
| `initialize=false` | `EngineWorklet.ts:236` | SyncSource does NOT send existing boxes on init — only future changes |

SyncSource flow:
1. `graph.subscribeTransaction()` — collects updates per transaction
2. `graph.subscribeToAllUpdatesImmediate()` — pushes each update (new/primitive/pointer/delete) to array
3. `onEndTransaction(rolledBack)` — if not rolled back, calls `sendUpdates(updates)` via Communicator
4. Processor's `createSyncTarget.sendUpdates()` — applies updates to processor's boxGraph in a transaction

## Remaining Blocker: AudioBusProcessor Silence

Despite deferred engine start + correct wiring, audio output is still zero. The problem is downstream of boxGraph — in the audio processing chain itself.

### What's Verified Working
- EngineProcessor receives project with all boxes ✅
- EngineProcessor.process() is called (position advances) ✅
- Sample data loaded in processor (loadingComplete=true) ✅
- AudioRegionBox.file pointer connected to AudioFileBox ✅

### Next Investigation Steps
1. Read `AudioBusProcessor.ts` — how it reads AudioRegionBox and schedules playback
2. Check if AudioBusProcessor sees the AudioRegionBox (it subscribes to track.regions)
3. Check if `processQueue` in EngineProcessor contains the AudioBusProcessor
4. Check if AudioUnit.input is connected (TapeDeviceBox requirement — see `references/offline-render-investigation-2026-06.md` Session 5)
5. **TapeDeviceBox may still be missing** — `createAudioTrack` creates TrackBox but no instrument. Need `p.api.createInstrument(InstrumentFactories.Tape)` before regions can play.

### Key Hypothesis
The June 30 session found that `TapeDeviceBox` is required for audio region playback. This session's test created a track via `api.createAudioTrack(au)` but did NOT create a TapeDeviceBox instrument. This is likely STILL the missing piece — deferred engine start solved the SyncSource problem, but the TapeDeviceBox problem persists.

### Export Bug (minor)
`export_mix` destructuring `{b}` instead of `{box}` when iterating audio units — causes `Cannot read properties of undefined (reading 'volume')`. Fix: `[{box}]` → access `box.volume`.

## PointerField Reading (API reference)

```javascript
// CORRECT ways to read PointerField state:
box.file.nonEmpty()          // true if pointer is set
box.file.targetAddress       // Option<Address> — String() gives "Option.Some(uuid)"
box.file.targetVertex        // Option<Vertex> — the actual box (only outside transactions)
box.pointerHub.incoming()    // Iterable of PointerFields pointing TO this box

// WRONG (returns undefined, not null):
box.file.target?.getValue?.()  // getValue doesn't exist on PointerField
box.file.getValue()            // PointerField has no getValue
```
