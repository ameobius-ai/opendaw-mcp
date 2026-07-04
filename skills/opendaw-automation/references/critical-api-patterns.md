# Critical API Patterns — openDAW headless (verified July 2)

Patterns that caused hours of debugging. Read before creating devices or starting engine.

## 1. Instrument/synth device creation — use InstrumentFactories, NOT raw DeviceBox.create()

**CRITICAL**: Creating synth devices (Vaporisateur, Nano, Soundfont, Apparat) via raw
`DeviceBox.create(graph, uuid, box => { box.host.refer(...) })` produces **NaN in audio
buffers** → `assertSanity()` crash → AudioWorklet ErrorEvent → auto-restart loop → silence
on ALL export (not just MIDI — Tape is affected too because the whole engine crashes).

Always use `InstrumentFactories`:
```javascript
// headless-daw/src/main.ts — add imports:
import { InstrumentFactories } from "@opendaw/studio-core";
// Also need IconSymbol from @opendaw/studio-enums
w.DAW_InstrumentFactories = InstrumentFactories;
w.DAW_IconSymbol = IconSymbol;

// In evaluate:
const Factory = window.DAW_InstrumentFactories.Vaporisateur; // or Nano/Soundfont/Apparat
const synth = Factory.create(p.boxGraph, au.input, "Lead", window.DAW_IconSymbol.Piano);
```

The factory calls `setInitValue()` for all 25+ DSP params (cutoff, resonance, ADSR,
oscillators, voicing, LFO). Without it, params are undefined → NaN → crash.

The `InstrumentFactories.Vaporisateur.create` function does:
```typescript
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

Same rule applies to EffectFactories (already used for audio effects — never raw create).

Source: `packages/studio/adapters/src/factories/InstrumentFactories.ts`

## 2. ErrorEvent capture — use capture=true to intercept before Project's kill+restart

`Project.startAudioWorklet()` (in `packages/studio/core/src/project/Project.ts`) registers
bubble-phase error handlers that kill+restart the worklet on any error, hiding the real
reason. To capture the actual error:

```javascript
// In DAW_startEngine, AFTER project.startAudioWorklet() returns the worklet:
const errorCapture = (event) => {
    console.error("[engine-capture] type:", event.type);
    console.error("[engine-capture] error:", event.error);
    console.error("[engine-capture] error.stack:", event.error?.stack);
    console.error("[engine-capture] error.toString:", String(event.error));
};
engineWorklet.addEventListener("error", errorCapture, true);
engineWorklet.addEventListener("processorerror", errorCapture, true);
```

The `true` (capture) flag fires BEFORE Project's bubble handler that calls
`lifecycle.terminate()` + `startAudioWorklet(restart)`.

This is how we discovered the `AudioBuffer is invalid (NaN)` root cause:
```
Error: AudioBuffer is invalid (NaN)
    at r.assertSanity (processors.js:1:43836)
    at uA.finishProcess (processors.js:79:97363)
    at uA.process (processors.js:79:77920)
```

## 3. Note tracks — MUST specify unit_index

When creating note tracks for MIDI playback, pass `unit_index` of the instrument AU that
contains the synth device. Default `-1` searches all AUs. Creating note tracks on the
output AU (which has no synth) → notes never play.

```javascript
// CORRECT — note track on the synth AU
const trackBox = p.api.createNoteTrack(instrumentAU);

// WRONG — note track on output AU (no synth → silence)
const trackBox = p.api.createNoteTrack(p.primaryAudioUnitBox);
```

## 4. Reset project — use box.delete(), not boxGraph.deleteBox()

```javascript
// CORRECT
p.editing.modify(() => {
    const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
    for (let i = units.length - 1; i >= 1; i--) {
        try { units[i].delete(); } catch(e) {}
    }
});

// WRONG — boxGraph.deleteBox is not a function
p.boxGraph.deleteBox(box);
```

## 5. BPM — use p.api.setBpm(), not timelineBox.tempo.setValue()

```javascript
// CORRECT
window.DAW.editing.modify(() => window.DAW.api.setBpm(120));

// WRONG — timelineBox.tempo is undefined
window.DAW.timelineBox.tempo.setValue(120);
```

## 6. Offline export — terminate engine, don't just suspend

`OfflineEngineRenderer.start()` creates its own AudioContext. If the engine's
AudioContext is still connected via `LiveStreamReceiver`, you get `"Already connected"`.

```javascript
// Terminate the worklet completely before offline render
if (window.DAW_engineWorklet) {
    window.DAW_engineWorklet.terminate();
    window.DAW_engineWorklet = null;
}
// Then run OfflineEngineRenderer.start()
```

`suspend()` alone may NOT be enough — `LiveStreamReceiver.connect` still throws
"Already connected" even when AudioContext is suspended. `terminate()` fully
disconnects the worklet.

**NEVER use `audioContext.close()`** — a closed AudioContext cannot be recreated.

## 7. createInstrument — return value shape + transaction requirement

`p.api.createInstrument(factory, options)` returns `{audioUnitBox, instrumentBox, trackBox}`, NOT the AU box directly.

```javascript
// CORRECT — extract .audioUnitBox from return value, call inside modify
let synthAU;
h.modify(() => {
    const result = p.api.createInstrument(IF.Vaporisateur, {});
    synthAU = result.audioUnitBox;
});
const noteTracks = h.noteTrackBoxes(synthAU);

// WRONG — using return value as AU box → "Cannot read properties of undefined (reading 'pointerHub')"
h.modify(() => {
    synthAU = p.api.createInstrument(IF.Vaporisateur, {});  // this is {audioUnitBox, ...} not a box
});
h.noteTrackBoxes(synthAU);  // crash

// WRONG — calling outside modify → "Modification only prohibited in transaction mode"
const result = p.api.createInstrument(IF.Vaporisateur, {});  // throws
```

## 8. insertEffect — first arg is `au.audioEffects` field, not AU box

```javascript
// CORRECT — pass the .audioEffects field from the AU box
const au = h.allAUBoxes()[unitIndex];
h.modify(() => {
    p.api.insertEffect(au.audioEffects, EF.Revamp);
});

// WRONG — passing AU box directly → "VaporisateurDeviceBox ... has no index field"
h.modify(() => {
    p.api.insertEffect(au, EF.Revamp);  // crash
});

// WRONG — using h.allAUs() (adapters) → "Cannot read properties of undefined (reading 'incoming')"
const auAdapter = h.allAUs()[unitIndex];
h.modify(() => {
    p.api.insertEffect(auAdapter.audioEffects, EF.Revamp);  // crash
});
```

Always use `h.allAUBoxes()` (boxes) for effect insertion, NOT `h.allAUs()` (adapters).

## 9. Effect parameter access — `record()`, not `_fields`

Effect boxes do NOT have a `_fields` Map or `_fields.entries()` method.

```javascript
// CORRECT — use record() which returns Record<fieldKey, Field>
const record = effectBox.record();
for (const [key, field] of Object.entries(record)) {
    const fname = field._fieldName || field.fieldName || key;
    if (fname === 'threshold') field.setValue(-18);
}

// WRONG — _fields does not exist
const fields = [...effectBox._fields.entries()];  // TypeError: Cannot read properties of undefined
```
