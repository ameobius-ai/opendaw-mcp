# openDAW Box/Field/Pointer API — Verified July 2, 2026

Patterns for manipulating openDAW boxes, fields, and pointers from Playwright `page.evaluate()`. All verified against commit 9e006511 (v0.0.150).

## Box Field Enumeration

### WRONG: `Object.keys(effectBox)` — returns empty, getters are on prototype
### CORRECT: `effectBox.record()` — returns `Record<string, Field>`

```javascript
const record = effectBox.record();
for (const [key, field] of Object.entries(record)) {
    const fname = field._fieldName || key;
    const value = field.getValue();
    // field._constraints has {min, max, unit} for Float32Field
}
```

⚠️ **CRITICAL**: `record()` returns keys as **numeric field keys** ("1", "2", "3", "10", etc), NOT field names. Use `field._fieldName` to get the real name ("volume", "cutoff", "enabled"). Discovered July 3 during instrument automation work — `recordKeys` showed ["1","2","3","4","5","10","11",...] not ["host","index","label","enabled","minimized","volume"].

## Box Deletion

### WRONG: `p.boxGraph.deleteBox(effectBox)` — no such method
### CORRECT: `effectBox.delete()` — instance method on Box

```javascript
p.editing.modify(() => {
    effectBox.delete();
});
```

## TrackType Enum

```typescript
enum TrackType { Undefined=0, Notes=1, Audio=2, Value=3 }
```

### WRONG: filter `box.type.getValue() === 0` for audio tracks (0 = Undefined)
### CORRECT: filter `box.type.getValue() === 2` for audio tracks

```javascript
const audioTracks = [...au.tracks.pointerHub.incoming()]
    .map(({box}) => box)
    .filter(box => box.type?.getValue?.() === 2); // TrackType.Audio = 2
```

## PointerField.refer()

`.refer()` takes a **Vertex**, not a Box directly. For existing boxes already in the graph, `.refer(box)` sometimes works via auto-wrapping. But for **newly created** boxes inside the same `editing.modify()` block, you MUST get the Vertex first:

### WRONG: `.refer(newBox)` or `.point(box)` on newly created boxes
- `PointerField` has NO `.point()` method — throws "is not a function"
- `.refer(newBox)` on a newly created (uncommitted) box may also fail

### CORRECT: Get Vertex via `graph.findVertex(box.address)`, then `.refer(vertex)`

```javascript
// For newly created boxes (inside editing.modify):
h.modify(() => {
    const newBox = SomeBox.create(h.boxGraph, UUID.generate(), (box) => {
        box.someField.setValue(value);
    });
    const vertex = h.boxGraph.findVertex(newBox.address);
    if (vertex.isEmpty()) return {error: "Vertex not found"};
    targetBox.somePointer.refer(vertex.unwrap());
});
```

```javascript
// For existing boxes (already in graph — common case):
p.editing.modify(() => {
    regionBox.file.refer(audioFileBox);   // works — audioFileBox already committed
    box.collection.refer(rootBox.audioUnits);
});
```

### Pattern: box creation + pointer linking in NeuralAmp model loading
```javascript
const UUID = window.DAW_UUID;
const modelBox = NeuralAmpModelBox.create(h.boxGraph, UUID.generate());
modelBox.label.setValue("NAM Model");
modelBox.model.setValue(modelJsonString);
const modelVertex = h.boxGraph.findVertex(modelBox.address);
effectBox.model.refer(modelVertex.unwrap());
```

## AudioRegionBox Fields (field key → name)
| Key | Field | Type |
|-----|-------|------|
| 1 | regions | PointerField<RegionCollection> |
| 2 | file | PointerField<AudioFile> |
| 3 | playback | StringField (deprecated) |
| 4 | timeBase | StringField |
| 5 | events | PointerField<ValueEventCollection> |
| 6 | warping | PointerField (deprecated) |
| 7 | waveformOffset | Float32Field |
| 16 | hue | Int32Field |
| 17 | gain | Float32Field |
| 18 | fading | Fading |

## AudioFileBox Fields
| Key | Field | Type |
|-----|-------|------|
| 1 | startInSeconds | Float32Field |
| 2 | endInSeconds | Float32Field |
| 3 | fileName | StringField |
| 10 | transientMarkers | Field<TransientMarkers> |

## UUID Handling

`UUID.generate()` returns a `UUID.Bytes` (Uint8Array). For Map lookups and string comparison, convert to string:

```javascript
const id = UUID.generate();
const idStr = UUID.toString(id);  // "4b990c0d-d6e1-48c1-9fb0-c1c0840d48b9"
window.DAW_localAudioBuffers.set(id, audioBuffer);      // by Bytes
window.DAW_localAudioBuffers.set(idStr, audioBuffer);    // by string
window.DAW_fileNameToAudioBuffer.set(idStr, audioBuffer); // sampleProvider resolves by fileName
```

### WRONG: `AudioData.fromAudioBuffer(audioBuffer)` — no such method
### CORRECT: `window.DAW_audioBufferToAudioData(audioBuffer)` — exposed by main.ts

## Audio Loading — URL vs Base64

For files inside `headless-daw/public/`, fetch via URL (handles large files):

```javascript
const response = await fetch("/stems/bass_0.wav");
const arrayBuffer = await response.arrayBuffer();
const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
```

### WRONG: base64 for 50MB+ files — EPIPE kills Vite process
### CORRECT: URL fetch for files in public/, base64 only for small external files

## Effect Parameter Setting

All parameter mutations MUST be wrapped in `p.editing.modify()`:

```javascript
p.editing.modify(() => {
    effectBox.inputGain.setValue(12.0);  // Float32Field
    effectBox.equation.setValue("tanh");  // StringField
    effectBox.enabled.setValue(false);    // BooleanField
});
```

## Pointers.Automation Detection (verified July 3)

To check if a field is automatable (supports `Pointers.Automation`):

```javascript
const Pointers = window.DAW_Pointers;  // enum loaded in headless-daw globals
const autoVal = Pointers.Automation;   // = 9 (numeric enum value)

const field = targetBox[paramName];
const accepts = field.pointerRules?.accepts;  // array of numeric Pointer enum values
const isAutomatable = !!(accepts && autoVal != null && accepts.includes(autoVal));
```

### Example: Vaporisateur volume field
- `field.pointerRules.accepts` = `[27, 9, 22]` (Modulation, Automation, MIDIControl)
- `Pointers.Automation` = `9`
- `accepts.includes(9)` → `true` → automatable ✅

### Fields with `NoPointers` (NOT automatable)
- `enabled` field on EffectBox: `pointerRules: NoPointers` → cannot be automated
- This is an architectural upstream limitation (issue #270), not fixable via MCP

### record() keys are NUMERIC, not field names
`record()` returns `{"1": field, "2": field, "3": field, "10": field, ...}` — NOT `{"host": ..., "index": ..., "volume": ...}`. Always use `field._fieldName` to get the human-readable name when iterating record entries.

## Instrument Automation

Instrument parameters (Vaporisateur cutoff, Tape flutter, Playfield sample mute) can be automated via `api.createAutomationTrack(au, field)`:

```javascript
// Find instrument box on AU
const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
const instBox = incoming.find(b => b.constructor.name !== "AudioBusBox");

// For Playfield sample-level params, target a specific sample:
const samples = [...instBox.samples.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
const targetBox = sampleIdx >= 0 ? samples[sampleIdx] : instBox;

// Create automation track + value clip + events
h.editing.modify(() => {
    autoTrack = h.api.createAutomationTrack(au, targetBox[paramName]);
    valueClip = h.api.createValueClip(autoTrack, 0, {name: paramName});
    collection = valueClip.events?.targetVertex?.unwrap?.()?.box;
    points.forEach(([beatPos, value], i) => {
        ValueEventBox.create(h.boxGraph, UUID.generate(), (box) => {
            box.events.refer(collection.events);
            box.position.setValue(Math.round(beatPos * Quarter));
            box.index.setValue(i);
            box.value.setValue(value);
            box.interpolation.setValue(1); // linear
        });
    });
});
```

Vaporisateur: 18/23 fields automatable (volume, octave, tune, waveform, cutoff, resonance, attack, decay, release, filterEnvelope, and more).

## Effect Chain Ordering

Effects are sorted by `box.index.getValue()`:
```javascript
const effects = [...au.audioEffects.pointerHub.incoming()]
    .map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue());
```

Default project has `MaximizerDeviceBox` at index 0. Added effects start at index 1.

## WaveshaperDeviceBox Fields
| Key | Field | Type | Default | Range |
|-----|-------|------|---------|-------|
| 10 | equation | StringField | "hardclip" | hardclip/tanh/cubicSoft/sigmoid/arctan/asymmetric |
| 11 | inputGain | Float32Field | 0 | 0-40 dB |
| 12 | outputGain | Float32Field | 0 | -24 to 24 dB |
| 13 | mix | Float32Field | 1 | 0-1 unipolar |

⚠️ **hardclip at inputGain=0dB on sub-0dBFS audio = no-op. Set inputGain > 0dB for distortion.**

## BlockFlags (for reference — NOT a bug source)
```typescript
const enum BlockFlag {
    transporting = 1 << 0,   // engine is playing
    discontinuous = 1 << 1,  // position jumped
    playing = 1 << 2,        // not counting in
    bpmChanged = 1 << 3,     // tempo changed
}
```
`BlockRenderer.process()` constructs blocks with correct flags during offline render (transporting=true after `play()` is called).
