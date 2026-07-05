# openDAW MCP Tool Catalog

283 MCP tools for headless openDAW control via Playwright bridge.

## Project & Info (12)
- `get_full_project_state` — Get a complete snapshot of the project — all AUs, tracks, regions, effects, mixer state.
- `get_project_duration` — Get the total project duration — the end position of the last region across all tracks.
- `get_project_info` — Get a quick project overview: BPM, time signature, track/AU/effect counts, total duration.
- `get_project_metadata` — Get project metadata: creation date, BPM, time signature, AU count, track count.
- `get_project_state` — Get full project state: BPM, sample rate, playing status, track list, effects chain.
- `get_studio_settings` — Get all studio preferences/settings (engine, visibility, editing, debug, storage, time-display, p...
- `load_project` — Load a previously saved project from a .odaw file.
- `reset_project` — Reset the project to a fresh state — removes all audio units, tracks, regions, effects.
- `save_project` — Save the current project state to a binary file.
- `serialize` — Serialize the current project state to JSON. Returns the serialized project data.
- `set_studio_setting` — Set a studio preference setting.
- `validate_project` — Check if the project is valid — detects overlapping regions on the same track.

## Transport (5)
- `set_bpm` — Set the project tempo in BPM.
- `set_loop_region` — Set the playback loop region.
- `set_position` — Set the playback position in beats.
- `set_time_signature` — Set the project time signature (e.g. 4/4, 3/4, 6/8, 7/8).
- `transport` — Control transport: play, stop, or toggle.

## Tempo & Signature (13)
- `add_signature_change` — Add a time signature change at a specific position in the track.
- `add_tempo_change` — Add a tempo (BPM) change at a specific position in the track.
- `change_base_signature` — Change the base time signature of the project.
- `delete_signature_change` — Delete a time signature change from the timeline.
- `get_bar_interval` — Get the start and end PPQN of the bar containing the given position.
- `get_signature_events` — List all time signature change events in the project.
- `get_tempo_at` — Get the BPM at a specific position, accounting for tempo automation.
- `list_signature_changes` — List all time signature changes on the timeline's signature track.
- `list_tempo_changes` — List all tempo (BPM) changes on the timeline's tempo track.
- `move_signature_event` — Move a time signature change event to a new PPQN position.
- `ppqn_to_parts` — Convert a PPQN position to musical parts: bars, beats, semiquavers, ticks.
- `ppqn_to_seconds` — Convert a position in beats (PPQN units) to seconds using the project's tempo map.
- `seconds_to_beats` — Convert a time in seconds to beats using the project's tempo map.

## Groove & Tuning (2)
- `set_groove_shuffle` — Set the groove/shuffle (swing) amount for the project.
- `set_tuning` — Set the A4 base frequency (concert pitch tuning).

## Tracks (10)
- `compact_tracks` — Remove empty tracks from an audio unit (or all AUs).
- `create_audio_track` — Create a new audio track on the primary audio unit.
- `create_instrument_track` — Create a new instrument audio unit with a Tape device and an audio track.
- `create_note_track` — Create a new note/MIDI track on an audio unit.
- `create_synth_track` — Create a new instrument audio unit with a synthesizer device and a note track.
- `delete_track` — Delete a track from an audio unit. Removes all regions, clips, and notes on that track.
- `get_track_info` — Get detailed info about a track — type, regions, clips, enabled state, target.
- `list_tracks` — List all tracks across all audio units with their type, effects, and regions.
- `move_track` — Move a track up or down within an audio unit.
- `set_track_enabled` — Enable or disable a track (equivalent to track mute in the UI).

## Audio Units (11)
- `delete_audio_unit` — Delete an entire audio unit with all its tracks, effects, and sends.
- `duplicate_audiounit` — Duplicate an audio unit with all its content: instrument, effects, tracks, regions, notes, automa...
- `freeze_audiounit` — Freeze an audio unit — pre-render its output offline to save CPU.
- `get_device_chain_detail` — Get detailed info about all devices on an AU — instrument, audio effects, MIDI effects.
- `get_unit_freeze_status` — Check if an audio unit is frozen and whether it can be frozen.
- `move_audio_unit` — Move an audio unit up or down in the mixer order.
- `rename_unit` — Rename an audio unit's instrument and optionally set its icon.
- `replace_from_preset` — Replace an audio unit's instrument/effects/timeline from a preset.
- `set_unit_minimized` — Minimize or expand an audio unit in the mixer view.
- `transfer_audiounit` — Transfer/copy an audio unit (instrument/effects/tracks/regions) within the project.
- `unfreeze_audiounit` — Unfreeze a frozen audio unit — resume real-time processing.

## Instruments (4)
- `list_automatable_fields` — List all automatable parameter fields on an instrument (or specific Playfield sample).
- `list_instrument_params` — List all parameters of the instrument connected to an audio unit.
- `replace_instrument` — Replace the instrument on an audio unit with a different MIDI instrument.
- `set_instrument_param` — Set a parameter on the instrument connected to an audio unit.

## Effects (17)
- `add_effect` — Add an audio effect to an audio unit's effect chain.
- `clone_effect_chain` — Copy all effects from one audio unit to another, including parameter values.
- `connect_sidechain` — Connect one audio unit's output as sidechain source to a Compressor/Gate on another unit.
- `duplicate_effect` — Duplicate a single effect within an AU's effect chain, copying all parameter values.
- `export_effect_chain` — Export an effect chain (audio or MIDI) from an AU as a base64 preset.
- `get_effect_chain` — Get the full effect chain for an audio unit.
- `get_effect_state` — Get full state of an effect: enabled, minimized, sidechain, all parameters.
- `list_effect_parameters` — List all parameters of an effect on an audio unit.
- `list_effects` — List all available audio and MIDI effect types.
- `move_effect` — Reorder an effect within an audio unit's effect chain.
- `remove_effect` — Remove an audio effect from an audio unit's chain.
- `set_device_label` — Rename an effect or MIDI effect device.
- `set_effect_enabled` — Enable or bypass an specific effect on an audio unit.
- `set_effect_parameter` — Set a parameter on an audio effect.
- `set_effect_parameter_bool` — Set a boolean parameter on an audio effect.
- `set_effect_parameter_int` — Set an integer parameter on an audio effect.
- `set_effect_parameter_string` — Set a string parameter on an audio effect (e.g. Waveshaper equation).

## MIDI Effects (6)
- `add_midi_effect` — Add a MIDI effect to an audio unit's MIDI effect chain.
- `get_midi_effect_chain` — Get the MIDI effect chain for an audio unit.
- `list_midi_effect_params` — List all parameters of a MIDI effect with current values.
- `list_midi_effects` — List all available MIDI effect types.
- `remove_midi_effect` — Remove a MIDI effect from an audio unit's MIDI chain.
- `set_midi_effect_param` — Set a parameter on a MIDI effect.

## Device-Specific Parameters (8)
- `list_vaporisateur_params` — Get full Vaporisateur synthesizer state: oscillators, LFO, noise, main params.
- `set_crusher_bits` — Set the bit depth on a Crusher (bitcrusher) effect.
- `set_crusher_crush` — Set the sample-rate reduction (crush) on a Crusher effect (0=clean, 1=max).
- `set_fold_oversampling` — Set the oversampling level on a Fold (wavefolding) effect.
- `set_stereo_tool_panning` — Set the panning mixing mode on a StereoTool effect.
- `set_waveshaper_equation` — Set the transfer function on a Waveshaper (hardclip/cubicSoft/tanh/sigmoid/arctan/asymmetric).
- `set_revamp_filter` — Configure a filter section on a Revamp parametric EQ (highpass/lowshelf/lowbell/midbell/highbell/highshelf/lowpass).
- `set_tidal_rate` — Set Tidal LFO rate using a musical fraction string (1/1, 1/2, 1/4, 1/8, 1/16, etc).
- `set_delay_sync` — Set Delay synced time using a musical fraction string (off, 1/128, 1/16, 1/8, 1/4, 1/2, 1/1, etc).
- `set_time_stretch_cents` — Set the pitch shift (in cents) on a time-stretched audio region.
- `set_vaporisateur_osc_param` — Set a parameter on a Vaporisateur oscillator.
- `set_vocoder_band_count` — Set the band count on a Vocoder effect (number of filter bands, typically 8-32).
- `set_vocoder_modulator_source` — Set the modulator source on a Vocoder effect.

## Notes (11)
- `create_note` — Create a MIDI note on a note track.
- `delete_note` — Delete a single note from a region.
- `duplicate_note_event` — Duplicate a note event within the same region with optional position/pitch offset.
- `duplicate_notes` — Duplicate all notes within a region, shifting them after the last note.
- `find_overlapping_notes` — Find notes that overlap a given pitch and time range within a note region.
- `get_note_range` — Get the pitch range and max duration of notes in a note region.
- `list_notes` — List all note events within a region.
- `quantize_notes` — Quantize note positions to a grid division.
- `set_note_advanced` — Set advanced note properties — chance, cent, playCount, playCurve.
- `set_note_properties` — Edit properties of a single note within a region.
- `transpose_notes` — Transpose all notes by a number of semitones. Supports region_index and skips out-of-range notes.
- `reverse_notes` — Reverse note order in a region (retrograde). Positions mirrored, durations/velocities preserved.
- `invert_notes` — Invert melody around a pitch axis (mirror reflection). newPitch = 2*axis - oldPitch.

## Note Editing (2)
- `consolidate_note` — Consolidate a repeated note (playCount > 1) into individual separate notes.
- `flatten_note_regions` — Flatten (merge) multiple overlapping note regions into a single region.

## Regions (20)
- `consolidate_region` — Consolidate a region's event collection — make it unique (not shared/mirrored).
- `list_note_regions` — List all note regions with position, duration, and note count.
- `copy_region_fades` — Copy fade in/out settings from one audio region to another.
- `copy_region_to_track` — Copy a region to a different track (or same track at new position).
- `create_track_region` — Create a region on any track (note or value) using the generic createTrackRegion API.
- `delete_audio_region` — Delete an audio region from the timeline.
- `delete_note_region` — Delete a note region from the timeline.
- `delete_region` — Delete a region from a track.
- `duplicate_note_region` — Duplicate a note region to a new position.
- `duplicate_region` — Duplicate any region (audio, note, or value) using the DAW's built-in duplicateRegion API.
- `get_region_info` — Get detailed info about a single region — position, duration, loop, mute, content.
- `move_region_content` — Shift the content start of a region without moving the region itself.
- `move_region_to_track` — Move a region from one track to another (possibly in a different audio unit).
- `set_region_color` — Set the color (hue) of a region or clip.
- `set_region_duration` — Set the duration of a region.
- `set_region_label` — Rename a region's label (display name).
- `set_region_loop` — Set loop parameters for a note region.
- `set_region_mute` — Mute or unmute a specific region without deleting it.
- `set_region_position` — Move a region to a new position on the timeline.
- `transfer_region` — Transfer/copy a region to another track at a specific position.

## Audio Regions (8)
- `get_audio_file_info` — Get metadata about the audio file referenced by an audio region.
- `get_region_play_mode` — Get the play mode of an audio region — stretch type, playback rate, cents, transient mode.
- `list_audio_regions` — List all audio regions with file name, position, and duration.
- `place_audio_region` — Place a previously loaded audio sample as a region on a track.
- `set_audio_region_fade` — Set fade in/out on an audio region.
- `set_audio_region_gain` — Set gain (in dB) on an audio region.
- `set_audio_region_time_base` — Set the time base of an audio region.
- `set_audio_region_waveform_offset` — Set the waveform display offset of an audio region.

## Audio Stretch & Warp (7)
- `create_pitch_stretched_region` — Place a pitch-stretched audio region on a track.
- `create_time_stretched_region` — Place a time-stretched audio region on a track.
- `create_warp_marker` — Add a warp marker to a time-stretched or pitch-stretched audio region.
- `delete_warp_marker` — Delete a warp marker from a time-stretched or pitch-stretched audio region.
- `list_transient_markers` — List transient markers for an audio region's audio file.
- `list_warp_markers` — List warp markers on a time-stretched or pitch-stretched audio region.
- `update_warp_marker` — Update a warp marker's position and/or seconds value.

## Clips (16)
- `clone_clip` — Clone a clip (note or value) on the same track. Optionally consolidate (make event collection uni...
- `consolidate_clip` — Consolidate a clip's event collection — make it unique (not shared/mirrored).
- `create_audio_clip` — Create an audio clip in the session view (clip launcher).
- `create_note_clip` — Create a note clip in the session view (clip launcher).
- `create_pitch_stretched_clip` — Create a pitch-stretched audio clip in session view.
- `create_time_stretched_clip` — Create a time-stretched audio clip in session view.
- `create_value_clip` — Create a value clip (automation clip) on an automation track in session view.
- `delete_clip` — Delete a clip from a track (session view).
- `list_clips` — List clips (session view / clip launcher) on tracks.
- `schedule_clip_play` — Schedule clips to play in session view (live triggering).
- `schedule_clip_stop` — Schedule clips to stop on specified tracks (session view).
- `set_clip_hue` — Set the color (hue) of a clip in the session view.
- `set_clip_label` — Set the label (name) of a clip in the session view.
- `set_clip_mute` — Mute or unmute a clip in the session view.
- `set_clip_playback` — Set clip playback parameters (loop, reverse, speed) on a clip.
- `set_clip_properties` — Set properties on a clip (session view): label, color, mute, duration.

## Markers (6)
- `add_marker` — Add a timeline marker at a position.
- `delete_marker` — Delete a timeline marker by index.
- `list_markers` — List all timeline markers with positions and labels.
- `set_marker_label` — Rename a timeline marker.
- `set_marker_position` — Move a timeline marker to a new position.
- `set_marker_repeat` — Set repeat count on a marker (0=infinite, 1-16=N repeats).

## Sends & Buses (12)
- `create_audio_bus` — Create a new audio bus (aux bus) with its own audio unit and track.
- `create_send` — Create a parallel FX send bus from an audio unit.
- `list_audio_buses` — List all audio buses in the project (primary output + FX buses).
- `list_sends` — List all aux sends on an audio unit.
- `remove_audio_bus` — Remove an FX audio bus and its associated audio unit.
- `remove_send` — Remove an aux send from an audio unit.
- `set_bus_color` — Set the color (hue 0-360) of an audio bus.
- `set_bus_enabled` — Enable or mute an audio bus (FX bus A/B comparison).
- `set_bus_label` — Set the label (name) of an audio bus.
- `set_send_level` — Set the send level for an existing aux send.
- `set_send_pan` — Set the stereo pan for an aux send (-1.0 = full left, 0.0 = center, 1.0 = full right).
- `set_send_routing` — Set the routing mode for an aux send (pre-fader or post-fader).

## Mixing (5)
- `get_mixer_state` — Get the full mixer state — all audio units with volume, panning, mute, solo, and type.
- `set_track_mute` — Mute or unmute an audio unit.
- `set_track_panning` — Set panning of an audio unit. -1.0 = full left, 0.0 = center, 1.0 = full right.
- `set_track_solo` — Solo or unsolo an audio unit.
- `set_track_volume` — Set volume of an audio unit in dB.

## Automation (12)
- `add_automation` — Add parameter automation to an effect on an audio unit.
- `add_instrument_automation` — Automate a parameter on the instrument connected to an audio unit.
- `create_automation_event` — Create a single automation event at a specific position on a value track.
- `delete_automation_event` — Delete a single automation event (ValueEventBox) from an automation track.
- `duplicate_automation_event` — Duplicate an automation event within the same region.
- `get_automation_value` — Get the automation value at a specific position on a value (automation) track.
- `list_automation_events` — List automation events (ValueEventBox) on a unit's automation tracks.
- `list_automation_events_detail` — List all automation events on a value track with full detail — position, value, interpolation.
- `list_value_regions` — List automation regions (ValueRegionBox) on value/automation tracks.
- `move_automation_event` — Move an automation event to a new position on the timeline.
- `set_automation_interpolation` — Set the interpolation type of an existing automation event.
- `update_automation_event` — Update an existing automation event's value and/or interpolation.

## Export & Rendering (13)
- `auto_gain` — Auto-adjust output volume to hit a target LUFS.
- `convert_audio` — Convert an exported WAV file to MP3 or FLAC using system ffmpeg.
- `export_midi` — Export a note region's notes as a standard MIDI file (.mid).
- `export_mix` — Render the full project mix to a WAV file.
- `export_single_stem` — Export a single audio unit as a stem WAV with its effect chain applied.
- `export_dry_stem` — Export a single audio unit as a DRY stem (instrument output, no effects/channel strip). Useful for freeze/flatten/re-amp workflows.
- `export_stems` — Export each audio unit as a separate stem WAV file.
- `export_stems_format` — Export stems as separate files and convert each to MP3 or FLAC.
- `import_midi` — Import a MIDI file and create note events on a note track.
- `load_audio` — Load an audio file (WAV/MP3/FLAC/OGG) into the DAW project.
- `measure_lufs` — Measure LUFS (integrated) and true peak of an exported WAV file.
- `render_full` — Render the entire project as a single stereo WAV file (full mixdown).
- `render_full_format` — Render the entire project and convert to MP3 or FLAC in one step.
- `render_range` — Render only a portion of the project (e.g. chorus only) for quick A/B comparison.

## Presets & DawProject (4)
- `export_dawproject` — Export the current project as a .dawproject file (Bitwig/Ableton/rePitch compatible format).
- `export_preset` — Export an audio unit as a preset (base64-encoded binary).
- `import_dawproject` — Import a .dawproject file into the current session.
- `import_preset` — Import a preset (base64-encoded binary) as a new audio unit.

## Scriptable Devices (5)
- `get_script_device_code` — Read the current user JavaScript code from a scriptable device.
- `list_script_params` — List @param declarations with full mapping info (min/max/type/unit).
- `list_script_samples` — List @sample declaration slots on a scriptable device.
- `set_script_device_code` — Set the user JavaScript code on a scriptable device (Apparat/Werkstatt/Spielwerk). Compiles via ScriptCompiler.
- `set_script_param` — Set a parameter value with range validation (clamps to min/max, rounds int, snaps bool).

## Playfield / Drum Machine (5)
- `copy_playfield_sample` — Copy a Playfield (drum machine) sample to a new index slot.
- `create_playfield_sample` — Add a drum pad to a Playfield drum machine.
- `list_playfield_samples` — List all drum pads (samples) on a Playfield drum machine.
- `reset_playfield_params` — Reset all parameters of a Playfield drum sample to defaults.
- `set_playfield_sample_enabled` — Enable/disable a drum pad on a Playfield drum machine.

## Modular System (7)
- `add_modular_module` — Add a module to a Modular device.
- `connect_modular_modules` — Connect two modules in a Modular device (create a patch cable).
- `list_modular_connections` — List all connections (patch cables) in a Modular device.
- `list_modular_devices` — List all Modular audio effect devices in the project.
- `list_modular_modules` — List all modules in a Modular device.
- `remove_modular_module` — Remove a module from a Modular device.
- `set_modular_module_param` — Set a parameter on a module in a Modular device.

## Piano Mode (6)
- `get_piano_mode` — Get piano roll view settings.
- `set_piano_keyboard` — Set the piano roll keyboard type.
- `set_piano_note_labels` — Toggle note labels (C, C#, D, etc.) in the piano roll.
- `set_piano_note_scale` — Set the piano roll note scale (vertical zoom).
- `set_piano_time_range` — Set the piano roll time range (horizontal view width in quarter notes).
- `set_transpose` — Set global transpose for the piano roll view (does not affect audio playback).

## NeuralAmp (2)
- `get_neuralamp_model` — Get the NeuralAmp (Tone3000) model JSON for a NeuralAmp effect.
- `set_neuralamp_model` — Load a Neural Amp Modeler (NAM/Tone3000) model JSON into a NeuralAmp effect.

## Engine Control (8)
- `capture_realtime` — Capture realtime audio output from the DAW engine.
- `engine_panic` — Send a panic signal to the engine — stops all notes immediately.
- `engine_sleep` — Put the audio engine to sleep — suspends audio processing to save CPU.
- `engine_wake` — Wake the audio engine from sleep — resumes audio processing.
- `get_engine_status` — Get real-time engine status: playing state, position, BPM, CPU load, recording state.
- `query_loading_complete` — Check if all audio samples are loaded and ready for playback.
- `set_metronome` — Configure metronome (enabled, gain, beat_subdivision).
- `start_engine` — Start the audio engine (AudioWorklet) after setting up tracks and regions.

## MIDI Output (1)
- `list_midi_output_devices` — List all MIDI output devices registered in the project (hardware MIDI outputs).

## Samples (2)
- `get_sample_info` — Get detailed info about an audio sample by UUID.
- `list_samples` — List all audio file samples used in the project.

## Editing (2)
- `redo` — Redo the last undone operation.
- `undo` — Undo the last editing operation.

## Debugging & Control (3)
- `evaluate_raw` — Execute arbitrary JavaScript in the DAW V8 context and return the result.
- `screenshot_daw` — Take a screenshot of the openDAW UI. Returns base64-encoded PNG image.
- `wait_for_condition` — Wait for a JavaScript condition to evaluate to true in the DAW context.

## Stem Splitter (2)
- `list_split_modes` — List all available stem separation modes with SDR scores and descriptions.
- `split_stems` — Split an audio file into stems using SOTA open-source separation models (BS-Roformer, HTDemucs, SCNet, MelBand Roformer). Runs locally on GPU. 7 modes: ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise. Optional auto-import into DAW.

## Preset Management (2)
- `save_effect_preset` — Encode an audio effect chain as a .opb preset bundle (ZIP: meta.json + preset.odp). Uses PresetEncoder.encodeEffects. Shareable, drag-and-drop into openDAW.
- `load_effect_preset` — Load a .opb preset file and decode it via PresetDecoder into a project skeleton. Returns imported unit count.

## Orchestration Tools (17)
High-level composers that combine multiple low-level operations into a single call.
Designed for agents — reduce token usage and round-trips when building musical structures.
- `create_notes_batch` — Create multiple MIDI notes from a JSON array in one call. Replaces 10-50 create_note calls.
- `create_drum_pattern` — Create a drum beat from compact step-sequencer notation (x/o/./X per 16th note). One call = full beat.
- `create_chord_progression` — Create chords from names (Cm, Fm7, Gdom7) — auto-voiced, positioned, batched.
- `create_melody` — Create a melody from a scale + rhythmic pattern using scale degrees (1-7). Supports 14 scales, rests, sustains, octave shifts.
- `create_bassline` — Create a bassline from root + rhythmic pattern using scale degrees. Low octave default (C2=36), high velocity (0.9), supports octave up/down (+/_).
- `create_arpeggio` — Create an arpeggio from a chord name with 6 patterns (up/down/updown/downup/random/chord) and 6 rates (32/16/8/4/16t/32t). One call replaces 8-32 create_note calls.
- `humanize_notes` — Add human-like velocity, timing, duration variation and swing to existing notes. Seeded PRNG for reproducibility. Makes programmed MIDI feel less robotic.
- `create_harmony` — Generate harmony parts from existing notes. Diatonic (thirds/fifths/sixths) and chromatic (octave/fifth/fourth/major-minor third) intervals. Up/down direction. Auto-creates target track.
- `create_counterpoint` — Generate counter-melody in contrary motion. Mirrors melody around center pitch. Adjustable interval. Auto-creates target track.
- `create_drum_fill` — Generate drum fills/transitions with 5 types (build, break, roll, crash, tom). Adjustable density and bar length. One call replaces 10-30 note creations.
- `create_ostinato` — Create a repeating melodic/rhythmic pattern as a foundation layer. Scale-based, 1-16 repeats. Common in minimalism, electronic, and film music.
- `create_crescendo` — Apply crescendo/decrescendo to existing notes. Linear, exponential, or logarithmic velocity curves. One call modifies all notes in a region.
- `apply_swing` — Apply pure swing feel to existing notes without changing velocity or duration. Deterministic, no randomness. 16th or 8th grid. 0.58 = classic hip-hop/lofi swing.
- `create_polyrhythm` — Create polyrhythms — two rhythmic streams with different subdivision counts (3:4, 2:3, 5:7, etc.). Jazz, electronic, progressive, math rock.
- `create_scale_run` — Create ascending/descending scale runs for fills and transitions. 14 scales, 1-4 octaves, adjustable step duration.
- `create_call_response` — Create call-and-response patterns (antecedent/consequent phrases). Foundation of blues, jazz, hip-hop, electronic. Alternates call → response with adjustable repeats.
- `create_walking_bass` — Create walking bass lines over chord progressions. Beat 1=chord root, beat 2=chord tone, beat 3=passing tone, beat 4=approach note. Jazz/blues/swing.
- `apply_sidechain` — Apply sidechain ducking via volume automation. Classic pumping/breathing effect for house/techno/EDM. Adjustable depth, attack, release, kick interval.
- `create_ghost_notes` — Add ghost notes (quiet grace notes) to existing drum patterns. Funk/R&B/neo-soul/hip-hop groove enhancer. Seeded reproducibility.
- `apply_velocity_curve` — Apply velocity envelope across notes (ramp_up/ramp_down/arc/trough/power). Deterministic curve shape for build-ups, fade-ins, expressive phrasing.
- `apply_articulation` — Apply articulation to notes (staccato/legato/tenuto/accent). Duration reshaping for phrasing character. Accent boosts velocity on downbeats.
- `add_mastering_chain` — Add EQ + Compressor + Maximizer to the output bus with genre-style presets (balanced/warm/loud/transparent).
- `create_genre_track` — Create a full genre starting point (house/techno/lofi/dnb/trap/ambient/coldwave/hiphop) — synth, drums, bass, chords, BPM in one call.
- `create_song_structure` — Create arrangement markers (intro/verse/chorus/bridge/outro) from JSON section list. Enables agents to reason about song form.
- `automation_sweep` — Create smooth automation ramps (filter sweeps, volume fades) with linear/exp/log curves in one call. Replaces 10-30 create_automation_event calls.
- `apply_mix_preset` — Apply volume/pan/mute/solo to all units from JSON or named preset (lofi/house/balanced/wide). Replaces 10-30 individual mixer calls.

**Total: 283 tools**

## DSP Scripts (scripts/) — 33 scripts

### Werkstatt (Audio Effects) — 22 scripts
- `werkstatt_darksat.js` — Tape saturation (drive, bias, tone, mix, output)
- `werkstatt_coldfold.js` — Wavefolding + bitcrush (drive, fold, crush, slew, mix)
- `werkstatt_chorus.js` — Stereo chorus (rate, depth, delay, feedback)
- `werkstatt_reverb.js` — Plate reverb (decay, predelay, wet, tone)
- `werkstatt_phaser.js` — Phaser (rate, depth, feedback, stages)
- `werkstatt_shimmer.js` — Shimmer delay (time, feedback, pitch, mix)
- `werkstatt_allpass.js` — Allpass filter (freq, feedback)
- `werkstatt_dcremover.js` — DC remover + stereo tool (dc_freq, width)
- `werkstatt_pitch_shift.js` — Pitch shifter (semitones -24..24)
- `werkstatt_lookahead.js` — Lookahead compressor (threshold, ratio, attack, release)
- `werkstatt_envfollower.js` — Envelope follower (tracks input amplitude, gain modulation)
- `werkstatt_granular_stretch.js` — Granular time-stretch (stretch 0.5..20x)
- `werkstatt_paulstretch.js` — Paulstretch extreme time stretch (no pitch change)
- `werkstatt_spectral_freezer.js` — Spectral freeze (captures snapshot, sustains indefinitely)
- `werkstatt_ringmod_env.js` — Ring modulator with envelope-followed freq modulation
- `werkstatt_adsr_trim.js` — ADSR trim utility (attack, decay, sustain, release)
- `werkstatt_flanger.js` — Stereo flanger (rate, depth, center, feedback, mix)
- `werkstatt_noisegate.js` — Noise gate (threshold, attack, hold, release, range)
- `werkstatt_tremolo.js` — Tremolo (rate, depth, shape sine→square, phase)
- `werkstatt_stereo_delay.js` — Stereo delay with ping-pong (time_l, time_r, feedback, tone, mix, pingpong)
- `werkstatt_overdrive.js` — Asymmetric soft-clip overdrive (drive, tone, level, bias, dry)
- `werkstatt_multifilter.js` — Multi-mode SVF filter: LP/HP/BP/Notch (mode, cutoff, resonance, drive, mix)
- `werkstatt_compressor.js` — Soft-knee peak compressor (threshold, ratio, attack, release, makeup, mix, knee)
- `werkstatt_paraeq.js` — 3-band parametric EQ + HP/LP (band1/2/3 freq+gain+Q, hp_freq, lp_freq, mix)
- `werkstatt_limiter.js` — Brickwall limiter with lookahead + TPDF dither (ceiling, release, lookahead, dither, mix)

### Apparat (Instruments) — 5 scripts
- `apparat_darkbass.js` — Dark bass synth (waveform, cutoff, resonance, envelope)
- `apparat_coldlead.js` — Cold lead synth (waveform, cutoff, resonance, envelope)
- `apparat_subcrusher.js` — Sub crusher bass (wave, cutoff, resonance, distortion)
- `apparat_fm.js` — 2-operator FM synth (carrier, ratio, mod_depth)
- `apparat_ringmod.js` — Ring modulator synth (frequency, waveform, envelope)

### Spielwerk (MIDI Effects) — 6 scripts
- `spielwerk_arpeggiator.js` — MIDI arpeggiator (rate, octave, pattern)
- `spielwerk_chordmemory.js` — Chord memory (chord type 0-6)
- `spielwerk_mididelay.js` — MIDI delay (time, feedback, mix)
- `spielwerk_powerchord.js` — Power chord generator (interval, voicing)
- `spielwerk_strum.js` — Strummer (speed, direction)
- `spielwerk_velocity.js` — Velocity scaler (scale, offset)

## DAW_HELPERS (17 helpers)
All box enumeration is done through typed helpers injected into the bridge context:
- `h.auBox(i)` — AU box by index
- `h.allAUBoxes()` — all audio unit boxes
- `h.effectBoxes(au)` — audio effects on an AU (sorted by index)
- `h.midiEffectBoxes(au)` — MIDI effects on an AU (sorted by index)
- `h.trackBoxes(au)` — tracks on an AU (sorted by index)
- `h.regionBoxes(track)` — regions on a track (no sort)
- `h.eventBoxes(collection)` — events in a collection (note or signature)
- `h.inputBoxes(au)` — input boxes on an AU
- `h.markerBoxes(mt)` — markers on a marker track
- `h.sendBoxes(au)` — aux sends on an AU (sorted by index)
- `h.busBoxes()` — all audio buses
- `h.sampleBoxes(pf)` — samples on a Playfield device
- `h.noteTrackBoxes(au)` — note tracks only (type===1, sorted)
- `h.clipBoxes(track)` — clips on a track
- `h.rootClipBoxes()` — root-level clips
- `h.scriptParams(device)` — @param declarations on a scriptable device
- `h.scriptSamples(device)` — @sample declarations on a scriptable device
- `h.chainBoxes(au, field)` — dynamic chain field (audioEffects or midiEffects)