# Headless Instrument AU — Audio Verified July 2, 2026

## Breakthrough

**First confirmed audio output from openDAW in headless Chromium.** `maxAmplitude: 0.592, hasSignal: True` on a 440Hz sine wave test region.

The root cause of ALL previous silence was: **no instrument AU with TapeDeviceBox**. The output AU has `AudioBusProcessor` (a mixer) as its input, but `AudioBusProcessor.#sources` is empty because no instrument AU feeds it. `TapeDeviceProcessor` (created from `TapeDeviceBox`) is the only processor that reads `AudioRegionBox` entries and writes audio.

## Why `p.api.createInstrument()` Doesn't Work in Headless Mode

`p.api.createInstrument(InstrumentFactories.Tape)` requires the full studio app UI layer (`studio-ui`, `RegionDragAndDrop`, `SampleSelection`, etc.) which is not loaded in headless mode. The headless host only loads `studio-core`, `studio-adapters`, `studio-boxes`, and `studio-enums`. So we must create the boxes manually using the same pattern that `AudioUnitFactory.create()` + `InstrumentFactories.Tape.create()` uses internally.

## main.ts Lazy-Load Requirements

These must be added to the lazy-load section in `headless-daw/src/main.ts`:

```typescript
// In studio-boxes lazy load:
w.DAW_TapeDeviceBox = boxes.TapeDeviceBox;
w.DAW_CaptureAudioBox = boxes.CaptureAudioBox;
w.DAW_AudioUnitBox = boxes.AudioUnitBox;

// New studio-enums lazy load:
const enums = await import("@opendaw/studio-enums");
w.DAW_AudioUnitType = enums.AudioUnitType;
w.DAW_TrackType = enums.TrackType;
w.DAW_Pointers = enums.Pointers;
```

## Verified Box Creation Sequence

```javascript
const p = window.DAW;
const UUID = window.DAW_UUID;
const AudioUnitBox = window.DAW_AudioUnitBox;
const TapeDeviceBox = window.DAW_TapeDeviceBox;
const CaptureAudioBox = window.DAW_CaptureAudioBox;
const AudioUnitType = window.DAW_AudioUnitType;
const AudioFileBox = window.DAW_AudioFileBox;

const rootBox = p.rootBox;
const primaryAudioBusBox = p.primaryAudioBusBox;
const outputUnitBox = p.primaryAudioUnitBox;

let instrumentAU, tapeDevice, captureBox, trackBox, regionBox, audioFileBox;
p.editing.modify(() => {
    // 1. CaptureAudioBox — required by instrument AU type
    captureBox = CaptureAudioBox.create(p.boxGraph, UUID.generate());

    // 2. Instrument AudioUnitBox
    //    output → primaryAudioBusBox.input (routes to output AU)
    //    capture → CaptureAudioBox
    instrumentAU = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.type.setValue(AudioUnitType.Instrument);  // "instrument"
        box.collection.refer(rootBox.audioUnits);
        box.output.refer(primaryAudioBusBox.input);
        box.capture.refer(captureBox);
        box.index.setValue(0);
        box.volume.setValue(0.7339449541284403); // 0 dB
    });

    // 3. TapeDeviceBox — the audio player instrument
    //    host → instrumentAU.input (THE MISSING LINK)
    tapeDevice = TapeDeviceBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.label.setValue("Tape");
        box.host.refer(instrumentAU.input);
    });

    // 4. Audio track on instrument AU
    trackBox = p.api.createAudioTrack(instrumentAU);

    // 5. AudioFileBox + AudioRegionBox
    audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.fileName.setValue(sampleId);
        box.startInSeconds.setValue(0.0);
        box.endInSeconds.setValue(audioBuffer.duration);
    });

    regionBox = p.api.createNotStretchedRegion({
        boxGraph: p.boxGraph,
        targetTrack: trackBox,
        position: 0,
        audioFileBox: audioFileBox,
        sample: {
            name: sampleId,
            duration: audioBuffer.duration,
            bpm: 120,
            sample_rate: audioBuffer.sampleRate,
        },
    });

    // 6. Set output AU volume to 0 dB too
    outputUnitBox.volume.setValue(0.7339449541284403);
});
```

## Box Count After Setup

15 boxes total (8 default + 7 created):
- CaptureAudioBox (1)
- AudioUnitBox (2 — output + instrument)
- TapeDeviceBox (1)
- TrackBox (1)
- AudioFileBox (1)
- AudioRegionBox (1)
- ValueEventCollectionBox (1 — created by createNotStretchedRegion)

## Deferred Engine Start

```typescript
// main.ts — DAW_startEngine() exposed on window
w.DAW_startEngine = async () => {
    if (engineWorklet) return;
    engineWorklet = project.startAudioWorklet();
    w.DAW_engineWorklet = engineWorklet;
    await project.engine.isReady();
};
w.DAW_engineStarted = () => engineWorklet !== null;
```

Engine must be started AFTER all boxes are created. `startAudioWorklet()` serializes `project.toArrayBuffer()` into the AudioWorklet processor. If started before boxes exist, processor gets empty project. SyncSource only sends deltas, not initial state.

## Playback Verification

```javascript
await window.DAW_startEngine();
await p.engine.queryLoadingComplete();  // wait for sample data
p.engine.setPosition(0);
p.engine.play();

// Tap audio output via AnalyserNode
const analyser = ctx.createAnalyser();
analyser.fftSize = 2048;
window.DAW_engineWorklet.connect(analyser, 0);

// After 250ms:
// analyser.getFloatTimeDomainData(data) → max = 0.592 ✅
```

## MCP Tools Added

| Tool | Purpose |
|------|---------|
| `mcp_opendaw_create_instrument_track(name="Tape")` | Creates CaptureAudioBox + AudioUnitBox(Instrument) + TapeDeviceBox + audio track. Returns unit_index + track_index. |
| `mcp_opendaw_start_engine()` | Starts AudioWorklet after setup. Must be called before play/export. |
| `mcp_opendaw_export_mix(filename, sample_rate)` | Updated: checks `DAW_engineStarted()` before `releaseWorklet()`, uses volume 0.734 for 0 dB. |

## Export Blockers (UNRESOLVED)

### OfflineEngineRenderer — `Exponential is inverse`
`ValueMapping.exponential(min, max)` asserts `min < max`. During static initialization of processors.js in OfflineAudioContext, some effect's exponential mapping has min >= max. This is an upstream bug. bd: `security-workstation-tttz`.

### AudioOfflineRenderer — `non-finite float value`
`OfflineAudioContext(numStems*2, numSamples, sampleRate)` — `numSamples = NaN` because `projectCopy.timelineBox.durationInPulses.getValue()` returns 0 for audio-only projects (no note content). Timeline duration is not auto-calculated from audio regions.

### Potential Workaround
Real-time capture via `MediaStreamAudioDestinationNode`:
```javascript
const dest = ctx.createMediaStreamDestination();
window.DAW_engineWorklet.connect(dest, 0);
// Use MediaRecorder to capture, or ScriptProcessor to read samples
```

## Source Files Referenced

- `packages/studio/adapters/src/project/ProjectSkeleton.ts` — `empty()` creates default project (line 76: bus→AU input)
- `packages/studio/adapters/src/factories/AudioUnitFactory.ts` — `create()` pattern (line 18: output.refer(primaryAudioBusBox.input))
- `packages/studio/adapters/src/factories/InstrumentFactories.ts` — `Tape` factory (line 34: TapeDeviceBox.create, host.refer)
- `packages/studio/core-processors/src/EngineProcessor.ts` — `render()` processQueue, primaryOutput
- `packages/studio/core-processors/src/AudioBusProcessor.ts` — mixer, `#sources` array, `addAudioSource()`
- `packages/studio/core-processors/src/AudioDeviceChain.ts` — `#wire()` connects channelStrip → audioBus
- `packages/studio/core-processors/src/devices/instruments/TapeDeviceProcessor.ts` — reads AudioRegionBox, `BlockFlag.transporting|playing` check
- `packages/studio/core/src/EngineWorklet.ts` — `SyncSource` (line 236, initialize=false), `processorOptions.project` (line 111)
- `packages/studio/core/src/AudioOfflineRenderer.ts` — `durationInPulses` → `numSamples` calculation
- `packages/lib/std/src/value-mapping.ts` — `Decibel.y(0) = -Infinity`, `Exponential` assert
