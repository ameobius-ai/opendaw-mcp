# Adapter Access Patterns — openDAW Headless Bridge

Critical patterns for accessing openDAW's adapter layer from `bridge.evaluate()` JS.
These were discovered through extensive E2E testing and are NOT documented upstream.

## 1. NEVER use `adapterFor(box, 'ClassName')` with string

`BoxAdapters.adapterFor(box, adapterClass)` requires the **actual class**, not a string.
Passing a string like `'AudioUnitBoxAdapter'` throws: `Error: Unknown checkType method`.

```javascript
// ❌ BREAKS: string argument
const adapter = p.boxAdapters.adapterFor(box, 'AudioUnitBoxAdapter');

// ✅ WORKS: use rootBoxAdapter.audioUnits.adapters() instead
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
const adapter = auAdapters.find(a => a.isInstrument);
```

## 2. Access chain: rootBoxAdapter → adapters → adapter properties

The canonical access chain for all adapter-based queries:

```javascript
const p = window.DAW;

// Audio units (sorted by index, includes Output)
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
// → each has: .indexField, .label, .type, .isInstrument, .isOutput, .isBus,
//   .namedParameter ({volume, panning, mute, solo}), .box, .uuid, .tracks

// Tracks on an AU
const trackAdapters = auAdapter.tracks.collection.adapters();
// → each has: .type (0=Notes, 1=Audio, 2=Value), .box, .regions, .clips, .enabled, .indexField

// Regions on a track
const regions = trackAdapter.regions.collection.asArray();
// → each has: .position, .duration, .complete, .mute, .hue, .label, .isMirrowed,
//   .optCollection, .onSelected(), .flatten(), .consolidate(), .copyTo()

// Audio effects on an AU
const fxAdapters = auAdapter.audioEffects.adapters();
// → each has: .box, .label, .indexField

// MIDI effects on an AU
const midiFxAdapters = auAdapter.midiEffects.adapters();
```

## 3. AudioUnitType is a string enum in adapters

`adapter.type` returns a **string**: `"instrument"`, `"output"`, `"bus"`.
But `box.type.getValue()` returns a **number**: 0=Instrument, 1=Output.

```javascript
// ✅ Use adapter properties (strings)
const synth = auAdapters.find(a => a.isInstrument);  // reliable
const output = auAdapters.find(a => a.isOutput);

// ⚠️ box.type.getValue() returns number
const typeNum = auBox.type.getValue();  // 0 or 1
```

## 4. TrackType values

`box.type.getValue()` on TrackBox: `0=Undefined, 1=Notes, 2=Audio, 3=Value`
`adapter.type` returns the same number.

Filter note tracks: `tracks.filter(t => t.type.getValue() === 1)` or `trackAdapters.find(t => t.type === 1)`

## 5. editing.modify() scoping — return values DON'T propagate

**Values assigned inside `editing.modify()` are NOT visible outside the closure**
if the closure throws or the modify transaction rolls back. Use a mutable outer variable:

```javascript
// ❌ Return value lost
const result = p.editing.modify(() => {
    return first.flatten(regions);  // result is undefined
});

// ✅ Mutable outer variable
let flatResult;
p.editing.modify(() => {
    flatResult = first.flatten(regions);
});
if (!flatResult || flatResult.isEmpty()) return {error: "flatten failed"};
```

## 6. Adapter collection refresh after editing.modify()

**`rootBoxAdapter.audioUnits.adapters()` does NOT immediately reflect new AUs
created inside the same `editing.modify()` block.** The IndexedBoxAdapterCollection
updates asynchronously via pointerHub subscription.

**Workaround**: Create AUs/tracks in SEPARATE `bridge.evaluate()` calls (separate JS executions),
not in the same `editing.modify()`. By the next evaluate, the adapter collection has refreshed.

```python
# ❌ WON'T WORK: adapter not visible in same eval
await bridge.evaluate('''() => {
    p.editing.modify(() => { p.api.createInstrument(IF.Vaporisateur, {}); });
    const au = p.rootBoxAdapter.audioUnits.adapters().find(a => a.isInstrument);
    // au is undefined — adapter collection hasn't refreshed yet
}''')

# ✅ WORKS: separate evals
await bridge.evaluate('''() => {
    p.editing.modify(() => { p.api.createInstrument(IF.Vaporisateur, {}); });
    return true;
}''')
# Next eval — adapter collection has refreshed
await bridge.evaluate('''() => {
    const au = p.rootBoxAdapter.audioUnits.adapters().find(a => a.isInstrument);
    // au is defined ✅
}''')
```

Same applies to tracks: create track in one eval, access `synthAdapter.tracks.collection.adapters()` in the next.

## 7. pointerHub.incoming() vs adapter collection

Both work but have different refresh semantics:

- `box.tracks.pointerHub.incoming()` — raw BoxGraph pointer edges. Updates synchronously
  within `editing.modify()`. Use for box-level access when you have the box reference.
- `adapter.tracks.collection.adapters()` — adapter collection. Updates asynchronously.
  Use when you need adapter properties (.type, .regions, .namedParameter).

**For regions**: `trackAdapter.regions.collection.asArray()` is the adapter path.
`trackBox.regions.pointerHub.incoming().map(({box}) => box)` is the box path.
Both should return the same regions once collections have refreshed.

## 8. Named parameters on AudioUnitBoxAdapter

```javascript
const np = auAdapter.namedParameter;
np.volume.getValue()   // dB, mapped via ValueMapping.decibel(-96, -9, +6)
np.panning.getValue()  // -1..1, bipolar
np.mute.getValue()     // bool
np.solo.getValue()     // bool
```

## 9. Region flatten requires onSelected() + returns BOX not adapter

`NoteRegionBoxAdapter.flatten(regions)` requires all regions to be marked selected first.
**Returns `Option<NoteRegionBox>` (a BOX, not an adapter)** — use `.getValue()` for fields, not direct property access.

```javascript
regions.forEach(r => r.onSelected());
let flatResult;
p.editing.modify(() => { flatResult = regions[0].flatten(regions); });
// flatResult.unwrap() → NoteRegionBox (box), NOT NoteRegionBoxAdapter
const newBox = flatResult.unwrap();
newBox.position.getValue()   // ✅ field access
newBox.duration.getValue()   // ✅
newBox.label.getValue()      // ✅
// newBox.position            ❌ returns Field object, not value
```

`canFlatten()` checks: same track, all selected, all NoteRegionBoxAdapter instances.
Same pattern applies to `ValueRegionBoxAdapter.flatten()` — returns `Option<ValueRegionBox>`.

## 9b. Region consolidate — no editing.modify needed

`region.consolidate()` works WITHOUT `editing.modify()` wrapper. It directly manipulates
the box graph pointer references. The event collection is replaced with a unique copy.

```javascript
const wasMirrored = region.isMirrowed;
region.consolidate();  // no editing.modify() needed
// isMirrowed now false if it was true before
```

## 10. Tempo map access

```javascript
const tempoMap = p.tempoMap;  // VaryingTempoMap instance
tempoMap.ppqnToSeconds(ppqn)   // → seconds (accounts for tempo automation)
tempoMap.secondsToPPQN(secs)   // → ppqn
tempoMap.getTempoAt(ppqn)      // → bpm at position
tempoMap.intervalToSeconds(from, to)  // → seconds for range
```

1 beat = PPQN.Quarter = 960 pulses. Convert: `ppqn = Math.round(beats * 960)`.

## 11. Project-level utilities

```javascript
p.lastRegionAction()     // → ppqn of last region end across all tracks
p.invalid()              // → bool (true if overlapping regions exist)
p.collectSampleUUIDs()   // → UUID[] of all AudioFileBox in project
p.audioUnitFreeze        // → AudioUnitFreeze instance
p.audioUnitFreeze.isFrozenUuid(uuid)              // → bool
p.audioUnitFreeze.hasSidechainDependents(adapter) // → bool
```

## 12. Audio region play mode (stretch)

Audio regions can have a "play mode" — time-stretch or pitch-stretch. Access via adapter:

```javascript
const region = trackAdapter.regions.collection.asArray()[i];
// region.isAudioRegion() → true for audio regions

const optPlayMode = region.observableOptPlayMode;
if (optPlayMode.isEmpty()) { /* plain playback, no stretch */ }
const playMode = optPlayMode.unwrap();

// Type check
playMode.constructor.name === 'AudioTimeStretchBoxAdapter'  // time-stretch
playMode.constructor.name === 'AudioPitchStretchBoxAdapter' // pitch-stretch

// Time-stretch only:
playMode.playbackRate    // → number (0.5..2.0)
playMode.cents           // → number (log2(rate) * 1200)
playMode.cents = 600     // setter: shifts pitch up 6 semitones (clamped ±1200)
playMode.transientPlayMode // → TransientPlayMode enum
playMode.warpMarkers.asArray()  // → WarpMarkerBoxAdapter[]

// Warp marker properties:
marker.position   // → ppqn position
marker.seconds    // → audio time in seconds
marker.isAnchor   // → bool (first/last marker)
```

Setting cents requires `editing.modify()`:
```javascript
p.editing.modify(() => { playMode.cents = 600; });
```

## 13. Audio file info via adapter

```javascript
const optFile = region.optFile;
if (optFile.isEmpty()) { /* no file attached */ }
const file = optFile.unwrap();
file.fileName        // → string
file.startInSeconds  // → number
file.endInSeconds    // → number

const loader = file.getOrCreateLoader();
loader.state         // → {type: 'loaded'|'progress'|'error', ...}
// When loaded:
const data = loader.data.unwrap();
data.sampleRate      // → Hz
data.numChannels     // → 1 or 2
data.numFrames       // → sample count
```

## 14. Automation value at position (valueAt)

TrackBoxAdapter has `valueAt(position, fallback)` for value/automation tracks.
Resolves the automation curve accounting for interpolation, region loops, and overlapping regions.

```javascript
const trackAdapter = auAdapter.tracks.collection.adapters()
    .find(t => t.type === 3);  // Value track
const value = trackAdapter.valueAt(ppqn, 0.0);  // → 0.0..1.0
```

Note: `trackAdapter.type` returns number: 0=Undefined, 1=Notes, 2=Audio, 3=Value.

## 15. Region content shift (moveContentStart)

Both NoteRegionBoxAdapter and AudioRegionBoxAdapter have `moveContentStart(delta)`:
shifts content inside the region without moving the region position.

```javascript
p.editing.modify(() => {
    region.moveContentStart(delta_ppqn);
});
// After: region.position unchanged, region.duration -= delta
// For audio: waveformOffset adjusts (seconds timeBase uses tempoMap conversion)
// For notes: note positions shift by -delta
```

## 16. createNoteEvent owner parameter

`api.createNoteEvent({owner, position, duration, pitch, velocity})` — the `owner`
is a **NoteEventCollectionBox** (the box, not the region). The API internally does:
`owner.events.targetVertex.unwrap().box.asBox(NoteEventCollectionBox).events`.

But in practice, passing the region box works because it has `.events` pointer:

```javascript
const region = api.createNoteRegion({trackBox: track, position: 0, duration: 4*960, loopDuration: 4*960});
const collectionBox = region.events.targetVertex.unwrap().box;
// Option A: use api.createNoteEvent with collectionBox as owner
api.createNoteEvent({owner: collectionBox, position: 0, duration: 960, pitch: 60, velocity: 0.8});
// Option B: create NoteEventBox directly (more reliable in headless)
NoteEventBox.create(boxGraph, UUID.generate(), box => {
    box.position.setValue(0); box.duration.setValue(960);
    box.pitch.setValue(60); box.velocity.setValue(0.8);
    box.events.refer(collectionBox.events);
});
```

Option B is more reliable — matches the pattern used by the `create_note` MCP tool.

## 17. Clips use .adapters() NOT .asArray() — collection type mismatch

Track clips use `IndexedBoxAdapterCollection` (has `.adapters()`), while track regions
use a different collection type (has `.asArray()`). This is an upstream inconsistency:

```javascript
// Regions — ✅ asArray()
const regions = trackAdapter.regions.collection.asArray();

// Clips — ❌ asArray() throws TypeError
const clips = track.clips.collection.asArray();  // TypeError: not a function

// Clips — ✅ adapters()
const clips = track.clips.collection.adapters();
```

## 18. Clip consolidate/clone need editing.modify() — regions don't

`region.consolidate()` works WITHOUT `editing.modify()` (directly manipulates pointers).
But `clip.consolidate()` and `clip.clone(consolidate)` MUST be wrapped:

```javascript
// Region — works without modify:
region.consolidate();

// Clip — needs modify:
p.editing.modify(() => { clip.consolidate(); });
p.editing.modify(() => { clip.clone(false); });
```

## 19. DAW_HELPERS — prefer helpers over manual adapter access

When writing new MCP tools, use `window.DAW_HELPERS` (injected in bridge.start())
instead of manual `rootBoxAdapter.audioUnits.adapters()` chains. See `references/daw-helpers.md`.

```javascript
// PREFER:
const h = window.DAW_HELPERS;
const region = h.region(unit_index, track_index, region_index);

// OVER:
const p = window.DAW;
const aus = p.rootBoxAdapter.audioUnits.adapters();
if (i >= aus.length) return {error: "No AU"};
// ... 10 more lines
```

## 20. Note collection analysis API

NoteEventCollectionBoxAdapter exposes pitch range and overlap detection:

```javascript
const region = h.region(auIdx, trackIdx, regIdx);
const collection = region.optCollection.unwrap();  // NoteEventCollectionBoxAdapter

collection.minPitch       // → int (lowest MIDI note)
collection.maxPitch       // → int (highest MIDI note)
collection.maxDuration    // → ppqn (longest note)
collection.events.asArray()  // → NoteEventBoxAdapter[] sorted by position

// Find notes at a specific pitch overlapping a time range:
const overlapping = collection.overlapping(fromPPQN, toPPQN, pitch);
// → NoteEventBoxAdapter[] (all notes at `pitch` whose [position, complete) overlaps [from, to))
```

## 21. Automation event creation + interpolation API

ValueEventCollectionBoxAdapter has `createEvent()` and events have settable `interpolation`:

```javascript
const region = h.region(auIdx, trackIdx, regIdx);
const collection = region.optCollection.unwrap();  // ValueEventCollectionBoxAdapter

// Create event — if one exists at same position+index, UPDATES value instead of duplicating
const event = collection.createEvent({
    position: ppqn,
    index: 0,
    value: 0.0,           // 0.0..1.0 (normalized)
    interpolation: {type: "linear"}  // or {type: "none"} or {type: "curve", slope: 0.3}
});

// Change interpolation of existing event:
h.modify(() => { event.interpolation = {type: "none"}; });

// List all events with interpolation detail:
const events = collection.events.asArray();
events.forEach(e => {
    e.position       // → ppqn
    e.value          // → 0.0..1.0
    e.index          // → int
    e.interpolation  // → {type: "none"|"linear"|"curve", slope?}
});
```

Interpolation types:
- `{type: "none"}` — step/hold (jump to value)
- `{type: "linear"}` — straight ramp
- `{type: "curve", slope: 0.0..1.0}` — custom curve (0.5 = linear)

**Pitfall:** Automation (value) tracks created via `api.createAutomationTrack(au, field)` appear
on the AU's track collection, but `synth.tracks.collection.adapters()` may not immediately show them.
Use separate `evaluate()` calls — create in one, query in next.

## 22. Scriptable device box access (Apparat/Werkstatt/Spielwerk)

All 5 scriptable device MCP tools find the device box differently depending on type:

```javascript
const dt = deviceType.toLowerCase();  // case-insensitive
let device = null;

if (dt === "werkstatt") {
    // Audio effect — via audioEffects pointerHub
    const fx = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box);
    device = fx[device_index] || null;
} else if (dt === "spielwerk") {
    // MIDI effect — via midiEffects pointerHub
    const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({box}) => box) : [];
    device = me[device_index] || null;
} else if (dt === "apparat") {
    // Instrument — via input pointerHub, NOT targetVertex
    const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({box}) => box) : [];
    device = incoming.find(b => b.constructor.name === "ApparatDeviceBox") || incoming[0] || null;
}
```

**CRITICAL: `au.input.targetVertex.unwrapOrNull()` does NOT work.** `targetVertex` is undefined on
AudioUnitBox — it crashes with "Cannot read properties of undefined (reading 'unwrapOrNull')".
The correct pattern is `au.input.pointerHub.incoming()` — same as all other instrument-access tools
(`list_instrument_params`, `set_vaporisateur_osc_param`, etc.).

**Case insensitivity**: `.toLowerCase()` is applied to both `dt` (device selection) and `headerTag`
(regex pattern + header generation). Examples can pass "Apparat", "APPARAT", or "apparat" — all work.

## 23. Adapter-level effect access goes stale across evaluate() calls

`au.audioEffects.adapters()` returns adapter objects that are **cached by the IndexedBoxAdapterCollection**.
When a new `bridge.evaluate()` call runs, the adapter collection does NOT refresh — it returns the same
stale adapter references from the previous call. This means:

- `fx.length` may be wrong if effects were added/removed in a previous eval
- `fx[i].box` may point to a detached/old box reference
- Mutations via `fxAdapter.box.someField.setValue()` may silently fail or target the wrong box

**The fix: use box-level access (`h.auBox(i)` + `h.effectBoxes(auBox)`) for ALL effect operations.**

```javascript
// ❌ STALE: adapter-level — cached, doesn't refresh between evals
const au = h.au(0);                    // returns adapter
const fx = au.audioEffects.adapters(); // cached collection — may be stale
fx[0].box.overSampling.setValue(2);   // may fail silently

// ✅ FRESH: box-level — reads pointerHub directly each call
const au = h.auBox(0);                // returns box via pointerHub.incoming()
const fx = h.effectBoxes(au);         // fresh pointerHub.incoming() each call
fx[0].overSampling.setValue(2);       // targets the correct box
```

**Migration pattern** (applied in v1.9.8, 8 tools migrated):

```python
# Old (adapter-level):
const au = h.au({unit_index});
const fx = au.audioEffects.adapters();

# New (box-level):
const au = h.auBox({unit_index});
const fx = h.effectBoxes(au);
```

Tools migrated: `get_device_chain_detail`, `get_neuralamp_model`, `set_neuralamp_model`,
`set_vocoder_modulator_source`, `set_vocoder_band_count`, `set_stereo_tool_panning`,
`set_fold_oversampling`, `set_crusher_bits`.

**Exceptions (safe to keep adapter-level):**
- `get_full_project_state` — read-only, needs `au.namedParameter` (adapter-only API)
- 6 modular tools — need `modDev.modular()` method (adapter-only API, no box equivalent)
- Any tool that needs `au.namedParameter` (volume/panning/mute/solo) — adapter-only

**E2E verification**: Fold `overSampling` 0→2 ✅, Crusher `bits` 16→8 ✅ — both via box-level access
after migration.

## 24. insertEffect API — pass collection field, not AU box

`api.insertEffect` takes a **Field<EffectPointerType>** (the collection), not the AU box itself.
Passing the AU box causes "AudioBusBox has no index field" or "UserInterfaceBox has no index field" errors.

```javascript
// ❌ BREAKS: passing AU box
await api.insertEffect(au, EF.Fold);
// Error: "AudioBusBox ... has no index field"

// ✅ WORKS: pass the collection field + wrap in editing.modify
h.modify(() => {
    effectBox = h.api.insertEffect(au.audioEffects, factory);
});
```

Also: `createInstrument` must be wrapped in `h.modify()` — it creates a CaptureMidiBox
which requires a transaction context. Without `h.modify()`: "Modification only prohibited
in transaction mode."

```javascript
// ❌ BREAKS: no transaction
await h.api.createInstrument(IF.Vaporisateur, {trackName: "Test"});

// ✅ WORKS: wrapped in modify + wait for Yjs sync
h.modify(async () => {
    await h.api.createInstrument(IF.Vaporisateur, {trackName: "Test"});
});
await new Promise(r => setTimeout(r, 500)); // let Yjs sync
```
