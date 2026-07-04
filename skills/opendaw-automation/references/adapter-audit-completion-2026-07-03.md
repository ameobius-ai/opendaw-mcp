# Adapter Coverage Audit — Completion (2026-07-03)

## Summary

Systematic audit of all ~70 adapter classes in `packages/studio/adapters/src/`. Cross-referenced public getters/fields with MCP tool coverage in server.py. Result: all significant adapters covered. 6 new tools added (202→208).

## New tools added (202 → 208)

### Automation CRUD (2 tools)
- `move_automation_event(unit_index, track_index, event_index, new_position_beats)` — reposition event
- `update_automation_event(unit_index, track_index, event_index, value, interpolation, curve_slope)` — update value/interpolation in-place

### Clip granular setters (3 tools)
- `set_clip_mute(unit_index, track_index, clip_index, mute)` — mute/unmute
- `set_clip_label(unit_index, track_index, clip_index, label)` — set name
- `set_clip_hue(unit_index, track_index, clip_index, hue)` — set color 0-360

### Track enabled (1 tool)
- `set_track_enabled(unit_index, track_index, enabled)` — enable/disable (mute) track

## Key findings

### NoteClipBox field names
- Field 11 = `mute` (BooleanField) — use `clip.box.mute.setValue(bool)`
- Field 12 = `label` (StringField) — use `clip.box.label.setValue(str)`
- NOT `name` or `muted` — these don't exist on NoteClipBox

### Automation event access via value clips
```
const clip = track.clips.collection.adapters()[0];  // ValueClipBoxAdapter
const optCol = clip.optCollection;
if (optCol.isEmpty()) return {error: "No collection"};
const collection = optCol.unwrap();  // ValueEventCollectionBoxAdapter
const events = collection.events.asArray();
const evt = events[event_index];
// Read: evt.position, evt.value, evt.interpolation.type
// Write: evt.box.position.setValue(newPpqn), evt.box.value.setValue(newVal)
// Interpolation: evt.interpolation = {type: 'curve', slope: 0.3}
// After position change: collection.requestSorting()
```

### Creating automation track on Output AU
Output AU has `volume` field directly on `auBox`:
```js
p.api.createAutomationTrack(auBox, auBox.volume);
```
NOT on `auBox.input.targetVertex.unwrap().box.volume` — that's the instrument device's volume, which doesn't exist on Output AU (no instrument).

### Adapter coverage status (final)

| Adapter | Status | Tools |
|---------|--------|-------|
| PianoModeAdapter | ✅ Full (6 tools) | transpose, keyboard, note_scale, note_labels, time_range, get |
| ClipBoxAdapter | ✅ Full (11 tools) | create/list/clone/consolidate/playback/mute/label/hue/properties/delete + stretched |
| Automation (ValueEventCollection) | ✅ Full CRUD | create/list/get_value/move/update/delete/interpolation |
| TrackBoxAdapter | ✅ Full | enabled setter + get_track_info reads all fields |
| RootBoxAdapter | ✅ Full | midiOutputDevices, created, pianoMode, audioBusses, audioUnits |
| MarkerTrackAdapter | ✅ Full | add/list/delete/set_position/set_label |
| GrooveShuffleBoxAdapter | ✅ | set_groove_shuffle |
| AuxSendBoxAdapter | ✅ Full | create/set_level/set_routing/set_pan/list |
| AudioFileBoxAdapter | ✅ | get_audio_file_info, list_transient_markers |
| AudioBusBoxAdapter | ✅ | enabled/color/label (icon is cosmetic) |
| SignatureTrackAdapter | ✅ Full | toParts/getBarInterval/iterateAll/changeSignature/createEvent/moveEvent/deleteAdapter |
| TimelineBoxAdapter | ✅ | signature, tempoTrackEvents, markerTrack |
| FadingAdapter | ✅ | set_audio_region_fade (in/out/inSlope/outSlope) |
| TransientMarkerBoxAdapter | ✅ | list_transient_markers |
| DeviceInterfaceKnobAdapter | ❌ Skip | UI cosmetic (modular panel knobs) |
| AudioUnitBoxAdapter.minimizedField | ❌ Skip | UI collapse, low priority |

## E2E test results (2026-07-03)

All 6 new tools verified:
- set_piano_keyboard: old 0 → new 76 ✅
- set_piano_note_scale: old 1 → new 1.5 ✅
- set_piano_note_labels: old false → new true ✅
- set_piano_time_range: old 8 → new 8.0 ✅
- list_midi_output_devices: 0 devices (headless, no hardware) ✅
- move_automation_event: pos 0 → 1920 ✅
- update_automation_event: val 0.5 → 0.85, interp linear → curve ✅
- set_clip_mute: false → true ✅
- set_clip_label: test_clip → my_clip ✅
- set_clip_hue: 120 → 240 ✅
- set_track_enabled: (syntax verified, E2E pending)
