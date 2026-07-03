# openDAW MCP Tool Catalog

211 MCP tools for headless openDAW control via Playwright bridge.

## Project (7)
- `get_project_state` — full state: BPM, sample rate, tracks, effects
- `get_project_info` — quick summary: BPM, time sig, counts, duration
- `serialize` — serialize project to JSON
- `reset_project` — clear all AUs/tracks/effects (keep master output)
- `save_project` — save to .odaw binary file
- `load_project` — load from .odaw file
- `list_tracks` — list all tracks across all AUs

## Transport (5)
- `transport` — play/stop/toggle
- `set_position` — set playback position in beats
- `set_bpm` — set tempo
- `set_time_signature` — set numerator/denominator
- `set_loop_region` — loop playback between two positions (from/to/enabled)

## Tempo & Signature (5)
- `add_tempo_change` — BPM automation point (ValueEventBox on TempoTrack, normalized 0..1→minBpm..maxBpm)
- `list_tempo_changes` — list all tempo events with BPM/interpolation
- `add_signature_change` — time signature change mid-track (SignatureEventBox)
- `list_signature_changes` — list all signature events
- `delete_signature_change` — remove signature event by index/position

## Groove & Tuning (2)
- `set_groove_shuffle` — swing/groove amount (0=straight, 1=full swing)
- `set_tuning` — A4 base frequency (440/432/415/466 Hz)

## Markers (5)
- `add_marker` — timeline marker at position (Verse, Chorus, etc.)
- `list_markers` — list all markers with positions and labels
- `delete_marker` — remove marker by index
- `set_marker_position` — move marker to new position
- `set_marker_label` — rename marker

## Tracks (7)
- `create_audio_track` — audio track on primary AU
- `create_note_track` — note track on an AU
- `create_instrument_track` — Tape device (audio playback)
- `create_synth_track` — synth instrument (Vaporisateur/Nano/Soundfont/Apparat)
- `delete_audio_unit` — remove AU + all tracks/effects/sends (index >= 1)
- `rename_unit` — set InstrumentBox.label + icon via au.input.pointerHub.incoming()
- `set_track_enabled` — enable/disable (mute) individual track via track.enabled field

## Instrument (1)
- `replace_instrument` — replace MIDI instrument (Vaporisateur↔Nano↔Soundfont↔Apparat) via api.replaceMIDIInstrument

## Audio (7)
- `load_audio` — load WAV/MP3 into DAW
- `place_audio_region` — place audio on timeline
- `start_engine` — start audio engine
- `delete_audio_region` — remove audio region
- `list_audio_regions` — list all audio regions
- `set_audio_region_fade` — fade in/out (seconds + curve slope)
- `set_audio_region_gain` — per-region gain in dB

## Effects (14)
- `list_effects` — list available effect types
- `add_effect` — add effect to AU chain
- `list_effect_parameters` — params with value/unit/min/max/scaling
- `get_effect_state` — full snapshot: enabled/minimized/sidechain + all params
- `set_effect_parameter` — set numeric parameter
- `set_effect_parameter_string` — set string parameter
- `remove_effect` — remove effect from chain
- `get_effect_chain` — full chain listing
- `set_effect_enabled` — bypass/enable effect
- `connect_sidechain` — wire sidechain source to compressor
- `add_automation` — automate effect parameter over time
- `clone_effect_chain` — copy chain from one AU to another
- `move_effect` — reorder effect in chain
- `compact_tracks` — remove empty tracks from AU

## Notes (9)
- `create_note` — add MIDI note to track
- `import_midi` — import .mid file (custom parser, PPQN 480→960)
- `transpose_notes` — shift all notes by semitones
- `delete_note_region` — remove note region
- `list_note_regions` — list all note regions
- `quantize_notes` — snap to grid (1/4, 1/8, 1/16, 1/32, 1/64)
- `duplicate_note_region` — copy region + notes to new position
- `duplicate_notes` — duplicate all notes within region (shift after last note)
- `list_notes` — list all note events in a region (position/duration/pitch/velocity/cent/chance)

## Note Editing (2)
- `set_note_properties` — edit single note: position/duration/pitch/velocity/cent/chance (-1=skip)
- `delete_note` — delete single note by index

## Regions (8)
- `set_region_position` — move region
- `set_region_duration` — resize region
- `set_region_mute` — mute/unmute
- `set_region_label` — rename
- `set_region_loop` — set loop offset/duration
- `set_region_color` — set region/clip hue (0-360 HSL)
- `create_track_region` — generic api.createTrackRegion for note/value tracks
- `delete_region` — delete region + all contents (note/audio/value)

## Clips (11)
- `list_clips` — list NoteClipBox/AudioClipBox/ValueClipBox on tracks (session view)
- `create_note_clip` — create NoteClipBox in session view (api.createNoteClip)
- `create_audio_clip` — create AudioClipBox in session view (api.createNotStretchedClip)
- `create_time_stretched_clip` — audio clip with playback rate + transient mode (api.createTimeStretchedClip)
- `create_pitch_stretched_clip` — pitch-aligned audio clip (api.createPitchStretchedClip)
- `set_clip_playback` — ClipPlaybackFields (loop/reverse/speed/quantise/trigger)
- `set_clip_properties` — label/hue/mute/duration on clips (batch setter)
- `set_clip_mute` — mute/unmute individual clip (granular)
- `set_clip_label` — set clip name (granular)
- `set_clip_hue` — set clip color 0-360 (granular)
- `delete_clip` — remove clip from track

## MIDI Export (1)
- `export_midi` — export note region to .mid file (lib-midi encoder)

## Export (7)
- `export_mix` — render full mix to WAV (offline/realtime/auto)
- `render_full` — render entire project as stereo WAV (OfflineEngineRenderer, Option.None)
- `export_stems` — render per-track stems
- `export_single_stem` — render one stem
- `render_range` — render a time range (OfflineEngineRenderer with ExportConfiguration.range)
- `measure_lufs` — measure integrated LUFS
- `auto_gain` — auto-adjust gain to LUFS target via Maximizer

## Sends (6)
- `create_send` — create aux send to FX bus
- `set_send_level` — set send gain (dB)
- `set_send_pan` — set send pan
- `set_send_routing` — pre/post fader
- `list_sends` — list all sends on AU
- `remove_send` — remove a send

## Buses (3)
- `list_audio_buses` — list FX buses
- `set_bus_enabled` — mute/unmute FX bus
- `remove_audio_bus` — remove FX bus + AU + sends

## Mixing (4)
- `set_track_volume` — set AU volume (dB)
- `set_track_panning` — set AU pan
- `set_track_mute` — mute AU
- `set_track_solo` — solo AU

## Automation (5)
- `add_automation` — create automation track + value events
- `create_value_clip` — create automation clip in session view (api.createValueClip)
- `list_automation_events` — list ValueEventBox points on automation tracks
- `list_value_regions` — list ValueRegionBox on automation tracks
- `delete_automation_event` — delete single automation event (ValueEventBox) by index

## Audio Stretch (3)
- `create_time_stretched_region` — audio region with playback rate + transient mode (api.createTimeStretchedRegion)
- `create_pitch_stretched_region` — pitch-stretched audio region (api.createPitchStretchedRegion)
- `duplicate_region` — duplicate any region via api.duplicateRegion (findFreeSpace option)

## MIDI Effects (6)
- `list_midi_effects` — list available MIDI effect types (Arpeggio/Pitch/Velocity/Zeitgeist/Spielwerk)
- `add_midi_effect` — add MIDI effect to au.midiEffects chain
- `remove_midi_effect` — remove MIDI effect from chain
- `get_midi_effect_chain` — get full MIDI effect chain for AU
- `list_midi_effect_params` — list MIDI effect parameters with values
- `set_midi_effect_param` — set MIDI effect parameter by name or field index

## Vaporisateur Synth (2)
- `list_vaporisateur_params` — full synth state: oscillators (waveform/volume/octave/tune), LFO, noise, main params (cutoff/resonance/ADSR/etc)
- `set_vaporisateur_osc_param` — set oscillator parameter (waveform: 0=Sine/1=Triangle/2=Saw/3=Square, volume dB, octave, tune)

## Instrument Parameters (2)
- `list_instrument_params` — universal: list all params of any instrument (Vaporisateur/Tape/Nano/Soundfont/MIDIOutput/Playfield/Apparat)
- `set_instrument_param` — universal: set any instrument parameter by name or field index

## Playfield / Drum Machine (3)
- `list_playfield_samples` — list drum pads (MIDI note, enabled, file status)
- `set_playfield_sample_enabled` — enable/disable a drum pad
- `create_playfield_sample` — add a drum pad (AudioFileBox + PlayfieldSampleBox, needs existing samples)

## Scriptable Devices (5)
- `set_script_device_code(device_type, unit_index, device_index, code)` — Compile JS code on Apparat/Werkstatt/Spielwerk. Parses @param/@sample, creates boxes, validates, registers worklet. device_index for multiple devices of same type.
- `get_script_device_code(device_type, unit_index, device_index)` — Read current JS code + header
- `list_script_params(device_type, unit_index, device_index)` — List @param WerkstattParameterBox entries (label, index, value, defaultValue)
- `set_script_param(device_type, unit_index, device_index, param_label, value)` — Set parameter value by label
- `list_script_samples(device_type, unit_index, device_index)` — List @sample WerkstattSampleBox entries (label, index, hasFile)

## Editing (2)
- `undo` — undo last action
- `redo` — redo

## Audio Unit (8)
- `duplicate_audiounit(unit_index)` — Deep-copy an AU: instrument (same factory + all params), audio effects (same types + all param values), MIDI effects, note tracks/regions/events, track volume/panning, AU label/volume. Python-orchestrated via existing MCP tools (create_synth_track → copy params → add_effect → create_note).
- `delete_track(unit_index, track_index)` — Delete a track from an AU via AudioUnitBoxAdapter.deleteTrack. Removes all regions/clips/notes.
- `move_region_to_track(src_unit_index, src_track_index, region_index, dst_unit_index, dst_track_index)` — Move a region between tracks (same or different AU). Checks type compatibility. Region keeps position/duration/content.
- `create_audio_bus(name)` — Create a new aux bus (AudioBusBox) routed to primary bus output. Use as send target.
- `move_audio_unit(unit_index, delta)` — Move AU up/down in mixer order (delta: +1 down, -1 up)
- `move_track(unit_index, track_index, delta)` — Move track up/down within an AU (delta: +1 down, -1 up)
- `transfer_region(src_unit_index, src_track_index, region_index, dst_unit_index, dst_track_index, insert_position, delete_source)` — Transfer/copy a region to another track at a specific position via TransferRegions.transfer. Copies region + all dependencies (notes, events, audio files). Preserved resources shared. delete_source=true for move semantics.
- `transfer_audiounit(unit_index, delete_source, insert_index)` — Deep-copy an AU with all dependencies (instrument, effects, MIDI effects, tracks, regions, notes, automation) via TransferAudioUnits.transfer. Box-graph serialization, more complete than duplicate_audiounit. Output unit cannot be copied.

## Presets (4)
- `export_preset(unit_index, include_timeline)` — Serialize an AU to base64 binary preset via PresetEncoder.encode. Includes instrument, effects, MIDI effects. include_timeline=true adds tracks/regions/notes.
- `import_preset(preset_b64)` — Import a base64 preset as a new AU via PresetDecoder.decode. Recreates instrument, effects, MIDI effects, tracks from the preset.
- `replace_from_preset(unit_index, preset_b64, keep_midi_effects, keep_audio_effects, keep_timeline)` — Replace an AU's instrument from preset via PresetDecoder.replaceAudioUnit. Optionally keep target's MIDI/audio effects and timeline. Preset must be compatible type (MIDI→MIDI).
- `export_effect_chain(unit_index, effect_type)` — Export an effect chain (audio or MIDI) as base64 preset via PresetEncoder.encodeEffects.

## Tempo & Project Info (7)
- `ppqn_to_seconds(position_beats)` — Convert beats to seconds using the project's VaryingTempoMap. Accounts for tempo automation. 1 beat = 960 ppqn.
- `seconds_to_beats(seconds)` — Convert seconds to beats using the tempo map. Roundtrip-accurate with tempo automation.
- `get_tempo_at(position_beats)` — Get BPM at a specific position, accounting for tempo automation events.
- `get_project_duration()` — Total project duration: end of last region across all tracks. Returns beats, ppqn, and seconds.
- `validate_project()` — Check for overlapping regions and validity issues. Returns valid (bool) + issue details.
- `list_samples()` — List all audio file sample UUIDs referenced in the project.
- `get_unit_freeze_status(unit_index)` — Check if an AU is frozen (pre-rendered) and whether it can be frozen (no sidechain dependents).
- `freeze_audiounit(unit_index)` — Freeze an AU — pre-render its output offline to save CPU. Cannot freeze AUs with sidechain dependents.
- `unfreeze_audiounit(unit_index)` — Unfreeze a frozen AU — resume real-time processing.

## Mixer & Region Advanced (3)
- `get_mixer_state()` — All AU channel strips: index, label, type, volume_db, panning, mute, solo, is_output/bus/instrument.
- `flatten_note_regions(unit_index, track_index, region_indices)` — Merge overlapping note regions into one. Originals deleted, notes combined. Requires 2+ regions.
- `consolidate_region(unit_index, track_index, region_index)` — Make a region's event collection unique (not shared/mirrored). Edits won't affect other regions.

## Warp Markers & Play Mode (3)
- `list_warp_markers(unit_index, track_index, region_index)` — List warp markers (position, seconds, isAnchor) on stretched audio regions.
- `get_region_play_mode(unit_index, track_index, region_index)` — Get stretch type, playback rate, cents, transient mode for audio regions.
- `set_time_stretch_cents(unit_index, track_index, region_index, cents)` — Set pitch shift in cents on time-stretched regions. ±1200 cents = ±1 octave.

## Automation & Audio Info (3)
- `get_automation_value(unit_index, track_index, position_beats)` — Resolve automation curve value at a position. Accounts for interpolation, loops, overlapping regions.
- `get_audio_file_info(unit_index, track_index, region_index)` — Audio region file metadata: name, start/end seconds, duration, sample rate, channels, loading state.
- `move_region_content(unit_index, track_index, region_index, delta_beats)` — Shift content inside a region without moving the region. Adjusts waveform offset (audio) or note positions (MIDI).

## Inspection Helpers (3) — using DAW_HELPERS
- `get_track_info(unit_index, track_index)` — Track metadata: type, enabled, regions (position/duration/mute/label/mirrored), clips.
- `get_full_project_state()` — Complete project snapshot: BPM, duration, all AUs (label/type/volume/pan/mute/solo/tracks/effects), all tracks (type/regions/clips).
- `get_region_info(unit_index, track_index, region_index)` — Single region: position/duration/loop/mute/label/hue/mirrored/type + notes count (MIDI) or file info (audio).

## Clip Operations (2)
- `clone_clip(unit_index, track_index, clip_index, consolidate)` — Clone a note/value clip on the same track. consolidate=true for independent event collection.
- `consolidate_clip(unit_index, track_index, clip_index)` — Make a clip's event collection unique (not shared/mirrored).

## Automation Event Management (5)
- `create_automation_event(unit_index, track_index, position_beats, value, interpolation, curve_slope)` — Create a single automation point with interpolation (none/linear/curve).
- `list_automation_events_detail(unit_index, track_index)` — List all automation events with full detail: position, value, interpolation type, curve slope.
- `set_automation_interpolation(unit_index, track_index, region_index, event_index, interpolation, curve_slope)` — Change interpolation type of an existing automation event.
- `move_automation_event(unit_index, track_index, event_index, new_position_beats)` — Move an automation event to a new position. Returns old/new positions.
- `update_automation_event(unit_index, track_index, event_index, value, interpolation, curve_slope)` — Update value and/or interpolation of an existing event. Skip with -1/empty.

## Note Collection Analysis (2)
- `get_note_range(unit_index, track_index, region_index)` — Pitch range (min/max), max note duration, note count. Useful for transpose planning.
- `find_overlapping_notes(unit_index, track_index, region_index, pitch, from_beat, to_beat)` — Find notes at a specific pitch within a time range. Collision detection.

## Note Advanced Properties (2)
- `set_note_advanced(unit_index, track_index, region_index, note_index, chance, cent, play_count, play_curve)` — Set chance (0-100%), cent (-50..+50), playCount (1-16), playCurve (-1..+1). Sentinel -1/-999 to skip.
- `consolidate_note(unit_index, track_index, region_index, note_index)` — Expand repeated note (playCount>1) into N individual notes via playCurve.

## Device Management (2)
- `set_device_label(unit_index, effect_index, label, is_midi_effect)` — Rename an audio or MIDI effect device.
- `get_device_chain_detail(unit_index)` — Full device chain: instrument (label/type/enabled), audio effects (index/label/type/enabled/minimized), MIDI effects.

## Key Technical Details

- **PPQN.Quarter = 960** — all positions in ticks, 1 beat = 960 ticks
- **Field values = physical units** — `field.setValue(thresholdDb)` directly
- **editing.modify()** — required wrapper for all box mutations
- **Send topology:** fxUnit→primaryBus, fxBus→fxUnit.input, send→fxBus.input (parallel)
- **Note events:** `region.events.targetVertex.unwrap().box` → `collection.events.pointerHub.incoming()`
- **NoteEventBox:** position(ppqn), duration(ppqn), pitch(0-127), velocity(0-1), cent, chance(0-100)
- **TempoTrack:** ValueEventBox with normalized value 0..1, bpm = minBpm + norm*(maxBpm-minBpm), default 60..240
- **SignatureEventBox:** relativePosition(bars), nominator, denominator
- **Region/clip hue:** Int32Field 0-360 (HSL)
- **Effect params:** `field.unit` and `field.constraints` public getters (scaling: unipolar/bipolar/decibel/exponential)
- **Bridge:** Playwright headless Chromium, Vite dev server on :5174, COOP/COEP enabled
- **AudioContext 44100 Hz** (realtime), OfflineEngineRenderer 48000 Hz
- **f-string:** ALL JS {/}→{{/}} in Python f-strings

## DSP Scripts (scripts/)
- **werkstatt_darksat.js** — Tape saturation/drive effect. Params: drive (0-1, tanh), bias (-0.5..0.5, DC offset), tone (0-1, shelving), mix (0-1, dry/wet), output (-24..6 dB). DC blocker one-pole HPF ~20Hz. API: `process(io, block)` where `io.src[0/1]` = input, `io.out[0/1]` = output.
- **werkstatt_coldfold.js** — Wavefolding + bitcrush effect. Params: drive (0-2), fold (0-1, mirror distortion), crush (0-1, bit depth 16→1), slew (0-1, sample-rate reduction), mix (0-1). API: `process(io, block)`.
- **apparat_darkbass.js** — Subtractive bass synth. Params: waveform (0=Sine/1=Tri/2=Saw/3=Square), cutoff (50-8000Hz exp), resonance (0.1-8), attack/decay/sustain/release (ADSR), subOsc (0-1, square one octave down), detune (0-0.5), volume (0-1). Multi-voice, lazy voice allocation. Constructor must accept `opts` with optional `sampleRate` (default 48000) — ApparatDeviceProcessor calls `new ProcessorClass()` without args. API: `process([outL, outR], block)` where block has s0/s1/bpm.
- **apparat_coldlead.js** — Cold lead synth (post-punk clav). Params: waveform (default triangle), cutoff (50-8000Hz exp), resonance, ADSR (long release), detune (0-0.5), volume. Two detuned oscillators with random phase start. Constructor accepts optional `opts.sampleRate`.
- **spielwerk_arpeggiator.js** — MIDI arpeggiator. Params: rate (60-1920 ppqn), mode (0=up/1=down/2=up-down/3=random), octaves (1-4), gate (0.1-1), velDecay (0.3-1). Tracks `nextStepPos` across blocks — critical because block size (~5ppqn) is much smaller than rate (240ppqn). API: `process(block, events)` returns array of `{position, duration, pitch, velocity, cent}`. Must use `return array` NOT `* process()` generator — `new Function()` rejects generator methods.
- **spielwerk_powerchord.js** — MIDI effect that generates power chord harmonies.

## Musical Grid & Signature (7 tools)
- **ppqn_to_parts** — Convert PPQN to bars/beats/semiquavers/ticks with time signature awareness
- **get_bar_interval** — Get bar boundaries (start/end/length) for a PPQN position
- **move_signature_event** — Move time signature change to new PPQN, auto-recalculates subsequent events
- **copy_region_fades** — Copy fade in/out + slopes between audio regions
- **get_signature_events** — List all time signature changes with accumulated positions
- **delete_signature_event** — Delete signature change, auto-recalculate
- **change_base_signature** — Change project base time signature (4/4 → 3/4 etc), recalculates events

## Advanced Operations (8 tools)
- **copy_playfield_sample** — Duplicate drum sample slot with all params (mute/solo/pitch/ADSR/gate)
- **reset_playfield_params** — Reset drum sample params to defaults
- **duplicate_note_event** — Copy note with position/pitch offset
- **duplicate_automation_event** — Copy automation event with position/value override
- **copy_region_to_track** — Copy any region (note/audio/automation) to a different track at optional new position
- **get_project_metadata** — Creation date, time signature, AU count, track count in one call
- **set_bus_label** — Rename an audio bus
- **set_bus_color** — Set bus color hue (0-360)

## Modular System (7 tools)
- **list_modular_devices** — Find all Modular audio effects in project (AU index, module/connection counts)
- **list_modular_modules** — List modules with type/label/x,y/inputs/outputs/parameter values
- **list_modular_connections** — List patch cables (source module.field → target module.field)
- **add_modular_module** — Add module: gain/delay/multiplier/audio-input/audio-output
- **connect_modular_modules** — Create patch cable between source output and target input
- **set_modular_module_param** — Set module parameter (gain in dB, time in ms) via box field
- **remove_modular_module** — Delete module and all its connections

## PianoMode (6 tools)
- **set_transpose** — Set global piano roll transpose (-48 to +48 semitones)
- **get_piano_mode** — Get keyboard type, time range, note scale, labels, transpose
- **set_piano_keyboard(keyboard_type)** — Set keyboard type: 88 (full piano), 76 (stage), 61 (compact), 49 (controller)
- **set_piano_note_scale(scale)** — Set vertical note zoom (0.5–2.0, 1.0=default)
- **set_piano_note_labels(show)** — Toggle note labels (C, C#, D, etc.) in piano roll
- **set_piano_time_range(quarters)** — Set horizontal view width in quarter notes (1.0–64.0)

## MIDI Output Devices (1 tool)
- **list_midi_output_devices** — List hardware MIDI output devices registered in the project (id, label, delay_ms, send_transport)

## Debugging & Control (3 tools)
- **screenshot_daw** — Take a screenshot of the openDAW UI. Returns base64-encoded PNG. Useful for visual debugging and verifying project state.
- **wait_for_condition(condition_js, timeout_ms, poll_interval_ms)** — Poll a JavaScript condition in the DAW context until truthy or timeout. Useful for waiting on async operations (render completion, file loading).
- **evaluate_raw(script)** — Execute arbitrary JavaScript in the DAW V8 context. For power users and debugging — explore openDAW internals directly. Script is wrapped in an async arrow function with access to window.DAW and all DAW_ globals.
