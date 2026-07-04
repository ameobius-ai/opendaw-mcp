# Warp Marker CRUD (v1.8.1)

3 new MCP tools for agent-driven tempo matching on stretched audio regions.

## Tools

- `create_warp_marker(unit_index, track_index, region_index, position_beats, seconds)` — adds WarpMarkerBox to stretch box's warpMarkers collection
- `delete_warp_marker(unit_index, track_index, region_index, marker_index)` — deletes non-anchor marker (first/last protected)
- `update_warp_marker(unit_index, track_index, region_index, marker_index, position_beats=-1, seconds=-1)` — updates position/seconds (-1 = unchanged)

## Implementation Details

### WarpMarkerBox (studio-boxes)
- Fields: position(2, Int32Field, ppqn), seconds(3, Float32Field, seconds), owner(1, PointerField→Pointers.WarpMarkers)
- `WarpMarkerBox.create(graph, uuid, constructor)` — standard box creation pattern

### Accessing the stretch box from a region adapter
```js
const region = trackAdapter.regions.collection.asArray()[regionIndex];
if (!region.isAudioRegion?.()) return error;
const optPlayMode = region.observableOptPlayMode;
if (optPlayMode.isEmpty()) return error; // not stretched
const playMode = optPlayMode.unwrap();
const stretchBox = playMode.box; // AudioTimeStretchBox or AudioPitchStretchBox
// stretchBox.warpMarkers is the pointer collection
```

### Creating a warp marker
```js
WarpMarkerBox.create(h.boxGraph, h.uuid.generate(), (box) => {
    box.position.setValue(posPpqn);
    box.seconds.setValue(secVal);
    box.owner.refer(stretchBox.warpMarkers);
});
```

### Anchor markers
- `WarpMarkerBoxAdapter.isAnchor` — true for first and last markers in the collection
- Cannot delete anchor markers (they pin the start/end of audio mapping)
- Non-anchor markers can be freely created/updated/deleted

### Globals required
- `DAW_WarpMarkerBox` — added to headless-daw/src/main.ts lazy-load block
- `DAW_TransientMarkerBox` — also added (for future transient marker tools)

## E2E Test Results (2026-07-03)

Test setup: load_audio → create_audio_track → create_time_stretched_region (120 BPM, transient mode)

1. **List initial**: 2 anchor markers (pos=0/0s, pos=3840ppqn/2s)
2. **Create**: warp marker at beat 1 (960ppqn, 0.5s) → 3 markers ✅
3. **Update**: marker 1 → position=1440ppqn (1.5 beats), seconds=0.75 ✅
4. **Delete**: marker 1 → 2 remaining markers ✅

## When to use warp markers

- Tempo matching audio to project BPM (pin specific beats to specific audio timestamps)
- Correcting drift in stretched audio regions
- Programmatic quantization of audio timing
- Creating custom warp maps for creative time-stretching effects
