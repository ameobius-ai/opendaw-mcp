# MIDI / Synth Pipeline — openDAW headless

How to drive MIDI synthesizers (Vaporisateur, Nano, Soundfont, Apparat) from the MCP bridge.
Established July 2, updated July 2 with NoteRegionBox fix + offline engine conflict resolution.

## The bug that was hiding in plain sight

`create_note_track` and `create_note` were both hardcoded to `p.primaryAudioUnitBox` —
the OUTPUT audio unit. The output AU has no synth device, so MIDI notes landed on a track
with no instrument to play them. Symptom: no error, no audio, silent export.

**Fix**: both tools now accept `unit_index` (default -1 = search all AUs for note tracks).
`create_note_track(unit_index=-1)` resolves the target AU; `create_note(unit_index=-1)`
finds note tracks on the specified AU or across all AUs.

## create_synth_track — the missing tool

`create_instrument_track` makes a Tape device (audio playback). There was no tool for
making a synth device (MIDI playback). `create_synth_track` fills that gap.

```python
# MCP call
create_synth_track(name="Lead", synth_type="vaporisateur")
# → {unit_index: 2, track_index: 0, synth_type: "vaporisateur", ...}
```

### Synth box creation pattern — CORRECT (InstrumentFactories)

**IMPORTANT**: Do NOT use raw `SynthDeviceBox.create()` — it produces NaN values that
crash the AudioWorklet. Use `InstrumentFactories` which sets all required init values.

```javascript
// In headless-daw/src/main.ts — add these imports:
import { InstrumentFactories } from "@opendaw/studio-core";
// Also need IconSymbol (from @opendaw/studio-enums or re-exported from studio-core)
w.DAW_InstrumentFactories = InstrumentFactories;
w.DAW_IconSymbol = IconSymbol; // ← still needs to be imported

// In MCP evaluate (create_synth_track):
const InstrumentFactories = window.DAW_InstrumentFactories;
const IconSymbol = window.DAW_IconSymbol;
const synthMap = {
    vaporisateur: InstrumentFactories.Vaporisateur,
    nano: InstrumentFactories.Nano,
    soundfont: InstrumentFactories.Soundfont,
    apparat: InstrumentFactories.Apparat,
};
const Factory = synthMap[synthType] || InstrumentFactories.Vaporisateur;

p.editing.modify(() => {
    captureBox = CaptureAudioBox.create(p.boxGraph, UUID.generate());
    instrumentAU = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.type.setValue(AudioUnitType.Instrument);
        box.collection.refer(rootBox.audioUnits);
        box.output.refer(primaryAudioBusBox.input);
        box.capture.refer(captureBox);
        box.index.setValue(0);
        box.volume.setValue(0.767835); // 0 dB
    });
    // Use factory — sets cutoff, resonance, ADSR, oscillators, voicing, LFO, etc.
    synthDevice = Factory.create(
        p.boxGraph,
        instrumentAU.input,  // host field
        name,                // display name
        IconSymbol.Piano     // icon (or appropriate per synth type)
    );
    trackBox = p.api.createNoteTrack(instrumentAU);
});
```

**Why raw `DeviceBox.create()` fails**: The box schema (`VaporisateurDeviceBox.ts` in
forge-boxes) defines `oscillators` as an ArrayField with `length: 2` and default values
like `volume: Number.NEGATIVE_INFINITY`. But `VaporisateurDeviceProcessor` reads these
through `bindParameter()` which expects `setInitValue()` to have been called. Without
the factory, oscillator waveforms are `undefined` → `ClassicWaveform[undefined]` → NaN
in DSP → `assertSanity()` crash → `ErrorEvent` → auto-restart loop → silence.

See "RESOLVED: AudioWorklet crash" section below for the full error capture and fix details.

## headless-daw lazy-load imports — REQUIRED

Synth DeviceBox classes are NOT loaded by default. They must be added to the
lazy-load block in `headless-daw/src/main.ts`:

```typescript
try {
    const boxes = await import("@opendaw/studio-boxes");
    // ... existing imports ...
    w.DAW_VaporisateurDeviceBox = boxes.VaporisateurDeviceBox;
    w.DAW_NanoDeviceBox = boxes.NanoDeviceBox;
    w.DAW_SoundfontDeviceBox = boxes.SoundfontDeviceBox;
    w.DAW_ApparatDeviceBox = boxes.ApparatDeviceBox;
} catch (e) { /* ... */ }
```

All four are exported from `@opendaw/studio-boxes/dist/index.js` (verified).
Without these window globals, `create_synth_track` throws
`"Synth type 'X' not loaded. Check headless-daw imports."`

**After editing main.ts, Vite must restart** to pick up the new imports.

## Available synth types

| synth_type | DeviceBox | Description |
|------------|-----------|-------------|
| vaporisateur | VaporisateurDeviceBox | Subtractive synth (default). Oscillators + filter + LFO + noise. Fields: volume, octave, tune, waveform, cutoff, resonance, attack, decay, sustain, release, filterEnvelope, glideTime, voicingMode, unisonCount, unisonDetune, unisonStereo, filterOrder, filterKeyboard |
| nano | NanoDeviceBox | Simple synth |
| soundfont | SoundfontDeviceBox | SF2 player (needs a loaded SoundfontFileBox) |
| apparat | ApparatDeviceBox | FM synth |

Vaporisateur is the default and the most versatile — 2 oscillators, unison, filter envelope.

## NoteRegionBox — the CORRECT way to place notes on the timeline (July 2 fix)

**Critical discovery**: `create_note` was using `NoteClipBox` (via `api.createNoteClip`),
which is a *clip container* — it has no `position` field and does NOT place notes on the
timeline. The real-time engine reads clips directly so it kind of worked, but the
**OfflineEngineRenderer never sees notes placed this way** → silent export.

The correct pattern (from openDAW's own `ProjectApi.createNoteRegion` and
`Project.#commitCapturedNotes`) uses **NoteRegionBox**, which has `position`, `duration`,
`loopDuration`, `eventOffset`, and `events` (pointing to a NoteEventCollectionBox).

### NoteRegionBox + NoteEventBox creation pattern

```javascript
const NoteEventCollectionBox = window.DAW_NoteEventCollectionBox;
const NoteRegionBox = window.DAW_NoteRegionBox;
const NoteEventBox = window.DAW_NoteEventBox;
const Quarter = PPQN.Quarter;
const startPosition = Math.round(startBeat * Quarter);
const noteDuration = Math.round(durationBeats * Quarter);

p.editing.modify(() => {
    // 1. Create the event collection (holds NoteEventBox instances)
    const collection = NoteEventCollectionBox.create(bg, UUID.generate());

    // 2. Create NoteRegionBox — places notes on the timeline
    //    ORDER MATTERS: events.refer BEFORE regions.refer
    //    Reversed order → "Edge has unannounced vertex" error
    const regionBox = NoteRegionBox.create(bg, UUID.generate(), (box) => {
        box.position.setValue(startPosition);
        box.label.setValue("Note " + pitch);
        box.mute.setValue(false);
        box.duration.setValue(noteDuration);
        box.loopDuration.setValue(0);           // loopOffset first
        box.loopDuration.setValue(noteDuration); // then loopDuration (matches ProjectApi)
        box.eventOffset.setValue(0);
        box.events.refer(collection.owners);    // ← BEFORE regions.refer
        box.regions.refer(trackBox.regions);
    });

    // 3. Create the note event (position is RELATIVE to region start)
    NoteEventBox.create(bg, UUID.generate(), (box) => {
        box.position.setValue(0);               // relative to region start, NOT absolute
        box.duration.setValue(noteDuration);
        box.velocity.setValue(velocity);
        box.pitch.setValue(pitch);
        box.chance.setValue(100);
        box.cent.setValue(0);
        box.events.refer(collection.events);
    });
});
```

### NoteClipBox vs NoteRegionBox — field comparison

| Feature | NoteClipBox | NoteRegionBox |
|---------|-------------|---------------|
| position | ❌ no field | ✅ Int32Field (ppqn) |
| duration | ✅ Int32Field | ✅ Int32Field |
| events | ✅ PointerField<NoteEventCollection> | ✅ PointerField<NoteEventCollection> |
| regions | ❌ no field | ✅ PointerField<RegionCollection> |
| clips | ✅ PointerField<ClipCollection> | ❌ no field |
| loopDuration | ❌ | ✅ Int32Field |
| eventOffset | ❌ | ✅ Int32Field |
| Used by timeline | via clips collection | via regions collection |

**Rule**: Use NoteRegionBox for notes that must render in offline export. NoteClipBox is
for the clip launcher / session view, not for timeline placement.

## Offline engine conflict — "Already connected" (July 2 fix)

**Problem**: `OfflineEngineRenderer.start()` creates its own AudioContext inside a Worker.
If the real-time engine's AudioContext is still running, you get:
`"Failed to construct 'AudioWorkletNode': ... Already connected"` or
`"AudioWorkletNode cannot be created: No execution context available."`

**Fix**: Suspend (NOT close!) the engine AudioContext before offline render, resume after.

### main.ts — DAW_stopEngine / DAW_resumeEngine

```typescript
// Suspend — required before OfflineEngineRenderer
w.DAW_stopEngine = async (): Promise<void> => {
    if (!engineWorklet) return;
    try { await audioContext.suspend(); } catch(e) { /* already suspended */ }
};

// Resume — after offline render completes
w.DAW_resumeEngine = async (): Promise<void> => {
    if (!engineWorklet) return;
    try { await audioContext.resume(); } catch(e) { /* already running */ }
};
```

**NEVER use `audioContext.close()`** — a closed AudioContext cannot be recreated in the
same page context. You'll get "No execution context available" on the next engine start.
Suspend/resume is the safe cycle.

### _export_offline — Python side

```python
async def _export_offline(safe_name, sample_rate):
    # Suspend engine if running
    was_running = await bridge.evaluate("() => window.DAW_engineStarted && window.DAW_engineStarted()")
    if was_running:
        await bridge.evaluate("() => window.DAW_stopEngine()")
        await asyncio.sleep(0.5)  # let suspend settle

    # ... do offline render ...

    # Resume engine if it was running
    if was_running:
        await bridge.evaluate("() => window.DAW_resumeEngine()")
```

## Export duration — lastRegionAction() misses MIDI (July 2 fix)

**Problem**: `Project.lastRegionAction()` only scans `trackAdapter.regions.collection`
for audio regions. MIDI-only projects (notes via NoteRegionBox on note tracks) return
`endPosition = 0` → OfflineEngineRenderer renders 0→0 → silence or 0.003s file.

**Fix**: Compute endPos from ALL content (audio regions + note regions/events) and pass
`range: { start: 0, end: endPos }` in the ExportConfiguration:

```javascript
const exportConfig = {
    stems: { [outputUuid]: { includeAudioEffects: true, ... } },
    range: { start: 0, end: endPos }  // ← explicit range overrides lastRegionAction()
};
```

The endPos computation scans note tracks' `regions.pointerHub.incoming()` for
NoteRegionBox position+duration, plus individual NoteEventBox position+duration within
each region's collection. Add 1 bar (Quarter*4) padding for release tails.

## RESOLVED: AudioWorklet crash — root cause found (July 2, session 2)

### Root cause: `VaporisateurDeviceBox.create()` without init values → NaN → crash

The AudioWorklet processor crashed with `Error: AudioBuffer is invalid (NaN)` because
synth device boxes were created **raw** — only `box.label.setValue()` and
`box.host.refer()` — without setting init values for any DSP parameters.

`VaporisateurDeviceProcessor` binds 25+ parameters via `bindParameter()` in its
constructor. When oscillator waveforms, cutoff, resonance, attack/decay/sustain/release,
unison settings, etc. are all undefined/NaN, the DSP math produces NaN in the audio
output buffer. `assertSanity()` in the processor catches this and throws, which triggers
`engineToClient.error(reason)` → `ErrorEvent` → Project's error handler kills and
auto-restarts the worklet (which crashes again → infinite restart loop → silence).

### Error capture technique (how we got the stack trace)

`Project.startAudioWorklet()` registers `worklet.addEventListener("error", handler)` in
bubble phase that kills+restarts the worklet, hiding the real error. To capture it:

```javascript
// In DAW_startEngine, AFTER project.startAudioWorklet() returns the worklet:
const errorCapture = (event: Event) => {
    const errEvent = event as ErrorEvent;
    console.error("[engine-capture] type:", event.type);
    console.error("[engine-capture] error:", errEvent.error);
    console.error("[engine-capture] error.stack:", errEvent.error?.stack);
    console.error("[engine-capture] error.toString:", String(errEvent.error));
};
// capture=true fires BEFORE bubble-phase handlers that kill the worklet
engineWorklet.addEventListener("error", errorCapture, true);
engineWorklet.addEventListener("processorerror", errorCapture, true);
```

This revealed:
```
Error: AudioBuffer is invalid (NaN)
    at r.assertSanity (processors.js:1:43836)
    at uA.finishProcess (processors.js:79:97363)
    at uA.process (processors.js:79:77920)
    at f_.process → A_.render
```

### Fix: use InstrumentFactories, not raw DeviceBox.create()

**WRONG** (what we were doing — produces NaN):
```javascript
synthDevice = VaporisateurDeviceBox.create(p.boxGraph, UUID.generate(), (box) => {
    box.label.setValue(name);
    box.host.refer(instrumentAU.input);
    // ← NO init values! All DSP params are NaN → crash
});
```

**CORRECT** (use the factory — sets all init values):
```javascript
// In headless-daw/src/main.ts:
import { InstrumentFactories } from "@opendaw/studio-core";
w.DAW_InstrumentFactories = InstrumentFactories;

// In MCP create_synth_track:
const InstrumentFactories = window.DAW_InstrumentFactories;
const IconSymbol = window.DAW_IconSymbol; // also needs importing
const synthDevice = InstrumentFactories.Vaporisateur.create(
    p.boxGraph,
    instrumentAU.input,  // host field
    name,                // display name
    IconSymbol.Piano     // icon
);
```

The factory sets ALL required init values:
```typescript
// InstrumentFactories.Vaporisateur.create does:
box.cutoff.setInitValue(8000.0)
box.resonance.setInitValue(0.1)
box.attack.setInitValue(0.005)
box.decay.setInitValue(0.100)
box.sustain.setInitValue(0.5)
box.release.setInitValue(0.5)
box.voicingMode.setInitValue(VoicingMode.Polyphonic)
box.lfo.rate.setInitValue(1.0)
box.oscillators.fields()[0].waveform.setInitValue(ClassicWaveform.saw)
box.oscillators.fields()[0].volume.setInitValue(-6.0)
box.oscillators.fields()[1].volume.setInitValue(Number.NEGATIVE_INFINITY)
box.oscillators.fields()[1].waveform.setInitValue(ClassicWaveform.square)
box.version.setValue(2)
```

### Still needed to complete the fix

1. **Import IconSymbol** in headless-daw main.ts — `import { IconSymbol } from "@opendaw/studio-enums"`
   (or re-export from studio-core). The factory requires an icon parameter.
2. **Update `create_synth_track` in server.py** — replace raw `SynthDeviceBox.create()`
   with `InstrumentFactories[synthType].create(graph, host, name, icon)` for all 4 types.
3. **Verify end-to-end** — synth + notes → engine → audio output > 0.
4. **File upstream** — `lastRegionAction()` missing note regions is still a real bug.

### What was NOT the problem (confirmed ruled out)

- ~~AudioWorklet thread not processing~~ — WebAudio works (oscillator test: 255/128)
- ~~Chromium autoplay policy~~ — AudioContext resumes fine
- ~~NoteClipBox vs NoteRegionBox~~ — structure was correct
- ~~Note event delivery~~ — crash happens in DSP, not in note pipeline
- ~~Headless Chromium audio device~~ — WebAudio oscillator works fine

## Full MIDI playback sequence (end-to-end)

```python
# 1. Create a synth track
synth = create_synth_track(name="Bass", synth_type="vaporisateur")
# → unit_index=1, track_index=0

# 2. Add notes (C major arpeggio: C4, E4, G4, C5)
for i, (pitch, beat) in enumerate([(60,0), (64,0.5), (67,1), (72,1.5)]):
    create_note(track_index=0, pitch=pitch, start_beat=beat,
                duration_beats=0.5, velocity=0.8, unit_index=1)

# 3. Start engine (deferred — serializes current boxGraph)
start_engine()

# 4. Export
export_mix(filename="synth_test", sample_rate=48000, method="auto")
```

## Pitfalls

- **RAW `DeviceBox.create()` produces NaN → AudioWorklet crash** — this is the #1 pitfall.
  Always use `InstrumentFactories.<Synth>.create(graph, host, name, icon)` instead of raw
  `VaporisateurDeviceBox.create(graph, uuid, box => { ... })`. The factory calls
  `setInitValue()` for all 25+ DSP parameters (cutoff, resonance, ADSR, oscillators,
  voicing, LFO). Without it, undefined params → NaN in audio buffer → `assertSanity()`
  crash → `ErrorEvent` → auto-restart loop → silence on ALL export. See "RESOLVED"
  section for full diagnostic chain.
- **ErrorEvent capture technique** — `Project.startAudioWorklet()` registers bubble-phase
  error handlers that kill+restart the worklet, hiding the real error. To capture the
  actual error reason, add listeners with `capture=true` AFTER `startAudioWorklet()`
  returns: `engineWorklet.addEventListener("error", handler, true)`. The `true` (capture)
  flag makes your handler fire BEFORE Project's kill-and-restart handler.
- **AudioWorklet processor crash = silence on ALL export** — if you see
  `warning: ErrorEvent` followed by `debug: start AudioWorklet` in console, the
  engine-processor crashed and auto-restarted. BOTH realtime and offline export will
  produce silence (max_sample: 0), even for Tape + audio regions (not just MIDI). A raw
  OscillatorNode will still produce audio (proving WebAudio works) — the crash is inside
  the AudioWorklet render thread. See "Open blocker" above for the full diagnostic chain.
- **Do NOT trust "realtime export works" from older summaries** — earlier compaction
  claims that realtime export produced audio were unverified. WAV files of the correct
  size were created (ScriptProcessorNode fills buffers regardless of content) but
  max_sample was never checked. Always analyser-verify: connect an AnalyserNode to
  engineWorklet output 0, play, check maxFreq/maxTime > 0.
- **NoteClipBox vs NoteRegionBox** — NoteClipBox has no `position` field. For timeline
  placement and offline render, ALWAYS use NoteRegionBox. NoteClipBox is for the clip
  launcher, not the timeline.
- **NoteRegionBox creation order** — `events.refer(collection.owners)` MUST come before
  `regions.refer(trackBox.regions)`. Reversed → "Edge has unannounced vertex" error.
- **NoteEventBox position is relative** — when using NoteRegionBox, NoteEventBox.position
  is relative to the region start (0 = region beginning), NOT absolute timeline position.
- **Note tracks on the wrong AU** — the original bug. `create_note_track()` with no args
  defaults to the output AU, which has no synth. Always pass `unit_index` of the synth AU,
  or use `create_synth_track` which creates both in one call.
- **Synth DeviceBox not in window globals** — add to headless-daw lazy-load imports,
  restart Vite. The MCP tool will throw a clear error if the global is missing.
- **Soundfont needs a sample** — SoundfontDeviceBox requires a loaded SoundfontFileBox
  before it produces audio. Vaporisateur/Nano/Apparat are self-contained.
- **Offline + engine "Already connected"** — suspend AudioContext before offline render,
  resume after. NEVER close (cannot be recreated).
- **lastRegionAction() misses MIDI** — compute endPos manually from note regions/events
  and pass explicit `range` in ExportConfiguration.
- **f-string `}}` bug** — when embedding JS object literals `{}` inside Python f-strings,
  every `{` and `}` in the JS must be doubled to `{{` and `}}`. A single `};` in an
  f-string raises `SyntaxError: f-string: single '}' is not allowed`. Check all
  `return { ... };` blocks in evaluate strings.
- **Vite restart after main.ts edits** — new lazy-load imports only take effect after
  Vite dev server restart. Stale server = `"not loaded"` error at runtime.
