# openDAW MCP Tool Catalog — 79 Tools (July 2026, session 9)

## Tool Count by Category

| Category | Count | Tools |
|----------|-------|-------|
| Project | 7 | get_project_state, get_project_info, serialize, reset_project, save_project, load_project, list_tracks |
| Transport | 6 | transport, set_position, set_bpm, set_time_signature, set_loop_region, set_groove_shuffle |
| Tuning | 1 | set_tuning |
| Markers | 3 | add_marker, list_markers, delete_marker |
| Tracks | 5 | create_audio_track, create_note_track, create_instrument_track, create_synth_track, delete_audio_unit |
| Audio | 7 | load_audio, place_audio_region, start_engine, delete_audio_region, list_audio_regions, set_audio_region_fade, set_audio_region_gain |
| Effects | 13 | list_effects, add_effect, list_effect_parameters, set_effect_parameter, set_effect_parameter_string, remove_effect, get_effect_chain, set_effect_enabled, connect_sidechain, add_automation, clone_effect_chain, move_effect, compact_tracks |
| Notes | 8 | create_note, import_midi, transpose_notes, delete_note_region, list_note_regions, quantize_notes, duplicate_note_region, duplicate_notes |
| Automation | 2 | list_automation_events, list_value_regions |
| Regions | 5 | set_region_position, set_region_duration, set_region_mute, set_region_label, set_region_loop |
| MIDI Export | 1 | export_midi |
| Export | 6 | export_mix, export_stems, export_single_stem, render_range, measure_lufs, auto_gain |
| Sends | 6 | create_send, set_send_level, set_send_pan, set_send_routing, list_sends, remove_send |
| Buses | 3 | list_audio_buses, set_bus_enabled, remove_audio_bus |
| Mixing | 4 | set_track_volume, set_track_panning, set_track_mute, set_track_solo |
| Editing | 2 | undo, redo |
| **Total** | **79** | |

## New Tools (76→79, session 9)

### set_audio_region_fade
AudioRegionBox field 18 = `Fading` ObjectField (NOT a Box). Fields: `in` (Float32Field, seconds, positive), `out` (Float32Field, seconds, positive), `inSlope` (Float32Field, 0-1, default 0.75), `outSlope` (Float32Field, 0-1, default 0.25). Access: `region.fading.in.setValue(0.5)`. Pass -1.0 to skip changing a parameter. Must be inside `editing.modify()`.

### set_audio_region_gain
AudioRegionBox field 17 = `gain` (Float32Field, decibel, "db" unit). Per-region gain trim. Access: `region.gain.setValue(-6.0)`. Must be inside `editing.modify()`.

### list_value_regions
Lists ValueRegionBox on type=3 (automation) tracks. Same field pattern as NoteRegionBox: position (Int32Field, ppqn), duration (Int32Field, ppqn), loopOffset, loopDuration, mute (BooleanField), label (StringField), hue (Int32Field). Returns all automation regions across a unit's value tracks.

## New Tools (74→76, session 8)

### duplicate_notes
Box-level implementation of `api.duplicateNotes` (which requires NoteEventBoxAdapter, unavailable in headless). Computes block span = max(pos+dur) - min(pos) across all notes, then creates NoteEventBox copies shifted by that span. All copies go into the same NoteEventCollection as the originals. Must be inside `editing.modify()`.

### list_automation_events
Reads ValueEventBox points from ValueClip → ValueEventCollectionBox on automation (type 3) tracks. Returns position_beats, value (0-1), index, interpolation type. Interpolation detection: field 12 value 1 = "linear", value 0 = "hold" (unless a ValueEventCurveBox is attached via pointerHub, then "curve").

## New Tools (68→74)

### set_loop_region
`timelineBox.loopArea` — LoopArea is an **ObjectField**, not a Box. Fields: `enabled` (BooleanField), `from` (Int32Field, ticks), `to` (Int32Field, ticks). Access directly: `p.timelineBox.loopArea.enabled.setValue(true)`.

### set_groove_shuffle
`rootBox.groove` — PointerField to GrooveShuffleBox. Access: `rootBox.groove.targetVertex.unwrap().box.amount.setValue(0.25)`. GrooveShuffleBox has `amount` (Float32Field, 0-1) and `duration` (Int32Field).

### set_tuning
`rootBox.baseFrequency` — Float32Field directly on RootBox. A4 concert pitch (default 440Hz). Access: `rootBox.baseFrequency.setValue(432.0)`.

### add_marker / list_markers / delete_marker
`timelineBox.markerTrack` — MarkerTrack (ObjectField). Collection: `markerTrack.markers.pointerHub.incoming()`. MarkerBox fields: `position` (Int32Field, ticks), `plays` (Int32Field), `label` (StringField), `hue` (Int32Field), `track` (PointerField → markerTrack.markers). MarkerBox requires lazy-load in main.ts. Delete: `markerBox.delete()` inside `editing.modify()`.

### list_effect_parameters (enhanced)
Now uses `field.unit` and `field.constraints` public getters instead of `field._constraints` private field. Returns scaling (unipolar/bipolar/decibel/exponential), min, max, mid, unit for each Float32Field parameter.

## Full catalog also maintained at
`/home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp/TOOL_CATALOG.md` — the live version inside the MCP server directory.
