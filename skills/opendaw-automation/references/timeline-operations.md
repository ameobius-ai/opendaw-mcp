# Timeline Operations — openDAW headless

How to manipulate note regions, audio regions, and MIDI data on the timeline via MCP.
Verified July 2 session 6, updated session 7.

## Box graph traversal — the key pattern

openDAW's box graph uses PointerFields to connect regions to their note collections.
Understanding this traversal is essential for any tool that reads or modifies notes.

### Region → Collection → Note Events

```
NoteRegionBox
  ├── position (Int32Field, ppqn ticks — ABSOLUTE timeline position)
  ├── duration (Int32Field, ppqn ticks)
  ├── events (PointerField → NoteEventCollectionBox.owners)
  │         └── targetVertex.unwrap().box = NoteEventCollectionBox
  │               └── events (PointerField ← NoteEventBox.events points HERE)
  │                     └── pointerHub.incoming() = [NoteEventBox, ...]
  └── regions (PointerField → TrackBox.regions)
```

### WRONG way (causes "cannot be pointed to" error)

```javascript
// DO NOT do this — pointerHub.incoming() on region.events returns boxes
// that point TO the events field, not the collection the field points TO
const events = [...region.events.pointerHub.incoming()].map(({box}) => box);
for (const evt of events) { evt.pitch.setValue(72); } // ← ERROR: not NoteEventBox
```

### CORRECT way

```javascript
// 1. Dereference the pointer to get the collection box
const vertex = region.events.targetVertex.unwrap();
const collectionBox = vertex.box || vertex;

// 2. Now read note events from the collection's events field
const noteEvents = [...collectionBox.events.pointerHub.incoming()].map(({box}) => box);
for (const evt of noteEvents) {
    evt.pitch.setValue(72);     // pitch: 0-127
    evt.position.setValue(0);   // position: RELATIVE to region start (ppqn)
    evt.duration.setValue(960); // duration: ppqn ticks (960 = 1 quarter note)
}
```

### Why `vertex.box || vertex`

`targetVertex.unwrap()` may return either:
- A Vertex object (has `.box` property → the actual box)
- The box itself (in some code paths)

The `|| vertex` fallback handles both cases.

## NoteEventBox fields

| Field | Type | Description |
|-------|------|-------------|
| `pitch` | Int32Field | MIDI note number (0-127, 60=C4) |
| `position` | Int32Field | Position RELATIVE to region start (ppqn ticks, 0=region beginning) |
| `duration` | Int32Field | Note length (ppqn ticks, 960=quarter note) |
| `velocity` | Float32Field | 0.0-1.0 |
| `chance` | Int32Field | Play probability (0-100, default 100) |
| `cent` | Float32Field | Detune in cents (default 0) |
| `events` | PointerField | Points to `NoteEventCollectionBox.events` |

**CRITICAL**: NoteEventBox.position is RELATIVE to the region start, not absolute timeline.
When quantizing or moving notes, you must handle both region.position (absolute) and
evt.position (relative) separately.

## Quantize implementation

Quantize must snap BOTH region positions and note positions within regions:

```javascript
const gridTicks = 960 * 4 / division; // 1/16 → 240 ticks, 1/4 → 960 ticks

for (const region of regions) {
    // 1. Quantize region position (absolute timeline)
    const regPos = region.position.getValue();
    const nearestReg = Math.round(regPos / gridTicks) * gridTicks;
    const newRegPos = regPos + (nearestReg - regPos) * strength;
    region.position.setValue(Math.round(newRegPos));

    // 2. Quantize note positions within region (relative)
    const collection = region.events.targetVertex.unwrap().box;
    const notes = [...collection.events.pointerHub.incoming()].map(({box}) => box);
    for (const evt of notes) {
        const current = evt.position.getValue();
        const nearest = Math.round(current / gridTicks) * gridTicks;
        const newPos = current + (nearest - current) * strength;
        evt.position.setValue(Math.round(newPos));
    }
}
```

**Strength parameter**: 1.0 = full snap, 0.5 = move 50% toward grid (preserves groove).

### Grid tick calculation

| Division | Grid ticks | Description |
|----------|-----------|-------------|
| 1/4 | 960 | Quarter note |
| 1/8 | 480 | Eighth note |
| 1/16 | 240 | Sixteenth note |
| 1/32 | 120 | Thirty-second note |
| 1/64 | 60 | Sixty-fourth note |

Formula: `gridTicks = 960 * 4 / division` where 960 = PPQN.Quarter.

## Duplicate note region

To duplicate a region with all its notes:

1. Get the source collection via `region.events.targetVertex.unwrap().box`
2. Create a NEW `NoteEventCollectionBox` (don't share — each region needs its own)
3. Copy each `NoteEventBox` with all fields (pitch, position, duration, velocity, chance, cent)
4. Create a new `NoteRegionBox` with position = srcPos + offsetTicks
5. Point `box.events.refer(newCollection.owners)` and `box.regions.refer(trackBox.regions)`

```javascript
p.editing.modify(() => {
    const newCollection = NoteEventCollectionBox.create(bg, UUID.generate());
    const srcNotes = [...srcCollection.events.pointerHub.incoming()].map(({box}) => box);
    for (const srcNote of srcNotes) {
        NoteEventBox.create(bg, UUID.generate(), (box) => {
            box.position.setValue(srcNote.position.getValue());
            box.duration.setValue(srcNote.duration.getValue());
            box.velocity.setValue(srcNote.velocity.getValue());
            box.pitch.setValue(srcNote.pitch.getValue());
            box.chance.setValue(srcNote.chance?.getValue?.() ?? 100);
            box.cent.setValue(srcNote.cent?.getValue?.() ?? 0);
            box.events.refer(newCollection.events);
        });
    }
    NoteRegionBox.create(bg, UUID.generate(), (box) => {
        box.position.setValue(newPos);
        box.duration.setValue(srcDuration);
        box.loopDuration.setValue(0);
        box.loopDuration.setValue(srcDuration);
        box.eventOffset.setValue(0);
        box.events.refer(newCollection.owners);
        box.regions.refer(trackBox.regions);
    });
});
```

## Track type constants

| Type value | Description |
|-----------|-------------|
| 1 | Note track (MIDI) |
| 2 | Audio track |

Filter tracks by type: `[...au.tracks.pointerHub.incoming()].filter(b => b.type?.getValue?.() === 1)`

## Time signature

TimelineBox has a `signature` compound field with `nominator` and `denominator`:

```javascript
p.timelineBox.signature.nominator.setValue(6);    // 6/8
p.timelineBox.signature.denominator.setValue(8);
```

Valid denominators: 1, 2, 4, 8, 16 (power-of-2 note values).
PPQN.fromSignature(numerator, denominator) computes bar length in ticks.

## Deleting regions

`region.delete()` removes the region from the track and cleans up box graph connections.
The associated NoteEventCollectionBox and NoteEventBox instances are NOT automatically
deleted — they become orphaned. For clean cleanup, delete the collection too:

```javascript
// Optional: clean up collection + events
const collection = region.events.targetVertex.unwrap().box;
region.delete();
// collection and events remain in boxGraph but are unreferenced
// They'll be garbage-collected on project save/load cycle
```

In practice, orphaned boxes don't cause issues for export or playback — they're just
dead weight in the boxGraph. Project save/load will clean them.

## Filename sanitization (fixed session 5-6)

All export tools sanitize filenames. The safe_name function:
```python
safe_name = "".join(c for c in filename if c.isalnum() or c in "-_.").strip() or "mix"
if safe_name.lower().endswith(".wav"):
    safe_name = safe_name[:-4]  # strip .wav if user included it
```

**Bug history**: originally `c in "-_"` (no dot) → `.wav` became `wav` → doubled extension `mix.wav.wav`.
Fixed by adding `.` to allowed chars AND stripping `.wav` if already present.

## Test results (session 6)

- set_time_signature(6, 8) → numerator=6, denominator=8 ✅
- set_time_signature(4, 3) → rejected (denominator must be 1,2,4,8,16) ✅
- transpose_notes(+12) on C4/E4/G4 → pitches [72, 76, 79] ✅
- transpose_notes(-12) back → pitches [60, 64, 67] ✅
- delete_note_region: 3 regions → delete 0 → 2 remaining ✅
- quantize_notes("1/4", strength=1.0): 0.3→0, 1.7→2.0, 2.55→3.0 beats ✅
- list_note_regions: 3 regions with note_count=1 each, label="Note 60" etc ✅
- list_audio_regions: 0 regions on empty project ✅

## Region field manipulation (session 7)

NoteRegionBox has these fields accessible at box level (all via `field.setValue()` inside `editing.modify()`):

| Field | Type | Unit | MCP Tool |
|-------|------|------|----------|
| `position` | Int32Field | ppqn ticks (960/beat) | `set_region_position` |
| `duration` | Int32Field | ppqn ticks | `set_region_duration` |
| `loopDuration` | Int32Field | ppqn ticks (0 = no loop) | `set_region_loop` |
| `loopOffset` | Int32Field | ppqn ticks | `set_region_loop` |
| `eventOffset` | Int32Field | ppqn ticks | `set_region_loop` |
| `mute` | BooleanField | true/false | `set_region_mute` |
| `label` | StringField | display text | `set_region_label` |
| `hue` | Int32Field | color hue | (not exposed) |

**All mutations require `p.editing.modify()` wrapper.**

### Loop behavior

When `loopDuration > 0`, the note pattern repeats within the region.
- `duration` = total region length on timeline
- `loopDuration` = length of one repetition
- `loopOffset` = where in the event collection the loop starts
- `eventOffset` = offset added to all note positions
- Number of loops = `duration / loopDuration`

Example: duration=16 beats, loopDuration=2 beats → 8 repetitions of the 2-beat pattern.

## compact_tracks (session 7)

`p.api.compactTracks(au)` removes empty tracks (tracks with no regions).
**MUST be wrapped in `editing.modify()`** — bare call crashes with
"Modification only prohibited in transaction mode".

```javascript
p.editing.modify(() => p.api.compactTracks(units[i]));
```

Test: AU with 2 empty note tracks → 1 track after compact (1 removed).

## Pitfalls

- **`region.events.pointerHub.incoming()` is WRONG** — returns boxes pointing TO the field,
  not the collection it points to. Use `region.events.targetVertex.unwrap().box` to get the
  collection, then `collection.events.pointerHub.incoming()` for note events.
- **NoteEventBox.position is RELATIVE** — 0 = region start, not absolute timeline. When
  quantizing, quantize region.position (absolute) AND evt.position (relative) separately.
- **JS variable name mismatch in f-strings** — Python `track_index` must be interpolated
  into JS as `const trackIdx = {track_index};`. If the JS code references `trackIdx` but
  it was never declared (because you forgot the `const trackIdx =` line), you get
  `"trackIdx is not defined"`. Always declare JS variables from Python params.
- **Duplicate needs new collection** — don't share NoteEventCollectionBox between regions.
  Each region gets its own collection with its own NoteEventBox instances.
- **AudioBusBox has no volume field** — volume is on AudioUnitBox. Use `set_track_volume`
  on the FX unit index to control bus level.
