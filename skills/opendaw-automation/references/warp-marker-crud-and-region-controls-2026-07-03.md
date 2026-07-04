# Warp Marker CRUD + Audio Region Controls (v1.8.1–v1.8.2)

Added 2026-07-03. 5 new tools (235→237).

## v1.8.1: Warp Marker CRUD (3 tools)

Warp markers define the mapping between musical position (ppqn) and audio time (seconds) on stretched audio regions. First and last markers are anchors — they pin the start/end of the audio and cannot be deleted.

### Tools

- `create_warp_marker(unit_index, track_index, region_index, position_beats, seconds)` — Adds a WarpMarkerBox to the stretch box's `warpMarkers` collection. Uses `WarpMarkerBox.create(boxGraph, uuid, (box) => { box.position.setValue(ppqn); box.seconds.setValue(sec); box.owner.refer(stretchBox.warpMarkers) })` inside `editing.modify()`.
- `delete_warp_marker(unit_index, track_index, region_index, marker_index)` — Deletes a non-anchor marker via `marker.box.delete()`. Anchor check: `marker.isAnchor` (first/last in `warpMarkers.asArray()`).
- `update_warp_marker(unit_index, track_index, region_index, marker_index, position_beats=-1, seconds=-1)` — Updates position and/or seconds. `-1` = leave unchanged. Position converted via `Math.round(beats * h.ppqn.Quarter)`.

### Access pattern

```javascript
const region = trackAdapter.regions.collection.asArray()[regionIndex];
const playMode = region.observableOptPlayMode.unwrap(); // AudioTimeStretchBoxAdapter or AudioPitchStretchBoxAdapter
const stretchBox = playMode.box; // AudioTimeStretchBox or AudioPitchStretchBox
const markers = playMode.warpMarkers.asArray(); // WarpMarkerBoxAdapter[]
// marker.box → WarpMarkerBox (fields: position Int32Field, seconds Float32Field, owner PointerField)
```

### Globals required

`DAW_WarpMarkerBox` and `DAW_TransientMarkerBox` added to headless-daw/src/main.ts in the studio-boxes lazy-load block.

### E2E test recipe

1. `mcp_opendaw_load_audio(wav_path, name)` → get `id` (UUID)
2. `mcp_opendaw_create_audio_track()`
3. `mcp_opendaw_create_time_stretched_region(sample_id, 0, 0, 0, 1.0, 'transient', 120)` — creates region with 2 anchor markers
4. `list_warp_markers` → 2 markers (anchors at position 0/0s and 3840ppqn/2s)
5. `create_warp_marker(0, 0, 0, 1.0, 0.5)` → 3 markers
6. `update_warp_marker(0, 0, 0, 1, 1.5, 0.75)` → position 1440ppqn, seconds 0.75
7. `delete_warp_marker(0, 0, 0, 1)` → 2 markers remaining

### Key gotchas

- `sample_id` for `create_time_stretched_region` is the UUID from `load_audio` response `.id`, NOT the name string.
- `playMode.box` gives the stretch box — `stretchBox.warpMarkers` is the PointerField collection to `.refer()` into.
- Anchor markers (`isAnchor === true`) cannot be deleted — tool returns error.
- WarpMarkerBox fields: `position` (field 2, Int32Field, ppqn), `seconds` (field 3, Float32Field), `owner` (field 1, PointerField→WarpMarkers).

## v1.8.2: Audio Region Time Base & Waveform Offset (2 tools)

### Tools

- `set_audio_region_time_base(unit_index, track_index, region_index, time_base)` — Sets `AudioRegionBox.timeBase` (StringField field 4). Values: `'musical'` (PPQN, tempo-following) or `'seconds'` (fixed wall-clock). Input sanitized and validated against enum. Access: `region.box.timeBase.setValue(value)`.
- `set_audio_region_waveform_offset(unit_index, track_index, region_index, offset)` — Sets `AudioRegionBox.waveformOffset` (Float32Field field 7). Offset in seconds. Access: `region.box.waveformOffset.setValue(offset)`.

### TimeBase enum

```typescript
enum TimeBase {
    Musical = "musical", // PPQN — duration follows tempo changes
    Seconds = "seconds", // fixed wall-clock time
}
```

### E2E test recipe

1. Load audio + create track + place audio region (non-stretched is fine)
2. `get_region_info(0, 0, 0)` → `time_base: "seconds"` (default for placed regions)
3. `set_audio_region_time_base(0, 0, 0, 'musical')` → old: "seconds", new: "musical"
4. `set_audio_region_waveform_offset(0, 0, 0, 0.25)` → old: 0, new: 0.25
5. Invalid time_base ('invalid') → error returned, no mutation

### Key gotchas

- `AudioRegionBox.playback` (field 3) is **deprecated** — do not use.
- `timeBase` is a StringField, not an enum field — set with `.setValue("musical")` or `.setValue("seconds")`.
- Sanitize string input: `safe_tb = time_base.replace('"','').replace("'","").replace('\\','').strip().lower()` before validating.
