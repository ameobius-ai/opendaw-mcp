# Session Patterns — July 2026 (Tools 44→68)

Patterns discovered extending the MCP tool set from 44 to 68 tools.

## editing.modify() is MANDATORY for ALL mutations

Every box mutation — `setValue`, `delete()`, `api.compactTracks()`, `api.deleteAudioUnit()` — must be wrapped:
```js
p.editing.modify(() => { /* mutations here */ });
```
Without it: `"Modification only prohibited in transaction mode"`.

## Bridge state isolation

`from server import bridge` creates a fresh `HeadlessDawBridge` per Python process. Each `python3 -c` or heredoc is a new process → new browser → new DAW. **All test calls (setup + action + verify) must be in the same `asyncio.run()` block.**

Symptom: `Cannot read properties of undefined (reading 'tracks')` — you lost state across processes.

## Field constraints — public getters, not private

```js
field.unit        // → "%", "dB", "s", "Hz"
field.constraints // → "unipolar" | "bipolar" | "decibel" | {min, max, mid, scaling: "exponential"}
```
Do NOT use `field._constraints` (private, often empty). The public getters work reliably on Float32Field.

Tested on ReverbDeviceBox:
- decay: unipolar, %
- preDelay: {min: 0.001, max: 0.5, scaling: "exponential"}, s
- damp: unipolar, %
- filter: bipolar, %
- wet/dry: decibel, dB

## Region fields — all box-level, no adapter needed

NoteRegionBox fields accessible via `box.fieldName.setValue(x)`:
- `position` (Int32Field, ticks)
- `duration` (Int32Field, ticks)
- `loopDuration` (Int32Field, ticks)
- `loopOffset` (Int32Field, ticks)
- `eventOffset` (Int32Field, ticks)
- `mute` (BooleanField)
- `label` (StringField)
- `hue` (Int32Field)

All mutations inside `editing.modify()`.

## AU has NO name field at box level

AudioUnitBox field 1 is `type` (StringField = "output"/"instrument"), NOT name.
AU label only via adapter: `input.adapter().labelField`.
Headless mode lacks boxAdapters → cannot rename AU after creation.
Set name at creation: `factory.create(graph, au.input, "Name", icon)`.

## api.duplicateRegion requires adapter — use manual copy

`ProjectApi.duplicateRegion(region, {findFreeSpace})` takes an adapter, not a raw box.
Headless mode has no adapter context. Manual box-level copy:
1. Create new `NoteEventCollectionBox`
2. Copy each `NoteEventBox` (position, duration, velocity, pitch, chance, cent)
3. Create new `NoteRegionBox` with new position + `events.refer(newCollection.owners)` + `regions.refer(trackBox.regions)`
4. All inside `editing.modify()`

## lib-midi lazy-load needs page reload

After adding lazy-load to `main.ts`:
```ts
const midi = await import("@opendaw/lib-midi");
w.DAW_MidiFile = midi.MidiFile;
w.DAW_MidiTrack = midi.MidiTrack;
w.DAW_ControlEvent = midi.ControlEvent;
w.DAW_ControlType = midi.ControlType;
```
Must reload: `window.location.reload()` + `await asyncio.sleep(6)` + poll for `window.DAW_MidiFile`.

## JS→Python binary transfer via base64

No file system sharing between Chromium and WSL. For MIDI/WAV:
```js
// JS: ArrayBuffer → base64
const bytes = new Uint8Array(buffer);
let binary = '';
for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
return { data_b64: btoa(binary) };
```
```python
# Python: decode + save
raw = base64.b64decode(result["data_b64"])
with open(filepath, "wb") as f:
    f.write(raw)
```

## InstrumentFactories inventory

| Factory | trackType | Notes |
|---------|-----------|-------|
| Tape | 2 (audio) | Audio playback device |
| Nano | 1 (note) | Simple synth |
| Playfield | 1 (note) | — |
| Vaporisateur | 1 (note) | Subtractive synth (default) |
| MIDIOutput | 1 (note) | MIDI out |
| Soundfont | 1 (note) | SF2 player |
| Apparat | 1 (note) | FM synth |

No drum-specific instrument. For drums: Soundfont + drum SF2, or Vaporisateur with manual patch.

## Effect factories via AudioNamed

```js
const factory = window.DAW_EffectFactories.AudioNamed["Reverb"];
p.api.insertEffect(au.audioEffects, factory);  // NOT factory.create(graph, field) directly
```

## deleteAudioUnit guard

`api.deleteAudioUnit(au)` works for any AU. Index 0 = master output — must not delete.
Tool enforces `unit_index >= 1`.

## compactTracks needs editing.modify wrapper

```js
p.editing.modify(() => p.api.compactTracks(au));  // NOT p.api.compactTracks(au) directly
```

## New box-level access patterns (68→74 session)

### RootBox direct fields
- `rootBox.baseFrequency` — Float32Field (A4 tuning, 440Hz default). No unwrap needed — direct field on RootBox.
- `rootBox.groove` — PointerField to GrooveShuffleBox. Access: `rootBox.groove.targetVertex.unwrap().box.amount`.

### LoopArea is an ObjectField, not a Box
`timelineBox.loopArea` is an ObjectField with sub-fields `enabled` (BooleanField), `from` (Int32Field), `to` (Int32Field). No `.targetVertex.unwrap()` needed — access sub-fields directly: `loop.enabled.setValue(true)`, `loop.from.setValue(ticks)`. NOT a Box, NOT in pointerHub.

### MarkerBox + MarkerTrack
MarkerTrack is an ObjectField on `timelineBox.markerTrack` with a `markers` Field (PointerField collection). MarkerBox is a real Box (needs lazy-load in main.ts + page reload). Create pattern:
```js
MarkerBox.create(p.boxGraph, UUID.generate(), (box) => {
    box.position.setValue(posTicks);
    box.plays.setValue(0);
    box.label.setValue("Verse 1");
    box.hue.setValue(0);
    box.track.refer(markerTrack.markers);  // connect to marker collection
});
```
Delete: `markerBox.delete()` inside `editing.modify()`.
List: `[...markerTrack.markers.pointerHub.incoming()].map(({box}) => box)`.

### ObjectField vs Box — critical distinction
- **Box** (NoteRegionBox, MarkerBox, AudioUnitBox): created via `BoxClass.create(graph, uuid, constructor)`, accessed via `pointerHub.incoming()`, has `.delete()`.
- **ObjectField** (LoopArea, MarkerTrack, Signature): sub-field of a parent Box, accessed directly as `parent.objectFieldName.subField`, no `.create()` or `.delete()`.
- **Field** (Float32Field, Int32Field, StringField): leaf values, `.getValue()` / `.setValue(x)`.
Confusing ObjectField with Box leads to `.targetVertex.unwrap()` errors on fields that don't have targetVertex.

## New patterns (74→76 session)

### TrackType integer values
- `trackBox.type.getValue()` returns integer: **1 = Notes**, **2 = Audio**, **3 = Value (automation)**
- Filter note tracks: `.filter(b => b.type?.getValue?.() === 1)`
- Filter automation tracks: `.filter(b => b.type?.getValue?.() === 3)`

### duplicate_notes — box-level (no adapter needed)
`api.duplicateNotes` takes `NoteEventBoxAdapter[]` (unavailable headless). Box-level equivalent:
1. Get all NoteEventBox from collection: `[...collection.events.pointerHub.incoming()].map(({box}) => box)`
2. Compute block span: `blockEnd - blockStart` where `blockEnd = max(pos+dur)`, `blockStart = min(pos)`
3. For each note, create new NoteEventBox with `position + shift`, same pitch/duration/velocity/chance/cent
4. `box.events.refer(collection.events)` — copies go into the SAME collection
5. All inside `editing.modify()`

### list_automation_events — ValueEventBox reading
Value clips live on type-3 tracks. Access chain:
```
au.tracks → filter type===3 → track.clips.pointerHub.incoming() → clip.events.targetVertex.unwrap().box → collection.events.pointerHub.incoming() → ValueEventBox[]
```
ValueEventBox fields:
- `position` (Int32Field, ppqn) → divide by Quarter(960) for beats
- `value` (Float32Field, 0-1 normalized)
- `index` (Int32Field, sequential)
- `interpolation` (Int32Field): **0 = hold** (or curve if ValueEventCurveBox attached via pointerHub.incoming()), **1 = linear**

### DAW_InstrumentFactories NOT in window.DAW_* lazy-load set
`window.DAW_InstrumentFactories` is accessible from browser context but is NOT among the `window.DAW_*` keys set by main.ts lazy-load. When tests create a fresh bridge process and try to use `IF.Tape` inside `editing.modify()`, it may fail with `Cannot read properties of undefined (reading 'Tape')`. 

**Fix**: The factories ARE on `window.DAW_InstrumentFactories` (verified with `typeof` check outside editing.modify). If it fails inside `editing.modify()`, capture the reference BEFORE entering the transaction:
```js
const IF = window.DAW_InstrumentFactories;  // capture before
const ef = window.DAW_EffectFactories;
p.editing.modify(() => {
    const inst = p.api.createAnyInstrument(IF.Tape);  // use captured ref
    // ...
});
```

### AudioRegionBox — uncovered fields (for future tools)
- `gain` (Float32Field, field 17) — per-region gain
- `fading` (Fading ObjectField, field 18) — sub-fields: `in` (Float32Field), `out` (Float32Field), `inSlope` (Float32Field, default 0.75), `outSlope` (Float32Field, default 0.25)
- `playMode` (PointerField, field 8) — points to AudioTimeStretchBox or AudioPitchStretchBox
- `waveformOffset` (Float32Field, field 7)

### ValueRegionBox — same fields as NoteRegionBox
ValueRegionBox (automation regions) has identical field layout: position, duration, loopOffset, loopDuration, mute, label, hue. Plus `events` (PointerField to ValueEventCollection) and `regions` (PointerField to RegionCollection). Access pattern same as NoteRegionBox.

### AudioTimeStretchBox / AudioPitchStretchBox
Both accept `Pointers.AudioPlayMode`. AudioTimeStretchBox has `warpMarkers` (Field), `transientPlayMode` (Int32Field, default 2), `playbackRate` (Float32Field, default 1). AudioPitchStretchBox has only `warpMarkers`. WarpMarkerBox: `position` (Int32Field, ppqn), `seconds` (Float32Field). These are for time/pitch-stretch features — creating them requires AudioContentFactory which uses complex props (not yet covered).

### ProjectApi methods — full coverage map
| Method | Covered by | Notes |
|--------|-----------|-------|
| setBpm | set_bpm | ✅ |
| createInstrument | create_synth_track, create_instrument_track | ✅ |
| replaceMIDIInstrument | — | ❌ Requires adapter (InstrumentBox.label) |
| insertEffect | add_effect | ✅ |
| createNoteTrack | create_note_track | ✅ |
| createAudioTrack | create_audio_track | ✅ |
| createAutomationTrack | add_automation | ✅ (internal) |
| compactTracks | compact_tracks | ✅ |
| createTimeStretchedRegion/Clip | — | ❌ Complex props, needs research |
| createPitchStretchedRegion/Clip | — | ❌ Complex props, needs research |
| createNoteClip | — | Partial (create_note creates events, not clips) |
| duplicateRegion | duplicate_note_region | ✅ (manual box-level copy) |
| exportMIDI | export_midi | ✅ (lib-midi encoder) |
| exportAudio | export_single_stem | ✅ |
| quantiseNotes | quantize_notes | ✅ |
| createValueClip | add_automation | ✅ (internal) |
| createNoteRegion | create_note (internal) | ✅ |
| createTrackRegion | — | Partial (create_note covers Note type) |
| createNoteEvent | create_note | ✅ |
| deleteAudioUnit | delete_audio_unit | ✅ |
| duplicateNotes | duplicate_notes | ✅ (box-level, no adapter) |

