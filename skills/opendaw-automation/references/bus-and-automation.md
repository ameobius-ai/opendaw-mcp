# Audio Bus & Automation Event Operations (tools #129-130, July 2026)

## create_audio_bus(name) — tool #129

Creates a new aux bus (AudioBusBox) with its own AudioUnitBox and TrackBox, following the upstream `AudioBusFactory.createAudioBus()` pattern.

### AudioBusBox fields
| Field Index | Name | Type | Notes |
|------------|------|------|-------|
| 1 | `collection` | PointerField<Pointers.AudioBusses> | refer to `p.rootBox.audioBusses` |
| 2 | `output` | PointerField<Pointers.AudioOutput> | MANDATORY — refer to the new AudioUnitBox.input, NOT primaryAudioBusBox.input |
| 4 | `enabled` | BooleanField | true |
| 6 | `label` | StringField | bus name |
| 7 | `icon` | StringField | e.g. "AudioBus" (use IconSymbol.toName) |

**PITFALL: AudioBusBox has NO `index` field.** Do not call `box.index.setValue()`. Bus index is derived from collection position.

**PITFALL: `output` must point to an AudioUnitBox.input, NOT another AudioBusBox.input.** The original implementation used `p.primaryAudioBusBox.input` — that's a bus-to-bus link, which is wrong. Upstream creates a dedicated AudioUnitBox for each bus and wires `bus.output.refer(unit.input)`.

**PITFALL: Creating a bare AudioBusBox without an AudioUnitBox causes IndexedBox crashes.** When `insertEffect` or other operations iterate `audioEffects`, the orphaned AudioBusBox (which lacks a proper `index` field) triggers `AudioBusBox <uuid> has no index field` panic inside `IndexedBox.collectIndexedBoxes`. Always create AudioUnitBox + TrackBox alongside the bus.

### RESOLVED: output.refer() — separate editing.modify() blocks (July 2026)

**CONFIRMED WORKING** — end-to-end tested July 2026: 1 bus ("Output") → create ReverbBus → 2 buses, unit_types ["output", "aux"] ✅

The root cause is the `#constructingBox` flag inside `BoxGraph.stageBox()`. When a box constructor callback runs, `#constructingBox = true`, and all pointer updates inside the constructor are **deferred** (`#deferredPointerUpdates.push(...)`). At `endTransaction`, deferred updates are processed via `#prepareDeferredPointerUpdate`, which calls `PointerUpdate.inverse()` → `field(graph)` → `graph.findVertex(address).unwrap()`. If the box was just staged inside the same constructor, `findVertex` can fail because the vertex isn't fully registered yet — the panic "Could not find PointerField at <uuid>/2" is the undo system trying to resolve a deferred pointer update to a vertex that wasn't available at deferral time.

**SOLUTION: Use separate `editing.modify()` blocks — create the target box first, then refer to it in a subsequent block.**

```javascript
// Block 1: Create AudioUnitBox (Aux)
p.editing.modify(() => {
    const unitIdx = [...p.rootBox.audioUnits.pointerHub.incoming()].length;
    newUnit = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.type.setValue(AudioUnitType.Aux);
        box.collection.refer(p.rootBox.audioUnits);
        box.index.setValue(unitIdx);
    });
});

// Block 2: Create AudioBusBox + wire output AFTER constructor
// Box is now fully staged — refer() works
p.editing.modify(() => {
    newBus = AudioBusBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.label.setValue('ReverbBus');
        box.collection.refer(p.rootBox.audioBusses);
        box.icon.setValue('AudioBus');
    });
    newBus.output.refer(newUnit.input);  // WORKS — unit is staged from block 1
});

// Block 3: Create TrackBox — also needs separate block
p.editing.modify(() => {
    TrackBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.tracks.refer(newUnit.tracks);
        box.index.setValue(0);
        box.type.setValue(TrackType.Undefined);
    });
});
```

**RULE: Any `refer()` that points to a box created in the SAME `editing.modify()` block must be called AFTER the `Box.create()` constructor returns, not inside the constructor callback.** If both the source and target boxes are created in the same block, the target box is staged by the time the source constructor finishes, so `refer()` after the constructor works. But if the target box is created in a LATER constructor within the same block, it will fail.

**SAFEST PATTERN: Use one `editing.modify()` block per box creation + its outgoing refers.** This is 3 blocks for create_audio_bus (unit, bus+output, track). Slightly more verbose but guaranteed to work.

### Globals required
- `DAW_AudioBusBox` — already in headless-daw/src/main.ts
- `DAW_TrackBox` — ADDED this session (was missing, caused `Cannot read properties of undefined`)
- `DAW_AudioUnitBox` — already in globals
- `DAW_AudioUnitType`, `DAW_TrackType` — already in globals

### Key difference from ProjectSkeleton
ProjectSkeleton creates the **primary** output bus with `AudioUnitType.Output` and `box.output.refer(rootBox.outputDevice)`. Aux buses use `AudioUnitType.Aux` and connect via `bus.output.refer(unit.input)`.

---

## delete_automation_event(unit_index, track_index, event_index) — tool #130

### Automation architecture: ValueClipBox, NOT ValueRegionBox

Automation events created by `add_automation` live in **ValueClipBox** (session view clips), NOT in ValueRegionBox (timeline regions).

```
TrackBox (type=3)
  └── clips.pointerHub.incoming()
        └── ValueClipBox
              └── events.targetVertex.unwrap().box
                    └── ValueEventCollectionBox
                          └── events.pointerHub.incoming()
                                └── ValueEventBox (position, value, interpolation)
```

**PITFALL**: `list_automation_events` and `delete_automation_event` use `track_index` as an index among automation tracks only (type=3), NOT among all tracks.

### The correct deletion API: box.delete()

**CONFIRMED WORKING** — end-to-end tested July 2026: 3 events → delete index 1 → 2 events remaining. Middle event (pos 2, val 0.5) removed cleanly, remaining: [pos 0, val 0.0] and [pos 4, val 1.0].

```javascript
p.editing.modify(() => {
    eventBox.delete();
});
```

### Why box.delete() works when unstageBox doesn't

`boxGraph.unstageBox(box)` calls `edges.unwatchVerticesOf(box)` which **panics** if the box has ANY outgoing or incoming edges:
```
{ValueEventBox <uuid> has outgoing edges: [...]}
```

ValueEventBox has a mandatory `events` PointerField (field 1) → ValueEventCollectionBox, creating an outgoing edge. Direct `unstageBox` fails.

`box.delete()` solves this by:
1. Calling `graph.dependenciesOf(box)` — finds all boxes and pointers depending on this box
2. `pointer.defer()` on all incoming pointers — breaks edges cleanly
3. `box.unstage()` on dependent boxes — recursively cleans up
4. `this.unstage()` — removes the box itself

All within the transaction context (`editing.modify()`).

### What does NOT work (do not attempt)

- ~~`ArrayField.remove(eventBox)`~~ — ArrayField is **fixed-length** (`ReadonlyArray<FIELD>`). There is no `remove()` method. The fields array is immutable after construction.
- ~~`boxGraph.unstageBox(eventBox)` without edge cleanup~~ — panics on outgoing edges.
- ~~`eventBox.events.refer(null)`~~ — mandatory pointer rejects null.
- ~~`try/catch around unstageBox`~~ — silently swallows the panic, event remains.

### Implementation

The tool collects all ValueEventBox entries from clips (and regions as fallback), picks the one at `event_index`, then calls `eventBox.delete()` inside `editing.modify()`. Returns `{success: true, deleted_event: N, remaining_events: count - 1}`.

### PITFALL: insertEffect API — first arg is the FIELD, not the unit

```javascript
// WRONG — passes the audio unit, causes IndexedBox crash
p.api.insertEffect(au, EF.Delay, 0);

// RIGHT — passes the audioEffects field
p.api.insertEffect(au.audioEffects, EF.Delay, 0);
```

`ProjectApi.insertEffect(field: Field, factory: EffectFactory, insertIndex)` expects `au.audioEffects` (the PointerField), not `au` (the AudioUnitBox). Passing the unit causes `IndexedBox.collectIndexedBoxes` to iterate wrong collections and panic on boxes without `index` fields.

### PITFALL: DelayDeviceBox automatable fields

DelayDeviceBox has NO `mix` field. The automatable fields (with `Pointers.Automation`) are:
- `feedback` (field 11) — Float32Field
- `cross` (field 12) — Float32Field
- `filter` (field 13) — Float32Field
- `wet` (field 14) — Float32Field
- `dry` (field 15) — Float32Field
- `delayMusical` (field 10) — Float32Field
- `preSyncTimeLeft/Right`, `preMillisTimeLeft/Right` — Float32Field
- `lfoSpeed`, `lfoDepth` — Float32Field

Use `delay.feedback` or `delay.wet` for automation tests. Non-automatable: `index`, `label`, `enabled`, `minimized`, `version`.

### PITFALL: Maximizer on Output unit

Upstream (July 2026) adds a Maximizer to the Output unit by default. When testing automation, the first effect on unit 0 may be `MaximizerDeviceBox` which has no automatable fields accessible via simple `box[fieldName].getValue()`. Add a Delay or other effect with known automatable params (mix, time, feedback) for testing.

### PITFALL: Sorting audioEffects by index

```javascript
// WRONG — AudioBusBox has no index field, crashes IndexedBox
const effects = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
    .sort((a,b) => a.index.getValue() - b.index.getValue());

// RIGHT — filter by class name
const effects = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box);
const delay = effects.find(e => e.constructor.name === 'DelayDeviceBox');
```

If a malformed AudioBusBox has leaked into the audioEffects collection (from a bad `create_audio_bus` call), sorting by `index` triggers `AudioBusBox <uuid> has no index field` panic. Always filter by class name instead of sorting, or ensure only proper effect boxes are in the collection.

---

## Globals added this session

### headless-daw/src/main.ts

```typescript
w.DAW_TrackBox = boxes.TrackBox;           // NEW — was missing
w.DAW_SignatureEventBox = boxes.SignatureEventBox;  // restored (accidentally removed during patching)
```

**PITFALL**: When patching main.ts globals, always verify with `search_files` for duplicates after. The file has ~30 DAW_ assignments and patch operations can accidentally create duplicate lines or remove adjacent entries.

## Vite IPv6 binding pitfall

Vite may bind to `[::1]:5174` (IPv6) instead of `127.0.0.1` (IPv4). `curl http://localhost:5174/` can fail with "Connection refused" if it resolves to IPv4 first. Diagnose with `ss -tlnp | grep 517` — if you see `[::1]:5174`, test with `curl -s http://[::1]:5174/`. The Playwright/Chromium bridge resolves `localhost` → `::1` correctly, so bridge operations work even when curl fails.
