# openDAW Offline Render — Troubleshooting Guide

## OER (OfflineEngineRenderer) — Working Setup

### Chromium launch — CORRECT args
```python
args=['--enable-features=SharedArrayBuffer', '--unlimited-storage',
      '--disable-site-isolation-trials', '--disk-cache-size=1',
      '--media-cache-size=1', '--disable-application-cache']
```
Do NOT use `--disable-web-security` — breaks COOP/COEP, SAB becomes undefined.

### Storage quota — REAL FIX: launch_persistent_context with fresh tmpdir
`--unlimited-storage` flag alone is NOT sufficient. Browser IndexedDB caches every decoded stem (7×~50MB=350MB) and accumulates across renders. The REAL fix is using `p.chromium.launch_persistent_context(tmpdir, ...)` with a FRESH `tempfile.mkdtemp()` profile directory each run.

```python
import tempfile, shutil
tmp_profile = tempfile.mkdtemp(prefix='opendaw_profile_')
context = await p.chromium.launch_persistent_context(
    tmp_profile, headless=True,
    args=['--enable-features=SharedArrayBuffer', '--unlimited-storage',
          '--disable-site-isolation-trials', '--disk-cache-size=1',
          '--media-cache-size=1', '--disable-application-cache'],
    accept_downloads=True,
)
# ... render ...
shutil.rmtree(tmp_profile)
```

Between renders also clean: `rm -rf /tmp/playwright* /tmp/.com.google.Chrome* /tmp/pw-* /tmp/.org.chromium*`

### OER render call
```javascript
const core = await import('/node_modules/.vite/deps/@opendaw_studio-core.js');
const OER = core.OfflineEngineRenderer;
const Option = window.DAW_Option;
const projectCopy = p.copy();
// OER.start(project, Option<ExportConfiguration>, progress, abortSignal?)
```

### CRITICAL — releaseWorklet() before OER, restart after (verified July 2)
`OfflineEngineRenderer.start()` throws `Error: Already connected` at `LiveStreamReceiver.connect()` because the main `EngineWorklet` already holds the `liveStreamReceiver` connection (EngineWorklet.ts:234). **Fix:** call `p.engine.releaseWorklet()` before render, `p.startAudioWorklet()` after.

```javascript
// OfflineEngineRenderer expects DefaultObservableValue<number>, NOT a bare function
const progress = {setValue: (v) => console.log("Render: " + Math.round(v*100) + "%")};

p.engine.releaseWorklet();  // releases LiveStreamReceiver connection
const audioData = await OfflineEngineRenderer.start(p, Option.None, progress, undefined, 48000);
try { p.startAudioWorklet(); } catch(_) {}  // restore main engine
```

`EngineFacade.releaseWorklet()` (EngineFacade.ts:67-72) calls `worklet.terminate()` → `this.#terminator.terminate()` (releases all owned resources including `liveStreamReceiver.connect()`) + `this.disconnect()` (disconnects AudioWorkletNode). Then sets `this.#worklet = Option.None`.

**AudioOfflineRenderer (AOR)** does NOT need `releaseWorklet()` — it calls `source.copy()` internally, which creates a new `Project` with its own `liveStreamReceiver`. No conflict. But AOR still produces silence if TapeDeviceBox is missing (see below).

**Return types:** OER returns `AudioData` (has `.frames: Float32Array[]` and `.sampleRate`). AOR returns `AudioBuffer` (has `.getChannelData(ch)` and `.duration`). `WavFile.encodeFloats()` accepts both.

### CRITICAL — output AU volume DEFAULTS TO 0 (raw) = -96 dB = MUTE
`VolumeMapper = ValueMapping.decibel(-96.0, -9.0, +6.0)` — this is **powerByCenter**, NOT exponential. The `y(x)` function returns `-Infinity` when `x <= 0.0`. So raw value 0 = -∞ dB = SILENCE, not 0 dB.

**0 dB = raw value 0.767835** (computed from powerByCenter: `exp = log(102/87)/log(2) ≈ 0.2295`, `raw = ((0-(-96))/102)^(1/0.2295) = 0.767835`).
```javascript
p.editing.modify(() => { outputAu.volume.setValue(0.767835); });  // 0 dB
```

**dB → raw conversion table** (use in Python MCP tools):
| dB | raw | |
|-----|-------|---|
| +6 | 1.0 | max |
| 0 | 0.768 | unity |
| -3 | 0.669 | |
| -6 | 0.580 | |
| -8 | 0.526 | |
| -12 | 0.429 | |
| -96 | 0.0 | mute |

Python converter:
```python
import math
MIN_DB, CENTER_DB, MAX_DB = -96.0, -9.0, 6.0
_EXP = math.log((MAX_DB - MIN_DB) / (CENTER_DB - MIN_DB)) / math.log(2)
def db_to_raw(db):
    if db <= MIN_DB: return 0.0
    if db >= MAX_DB: return 1.0
    return ((db - MIN_DB) / (MAX_DB - MIN_DB)) ** (1.0 / _EXP)
```

**Previous value 0.7339449541284403 was WRONG** — that was computed from exponential mapping, but VolumeMapper uses powerByCenter. Corrected July 2.

**MCP tool `set_track_volume(volume_db)` now converts dB→raw internally** — pass dB directly, not raw values.

### AudioOfflineRenderer (AOR) — alternative
`window.DAW_AudioOfflineRenderer` — partially working:
- Returns an `AudioBuffer` (not `{frames}` object like OER) — use `.getChannelData(0)` instead of `.frames[0]`
- Accepts live project (no `p.copy()` needed): `AOR.start(p, Option.None, {setValue: ()=>{}})`
- Also produces silence if output AU volume is 0

### Large files (>~95MB WAV)
Cannot be transferred via base64 through page.evaluate — Node.js string length limit (`ERR_STRING_TOO_LONG`). Use a download trigger or chunked transfer instead.

### Effect stability table (CORRECTED July 2)
| Effect | Status | Notes |
|--------|--------|-------|
| DattorroReverb | ✅ Works | Verified F08h. Params: preDelay, bandwidth, decay, damping, wet, dry |
| Revamp (master EQ) | ✅ Works | highShelf/highBell on output AU. Verified F09: HS+8 doubled air |
| Revamp (per-stem) | ✅ Works | Same DSP as master Revamp |
| Waveshaper | ✅ Works | CORRECTED July 2: DSP runs unconditionally. 0dB inputGain = no-op. Set +6 to +12dB |
| Tidal | ✅ Works | CORRECTED July 2: audio loop unconditional. BlockFlag check only affects UI phase |
| Delay | ✅ Works | CORRECTED July 2: processes unconditionally, no transport gating |
| Compressor | ✅ Works | Sidechain via ProcessPhase.Before. Potential graph cycle if sidechain creates loop |
| Maximizer | ✅ Works | Params: lookahead(bool), threshold(float). Tested on output AU, threshold -1dB ceiling |

### Compressor sidechain connection (VERIFIED July 2)
`compBox.sideChain` is `PointerField<Pointers.SideChain>`. Refer to the **source AU box**, NOT its output field:
```javascript
// CORRECT — refer to the drums AudioUnitBox
compBox.sideChain.refer(drumsAU);

// WRONG — "40 does not satisfy any of the allowed types"
compBox.sideChain.refer(drumsAU.output);  // ← type mismatch
```
Sidechain params: threshold -20dB, ratio 4:1, attack 5ms, release 80ms, makeup +3dB, mix 1.0.
`hasSidechainDependents()` checks edges from effect boxes — a sidechain source AU cannot be frozen.

### Compressor full parameter list
`lookahead`(bool), `automakeup`(bool), `autoattack`(bool), `autorelease`(bool), `inputgain`(float), `threshold`(float, default -10), `ratio`(float, default 2), `knee`(float), `attack`(float), `release`(float, default 25), `makeup`(float, default 0), `mix`(float, default 1), `sideChain`(PointerField)

### Reverb full parameter list
`decay`(float, default 0.5), `preDelay`(float, default 0.001), `damp`(float, default 0.5), `filter`(int, default 0), `wet`(float, default -3), `dry`(float, default 0). All automatable via `add_automation` MCP tool.

### Parameter automation (VERIFIED July 2)
```javascript
// 1. Create automation track targeting an automatable field
const autoTrack = p.api.createAutomationTrack(au, effectBox[paramName]);
// 2. Create value clip on the track
const valueClip = p.api.createValueClip(autoTrack, 0, {name: paramName});
// 3. Get event collection from clip
const collection = valueClip.events?.targetVertex?.unwrap?.()?.box;
// 4. Create ValueEventBox per automation point
ValueEventBox.create(p.boxGraph, UUID.generate(), (box) => {
    box.events.refer(collection.events);
    box.position.setValue(Math.round(beatPos * PPQN.Quarter));  // ppqn
    box.index.setValue(i);
    box.value.setValue(0.0_to_1.0);  // normalized 0-1
    box.interpolation.setValue(1);  // 1=linear
});
```
MCP tool: `add_automation(unit_index, effect_index, parameter_name, points)` where points = JSON `[[beat, value_0_to_1], ...]`.
Tested: Reverb decay automated [0.3→0.8→0.3] over 30 beats. Export with automation → max 1.031, 11.4MB WAV.

### Effect limits
Adding 5+ effects across 5 stems triggers: `Error: [remove] Edge has unannounced vertex. ({r (0)})`. Box graph can't handle effect node count during offline render termination. **Add effects ONE AT A TIME per render.**

### July 2 Session — `--disable-web-security` causes SILENT renders
**CONFIRMED**: server.py was using `args=['--disable-web-security', '--enable-features=SharedArrayBuffer']`. Even though SAB check passed, `AudioOfflineRenderer.start()` produced 256 seconds of silence (peak=0) on a test sine wave. The `--disable-web-security` flag breaks COOP/COEP headers, which causes AudioWorklet processors (EngineProcessor) to fail silently — no audio output.

**Fix**: Remove `--disable-web-security` from server.py. Use only:
```python
args=['--enable-features=SharedArrayBuffer', '--unlimited-storage',
      '--disable-site-isolation-trials', '--disk-cache-size=1',
      '--media-cache-size=1', '--disable-application-cache']
```

### July 2 Session — Missing TapeDeviceBox → silence (ROOT CAUSE CONFIRMED, AUDIO VERIFIED)
`createAudioTrack` on `primaryAudioUnitBox` creates a TrackBox but NO instrument. AudioUnit needs a `TapeDeviceBox` to play audio regions. Without it, regions exist but produce zero output.

**VERIFIED**: `maxAmplitude: 0.592, hasSignal: True` — real-time AudioWorklet output confirmed for the first time on July 2.

**Full root cause chain** (traced through source code):
1. `ProjectSkeleton.empty()` creates: `primaryAudioBus` (AudioBusBox) + `primaryAudioOutputUnit` (AudioUnitBox, type=Output). Line 76: `primaryAudioBus.output.refer(primaryAudioOutputUnit.input)` — connects bus → AU input.
2. `AudioUnitBoxAdapter.input` → `AudioUnitInput` → watches `pointerHub` for incoming pointers. For output AU, `AudioBusBox.output` points to `AudioUnitBox.input`.
3. In `EngineProcessor`, `InstrumentDeviceProcessorFactory.create()` is called with `input.box.box`. For `AudioBusBox`, it creates `AudioBusProcessor` (NOT TapeDeviceProcessor).
4. `AudioBusProcessor` is a simple mixer — it sums `#sources` array via `addAudioSource()`. If `#sources` is empty → silence.
5. `AudioDeviceChain.#wire()` connects `channelStrip.audioOutput` → `audioBus.addAudioSource()`. But this connects the OUTPUT AU's channel strip TO the bus. The bus needs an INSTRUMENT AU feeding it.
6. `TapeDeviceProcessor` (created from `TapeDeviceBox`) is the processor that reads `AudioRegionBox` entries via `adapter.regions.collection.iterateRange(p0, p1)` and writes audio to its `audioOutput`.
7. Without a `TapeDeviceBox` in the project, no `TapeDeviceProcessor` exists, no audio regions are read, `AudioBusProcessor.#sources` stays empty → silence.

**HEADLESS MODE — `p.api.createInstrument()` is NOT available.** Must create boxes manually. See `references/headless-instrument-au-2026-07-02.md` for the full verified recipe and test script.

**Required sequence (HEADLESS — manual box creation)**:
```javascript
const AudioUnitBox = window.DAW_AudioUnitBox;
const TapeDeviceBox = window.DAW_TapeDeviceBox;
const CaptureAudioBox = window.DAW_CaptureAudioBox;
const AudioUnitType = window.DAW_AudioUnitType;

p.editing.modify(() => {
    // 1. CaptureAudioBox (required for instrument AU)
    captureBox = CaptureAudioBox.create(p.boxGraph, UUID.generate());

    // 2. Instrument AudioUnitBox — output → primaryAudioBusBox.input
    instrumentAU = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.type.setValue(AudioUnitType.Instrument);
        box.collection.refer(rootBox.audioUnits);
        box.output.refer(primaryAudioBusBox.input);
        box.capture.refer(captureBox);
        box.index.setValue(0);
        box.volume.setValue(0.767835); // 0 dB (powerByCenter, corrected July 2)
    });

    // 3. TapeDeviceBox — THE instrument that reads audio regions
    tapeDevice = TapeDeviceBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.label.setValue("Tape");
        box.host.refer(instrumentAU.input);  // ← THE MISSING LINK
    });

    // 4. Audio track on instrument AU
    trackBox = p.api.createAudioTrack(instrumentAU);

    // 5. AudioFileBox + region
    audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.fileName.setValue(sampleId);
        box.startInSeconds.setValue(0.0);
        box.endInSeconds.setValue(audioBuffer.duration);
    });
    regionBox = p.api.createNotStretchedRegion({
        boxGraph: p.boxGraph, targetTrack: trackBox, position: 0,
        audioFileBox: audioFileBox,
        sample: { name: sampleId, duration: audioBuffer.duration, bpm: 120 },
    });

    // 6. Set output AU volume to 0 dB too
    p.primaryAudioUnitBox.volume.setValue(0.767835);  // powerByCenter, corrected July 2
});

// 7. Start engine AFTER all boxes created (deferred start)
await window.DAW_startEngine();
```

**MCP tool**: `mcp_opendaw_create_instrument_track(name="Tape")` — creates the full chain above and returns `unit_index` + `track_index`.

### July 2 Session — Export RESOLVED (TWO methods working)

**OfflineEngineRenderer WORKS** — produces real audio. Previous "Exponential is inverse" error was NOT reproducible in the current build with effects present. The `DelayDeviceDsp.FilterMapping` static initializer (`ValueMapping.exponential(20.0/sampleRate, 20000.0/sampleRate)`) works correctly because `setupWorkletGlobals()` sets `globalThis.sampleRate` BEFORE `import(config.processorsUrl)` in the worker (`offline-engine-main.ts:22-24`).

**Verified**: 30s anchor stem → 11.6MB WAV, max sample 0.451. 5-stem Серебро mix → 61.2s, 22.4MB, 48kHz, max 1.172.

**OfflineEngineRenderer export call (CORRECTED July 2)**:
```javascript
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
const outputUuid = String(units[0].address);
const exportConfig = {
    stems: { [outputUuid]: {
        includeAudioEffects: true,
        includeSends: true,
        useInstrumentOutput: false,
        fileName: "mix"
    }}
};
const progress = {setValue: (v) => {}};
const audioData = await OfflineEngineRenderer.start(
    p, Option.wrap(exportConfig), progress, undefined, 48000
);
// audioData.frames: Float32Array[], audioData.sampleRate: number
const wav = WavFile.encodeFloats(audioData);
```

**Real-time capture (FALLBACK method)** — ScriptProcessorNode connected to EngineWorklet output 0:
```javascript
// main.ts exposes DAW_captureRealtime(durationSeconds)
// Connects: engineWorklet.connect(scriptProcessor, 0) → processor.connect(ctx.destination)
// Collects Float32Array[] → AudioData → WavFile.encodeFloats
const audioData = await window.DAW_captureRealtime(durationSeconds);
```
Requires engine started. Records in real-time (slower than offline). Test: 31s, 10.4MB, max 0.480.

**MCP `export_mix(method="auto")`** — tries offline first, falls back to realtime. Also accepts `method="offline"` or `method="realtime"`.

**Per-stem export (`export_stems` MCP tool)** — each instrument AU as separate stereo pair:
```javascript
const stems = {};
for (let i = 1; i < units.length; i++) {  // skip output AU (index 0)
    stems[String(units[i].address)] = {
        includeAudioEffects: true, includeSends: false,
        useInstrumentOutput: true, fileName: "stem_" + i
    };
}
const audioData = await OfflineEngineRenderer.start(p, Option.wrap({stems}), progress, undefined, 48000);
// audioData.frames.length = numStems * 2 (interleaved stereo pairs)
```
Test: 2 stems → 4 channels, 22MB WAV.

**AudioOfflineRenderer** — `TypeError: Cannot create property 'onabort' on number '48000'` — API signature mismatch (4th param is abortSignal, not sampleRate). Use OfflineEngineRenderer instead.

### July 2 Session — Deferred engine start (DAW_startEngine)
**Problem**: `startAudioWorklet()` serializes `project.toArrayBuffer()` into `processorOptions` (EngineWorklet.ts:111). If called BEFORE tracks/regions are created, the processor gets an empty project. SyncSource (EngineWorklet.ts:236, `initialize=false`) only sends DELTAS, not initial state. So regions created after worklet start must propagate via SyncSource MessagePort — which can fail silently in headless mode.

**Fix**: Defer `startAudioWorklet()` until AFTER all setup (load audio, create track, place region, set volume). Expose `DAW_startEngine()` on window. MCP calls it explicitly before play/render.

```typescript
// main.ts — expose globals BEFORE starting worklet
w.DAW = project;  // etc.
w.DAW_startEngine = async () => {
    if (engineWorklet) return;
    engineWorklet = project.startAudioWorklet();  // serializes CURRENT boxGraph
    w.DAW_engineWorklet = engineWorklet;
    await project.engine.isReady();
};
w.DAW_engineStarted = () => engineWorklet !== null;
```

```python
# server.py — new MCP tool
@mcp.tool()
async def mcp_opendaw_start_engine() -> str:
    result = await bridge.evaluate("() => DAW_startEngine()")
```

**Export tool**: check `DAW_engineStarted()` before calling `releaseWorklet()` — if engine never started, skip release.

### July 2 Session — TapeDeviceProcessor transport flags
`TapeDeviceProcessor.#processBlock()` (line 112): `if (!Bits.every(flags, BlockFlag.transporting | BlockFlag.playing))` → fade out all voices + return. Audio only plays when transport is active. `engine.play()` sets `this.#timeInfo.transporting = true` (EngineProcessor.ts:494). `engine.stop(true)` clears it.

`adapter.regions.collection.iterateRange(p0, p1)` — iterates regions whose position range overlaps [p0, p1]. Region at position=0, duration=2s @ 120bpm = 3840 PPQN. If playback position > 3840, region is past and produces no audio. Use `engine.setPosition(0)` before `engine.play()` to start from beginning.

### July 2 Session — `place_audio_region` must use `api.createNotStretchedRegion()`
Manual `AudioRegionBox.create()` fails with "requires an edge" because the `events` field (field 5) needs a `ValueEventCollectionBox.owners` pointer. The API method handles this internally. See `references/mcp-api-fix-session-2026-07-02.md` for full details.

### Reverb params (subtile, "ушной оргазм")
preDelay 15ms, bandwidth 0.7, decay 0.5, damping 0.3 (dark), wet -12 dB (barely audible), dry 0 dB. maxS unchanged (0.64) — reverb adds spatial energy but not peak.

User directive: Suno vocals are already processed, effects must be SUBTLE. Wet -12 dB is the starting point.
