# openDAW Session Patterns — July 2026

## Bridge Singleton & InstrumentFactories

**Problem:** Each `python3 -c` / `python3 << 'PYEOF'` creates a NEW Playwright browser → new page → state lost. InstrumentFactories (lazy-loaded in main.ts) may not be available.

**Fix:** Bridge `start()` now waits for `DAW_InstrumentFactories`:
```python
await self.page.wait_for_function(
    "typeof window.DAW_InstrumentFactories !== 'undefined'", timeout=15000
)
```

**Key rule:** All bridge calls in ONE `asyncio.run()`. Never split setup + test across Python processes.

## AudioRegionBox Creation (full pattern)

AudioRegionBox requires TWO mandatory pointers: `file` (AudioFileBox) and `events` (ValueEventCollectionBox). Missing either → "Pointer requires an edge" error.

```javascript
const fileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), box => {
    box.fileName.setValue("test.wav");
    box.startInSeconds.setValue(0);
    box.endInSeconds.setValue(4);
});
const eventCollection = ValueEventCollectionBox.create(p.boxGraph, UUID.generate());
AudioRegionBox.create(p.boxGraph, UUID.generate(), box => {
    box.position.setValue(0);
    box.duration.setValue(4 * 960);
    box.label.setValue("TestRegion");
    box.mute.setValue(false);
    box.gain.setValue(0);          // Float32Field, decibel
    box.fading.in.setValue(0);     // Fading ObjectField: in (seconds)
    box.fading.out.setValue(0);    // Fading ObjectField: out (seconds)
    box.file.refer(fileBox);       // MUST refer to AudioFileBox directly
    box.events.refer(eventCollection.owners);  // MUST refer to ValueEventCollectionBox.owners
    box.regions.refer(track.regions);
});
```

## Fading ObjectField

`AudioRegionBox.fading` = ObjectField with 4 Float32Fields:
- `in`: fade-in duration in seconds (positive)
- `out`: fade-out duration in seconds (positive)
- `inSlope`: curve 0-1 (0.75 = fast start, 0.25 = slow start, 0.5 = linear)
- `outSlope`: curve 0-1 (0.25 = fast end, 0.75 = slow end)

## Clips (Session View)

Three clip types on `TrackBox.clips` (ClipCollection):
- **NoteClipBox**: index, duration, mute, label, hue, triggerMode, events (NoteEventCollection)
- **AudioClipBox**: same + file, gain, playMode, events (ValueEventCollection)
- **ValueClipBox**: same + events (ValueEventCollection)

Create via `p.api.createNoteClip(trackBox, clipIndex, {name, hue})` / `p.api.createValueClip(trackBox, clipIndex, {name, hue})`.

### ClipPlaybackFields (triggerMode ObjectField)

On all clip types: `clip.triggerMode` = ObjectField with:
- `loop`: BooleanField (default true)
- `reverse`: BooleanField
- `speed`: Int32Field (1 = normal)
- `quantise`: Int32Field
- `trigger`: Int32Field

Mutate via `clip.triggerMode.loop.setValue(false)` inside `editing.modify()`.

## SignatureEventBox (Time Signature Changes)

`timelineBox.signatureTrack` = SignatureTrack ObjectField with `events` (Field<Pointers.SignatureAutomation>).

SignatureEventBox fields:
- `index`: Int32Field (sequential)
- `relativePosition`: Int32Field (ppqn)
- `nominator`: Int32Field (numerator, e.g. 4)
- `denominator`: Int32Field (e.g. 4, 8)

```javascript
SignatureEventBox.create(p.boxGraph, UUID.generate(), (box) => {
    box.events.refer(sigTrack.events);
    box.index.setValue(idx);
    box.relativePosition.setValue(posTicks);
    box.nominator.setValue(nom);
    box.denominator.setValue(denom);
});
```

**Lazy-load needed in main.ts:** `SignatureEventBox`, `AudioClipBox`, `NoteClipBox`.

## ValueRegionBox (Automation Regions)

On Value-type tracks (type=3). Same fields as NoteRegionBox: position, duration, loopOffset, loopDuration, mute, label, hue. Plus `events` (PointerField<Pointers.ValueEventCollection>).

## duplicate_notes (box-level)

Box-level equivalent of `api.duplicateNotes` (which needs adapters):
1. Get all notes from collection: `collection.events.pointerHub.incoming()`
2. Calculate shift: `max(pos+dur) - min(pos)`
3. Create new NoteEventBox for each, shifted by `shift`
4. All inside `editing.modify()`

## ValueEventBox (Automation Events)

Fields: position (ppqn), index, interpolation (0=hold, 1=linear, +curve box), value (0-1).

InterpolationFieldAdapter:
- 0 + no curve box → "hold" (step)
- 1 → "linear"
- 0 + curve box (ValueEventCurveBox) → "curve" with slope

## Lazy-Loaded Boxes in main.ts (as of July 2026)

```
DAW_AudioFileBox, DAW_AudioRegionBox, DAW_ValueEventCollectionBox,
DAW_NoteEventCollectionBox, DAW_NoteRegionBox, DAW_NoteEventBox,
DAW_TapeDeviceBox, DAW_CaptureAudioBox, DAW_MarkerBox,
DAW_AudioUnitBox, DAW_ValueEventBox, DAW_ValueClipBox, DAW_ValueRegionBox,
DAW_VaporisateurDeviceBox, DAW_NanoDeviceBox, DAW_SoundfontDeviceBox,
DAW_ApparatDeviceBox, DAW_AuxSendBox, DAW_AudioBusBox,
DAW_SignatureEventBox, DAW_AudioClipBox, DAW_NoteClipBox,
DAW_AudioTimeStretchBox, DAW_AudioPitchStretchBox
```

**Adapter classes (from @opendaw/studio-adapters, lazy-loaded in main.ts):**
```
DAW_TrackBoxAdapter, DAW_NoteRegionBoxAdapter, DAW_AudioRegionBoxAdapter,
DAW_ValueRegionBoxAdapter, DAW_RegionAdapters
```
Required for `adapterFor(box, AdapterClass)` calls — see "Region adapter" section.

**Added in session 99→103:** `DAW_AudioTimeStretchBox`, `DAW_AudioPitchStretchBox` — required for `createTimeStretchedRegion` / `createPitchStretchedRegion`.

**Added in session 103→105:** `DAW_TrackBoxAdapter`, `DAW_NoteRegionBoxAdapter`, `DAW_AudioRegionBoxAdapter`, `DAW_ValueRegionBoxAdapter`, `DAW_RegionAdapters` — required for `duplicateRegion` via `adapterFor`.

## Tool Count: 105

### New tools (sessions 87→99):
- `duplicate_notes` — duplicate individual notes within region (box-level)
- `list_automation_events` — ValueEventBox points in value clips
- `set_audio_region_fade` — Fading ObjectField (in/out/inSlope/outSlope)
- `set_audio_region_gain` — AudioRegionBox.gain (dB)
- `list_value_regions` — ValueRegionBox on automation tracks
- `list_clips` — NoteClipBox/AudioClipBox/ValueClipBox (session view)
- `add_signature_change` — SignatureEventBox for time signature changes
- `set_clip_playback` — ClipPlaybackFields (loop/reverse/speed)
- `add_tempo_change` — BPM automation via ValueEventBox on TempoTrack
- `list_tempo_changes` — read tempo map (position/bpm/interpolation)
- `list_signature_changes` — read signature events (position/num/den)
- `delete_signature_change` — remove signature event by index or position
- `set_region_color` — hue Int32Field on regions/clips (0-360 HSL)
- `list_notes` — list all note events in a region (position/duration/pitch/velocity/cent/chance)
- `set_note_properties` — edit single note: position/duration/pitch/velocity/cent/chance (-1=skip)
- `delete_note` — delete single note by index
- `delete_region` — delete region + all contents (note/audio/value)
- `set_clip_properties` — clip label/hue/mute/duration
- `delete_clip` — delete clip from track
- `rename_unit` — set InstrumentBox.label + icon
- `replace_instrument` — api.replaceMIDIInstrument (Vaporisateur↔Nano↔Soundfont↔Apparat)
- `create_value_clip` — api.createValueClip on automation track
- `set_marker_position` — move marker to new position
- `set_marker_label` — rename marker
- `get_effect_state` — full snapshot: enabled/minimized/sidechain + all params

### New tools (sessions 99→103):
- `create_time_stretched_region` — audio region with playbackRate + TransientPlayMode (warp markers, TimeBase.Musical)
- `create_pitch_stretched_region` — pitch-stretched audio region (warp markers, TimeBase.Musical)
- `duplicate_region` — api.duplicateRegion with findFreeSpace option (see pitfall below)
- `create_note_clip` — NoteClipBox in session view via api.createNoteClip

### New tools (sessions 103→105):
- `create_track_region` — generic api.createTrackRegion for note/value tracks (auto-detects type)
- `create_audio_clip` — AudioClipBox in session view via api.createNotStretchedClip

## Attempt API (replaceMIDIInstrument)

`api.replaceMIDIInstrument(target, factory)` returns `Attempt<InstrumentBox, string>`.

**Interface:** `isSuccess()` / `isFailure()` / `result()` / `failureReason()` — NOT `ok` / `value`.

```javascript
const attempt = p.api.replaceMIDIInstrument(oldInst, factory);
if (attempt.isSuccess()) {
    newInst = attempt.result();
} else {
    errMsg = attempt.failureReason();
}
```

**Constraints:** Only MIDI instruments (trackType=Notes): Vaporisateur, Nano, Soundfont, Apparat. Tape (trackType=Audio) fails with "Cannot replace instrument without CaptureMidiBox".

## InstrumentBox Access (NOT targetVertex)

`au.input` is a `Field` (hook), NOT a `PointerField`. Do NOT use `au.input.targetVertex.unwrap().box`.

**Correct:** `[...au.input.pointerHub.incoming()][0].box`
```javascript
const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
if (incoming.length === 0) return {error: "AU has no instrument"};
const instBox = incoming[0];  // InstrumentBox: label, icon, etc.
```

## MarkerBox Field (NOT box.markers)

MarkerBox has `box.track` (PointerField), NOT `box.markers`. To connect a marker to the track:

```javascript
MarkerBox.create(p.boxGraph, UUID.generate(), (box) => {
    box.position.setValue(pos);
    box.label.setValue("Verse 1");
    box.track.refer(markerTrack.markers);  // CORRECT: box.track, NOT box.markers
});
```

## Separate editing.modify() for Each Box Creation

**Pitfall:** Creating two boxes inside one `editing.modify()` block can trigger "Cannot construct box while other box is constructing".

**Fix:** Use separate `editing.modify()` blocks for each box creation, or separate `bridge.evaluate()` calls when creating instrument + effect:

```javascript
// WRONG: nested creation in one modify
p.editing.modify(() => {
    product = p.api.createInstrument(factory);  // creates multiple boxes internally
    effectBox = p.api.insertEffect(au.audioEffects, eff);  // FAILS
});

// CORRECT: separate modify blocks
p.editing.modify(() => { product = p.api.createInstrument(factory); });
// ... separate evaluate call ...
p.editing.modify(() => { effectBox = p.api.insertEffect(au.audioEffects, eff); });
```

## DAW_URL (Vite port)

Vite config (`headless-daw/vite.config.ts`) sets `server.port: 5174`. DAW_URL in server.py must be `http://localhost:5174`, NOT 5175. If bridge fails with "Vite dev server did not start within 30s", check the port.

## TempoTrack (BPM Automation)

`timelineBox.tempoTrack` = TempoTrack ObjectField with:
- `events`: PointerField<Pointers.ValueEventCollection> — ValueEventCollectionBox
- `minBpm`: Int32Field (default 60)
- `maxBpm`: Int32Field (default 240)
- `enabled`: BooleanField (must set true for automation to work)

**Normalized value conversion**: ValueEventBox.value stores 0..1, mapped via `minBpm + normalized * (maxBpm - minBpm)`. TempoAutomationConverter in @opendaw/lib-dawproject does the same conversion.

```javascript
// Enable tempo track + create/reuse collection
tempoTrack.enabled.setValue(true);
let collection;
const existingVertex = tempoTrack.events.targetVertex;
if (!existingVertex.isEmpty()) {
    collection = existingVertex.unwrap().box;
} else {
    collection = ValueEventCollectionBox.create(p.boxGraph, UUID.generate());
    tempoTrack.events.refer(collection.owners);
}
// Add event
ValueEventBox.create(p.boxGraph, UUID.generate(), (box) => {
    box.events.refer(collection.events);
    box.position.setValue(posTicks);
    box.index.setValue(maxIndex + 1);
    box.value.setValue((targetBpm - minBpm) / (maxBpm - minBpm));
    box.interpolation.setValue(1); // 1=linear, 0=hold
});
```

## Region/Clip Color (hue)

All region types (NoteRegionBox, AudioRegionBox, ValueRegionBox) and clip types (NoteClipBox, AudioClipBox, ValueClipBox) have `hue: Int32Field` (0-360 HSL). MarkerBox also has hue. TrackBox and AudioUnitBox do NOT have hue.

```javascript
p.editing.modify(() => { region.hue.setValue(240); }); // 0=red, 120=green, 240=blue
```

## Python f-string Escaping Pitfall

When writing JS code inside Python f-strings in server.py, ALL `{` and `}` in the JS must be doubled to `{{` and `}}`. A single `}` in the JS (e.g. a closing object brace `};`) inside an f-string causes `SyntaxError: f-string: single '}' is not allowed`.

**This breaks silently** — the linter catches it, but if you patch and don't check, the server won't import. Always run `python3 -c "import ast; ast.parse(open('server.py').read())"` after patching server.py.

When a non-f-string block (like `"""() => { ... }"""` without f-prefix) is adjacent to an f-string block, the f-string's `}}` escaping must be balanced independently within that f-string segment.

## Time/Pitch Stretched Audio Regions (session 99→103)

`api.createTimeStretchedRegion` and `api.createPitchStretchedRegion` create musically-timed audio regions with warp markers (TimeBase.Musical), unlike `createNotStretchedRegion` which uses TimeBase.Seconds.

### AudioContentFactory Props

```typescript
type Props = {
    boxGraph, targetTrack: TrackBox, audioFileBox: AudioFileBox,
    sample: Sample,  // {name, duration, bpm, sample_rate}
    duration?: ppqn,  // override calculated duration
    warpMarkers?: WarpMarkerTemplate[],  // custom warp markers
    gainInDb?: number, waveformOffset?: number, disableQuantize?: boolean
}
type TimeStretchedProps = Props & { transientPlayMode?: TransientPlayMode, playbackRate?: number }
type PitchStretchedProps = Props  // no additional props yet
```

### TransientPlayMode enum

```
0 = Once, 1 = Repeat, 2 = Pingpong (default)
```

### Usage pattern

```javascript
p.editing.modify(() => {
    audioFileBox = AudioFileBox.create(p.boxGraph, UUID.generate(), box => {
        box.fileName.setValue(sampleId);
        box.startInSeconds.setValue(0.0);
        box.endInSeconds.setValue(audioBuffer.duration);
    });
    regionBox = p.api.createTimeStretchedRegion({
        boxGraph: p.boxGraph, targetTrack: trackBox,
        position: Math.round(startBeat * Quarter),
        audioFileBox, sample: {name, duration: audioBuffer.duration, bpm: 120, sample_rate: audioBuffer.sampleRate},
        playbackRate: 0.5,  // 0.5=half-speed, 2.0=double
        transientPlayMode: 2,  // Pingpong
    });
});
// Result: timeBase="musical", has_playmode=true, warp markers auto-created
```

### AudioContentHelpers (internal)

`addDefaultWarpMarkers` creates 2 WarpMarkerBox entries: one at (0ppqn, 0s) and one at (durationPPQN, durationSeconds). Custom warp markers can be passed via `warpMarkers` prop as `[{position: ppqn, seconds: number}]`.

### createNoteClip (session view)

```javascript
clipBox = p.api.createNoteClip(trackBox, clipIndex, {name: "Verse 1", hue: 45});
// Returns: NoteClipBox with index, label, duration (default PPQN.Bar=3840), events (NoteEventCollection)
```

Requires note track (TrackType.Notes=1). Track must be on an instrument AU with a synth device.

### createTrackRegion (generic, session 103→105)

```javascript
const opt = p.api.createTrackRegion(trackBox, positionPPQN, durationPPQN, {name, hue});
// Returns: Option<NoteRegionBox | ValueRegionBox>
// Note track (type=1) → NoteRegionBox with NoteEventCollection
// Value track (type=3) → ValueRegionBox with ValueEventCollection
// Audio track (type=2) → Option.None (use createNotStretchedRegion instead)
opt.match({
    some: (box) => { ... },
    none: () => { error }
});
```

### createNotStretchedClip (session view audio, session 103→105)

```javascript
clipBox = p.api.createNotStretchedClip({
    boxGraph, targetTrack, index: clipIndex,
    audioFileBox, sample: {name, duration, bpm, sample_rate}
});
// Returns: AudioClipBox with TimeBase.Seconds, index, label from sample.name
// Audio track (type=2) required
```

## adapterFor Pitfall — adapterFor(box, AdapterClass) NOT adapterFor(box)

**CRITICAL:** `p.boxAdapters.adapterFor(box)` with ONE argument throws "Unknown checkType method". The method ALWAYS requires a second argument — the adapter class (e.g. `TrackBoxAdapter`, `NoteRegionBoxAdapter`, `AudioRegionBoxAdapter`).

```javascript
// WRONG — panics with "Unknown checkType method"
const adapter = p.boxAdapters.adapterFor(trackBox);

// CORRECT — needs the adapter class
const adapter = p.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
```

**Problem:** Adapter classes (`TrackBoxAdapter`, `NoteRegionBoxAdapter`, etc.) are NOT exported in the headless DAW context. They live in `@opendaw/studio-adapters` but are not lazy-loaded in main.ts.

**This blocks `api.duplicateRegion()`** which requires a region adapter as input. Two possible fixes:
1. **Lazy-load adapter classes** in main.ts (TrackBoxAdapter, NoteRegionBoxAdapter, AudioRegionBoxAdapter, ValueRegionBoxAdapter, RegionAdapters)
2. **Use `box.accept()` visitor pattern** — `RegionAdapters.for(boxAdapters, box)` internally calls `adapterFor` with the correct class via visitor

### Region adapter — WORKING pattern (session 103→105)

**`RegionAdapters.for(boxAdapters, srcRegion)` FAILS** with "Cannot read properties of undefined (reading 'accept')" — the raw box from `pointerHub.incoming()` doesn't expose `accept()` in the headless context.

**Working approach:** Get TrackBoxAdapter, then use `regions.collection.asArray()`:

```javascript
const TrackBoxAdapter = window.DAW_TrackBoxAdapter;
const trackAdapter = p.boxAdapters.adapterFor(trackBox, TrackBoxAdapter);
const regionAdapters = trackAdapter.regions.collection.asArray();
const regionAdapter = regionAdapters[regionIdx]; // pick by index
```

This is the ONLY reliable way to get a region adapter for `api.duplicateRegion()`.

### duplicateRegion API signature

```typescript
api.duplicateRegion<R>(region: R, options?: {findFreeSpace?: boolean}): Option<R>
// findFreeSpace=true → scans tracks for first available gap (auto-resolves overlaps)
// findFreeSpace=false → places on same track at original's end position
// Returns Option (use .match({some: ..., none: ...}))
```

## AU Lookup by Device Class (not by index)

**Problem:** AU indices are NOT sequential by creation order. The output AU has index=2, instrument AUs get index=0, index=1 etc. Searching by `b.index === 1` is unreliable.

**Correct pattern:** Find AU by device class name:

```javascript
const allAUs = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
const tapeAU = allAUs.find(au => {
    const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
    return incoming.some(b => b.constructor?.ClassName === "TapeDeviceBox");
});
const vapAU = allAUs.find(au => {
    const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
    return incoming.some(b => b.constructor?.ClassName === "VaporisateurDeviceBox");
});
```

**Device class names:** `TapeDeviceBox`, `VaporisateurDeviceBox`, `NanoDeviceBox`, `SoundfontDeviceBox`, `ApparatDeviceBox`. Check `box.constructor.ClassName`.

## TrackType enum values

From `@opendaw/studio-enums`:
```
TrackType.Notes = 1  (MIDI/synth tracks — filter with box.type.getValue() === 1)
TrackType.Audio = 2  (audio tracks — filter with box.type.getValue() === 2)
TrackType.Value = 3  (automation tracks — filter with box.type.getValue() === 3)
```

These are verified in runtime tests. Always filter by numeric value, not enum name.
