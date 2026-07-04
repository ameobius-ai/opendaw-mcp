# Tempo, Mixer & Region Advanced Tools (149-154)

Tools added in the July 2026 session that expanded coverage beyond the original 148.

## Tempo & Project Info (149-155, 7 tools)

### ppqn_to_seconds(position_beats)
Converts beats to seconds using `p.tempoMap.ppqnToSeconds()`. Accounts for tempo automation.
- 1 beat = PPQN.Quarter = 960 pulses
- `ppqn = int(position_beats * 960)`
- E2E: 4 beats @120 BPM → 2.0 seconds ✅

### seconds_to_beats(seconds)
Inverse of above. Uses `p.tempoMap.secondsToPPQN()`. Roundtrip-accurate.
- E2E: 2.0s @120 BPM → 4.0 beats ✅

### get_tempo_at(position_beats)
Gets BPM at a position via `p.tempoMap.getTempoAt()`. Accounts for tempo automation events.

### get_project_duration()
Returns end of last region across all tracks. Uses `p.lastRegionAction()`.
Returns duration in beats, ppqn, and seconds (via tempoMap).

### validate_project()
Checks for overlapping regions via `p.invalid()`. If invalid, scans all tracks for specific overlap locations.

### list_samples()
Lists all AudioFileBox UUIDs via `p.collectSampleUUIDs()`. Returns hex UUID strings.

### get_unit_freeze_status(unit_index)
Checks `p.audioUnitFreeze.isFrozenUuid(uuid)` and `hasSidechainDependents(adapter)`.
An AU with sidechain dependents cannot be frozen.
Uses `auAdapters[{unit_index}].uuid` — not `box.address.uuid`.

## Mixer & Region Advanced (146-148, 3 tools)

### get_mixer_state()
Returns all AU channel strips: index, label, type, volume_db, panning, mute, solo, is_output/bus/instrument.
Uses `p.rootBoxAdapter.audioUnits.adapters()` and `adapter.namedParameter`.
Volume is in dB (mapped via ValueMapping.decibel(-96, -9, +6)).

### flatten_note_regions(unit_index, track_index, region_indices)
Merges overlapping note regions into one. `region_indices` is comma-separated string.
**Critical**: regions must be selected first (`onSelected()`), and flatten must run inside `editing.modify()`.
Returns box (not adapter) — use `.getValue()` for fields.
E2E: 2 regions (0-4beat, 2-6beat) → 1 region (0-6beat) ✅

### consolidate_region(unit_index, track_index, region_index)
Makes event collection unique (not shared/mirrored). No `editing.modify()` needed.
`region.consolidate()` directly manipulates pointer references.

## Warp Markers & Play Mode (149-151, 3 tools)

### list_warp_markers(unit_index, track_index, region_index)
Lists warp markers on stretched audio regions. Access via `region.observableOptPlayMode`.
Returns: position (ppqn), seconds, isAnchor for each marker.
Non-stretched regions return empty list.

### get_region_play_mode(unit_index, track_index, region_index)
Returns stretch type ('time-stretch'/'pitch-stretch'/'none'), playback_rate, cents, transient_mode, warp_marker_count.
`playMode.constructor.name` distinguishes time vs pitch stretch.

### set_time_stretch_cents(unit_index, track_index, region_index, cents)
Sets pitch shift on time-stretched regions. `playMode.cents = value` (setter clamps to ±1200).
Requires `editing.modify()`. Only works on AudioTimeStretchBoxAdapter.

## Automation & Audio Info (152-153, 2 tools)

### get_automation_value(unit_index, track_index, position_beats)
Resolves automation curve via `trackAdapter.valueAt(ppqn, 0.0)`.
Accounts for interpolation, region loops, overlapping regions.
Returns normalized 0.0-1.0 value.

### get_audio_file_info(unit_index, track_index, region_index)
Returns file metadata via `region.optFile.unwrap()`:
- fileName, startInSeconds, endInSeconds, duration_seconds
- When loaded: sampleRate, numChannels, numFrames

## Region Content Shift (154, 1 tool)

### move_region_content(unit_index, track_index, region_index, delta_beats)
Shifts content inside region via `region.moveContentStart(delta_ppqn)`.
- For audio: waveformOffset adjusts (seconds timeBase uses tempoMap conversion)
- For notes: note positions shift by -delta
- Region position unchanged, duration shrinks from left
- Requires `editing.modify()`

## Common access pattern for all new tools

All new tools follow the same adapter access chain:
```javascript
const auAdapters = p.rootBoxAdapter.audioUnits.adapters();
const auAdapter = auAdapters[unit_index];
const trackAdapters = auAdapter.tracks.collection.adapters();
const trackAdapter = trackAdapters[track_index];
const regions = trackAdapter.regions.collection.asArray();
const region = regions[region_index];
```

**Never** use `p.boxAdapters.adapterFor(box, 'ClassName')` — strings fail with "Unknown checkType method".
