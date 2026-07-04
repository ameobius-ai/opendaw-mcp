# New Tools 159–164 + DAW_HELPERS Optimization

Session: 2026-07-03. Added 5 tools (159→164) + DAW_HELPERS injection pipeline optimization.

## DAW_HELPERS Injection (pipeline optimization)

**Problem:** Every tool repeated 15+ lines of boilerplate to get AU/track/region adapters.

**Fix:** Inject JS helper functions into page context during `bridge.start()`:

```javascript
window.DAW_HELPERS = {
    au: (i) => { /* rootBoxAdapter.audioUnits.adapters()[i] */ },
    track: (auIdx, trackIdx) => { /* au.tracks.collection.adapters()[trackIdx] */ },
    region: (auIdx, trackIdx, regIdx) => { /* track.regions.collection.asArray()[regIdx] */ },
    allAUs: () => p.rootBoxAdapter.audioUnits.adapters(),
    instrumentAU: () => { /* find(a => a.isInstrument) */ },
    modify: (fn) => p.editing.modify(fn),
    project: p, api: p.api, boxGraph: p.boxGraph, editing: p.editing,
    tempoMap: p.tempoMap, audioUnitFreeze: p.audioUnitFreeze, rootBoxAdapter: p.rootBoxAdapter,
};
```

**Result:** New tools are 3x shorter. Old tools still use `const p = window.DAW;` — refactor incrementally.

## Critical Patterns Discovered

### 1. `type.getValue()` returns STRING not number
```javascript
// WRONG — returns 'instrument'/'output', not 0/1
const synth = units.find(u => u.type.getValue() === 0);
// RIGHT — use adapter boolean properties
const synth = auAdapters.find(a => a.isInstrument);
```

### 2. `adapterFor(box, 'StringClassName')` does NOT work
```javascript
// WRONG — panics with "Unknown checkType method"
const adapter = p.boxAdapters.adapterFor(box, 'AudioUnitBoxAdapter');
// RIGHT — use collection adapters() or DAW_HELPERS
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
```

### 3. `flatten()` returns BOX not adapter
```javascript
// flatten returns Option<NoteRegionBox> (box), not adapter
// Use .getValue() for field access:
const newBox = flatResult.unwrap();
return { position: newBox.position.getValue() };  // NOT newBox.position
```

### 4. `editing.modify()` result via outer `let`
```javascript
// JS closures: variable must be declared OUTSIDE modify()
let flatResult;
h.modify(() => { flatResult = first.flatten(toFlatten); });
// flatResult is now accessible outside
```

### 5. `track.clips.collection.asArray()` does NOT exist
```javascript
// WRONG — clips collection is IndexedBoxAdapterCollection, not EventCollection
const clips = track.clips.collection.asArray();
// RIGHT — use .adapters()
const clips = track.clips.collection.adapters();
```

### 6. Automation tracks on AU, not instrument tracks list
`createAutomationTrack(au, field)` creates a track on the AU, but `synth.tracks.collection.adapters()` only shows note/audio tracks. Automation (value, type=2) tracks ARE in the collection but may need separate eval to be visible.

### 7. Clips/tracks created in `editing.modify()` not visible in same eval
Adapter collections update asynchronously. Create AU/track/clip in one `evaluate()`, then access in a separate `evaluate()` call.

## Tools Added (159→164)

| # | Tool | What it does |
|---|------|-------------|
| 160 | `create_automation_event` | Single automation point with interpolation (none/linear/curve) |
| 161 | `list_automation_events_detail` | Full detail: position, value, interpolation type, curve slope |
| 162 | `set_automation_interpolation` | Change interpolation of existing event |
| 163 | `get_note_range` | min/max pitch, max duration, note count for a region |
| 164 | `find_overlapping_notes` | Find notes at specific pitch in time range (collision detection) |

## Interpolation API

```typescript
type Interpolation = { type: "none" } | { type: "linear" } | { type: "curve", slope: unitValue }
```

- `none` = step/hold (jump to value)
- `linear` = straight ramp
- `curve` = custom slope (0.0-1.0, 0.5 = linear)

`collection.createEvent({position, index, value, interpolation})` — if event exists at position, updates value instead of duplicating.

## Note Collection API

- `collection.minPitch` / `collection.maxPitch` — pitch range
- `collection.maxDuration` — longest note in ppqn
- `collection.overlapping(fromPPQN, toPPQN, pitch)` — returns array of NoteEventBoxAdapter
- `collection.events.asArray()` — all events sorted by position
