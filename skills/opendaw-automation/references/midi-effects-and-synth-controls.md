# MIDI Effects & Vaporisateur Synth Controls — July 2026

## MIDI Effects (sessions 105→111)

AudioUnitBox has TWO effect chains:
- `au.audioEffects` (field 23) — audio effects (Delay, Reverb, Compressor, etc.)
- `au.midiEffects` (field 21) — MIDI effects (Arpeggio, Pitch, Velocity, Zeitgeist, Spielwerk)

Both use the **same API**: `p.api.insertEffect(field, factory)`. The only difference is which field you pass.

### Available MIDI Effect Factories

From `EffectFactories.MidiNamed` (lazy-loaded as `DAW_EffectFactories`):

| Factory | Box Class | Purpose |
|---------|-----------|---------|
| `Arpeggio` | `ArpeggioDeviceBox` | Arpeggiator |
| `Pitch` | `PitchDeviceBox` | Pitch shifter (semiTones/cents/octaves) |
| `Velocity` | `VelocityDeviceBox` | Velocity processor |
| `Zeitgeist` | `ZeitgeistDeviceBox` | MIDI delay/echo |
| `Spielwerk` | `SpielwerkDeviceBox` | MIDI sequence player |

### Usage Pattern

```javascript
const ef = window.DAW_EffectFactories;
const au = allUnits[unitIdx];

// Add MIDI effect — same API as audio effects
p.editing.modify(() => {
    p.api.insertEffect(au.midiEffects, ef.MidiNamed.Pitch);
});

// List MIDI effects
const midiFx = [...au.midiEffects.pointerHub.incoming()]
    .map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue());

// Remove MIDI effect
p.editing.modify(() => { midiFx[effectIdx].delete(); });
```

### PitchDeviceBox Fields

| Field Index | Name | Type | Default | Notes |
|-------------|------|------|---------|-------|
| 2 | label | String | "Pitch" | |
| 4 | enabled | Boolean | true | |
| 5 | minimized | Boolean | false | |
| 10 | semiTones | Int32 | 0 | Semitone offset |
| 11 | cents | Int32 | 0 | Cents offset |
| 12 | octaves | Int32 | 0 | Octave offset |

Set via `effectBox.getField(10).setValue(7)` inside `editing.modify()`.

### MCP Tools Added (105→111)

- `list_midi_effects` — list available MIDI effect factory names
- `add_midi_effect` — add MIDI effect to au.midiEffects chain
- `remove_midi_effect` — remove MIDI effect from chain
- `get_midi_effect_chain` — get full MIDI effect chain for AU
- `list_midi_effect_params` — list MIDI effect parameters with current values
- `set_midi_effect_param` — set MIDI effect parameter by name or field index

## Vaporisateur Synth Controls (sessions 111→113)

VaporisateurDeviceBox has sub-objects accessible directly: `oscillators`, `lfo`, `noise`.

### ArrayField Access Pattern (CRITICAL)

`VaporisateurDeviceBox.oscillators` is an `ArrayField`, NOT a regular array.

**WRONG:** `vap.oscillators.get(0)` → `TypeError: get is not a function`
**WRONG:** `vap.oscillators[0]` → undefined
**WRONG:** `vap.oscillators.length` → undefined

**CORRECT:**
```javascript
const oscFields = vap.oscillators.fields();  // ReadonlyArray<VaporisateurOsc>
const oscCount = vap.oscillators.size();     // number (NOT .length)
const osc0 = oscFields[0];                   // access by index
```

`ArrayField` API (from `@opendaw/lib-box`):
- `.fields()` → ReadonlyArray of sub-fields
- `.size()` → count (NOT `.length`)
- `.getField(key)` → get sub-field by key
- `.record()` → Record<string, Field>

### Oscillator Fields (VaporisateurOsc)

| Field Index | Name | Type | Default | Notes |
|-------------|------|------|---------|-------|
| 1 | waveform | Int32 | 2 (Saw) | 0=Sine, 1=Triangle, 2=Saw, 3=Square |
| 2 | volume | Float32 | -6 (dB) | -Infinity to +6 |
| 3 | octave | Int32 | 0 | Octave offset |
| 4 | tune | Float32 | 0 | Semitone offset (float) |

Default Vaporisateur has 2 oscillators: osc0 (Saw, -6dB), osc1 (Square, -Infinity).

### LFO Fields (VaporisateurLFO)

| Field | Default | Notes |
|-------|---------|-------|
| 1 (waveform) | 0 | LFO waveform |
| 2 (rate) | 1 | Rate |
| 3 (sync) | false | Sync to tempo |
| 10 | 0 | |
| 11 | 0 | |
| 12 | 0 | |

### Noise Fields (VaporisateurNoise)

| Field | Default | Notes |
|-------|---------|-------|
| 1 | 0.001 | Volume/attack |
| 2 | 0.001 | Decay |
| 3 | 0.001 | |
| 4 | 0.001 | |

### Vaporisateur Main Params (non-deprecated)

Fields 14-27 on VaporisateurDeviceBox (fields 10-13 are deprecated):

| Field | Name | Type | Notes |
|-------|------|------|-------|
| 14 | cutoff | Float32 | Filter cutoff |
| 15 | resonance | Float32 | Filter resonance |
| 16 | attack | Float32 | Amp ADSR |
| 17 | release | Float32 | Amp ADSR |
| 18 | filterEnvelope | Float32 | |
| 19 | decay | Float32 | ADSR decay |
| 20 | sustain | Float32 | ADSR sustain |
| 21 | glideTime | Float32 | Portamento |
| 22 | voicingMode | Int32 | |
| 23 | ? | Int32 | |
| 24-27 | various | Float32/Int32 | |

### Finding Vaporisateur in the Box Graph

The master output AU has index=0 and contains `AudioBusBox` (not an instrument). Instrument AUs have higher indices.

**Auto-detect pattern:**
```javascript
const allUnits = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
let vap = null;
for (const au of allUnits) {
    const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
    vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
    if (vap) break;
}
```

### MCP Tools Added (111→113)

- `list_vaporisateur_params` — full synth state: oscillators, LFO, noise, main params (auto-detect or by unit_index)
- `set_vaporisateur_osc_param` — set oscillator parameter (waveform/volume/octave/tune)

## Universal Instrument Parameters (sessions 113→115)

All instrument types share a common pattern for parameter access. The `list_instrument_params` and `set_instrument_param` tools work universally by:
1. Finding the instrument box on `au.input.pointerHub.incoming()` (filtering out `AudioBusBox`)
2. Reading `instBox.record()` for all fields with `.getValue()` methods
3. Setting via `field.setValue()` inside `editing.modify()`

Skip fields: host, index, collection, editing, output, input, sideChain, capture, tracks, audioEffects, midiEffects, auxSends, oscillators, lfo, noise, samples, parameters, device, file (these are structural, not parameters).

## Playfield / Drum Machine (sessions 115→118)

### Creating a Playfield with Samples

**CRITICAL**: `api.createInstrument(IF.Playfield, {attachment: [...]})` — the second arg is `InstrumentOptions`, NOT the attachment directly. Passing the array directly silently creates a Playfield with NO samples.

```javascript
// CORRECT
const attachment = [{note: 36, uuid: UUID.generate(), name: "kick.wav", durationInSeconds: 0.5, exclude: false}];
p.api.createInstrument(IF.Playfield, {attachment: attachment});

// WRONG — creates empty Playfield
p.api.createInstrument(IF.Playfield, attachment);
```

### Adding Pads to Existing Playfield

`PlayfieldSampleBox` is NOT exposed on `window` as `DAW_PlayfieldSampleBox`. To create new pads:
1. Get the class constructor from an existing sample: `existingSamples[0].constructor`
2. Create `AudioFileBox` AND `PlayfieldSampleBox` in the SAME `editing.modify()` block
3. Connect them: `box.file.refer(fileBox)` — this creates the edge that prevents "requires an edge" validation error

```javascript
const existingSamples = [...pf.samples.pointerHub.incoming()].map(({box}) => box);
const SampleClass = existingSamples[0].constructor;

p.editing.modify(() => {
    const fileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), box => {
        box.fileName.setValue("snare.wav");
        box.endInSeconds.setValue(0.3);
    });
    SampleClass.create(p.boxGraph, UUID.generate(), box => {
        box.device.refer(pf.samples);
        box.file.refer(fileBox);
        box.index.setValue(38); // MIDI note
        box.enabled.setValue(true);
    });
});
```

**Pitfalls**:
- `boxGraph.createBox("PlayfieldSampleBox")` → UUID comparator crash. Must use class `.create()`.
- `AudioFileBox.create()` outside `editing.modify()` → "Modification only prohibited in transaction mode"
- `AudioFileBox` without edge → "Target AudioFileBox requires an edge" at `endTransaction` validation
- Empty Playfield (0 samples) → no constructor reference → error. Must have ≥1 sample.

### MCP Tools Added (115→118)

- `list_playfield_samples` — list drum pads (midi_note, enabled, has_file)
- `set_playfield_sample_enabled` — enable/disable a drum pad
- `create_playfield_sample` — add a pad (needs existing samples for constructor reference)

## ProjectApi Coverage — Complete

All high-level `ProjectApi` methods now have MCP equivalents:

| ProjectApi Method | MCP Tool(s) |
|-------------------|-------------|
| createInstrument | create_instrument_track, create_synth_track |
| replaceMIDIInstrument | replace_instrument |
| insertEffect | add_effect, add_midi_effect |
| createNoteTrack | create_note_track |
| createAudioTrack | create_audio_track |
| createAutomationTrack | add_automation |
| compactTracks | compact_tracks |
| createTimeStretchedRegion | create_time_stretched_region |
| createPitchStretchedRegion | create_pitch_stretched_region |
| createNotStretchedRegion | place_audio_region |
| createNoteClip | create_note_clip |
| createValueClip | create_value_clip |
| createNotStretchedClip | create_audio_clip |
| createTimeStretchedClip | create_time_stretched_clip |
| createPitchStretchedClip | create_pitch_stretched_clip |
| duplicateRegion | duplicate_region |
| createTrackRegion | create_track_region |
| createNoteEvent | create_note |
| createNoteRegion | (via create_track_region) |
| deleteAudioUnit | delete_audio_unit |
| duplicateNotes | duplicate_notes |
| quantiseNotes | quantize_notes |
| exportMIDI | export_midi |
| exportAudio | export_single_stem (headless alternative) |
| setBpm | set_bpm |
| catchupAndSubscribeBpm | (UI-only, not for MCP) |

**Not covered (UI-only / requires FileAPI):**
- `PresetStorage` — binary `.odp` preset files, needs FileAPI
- `RecordAutomation` — live recording during transport, needs UI interaction
- `YService` / `YMapper` — Yjs collaborative editing, WebSocket-based

**PlayfieldSampleBox**: covered via `create_playfield_sample` MCP tool. See Playfield section above for the constructor-reference pattern.
