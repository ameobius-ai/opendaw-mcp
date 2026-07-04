# openDAW Routing API — Vertex Type Constraints

Reverse-engineered June 2026 from source inspection of `@opendaw/studio-core` and `@opendaw/studio-boxes`.

## Default Project Routing

```
AudioBusBox ("Output")
    .output (PointerField) → outputAu.input (Field, field 22)

AudioUnitBox (type="output", units[0])
    .input (Field, accepts [19, 5])  ← bus.output points here
    .output (PointerField, accepts []) → points to rootBox.outputDevice
    .tracks (Field) ← trackBox.target points here
```

## Pointer Type IDs

| ID | Type | Notes |
|----|------|-------|
| 5  | AudioBusBox | Bus channel strip |
| 19 | InstrumentHost | Instrument input |
| 38 | AudioRegionBox? | Accepted by AU.output |
| 40 | AudioOutput | Accepted by AU.output |

## Field Types

- **PointerField** — has `.refer()`, `.isEmpty()`, `.targetVertex`, `.targetAddress`. Used for output routing.
- **Field** — no `.refer()`. Has `.pointerHub`, `.box`. Used for input/collection targets (things that receive pointers, not send them).

## What Accepts What

| Source Field | Accepts Types | Meaning |
|---|---|---|
| `AudioUnitBox.output` | 40, 38 | AU sends audio out to these types |
| `AudioUnitBox.input` | 19, 5 | AU receives audio from InstrumentHost or Bus |
| `AudioBusBox.input` | 5 | Bus receives from other buses only |
| `AudioBusBox.output` | [] (NoPointers) | Bus sends to anything? (existing: → AU.input) |
| `rootBox.outputDevice` | (Field) | Final destination — receives from AU.output |

## Exclusive vs Non-Exclusive

`AudioUnitBox.input` is **exclusive** — only ONE incoming pointer. The default project has `bus.output → outputAu.input`. You cannot add a second connection to `outputAu.input`.

To add a new stem AU to the chain, you need an intermediate bus:

```
newAU.output → newBus (somehow — type constraint unresolved)
newBus.output → existingBus.input (bus.input accepts type 5)
existingBus.output → outputAu.input (already connected)
```

**UNRESOLVED (June 2026):** How to connect `newAU.output → newBus`. AU.output accepts types 40/38, but AudioBusBox is type 5. AudioBusBox.input accepts type 5 (other buses), not AudioUnitBox. The correct routing may involve:
1. An intermediate vertex type (AudioOutput? type 40) that bridges AU to Bus
2. Or `newBus.output → existingBus.input` and `newAU.output` connects to something else entirely
3. Or tracks on the default output AU work without additional routing (regions on `units[0].tracks` are already routed through the existing chain)

## Key Functions

### `p.api.createNotStretchedRegion(props)`

Props object:
```javascript
{
    boxGraph: p.boxGraph,
    targetTrack: trackBox,      // TrackBox from createAudioTrack
    audioFileBox: audioFileBox, // AudioFileBox from AudioFileBox.create
    sample: { name: uuidString, duration: audioBuffer.duration, bpm: 0 },
    position: 0,                // PPQN position
    name: 'stem-name'
}
```

Internally calls `AudioContentFactory.createNotStretchedRegion` which:
1. Creates `AudioRegionBox` with proper `regions.refer(targetTrack.regions)` wiring
2. Creates `ValueEventCollectionBox` for events
3. Wires `box.file.refer(audioFileBox)` (NOT `audioFileBox.file`)
4. All inside `AudioRegionBox.create()` constructor callback

### `AudioFileBoxFactory.createModifier`

Source: `@opendaw/studio-core/dist/project/audio/AudioFileBoxFactory.js`

Creates AudioFileBox with audio data binding. The DAW's `sampleProvider.fetch(uuid)` (in main.ts) looks up `window.DAW_localAudioBuffers.get(uuidString)` — if the fileName stored on the AudioFileBox doesn't match, the sample loads in the UI but produces silence during render.

### `OfflineEngineRenderer.start(source, optExportConfiguration, progress, abortSignal, sampleRate)`

Source: `@opendaw/studio-core/dist/OfflineEngineRenderer.js`

- `source` must be a project copy (`p.copy()`) — original returns "Already connected"
- `progress` must be `{ setValue: (v) => {} }` — NOT a bare function
- Returns `{ sampleRate, numberOfFrames, numberOfChannels, frames: Float32Array[] }` — NOT an AudioBuffer
- `frames[0]` is channel 0 (left), `frames[1]` is channel 1 (right)
- If `maxSample === 0` and `nonZero === 0` → routing problem OR sample not loaded

**⚠️ CRITICAL — install() must be called on YOUR imported module instance.** `workerUrl` is a module-scoped `let`, NOT a static class field. main.ts calls `install()` on ITS import, but `page.evaluate()` dynamic imports may get a different module instance. Always re-install:
```javascript
const core = await import('/node_modules/.vite/deps/@opendaw_studio-core.js');
core.AudioWorklets.install('/node_modules/@opendaw/studio-core/dist/processors.js');
core.OfflineEngineRenderer.install('/node_modules/@opendaw/studio-core/dist/offline-engine.js?worker_file&type=module');
```

**⚠️ project.copy() regenerates AudioFileBox UUIDs.** The offline worker fetches audio via `source.sampleManager.getOrCreate(copyUUID)`, but the copy's UUIDs don't exist in `localAudioBuffers`. This causes "Sample not loaded" errors and 0% progress hang. **UNRESOLVED** — see `references/offline-render-investigation-2026-06.md` for attempted fixes. The most promising untried approach: modify main.ts sampleProvider to use fileName-based lookup instead of UUID-based.

- Uses `source.sampleManager.getOrCreate(uuid)` for fetchAudio — copy preserves sampleManager structurally but NOT loaded sample data
