# openDAW API Investigation — June 2026

## Goal

Load 6 audio stems into openDAW, set volumes/panning, add effects (Compressor sidechain, StereoTool), and export the mix. This is the "minus-king" 6-stem pipeline: anchor (ghost -30dB), minus (king +3dB), bass, drums, vocal L, vocal R.

## What works

### Audio loading via Vite public dir + fetch()
- Copy files to `headless-daw/public/stems/`
- `fetch('/stems/file.wav')` → `arrayBuffer()` → `decodeAudioData()` → store in `DAW_localAudioBuffers`
- Works for any file size (tested 70MB WAV, 5.5MB OGG)
- Sample rate: decoded at 44100 regardless of source (AudioContext sample rate)

### Track creation
- `p.api.createAudioTrack(au)` works — returns TrackBox with type=2 (audio)
- TrackBox has: `regions` (Field), `target` (PointerField), `clips`, `index`, `type`, `enabled`

### Volume/panning on audio units
- `au.volume.setValue(-30)` — works
- `au.panning.setValue(-0.7)` — works (range -1.0 to 1.0)

### Effects
- `p.api.insertEffect(au.audioEffects, ef.AudioNamed['Compressor'])` — works
- 15 audio effects available: Compressor, Crusher, DattorroReverb, Delay, Fold, Gate, Maximizer, NeuralAmp, Reverb, Revamp, StereoTool, Tidal, Vocoder, Waveshaper, Werkstatt

### BPM
- `p.api.setBpm(110)` — works

## What DOES NOT work

### AudioRegionBox placement — BLOCKED

The core blocker. Cannot place audio regions on tracks.

**MCP server approach (fails):**
```javascript
AudioRegionBox.create(boxGraph, uuid, (box) => {
    box.regions.refer(trackBox.regions);  // FAILS
    box.position.setValue(0);
    box.duration.setValue(durationPulses);
    box.audioFile.refer(audioFileBox.file);
});
```
Error: "Could not find PointerField at <uuid>/1"

**Root cause:**
- `trackBox.regions` is a `Field` — no `refer()` method
- `trackBox.target` IS a `PointerField` with `refer()`, but wrong vertex type:
  "36 does not satisfy any of the allowed types (38, 35, 0)"
- Type 36 = TrackBox, types 38/35/0 = NoteRegionBox/ValueRegionBox/?

**How NoteRegionBox does it (works):**
```javascript
const events = NoteEventCollectionBox.create(boxGraph, uuid);
NoteRegionBox.create(boxGraph, uuid, (box) => {
    box.regions.refer(events.owners);  // events.owners is a valid vertex
});
```
`events.owners` is a vertex that satisfies the `regions` PointerField type constraint.

**What AudioRegionBox needs:** an equivalent to `events.owners` — some vertex that satisfies types (38, 35, 0). Possibly an AudioFileBox field, or a separate collection box.

**Attempted and failed:**
- `trackBox.regions.box` → type mismatch
- `trackBox.target` → type mismatch (36 ≠ 38/35/0)
- `AudioFileBox.file` → not investigated yet (might work for `audioFile.refer()` but not `regions.refer()`)
- `api.createNotStretchedRegion(props)` → takes props object, shape unknown, throws "Cannot read properties of undefined (reading 'name')"

**Next steps to try:**
1. Inspect `AudioContentFactory.createNotStretchedRegion` source in the SDK bundle
2. Check if there's an `AudioCollectionBox` or `AudioContentBox` that provides an `owners` vertex
3. Try `api.createNotStretchedClip(props)` with various prop shapes
4. Look at the openDAW UI source for how audio drag-and-drop creates regions

### AudioUnitBox creation — BLOCKED

`p.api.createAudioUnit` does not exist. `AudioUnitBox.create(boxGraph, uuid)` without constructor callback fails: "PointerField (collection) requires an edge".

The box needs to be wired to `rootBox.audioUnits` in the same transaction. The constructor callback approach (`AudioUnitBox.create(boxGraph, uuid, (box) => { ... })`) fails with "box.name.setValue is not a function" — the box isn't fully initialized during the callback.

**Workaround:** Use the single existing audio unit (units[0]) and create multiple tracks on it. Limitation: volume/panning is per-unit, not per-track, so all stems share one volume/panning.

### `AudioData.fromAudioBuffer` — does not exist

MCP server references this. Correct function: `window.DAW_audioBufferToAudioData(audioBuffer)`.

### `sampleManager.default` — undefined

MCP server calls `window.DAW_sampleManager.default.load(...)`. `default` doesn't exist. SampleManager methods: `fetch`, `remove`, `invalidate`, `register`, `record`, `getOrCreate`, `getAudioData`.

## Global DAW_ variables (full list)

```
DAW_audioContext          — AudioContext (44100Hz)
DAW_EffectFactories       — { AudioNamed: {...}, MidiNamed: {...} }
DAW_UUID                  — UUID generator
DAW_PPQN                  — { Quarter: 960, ... }
DAW_Option                — Option monad (None, wrap)
DAW_WavFile               — WavFile.encodeFloats(audioBuffer)
DAW_AudioData             — AudioData.create(sr, frames, channels)
DAW_localAudioBuffers     — Map<UUID, AudioBuffer>
DAW_sampleManager         — sample manager (no .default)
DAW_audioBufferToAudioData — (audioBuffer) → { sampleRate, numberOfFrames, numberOfChannels, frames }
DAW_AudioFileBox          — AudioFileBox.create(graph, uuid, callback?)
DAW_AudioRegionBox        — AudioRegionBox.create(graph, uuid, callback?)
DAW_ValueEventCollectionBox
DAW_NoteEventCollectionBox
DAW_NoteRegionBox
DAW_NoteEventBox
DAW_AudioOfflineRenderer  — .start(project, option, onProgress, undefined, {sample_rate})
```

## Playwright API notes

- `page.evaluate(js)` — ONE argument only. No positional args, no `timeout` kwarg.
- Pass data via string interpolation: `f"({fn})({json.dumps(data)})"`
- For async functions: `page.evaluate("async () => { ... }")`
- Multiple page.reload() corrupts DAW state — restart Vite + fresh browser instead
