# openDAW MCP Tool Catalog (67 tools, verified July 2 session 7)

## Architecture
MCP Server (Python/FastMCP) → Playwright → headless Chromium → Vite :5175 → @opendaw/studio-sdk
Server: `/home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp/server.py`

## Full tool list

### Project & Transport (6)
- `get_project_state` — BPM, sampleRate, isPlaying, position, audioUnits, effects, totalBoxes
- `get_project_info` — **Added session 7** (tool #65). Quick summary: bpm, time_signature, audio_units, tracks, regions, effects, notes, duration_beats, duration_bars. Lighter than get_project_state. Test: empty project → 120bpm 4/4, 1 AU, 0 tracks.
- `transport(action)` — play/stop/toggle
- `set_position(position_beats)` — playback position in beats
- `set_bpm(bpm)` — project tempo
- `set_time_signature(numerator, denominator)` — Time signature: 4/4, 3/4, 6/8, 7/8 etc. Uses `timelineBox.signature.nominator/denominator`. Validated: numerator 1-16, denominator in {1,2,4,8,16}.

### Tracks (5)
- `create_audio_track` — audio track on primary AU (use create_instrument_track instead)
- `create_note_track(unit_index=-1)` — MIDI track. -1 = primary AU, or pass instrument AU index with a synth device.
- `create_instrument_track(name)` — **REQUIRED for audio playback**: CaptureAudioBox + AudioUnitBox(Instrument) + TapeDeviceBox + audio track. Returns unit_index + track_index.
- `create_synth_track(name, synth_type)` — **MIDI synth playback**: CaptureAudioBox + AudioUnitBox(Instrument) + synth device + note track. synth_type: "vaporisateur"(default, subtractive), "nano"(simple), "soundfont"(SF2), "apparat"(FM). Returns unit_index + track_index. See `references/midi-synth-pipeline.md`.
- `list_tracks()` — structured listing of all AUs with their tracks, effects, and types.

### Audio (5)
- `load_audio(url_or_path)` — fetch + decodeAudioData → DAW_localAudioBuffers + DAW_fileNameToAudioBuffer. Returns sample_id.
- `place_audio_region(sample_id, unit_index, start_beat, track_index)` — uses `api.createNotStretchedRegion`. Requires instrument AU with TapeDeviceBox.
- `start_engine` — deferred start, serializes current boxGraph into AudioWorklet. Call AFTER all setup.
- `delete_audio_region(unit_index, track_index, region_index)` — Deletes an audio region (type=2 tracks).
- `list_audio_regions(unit_index, track_index)` — Lists audio regions: region_index, track_index, position_beats, duration_seconds, file_name.

### Effects (11)
- `list_effects` — available audio + MIDI effect names
- `add_effect(unit_index, effect_type)` — inserts effect, returns effect_index. **Case-insensitive**: `reverb`→`Reverb`, `COMPRESSOR`→`Compressor`.
- `list_effect_parameters(unit_index, effect_index)` — uses box.record(), shows name/value/type/range
- `set_effect_parameter(unit_index, effect_index, parameter_name, value)` — numeric params. Values in physical units (dB, Hz, ms).
- `set_effect_parameter_string(unit_index, effect_index, parameter_name, string_value)` — string params (e.g. Waveshaper equation)
- `remove_effect(unit_index, effect_index)` — deletes effect box
- `get_effect_chain(unit_index)` — ordered list of effects with type/enabled/label
- `set_effect_enabled(unit_index, effect_index, enabled)` — bypass/re-enable without removing
- `clone_effect_chain(src_unit, dst_unit)` — Copies all effects from src AU to dst AU with parameter values.
- `move_effect(unit_index, from_index, to_index)` — Reorders effects in chain by shifting index values.
- `connect_sidechain(compressor_unit, compressor_effect_index, source_unit_index)` — wraps `compBox.sideChain.refer(sourceAU)`.

### Sends & Buses (9)
- `create_send(src_unit, name, send_level_db, routing)` — Creates a parallel FX send bus. Returns `fx_unit_index`. See `references/send-return-routing.md`.
- `set_send_level(src_unit, send_index, level_db)` — Sets send gain in dB.
- `set_send_pan(src_unit, send_index, pan)` — Stereo pan: -1.0 (left) to 1.0 (right).
- `set_send_routing(src_unit, send_index, routing)` — Pre/post fader switch.
- `list_sends(unit_index)` — Lists all sends on AU.
- `remove_send(unit_index, send_index)` — Deletes an aux send.
- `list_audio_buses()` — Lists all AudioBusBox.
- `set_bus_enabled(bus_index, enabled)` — Mute/unmute bus.
- `remove_audio_bus(bus_index, fx_unit_index)` — Removes FX bus + AU + cleans up sends.

### Notes & MIDI (2)
- `create_note(track_index, pitch, start_beat, duration_beats, velocity, unit_index=-1)` — NoteEventBox on note track. Uses NoteRegionBox for timeline placement.
- `import_midi(file_path, unit_index, track_index, offset_beats)` — Custom Python MIDI parser (no deps). PPQN conversion (source→960). Creates one region + collection with all notes.

### Region Operations (8) — Added sessions 6-7
- `transpose_notes(semitones, unit_index=-1, track_index=-1)` — Shift all note pitches by semitones. Clamps to 0-127.
- `quantize_notes(division, unit_index=-1, track_index=-1, strength=1.0)` — Snap to grid: 1/4, 1/8, 1/16, 1/32, 1/64. Quantizes BOTH region.position (absolute) AND evt.position (relative).
- `delete_note_region(unit_index=-1, track_index=0, region_index=0)` — Deletes a note region via `region.delete()`.
- `list_note_regions(unit_index=-1, track_index=-1)` — Lists note regions with position, duration, label, note_count.
- `duplicate_note_region(unit_index=-1, track_index=0, region_index=0, offset_beats=4.0)` — Copies region + all notes to new position. Creates new NoteEventCollectionBox + NoteRegionBox. **Tested session 7**: region 0 (Original, pos=0, 3 notes 60/64/67) → region 1 (Original copy, pos=4 beats, same 3 notes).
- `set_region_position(track_index, region_index, position_beats, unit_index=-1)` — **Added session 7** (tool #61). Move region on timeline. Test: 0→8 beats ✅.
- `set_region_duration(track_index, region_index, duration_beats, unit_index=-1)` — **Added session 7** (tool #62). Resize region + loopDuration. Test: 4→2 beats ✅.
- `set_region_mute(track_index, region_index, mute, unit_index=-1)` — **Added session 7** (tool #63). Mute/unmute individual region. Test: false→true ✅.
- `set_region_label(track_index, region_index, label, unit_index=-1)` — **Added session 7** (tool #64). Rename region display label. Test: Original→Verse 1 ✅. **Note**: AU rename (rename_track) not possible — AudioUnitBox has no `name` field at box level, only via adapter (`input.adapter().labelField`), which requires boxAdapters context unavailable in headless mode. AU name is set at creation via `factory.create(graph, au.input, name, icon)`.
- `set_region_loop(track_index, region_index, loop_beats, loop_offset_beats, event_offset_beats, unit_index=-1)` — **Added session 7** (tool #67). Set loop parameters: loopDuration, loopOffset, eventOffset. Test: loop 4→2 beats, offset 0.5, duration 16 beats = 8 loops ✅.

### MIDI Export (1) — Added session 7
- `export_midi(filename, unit_index, track_index, region_index)` — **Tool #60**. Exports note region as .mid file. Uses @opendaw/lib-midi MidiFileEncoder (lazy-loaded: MidiFile, MidiTrack, ControlEvent, ControlType, ArrayMultimap). Encoder → ArrayBuffer → base64 → Python save. timeDivision=96. Velocity conversion: openDAW 0-100 → MIDI 0-127 (`Math.round(vel * 127 / 100)`). Test: 3 notes (C4/E4/G4) → 46 byte .mid, valid MThd header ✅.

### Export (5)
- `export_mix(filename, sample_rate, method)` — method: "auto"(default, offline→realtime fallback), "offline", "realtime". safe_name allows `.` and strips `.wav` if already present.
- `export_stems(filename_prefix, sample_rate)` — per-instrument-AU stems, useInstrumentOutput=true. Multi-channel WAV.
- `export_single_stem(unit_index, filename, sample_rate)` — Exports one AU with effect chain.
- `render_range(start_beat, end_beat, filename, sample_rate)` — Partial project export. ~0.6s tail for reverb decay.
- `measure_lufs(filename)` — simplified ITU-R BS.1770. Returns lufs, true_peak_db, block_count.

### Loudness (1)
- `auto_gain(target_lufs=-14, filename, sample_rate, max_iterations=3)` — iterative: export→measure→adjust→re-export. Maximizer integration when output AU at +6dB max and diff > 0.5dB.

### Mixing (4)
- `set_track_volume(unit_index, volume_db)` — **dB input**, converts to raw internally (0dB=0.768)
- `set_track_panning(unit_index, panning)` — -1.0 to 1.0
- `set_track_mute(unit_index, mute)`
- `set_track_solo(unit_index, solo)`

### Project management (8)
- `reset_project()` — clears all non-output boxes for a fresh session.
- `undo` / `redo`
- `serialize` — boxGraph.toJSON()
- `save_project(filename)` — `project.toArrayBuffer()` → .odaw file (base64).
- `load_project(filename)` — .odaw file → `Project.load()` (via `p.copy()` hack).
- `compact_tracks(unit_index=-1)` — **Added session 7** (tool #66). Remove empty tracks via `api.compactTracks()`. **MUST wrap in `editing.modify()`** — bare `api.compactTracks()` crashes with "Modification only prohibited in transaction mode". Test: AU with 2 empty note tracks → 1 after compact ✅.

## Field value convention (CRITICAL)

**openDAW PrimitiveField values store PHYSICAL UNITS, not normalized 0..1.**

- `field.getValue()` → physical units (dB, Hz, ms, ratio, etc.)
- `field.setValue(x)` → expects physical units
- `adapter.getUnitValue()` → normalized 0..1 (for UI sliders / automation only)

## Box graph traversal pattern

```javascript
// region.events is a PointerField → targetVertex → vertex.box = NoteEventCollectionBox
const vertex = region.events.targetVertex.unwrap();
const collectionBox = vertex.box || vertex;
const noteEvents = [...collectionBox.events.pointerHub.incoming()].map(({box}) => box);
```

**DO NOT use `region.events.pointerHub.incoming()`** — returns boxes pointing TO the events field, not the collection. Use `targetVertex.unwrap().box` first.

## editing.modify() is MANDATORY for all box mutations

All field.setValue() and api calls that modify the box graph MUST be wrapped in `p.editing.modify(() => { ... })`. Without it:
- `field.setValue()` → silently fails or crashes
- `api.compactTracks()` → "Modification only prohibited in transaction mode"
- `api.createNoteTrack()` → similar transaction error

## lib-midi lazy-load (added session 7)

Added to `main.ts`:
```typescript
const midi = await import("@opendaw/lib-midi");
w.DAW_MidiFile = midi.MidiFile;
w.DAW_MidiTrack = midi.MidiTrack;
w.DAW_ControlEvent = midi.ControlEvent;
w.DAW_ControlType = midi.ControlType;

const std = await import("@opendaw/lib-std");
w.DAW_ArrayMultimap = std.ArrayMultimap;
```

**Pitfall**: After adding new lazy-load modules to main.ts, the page must be reloaded for them to take effect. A running bridge session won't pick up changes without `window.location.reload()`.

## ProjectApi methods NOT exposed (require adapter context)

These `p.api` methods require `boxAdapters.adapterFor(box, AdapterClass)` which is unavailable in headless mode:
- `duplicateRegion(region, {findFreeSpace})` — takes adapter, not box. Manual box copy works instead.
- `exportMIDI(collection, name)` — uses `Files.save` (browser dialog). Use MidiFileEncoder directly instead.
- `compactTracks(au)` — works at box level BUT needs `editing.modify()` wrapper.

## Upstream contribution
- PR #280: https://github.com/andremichelle/openDAW/pull/280 — lazy-init FilterMapping fix. coderabbitai reviewed, nitpick fixed. Awaiting andremichelle.
- Issues #278/#281/#282 — bug reports, awaiting response.
