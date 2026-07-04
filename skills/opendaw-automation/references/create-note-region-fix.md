# create_note Region Accumulation Fix (2026-07-03)

## Root Cause of Silent Render

`export_stems` / `OfflineEngineRenderer.start()` produced WAV files with `max_sample=0` (silent). Root cause traced to `create_note` creating a new `NoteRegionBox` + `NoteEventCollectionBox` for EVERY note call.

### Before fix
3 calls to `create_note(0, 60, 0, 4, ...)` + `create_note(0, 64, 0, 4, ...)` + `create_note(0, 67, 0, 4, ...)` → 3 overlapping NoteRegionBox at position 0, each with 1 NoteEventBox. OfflineEngineRenderer cannot render overlapping regions → silence.

```
NoteRegionBox #1 (pos=0, dur=3840) → NoteEventCollectionBox #1 → NoteEventBox(pitch=60)
NoteRegionBox #2 (pos=0, dur=3840) → NoteEventCollectionBox #2 → NoteEventBox(pitch=64)
NoteRegionBox #3 (pos=0, dur=3840) → NoteEventCollectionBox #3 → NoteEventBox(pitch=67)
```

### After fix
`create_note` now checks for existing regions on the track. If found, adds NoteEventBox to the first region's events collection. Only creates a new region if none exists.

```
NoteRegionBox #1 (pos=0, dur=3840) → NoteEventCollectionBox #1 → 3 NoteEventBoxes (pitch=60, 64, 67)
```

### Key code pattern
```javascript
// Find existing region
const existingRegions = [...trackBox.regions.pointerHub.incoming()].map(({box}) => box);
let regionBox = null;

if (existingRegions.length > 0) {
    regionBox = existingRegions[0];  // use first existing region
} else {
    // Create new NoteEventCollectionBox + NoteRegionBox
    collection = NoteEventCollectionBox.create(bg, UUID.generate());
    regionBox = NoteRegionBox.create(bg, UUID.generate(), (box) => {
        box.position.setValue(0);
        box.label.setValue("Notes");
        box.duration.setValue(Math.max(noteDuration, 4 * Quarter));
        box.loopDuration.setValue(Math.max(noteDuration, 4 * Quarter));
        box.eventOffset.setValue(0);
        box.events.refer(collection.owners);
        box.regions.refer(trackBox.regions);
    });
}

// Note position is RELATIVE to region start
const regionStart = regionBox.position.getValue();
const notePos = Math.max(0, startPosition - regionStart);

// Access events collection from existing region
const eventsField = regionBox.events.targetVertex.unwrap();  // returns Field
const collBox = eventsField.box;  // NoteEventCollectionBox

NoteEventBox.create(bg, UUID.generate(), (box) => {
    box.position.setValue(notePos);
    box.duration.setValue(noteDuration);
    box.pitch.setValue(pitch);
    box.velocity.setValue(velocity);
    box.chance.setValue(100);
    box.cent.setValue(0);
    box.events.refer(collBox.events);  // point note to collection's events field
});

// Auto-extend region if note extends beyond
const noteEnd = notePos + noteDuration;
if (noteEnd > regionBox.duration.getValue()) {
    regionBox.duration.setValue(noteEnd);
    regionBox.loopDuration.setValue(noteEnd);
}
```

### Upstream reference
`packages/studio/core/src/project/Project.ts` line 359: `box.events.refer(collection.events)` — same pattern. `collection` is a NoteEventCollectionBox, `box` is a NoteEventBox. The `.refer()` call makes the note event's `events` field point to the collection's `events` pointer field.

### Known display issue
`collBox.events.pointerHub.incoming()` may show only 1 event even when 3+ NoteEventBox exist in boxGraph. The notes ARE created and DO render (audio confirmed), but the pointer hub's incoming count is unreliable. To verify actual note count:

```javascript
let count = 0;
for (const box of p.boxGraph.boxes()) {
    if (box.constructor.name === 'NoteEventBox') count++;
}
// returns correct count (3)
```

### Verification
- 3 NoteEventBox created with correct pitches [67, 60, 64] and positions [1920, 0, 960]
- `OfflineEngineRenderer.start(p.copy(), Option.None, ...)` → max_sample=0.877 ✅
- `export_stems` → 11.5MB WAV, 132192 samples at 48kHz ✅
