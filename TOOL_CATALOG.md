# openDAW MCP Tool Catalog

373 MCP tools for headless openDAW control via Playwright bridge.

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
- `copy_notes_to_track` — Copy notes from one track/region to another — MIDI layering and doubling. Optional transpose (semitones), time_offset (beats), velocity_scale. Use cases: layer drums, create octave harmony, echo/call-and-response, doubles. Cross-AU support via dest_unit_index.
- `reverse_notes` — Reverse note order in a region (retrograde). Positions mirrored, durations/velocities preserved.
- `invert_notes` — Invert melody around a pitch axis (mirror reflection). newPitch = 2*axis - oldPitch.
- `augment_notes` — Augment or diminish note durations by a factor (0.25-4.0). The fourth classical transformation. "scale" mode (phrase slows/speeds) or "stretch" mode (durations only).

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
- `download_audio` — Download audio from URL (Suno CDN, any HTTP source) to local disk. Streaming download with timeout, filename sanitization, next_step suggestion pointing to import_audio_to_tracks. Bridges AI generators → DAW pipeline.
- `measure_lufs` — Measure LUFS (integrated) and true peak of an exported WAV file.
- `detect_bpm` — Detect BPM (tempo) of a WAV file using onset detection + autocorrelation. Pure Python (no numpy). 60-200 BPM range, confidence score. Essential for Suno integration: detect BPM → set_bpm for correct beat alignment.
- `detect_key` — Detect musical key and mode of a WAV file using chroma features + Krumhansl-Schmuckler key profiles. Pure Python radix-2 FFT (no numpy). 24 keys (12 roots × major/minor), confidence, alternatives, chroma vector. Essential for Suno integration: detect key → build matching chord progression → harmonic arrangement.
- `create_progression_from_key` — Auto-generate diatonic chord progression from detected key + mode. 6 styles (pop/jazz/rock/synthwave/folk/lofi), 12 templates (major + minor). Delegates to create_chord_progression. Eliminates manual chord typing — just pass key="A", mode="minor".
- `analyze_track` — Full audio analysis in one call: BPM + key + mode + LUFS + true peak + duration + dynamic range + chroma. Composite of detect_bpm + detect_key + measure_lufs. One call instead of three.
- `remix_track` — Full Suno remix pipeline in one call: analyze → set_bpm → import stems → auto-progression from key → harmonic arrangement → genre mix → mastering. 7 steps, one call. Default: synthwave genre, bs4 stems, -14 LUFS.
- `transcribe_drums` — Audio-to-MIDI drum transcription. Splits WAV into 3 frequency bands (kick <250Hz, snare 250-2500Hz, hat >2500Hz), detects onsets per band, classifies → MIDI notes (kick=36, snare=38, hat=42). Auto-BPM detection. Velocity from amplitude. One call: drum loop WAV → note track.
- `transcribe_melody` — Monophonic audio-to-MIDI melody transcription. Autocorrelation per frame → fundamental frequency → MIDI pitch (cents via parabolic interpolation). Groups frames into sustained notes, velocity from energy. One call: melody WAV → note track.
- `transcribe_audio` — Composite audio-to-MIDI transcription in one call. Runs transcribe_drums + transcribe_melody simultaneously — drum track (kick/snare/hat) + melody track (pitched notes). Auto-BPM. Audio-to-MIDI family complete.
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
- `import_audio_to_tracks` — One-call Suno-to-DAW pipeline: audio file → (optional stem separation) → create instrument tracks → load → place. Without mode = single track. With mode = one track per stem. Replaces 12+ manual calls (split + create + load + place per stem).

## Preset Management (2)
- `save_effect_preset` — Encode an audio effect chain as a .opb preset bundle (ZIP: meta.json + preset.odp). Uses PresetEncoder.encodeEffects. Shareable, drag-and-drop into openDAW.
- `load_effect_preset` — Load a .opb preset file and decode it via PresetDecoder into a project skeleton. Returns imported unit count.

## Orchestration Tools (38)
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
- `create_riser` — Generate ascending pitch sweep for build-up transitions. 3 curves (linear, exp, log). Adjustable pitch range, step count, and length. Velocity ramps up proportionally.
- `create_impact` — Single hit transition element for drops and section changes. 5 types: sub_boom, impact_hit, downlifter, sub_drop, punch.
- `create_buildup` — Combined build-up: riser + snare roll in one call. 5 styles: edm, trap, techno, rock, minimal.
- `create_filter_sweep` — Smart filter sweep on Vaporisateur cutoff. Direction-aware (open/close), exp curve default, optional resonance boost at midpoint. The most common EDM/techno transition technique in one call.
- `create_volume_fade` — Smart volume fade automation on AU volume. Direction-aware (in/out), dB-to-normalized conversion via VolumeMapper powerByCenter, exp curve default. For intros, outros, breakdowns, section transitions.
- `create_pan_sweep` — Stereo panning automation sweep. L→R or R→L or partial. Linear curve default (panning is psychoacoustic). For intros, guitar solos, EDM builds, stereo movement.
- `create_mute_automation` — Timed mute/unmute events for section dynamics. Mute drums in breakdowns, unmute for drops, create structural silences. Step interpolation (boolean, no smooth ramp). Replaces multiple set_track_mute calls.
- `create_solo_automation` — Mute all tracks except one for a beat range, then restore. Drum break, bass spotlight, vocal spotlight in one call. Internally calls create_mute_automation for each non-solo track. Replaces N manual mute automation calls.
- `create_section_transition` — Composite section transition in one call. 5 presets: drop (breakdown→drop), buildup (verse→chorus), breakdown (main→breakdown), intro (silence→intro), outro (main→outro). Combines filter sweeps, volume fades, mute automation, impacts. Replaces 3-5 individual calls.
- `create_stab` — Generate rhythmic chord stabs for house/disco/funk. Grid pattern with 'x' (stab), '-' (rest), '.' (ghost). Cycles through chord progressions. Adjustable octave, velocity, stab duration.
- `create_break` — Generate classic drum breaks (Amen, Think, Ashanti, Funky Drummer, When the Levee, Synthetic). 1-8 bars with variation modes (none/fill/humanize/drop) and swing.
- `create_bass_drop` — Generate descending pitch sweep into sustained sub bass for dubstep/EDM/trap drops. 3 curves (linear/exp/log), adjustable sweep/hold duration.
- `create_chop` — Slice source pitches into segments and rearrange. 5 modes: reverse (Dilla flip), stutter (glitch repeat), shuffle (Madlib random), ping-pong (ABBA), gate (chopped break). Octave shift, velocity variation, inner-pitch reverse.
- `create_trill` — Create rapid two-note alternation (ornament). 5 rates (32nd/16th/8th/32t/16t). Upper note accent (baroque style). Start on upper or lower. Classical, jazz, metal, electronic.
- `create_mordent` — Classical ornament: main → neighbor → main. Upper/lower direction, adjustable interval (1-7 semitones). One of four essential baroque ornaments. Bach, Mozart.
- `create_turn` — Circular ornament (gruppetto): main → upper → main → lower → main. Upper/lower direction. Third of four essential ornaments. Mozart, Beethoven, Bach.
- `create_appoggiatura` — Expressive leaning grace note: approach → main. Fourth and final essential ornament. Adjustable ratio (0.5-0.9), above/below direction. Bach cello suites, Mozart operas, Chopin. **Completes ornaments set.**
- `create_glissando` — Smooth scale run between two pitches. 6 scale types (chromatic/major/minor/pentatonic/whole_tone). 5 rates. 4 velocity curves (flat/ramp_up/ramp_down/arc). Ascending or descending.
- `create_sequence` — Repeat a melodic pattern at transposed pitch levels. 3 directions (up/down/alternating). Adjustable transposition (semitones), repeats (1-8), velocity decay. The fundamental compositional technique — baroque sequences, jazz chains, film score builds.
- `create_pedal_point` — Sustained bass note under changing chords. Retrigger or sustained mode. Chord name parsing (maj/min/m7/maj7/sus2/sus4/dim/aug). Adjustable time signatures. Film scoring, organ preludes, rock ballads.
- `create_chorale` — 4-voice SATB chorale with voice-leading rules. Nearest chord tone movement, parallel fifth/octave detection, voice range clamping (S/A/T/B). Per-voice velocity, voice_spread. Bach chorale style — vocal harmonies, string arrangements, synth pads.
- `create_fugue` — Polyphonic fugue with subject, tonal/real answer, optional countersubject, stretto. Voice alternation (subject→answer→subject oct-down→answer). 2-5 voices. Bach WTC/Art of Fugue style. Distinct from canon (strict imitation) — fugue uses tonal answer adjustment.
- `create_two_hand_piano` — Two-hand piano arrangement: left hand accompaniment (block/arpeggio up-down-updown/Alberti bass/bass+chord) + right hand (chord tones/arpeggio/melody). Separate bass/chord/melody octaves, adjustable arpeggio rate. Piano ballads, jazz comping, classical accompaniment, lofi piano.
- `create_variations` — Thematic variation generator. Reads source notes, generates N variations with 9 transformation types: transpose, invert (with axis), reverse, augment, diminish, fragment, octave_up, octave_down. Bach Goldberg, Beethoven Diabelli, jazz reharmonization. Generative — non-destructive, writes new regions.
- `create_motif_development` — Through-composed melodic development. 2-8 note motif → ONE continuous evolving line through 11 stages: statement, sequence_up/down, fragment/fragment_end, invert, octave_up/down, expand, compress, cadence. Beethoven 5th approach.
- `create_stutter` — Stutter edit: rapid rhythmic repetitions with evolving rate (accelerate/decelerate/ping_pong/random), 5 accent patterns, 5 velocity ramps, gate, pitch jitter. Unlike create_chop (equal segments) — rate changes over time. BT/Imogen Heap/Deadmau5 stutter technique.
- `create_cross_rhythm` — Cross-rhythm: multiple voices with independent period lengths creating shifting alignment. Unlike polyrhythm (divides one bar into n+m parts), cross-rhythm gives each voice its own period in beats. Voices cycle independently, only realign at LCM of all periods. 2-6 voices, velocity attenuation. African cross-rhythms, Steve Reich, Talking Heads.
- `create_clave` — Afro-Cuban clave pattern: 5-note rhythmic skeleton across 2 bars. 6 clave types (son 3-2, son 2-3, rumba 3-2, rumba 2-3, bossa nova, 6/8). Direction (3-2 or 2-3) determines feel. All other rhythms align to clave.
- `create_euclidean_rhythm` — Euclidean rhythm: distributes k onsets across n steps maximally evenly via Björklund's algorithm. Generates world rhythms: E(3,8)=tresillo, E(5,8)=cinquillo, E(7,16)=samba, E(7,12)=bembé, E(4,9)=Aksak. Rotation shifts pattern.
- `create_tumbao` — Afro-Cuban tumbao (conga) pattern: rhythmic foundation of salsa. 4 variants (salsa, salsa_slap, rumba guaguancó, bolero). 3 stroke types → 3 conga pitches: tone (closed, low), open (resonant, mid), slap (sharp, high). Open tone on &4 anticipates downbeat — the tumbao signature.
- `create_cascara` — Afro-Cuban cáscara pattern: timbale shell rhythm that fills space around clave and tumbao. Completes the rhythm section trilogy. 4 variants (son 3-2, son 2-3, guaguanco, mambo). Two stroke heights: high (rim, accented) + low (shell, unaccented) + ghost (soft). High/low alternation creates call-and-response.
- `create_dembow` — Reggaeton/dancehall dembow rhythm: the 3-3-2 syncopated gallop that drives all reggaeton. 5 variants (classic, dancehall, trap_latino, perreo, urbano). Kick + snare + ghost strokes. From Bobby Dixon's riddim to Daddy Yankee to Bad Bunny.
- `create_boom_bap` — Boom-bap hip-hop drum pattern: the foundational beat of hip-hop. "boom"=kick, "bap"=snare. 5 variants (classic, old_school, trap, lofi, drill). Kick on 1/3, snare on 2/4, hi-hats fill. From Run-DMC to Nas to Kendrick. J Dilla laid-back, UK drill aggression.
- `create_four_on_floor` — Four-on-the-floor: the foundational beat of house, techno, and disco. Kick on every quarter (beats 1-2-3-4). 5 variants (classic_house, deep_house, techno, disco, tech_house). Open hats on off-beats, clap on 2+4, 16th hats. From Moroder to Frankie Knuckles to Jeff Mills.
- `create_breakbeat` — Breakbeat: the syncopated skeleton of jungle, DnB, big beat, and breakbeat hardcore. Broken drum patterns with off-grid kicks/snares. 5 variants (amen, dnb, big_beat, 2_step, funky_drummer). The Amen break, Funky Drummer, UK garage 2-step. All syncopated.
- `create_trap_rolls` — Trap hi-hat roll patterns: evolving density technique. 5 variants (modern, migos, bubble, skrrt, evolving). Triplet bursts, 32nd doubles, stutter patterns. Travis Scott, Migos, Young Thug, Metro Boomin.
- `create_electronic_bass` — Genre-specific electronic basslines. Bass as rhythmic engine locking with kick. 6 variants (house_offbeat, techno_sub, dnb_reese, dubstep_wobble, acid_303, garage_2step). Root/fifth/octave movement. House off-beat, techno sub, DnB Reese, dubstep wobble, TB-303 acid, UK 2-step.
- `create_dnb_arrangement` — First multi-track genre arrangement. Complete DnB section across 3 tracks: drums (Amen breakbeat), bass (Reese), pad (minor triad). Elements lock rhythmically. Tempo-aware 140-200 BPM. 4-32 bars. One call replaces 100+ individual note calls.
- `create_liquid_dnb_arrangement` — Liquid DnB: 4-track smooth melodic arrangement. Drums (smooth breakbeat with rimshots, not Amen ghosts), bass (melodic sub-bass: root→fifth→octave→third walks, not Reese stabs), pad (lush min9/maj9 extended chords, not plain triads), melody (soulful pentatonic lead with call-response phrases). Default root F, velocity 0.75 (smoother than DnB's 0.85). LTJ Bukem, Calibre, High Contrast.
- `create_house_arrangement` — Second multi-track genre arrangement. Complete house section: drums (four-on-floor), bass (off-beat), stabs (minor triad). Kick and bass perfectly interleaved. Tempo-aware 110-140 BPM.
- `create_trap_arrangement` — Third multi-track arrangement. Complete trap section: drums (trap rolls with triplet bursts), bass (808 sub-bass slides with negative offsets), melody (minor bell plucks with echo). F# minor default. Tempo-aware 120-170 BPM.
- `create_techno_arrangement` — Fourth multi-track arrangement. Berlin/Detroit techno: drums (relentless four-on-floor with industrial hats + claps), bass (sustained sub-bass drone with root/fifth shifts — not rhythmic, continuous), stabs (Detroit percussive atonal stabs on off-beats). C minor default. Tempo-aware 120-150 BPM. Minimum 8 bars (techno needs longer forms).
- `create_dubstep_arrangement` — Fifth multi-track arrangement. Dubstep: drums (half-time at 140 BPM — kick on 1, snare on 3, feels like 70 BPM), bass (wobble bass — sustained root with octave/fifth stabs simulating LFO cutoff modulation), lead (minor arpeggio, dark and atmospheric). G minor default. 130-155 BPM. The half-time feel is the fundamental difference from all other arrangements.
- `create_afrobeat_arrangement` — Sixth multi-track arrangement. First non-electronic genre. Fela Kuti-style afrobeat across 4 tracks: drums (layered polyrhythm — kick + shaker + clave + triplet accents, 12/8 feel in 4/4), bass (repetitive ostinato — root/octave/fifth/fourth, 16th-note driving pattern), horns (brass section call-and-response — sustained minor chords + syncopated stabs), guitar (off-beat "chanka" stabs — two-note voicings, percussive). F minor default. 95-135 BPM. Minimum 8 bars. First arrangement with 4 tracks.
- `create_rock_arrangement` — Seventh multi-track arrangement. Classic rock with blues-based I-IV-V harmony across 4 tracks: drums (rock beat — kick on 1&3, snare on 2&4, crash on downbeat, tom fill), bass (root-fifth walking bassline locking with kick), guitar (power chords — root+fifth, no third, palm-muted downstrokes), keys (major triad pads — root+major third+fifth, sustained). E minor default (most common rock guitar key). 80-180 BPM. Second organic 4-track arrangement.
- `create_jazz_arrangement` — Eighth multi-track arrangement. Jazz with ii-V-I harmony and swing feel across 4 tracks: drums (swing ride spang-a-lang — ride on every beat + swung 8th at 0.66, ghost snare comping, feathered bass drum), bass (walking bass — quarter notes through ii-V-I using chord tones root/third/fifth/seventh, min7 on ii/V, maj7 on I), piano (comping — shell voicings root+third+seventh, syncopated off-beat stabs with space), horn (bluesy head — melodic line following changes, blue notes, swing phrasing). ii-V-I harmony is the fundamental jazz chord change. Swing 8ths (triplet feel at 0.66) is the rhythmic signature. F default (classic jazz key). 50-220 BPM. Third organic 4-track arrangement.
- `create_pop_arrangement` — Ninth multi-track arrangement. First with real song structure (verse-chorus-bridge). Pop across 4 tracks with section-aware patterns: drums (verse=sparse kick+hat → chorus=full kick+snare+crash → bridge=building toms → outro=winding down), bass (verse=root notes → chorus=octave jumps → bridge=walking chord tones), chords (I-V-vi-IV "four chords of pop" — verse=light arpeggios → chorus=full block chords → bridge=sus4→resolution), melody (verse=sparse low → chorus=anthemic hook high register → bridge=chromatic tension). I-V-vi-IV is the most used pop progression — different from rock's I-IV-V and jazz's ii-V-I. Song structure (not loops) is the key difference from all other arrangements. C default. 85-145 BPM. Min 16 bars. Fourth organic 4-track.
- `create_funk_arrangement` — Tenth multi-track arrangement. James Brown / P-Funk style — vamp-based (one chord, no progression): drums (Funky Drummer — Clyde Stubblefield's most sampled break, syncopated kick, ghost snare, 16th-note hi-hat with varying dynamics), bass (slap bass — thumb/pluck alternation, root→octave→root→fifth, min7 for funk flavor, 16th-note density), guitar (scratch "chank" — all 16 16ths played with accent pattern, root+min7 voicing, extremely short), horns (dominant7 stabs — root+maj3+min7, on the "and" of beats, short and tight). Vamp (one chord groove, no changes) is the fundamental difference from all 9 other arrangements. 1-bar cycle (not 2-bar). 16th-note syncopation is the rhythmic DNA. D default. 85-120 BPM. Fifth organic 4-track.
- `create_reggae_arrangement` — Eleventh multi-track arrangement. Roots reggae with one-drop feel across 4 tracks: drums (one-drop — kick AND snare TOGETHER on beat 3, no kick on 1, 8th-note hi-hat), bass (THE lead instrument — melodic walk root→octave→fifth→root, sustained, follows I-IV changes), guitar (skank — staccato chops on ALL off-beats, root+min3 voicing), keys (organ bubble — sustained minor triad, Hammond-style). One-drop (kick+snare together on 3, empty on 1) is unique among all arrangements. Bass as lead instrument is unique. I-IV minor vamp. A minor default. 60-100 BPM. Sixth organic 4-track.
- `create_synthwave_arrangement` — Twelfth multi-track arrangement. 80s-inspired synthwave across 4 tracks: drums (retro four-on-floor — kick on every quarter softer than house, snare on 2&4, 8th-note hats), bass (ARPEGGIATED 16th notes — root→octave→fifth→octave, the relentless engine), pads (sustained minor chords with octave doubling, dreamy 3.8-beat wash), lead (nostalgic melody following chord changes, chord-tone based with echo space). i-VI-III-VII progression (Am-F-C-G) — same chords as pop's I-V-vi-IV but minor-key. Arpeggiated bass is unique — no other arrangement uses 16th-note arpeggios. A minor default. 90-130 BPM, default 110. Sixth electronic 4-track.
- `create_trance_arrangement` — Thirteenth multi-track arrangement. Uplifting trance across 4 tracks: drums (driving four-on-floor — hard kick on every quarter, clap on 2&4, open hats on off-beats, snare rush buildup on last bar), bass (ROLLING off-beat 8ths — sustained notes on the "and" of every beat, root→octave alternation, the relentless trance engine), supersaw arp (16th-note chord arpeggio — root+third+fifth+octave cycling, wall of sound), pluck lead (staccato off-beat plucks answering the supersaw, chord-tone based). i-VI-III-VII progression (same as synthwave but euphoric, not nostalgic). Rolling off-beat bass is unique — house has short stabs, techno has drones, synthwave has 16th arpeggios, trance has sustained 8ths. F minor default. 128-145 BPM, default 138. Seventh electronic 4-track.
- `create_disco_arrangement` — Fourteenth multi-track arrangement. Classic 70s disco across 4 tracks: drums (four-on-floor with 16th OPEN hats — not closed 8ths like house, kick every quarter, clap 2+4, open hat on every 16th off-beat), bass (SYNCOPATED OCTAVE — the "good times" bass line: root on beat 1, octave jumps on the "and" of beats 2&4, fifth walks, melodic hook not just rhythmic), strings (sustained chord pads with octave doubling, 3.8-beat sustain, lush orchestral — house uses stabs, disco uses sustained strings), guitar (wah-wah 16th chops — ALL 16 16ths with accent pattern, root+min7 voicing, funk-influenced "chukka-chukka"). I-vi-IV-V progression (G-Em-C-D in G major) — major-key optimistic, the "feel good" sound. Syncopated octave bass + 16th open hats are the fundamental differences from house (its descendant): house has off-beat stabs with closed 8th hats, disco has melodic octave bass with 16th open hats. No sidechain (organic-electronic hybrid). G major default. 110-130 BPM, default 120. Eighth electronic 4-track.
- `create_lofi_arrangement` — Sixteenth multi-track arrangement. Lofi hip-hop (Nujabes/J Dilla/chillhop) across 4 tracks: drums (boom-bap — kick on 1+3, snare on 2+4 with laid-back timing bias +0.03, swing 0.58, dusty hat 16ths with velocity variation), bass (mellow walking — root→fifth→octave→chromatic walk, sustained quarter notes, not driving), chords (jazzy ii-V-I — Gm7-C7-Fmaj7 extended 7ths, sustained 3.8-beat wash with slow attack), melody (sparse sleepy pentatonic — 3-4 notes per bar with long rests, D minor pentatonic). F major default. 78 BPM. Ninth electronic 4-track. The swing + laid-back timing is unique — no other arrangement uses both. Lush 7th chords over pentatonic melody = signature lofi texture.
- `create_soul_arrangement` — Seventeenth multi-track arrangement. Motown/Stax soul across 4 tracks: drums (gospel backbeat — steady kick on 1+3, ghost snare on 2+4 with subtle ghost notes, ride with bell accents on off-beats), bass (melodic walking — root→fifth→octave→chromatic walk, quarter notes, follows I-IV-vi-V changes), chords (Rhodes stabs — maj7/dom7/min9 gospel voicings on I-IV-vi-V, syncopated off-beat placement), melody (Motown horn stabs + pentatonic fills — call-and-response between sustained notes and quick runs). C major default, I-IV-vi-V gospel changes (Cmaj7-Fmaj7-Am7-G7). 72 BPM. Seventh organic 4-track. Gospel changes (I-IV-vi-V) + Rhodes + walking bass = signature soul texture.
- `create_rnb_arrangement` — Eighteenth multi-track arrangement. Contemporary R&B (The Weeknd / Frank Ocean / SZA) across 4 tracks: drums (half-time groove — kick on 1, clap+snare on 3, triplet hi-hat rolls for trap influence, open hat on "and" of 4), bass (deep sub — long sustained root + octave on bar 2, felt not heard), chords (dark extended voicings — min9/maj7/min7 on i-VI-III-VII minor-key, long sustain + re-stab), lead (vocal-style phrases — pentatonic minor + blue notes b5, wide leaps, melismatic fills, call-and-response). C minor default, 68 BPM. The half-time drums + sub bass + dark 9ths = The Weeknd "After Hours" aesthetic. Triplet hats are the trap/R&B crossover signature.
- `create_blues_arrangement` — Nineteenth multi-track arrangement. Classic 12-bar blues across 4 tracks: drums (shuffle groove — kick on 1+3, snare on 2+4, triplet-feel hi-hats), bass (walking bass — quarter notes, root→fifth→octave→chromatic approach to next chord), chords (dominant 7th stabs — I7/IV7/V7 on beats 1+3, the blues never uses triads), lead (blues scale — root/b3/4/b5/5/b7 with blue notes, bends, long sustained notes + turnaround runs). 12-bar form: I-I-I-I-IV-IV-I-I-V-IV-I-V. A default, 120 BPM (Chicago blues). At 90 BPM = slow blues (B.B. King), 140 = fast shuffle (SRV). The most important chord progression in popular music — DNA of rock, jazz, soul, R&B.
- `apply_genre_humanization` — Genre-aware MIDI humanization. After arrangement, notes are perfectly quantized — robotic. This tool applies genre-appropriate humanization: jazz gets loose timing (0.20) + wide velocity variation (0.20) + swing (0.66); electronic genres stay tight (timing 0.02-0.04); funk gets behind-the-beat bias (0.02); reggae gets laid-back bias (0.03); pop is subtle (0.05). Per-track scaling: drums get full humanization (factor 1.0), bass gets half (0.5 — should stay tight), harmony gets 0.7, melody gets 0.8. Pipeline: create_arrangement → apply_genre_mix → apply_genre_humanization → add_mastering_chain.
- `create_genre_sections` — Multi-section electronic track structure. Transforms loop-based arrangements into song structure: intro (drums only, 0.5 energy) → buildup (drums+bass, 0.7) → drop (all tracks, 1.0) → breakdown (harmony+melody only, 0.6) → outro (drums+bass fading, 0.4). Each section is a separate arrangement call at different start_beat with energy-scaled velocity. 8 electronic genres supported. Custom section lengths via comma-separated bar counts (default "4,8,8,8,4" = 32 bars).
- `create_arrangement_variation` — Create a musically varied section with real transformations. Unlike create_genre_sections (which repeats the same loop at different velocities), this applies per-track musical transforms: drum density (sparse/busy), bass octave shift (±1-2), melody inversion/transposition/retrograde/fragment, and independent track inclusion/exclusion. All 14 genres supported. Build songs where each section has real musical variation: breakdown = sparse drums + no bass + inverted melody; bridge = octave-up bass + retrograde melody.
- `create_song_with_variations` — Build a complete song with real musical variations between sections in one call. 12 presets (full, drums_only, drums_bass, full_busy, breakdown, melody_invert/reverse/octave_up/transposeN, bass_octave_up, bass_sub, fade, drop). Default: 36-bar song (intro:4:0.5:drums_only → verse1:8:0.8:full → chorus:8:1.0:full_busy → verse2:8:0.8:melody_transpose5 → bridge:4:0.6:breakdown → outro:4:0.4:fade). Optional post-processing: apply_genre_mix + apply_genre_humanization + add_mastering_chain. All 14 genres.
- `render_full_song` — Render the entire project — auto-detects song length from all regions. Scans all note and audio regions to find latest ending, adds configurable tail (default 4 beats for reverb/delay), then delegates to render_range. Closes the pipeline: create_song_with_variations → render_full_song = complete zero-to-WAV pipeline.
- `create_full_genre_pipeline` — Zero-to-render-ready in one call. New `progression` parameter adds harmonic layers (arp + melody) on top of genre rhythm. Pads/bass skipped (genre already has them). `add_counter_melody` flag adds contrary-motion 5th layer. Steps: set_bpm → create_tracks → arrangement → harmonic_layers (optional) → genre_mix → humanization → mastering. 15 genres. Summary: rhythm_notes + harmonic_notes + progression.
- `create_chord_pads` — Create chord pads from a human-readable progression string (e.g. "Am-F-C-G"). Unlike create_chord_progression (JSON arrays), this takes simple hyphen-separated chord names. 10 chord types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug. Configurable octave, velocity, bars per chord, note duration. Default: i-VI-III-VII in A minor (synthwave/trance). Also: "C-G-Am-F" = pop I-V-vi-IV, "Dm7-G7-Cmaj7-Am7" = jazz ii-V-I-vi.
- `create_arpeggiated_progression` — Create an arpeggiated chord progression — synthwave/trance arp engine. Takes same progression string as create_chord_pads ("Am-F-C-G") but generates arpeggiated notes cycling through chord tones. 5 patterns: up (root→3rd→5th→oct), down (oct→5th→3rd→root), updown (full cycle), random (dreamy), bass (root only, driving). Configurable octave (2=bass arp, 4=mid, 5=lead), step_duration (16th/8th/32nd), bars_per_chord. Unlike create_arpeggio (single chord), this cycles through a full progression.
- `create_bass_from_progression` — Create a bass line from a chord progression string. Completes the harmonic trio: create_chord_pads (sustained harmony) + create_arpeggiated_progression (melodic movement) + this (bass foundation). All three take the same "Am-F-C-G" string. 6 patterns: root (beat 1+3), root_fifth (rock/pop), walking (jazz: root→chord tone→chord tone→chromatic approach), pedal (techno/house sub-bass), octave (disco/funk 8th alternation), root_octave (pop/rock power). Configurable octave (1=sub-bass, 2=bass, 3=mid), velocity, bars_per_chord.
- `create_melody_from_progression` — Create a lead melody from a chord progression string. Completes the harmonic quartet: create_chord_pads + create_arpeggiated_progression + create_bass_from_progression + this. All four take the same "Am-F-C-G" string. Melody hits chord tones on strong beats (1, 3) and passing/neighbor tones on weak beats (2, 4). 5 patterns: chord_tones (4 quarters: chord tones + passing), sustained (1 chord tone per bar, ballad), syncopated (8th notes: downbeat=chord, upbeat=passing), triadic (8th arpeggios with octave variation, folk/country), stepwise (scale steps between chord tones, pop/classical). Configurable octave (5=typical lead), velocity, bars_per_chord.
- `create_harmonic_arrangement` — One-call harmonic quintet: creates all five harmonic layers (chord pads + arpeggiated progression + bass + melody + counter-melody) from a single "Am-F-C-G" progression string. Replaces 5 separate calls with 1. Configurable per-layer: pad_octave, arp_pattern (up/down/updown/random/bass or "" to skip), arp_octave, arp_step, bass_pattern (root/root_fifth/walking/pedal/octave/root_octave or "" to skip), bass_octave, melody_pattern (chord_tones/sustained/syncopated/triadic/stepwise or "" to skip), melody_octave, counter_melody_pattern (contrary/oblique/parallel_third/parallel_sixth/call_response or "" to skip, default skip), counter_melody_octave. Velocity auto-scaled per layer (pads=0.9x, bass=1.0x, arp=0.85x, melody=0.75x, counter_melody=0.6x). Track auto-routing: pads=2, bass=1, arp=3, melody=3-4, counter_melody=3-5 depending on which layers active.
- `create_counter_melody_from_progression` — Create a counter-melody (second melodic line) from a chord progression string. Completes the harmonic quintet: chord_pads + arpeggiated_progression + bass_from_progression + melody_from_progression + this. 5 contrapuntal patterns: contrary (opposite root motion, species-1 counterpoint), oblique (sustained tone, drone-like), parallel_third (sweet consonance), parallel_sixth (open cinematic), call_response (rests 1-2, plays 3-4, gospel/soul). Default velocity 0.6 (supportive, not competing with melody at 0.75). Default track 4 (above melody track 3), default octave 4 (below melody octave 5).
- `modulate_progression` — Transpose a chord progression to a new key. Preserves chord qualities (min/maj/7th) and interval relationships. Supports up/down direction, flat/sharp key naming, per-chord root shift mapping. Returns modulated progression string. Common: Am→C (relative major), C→Am (relative minor), C→F (up P4, chorus), C→G (up P5, triumphant), C→A (down m3, bridge).
- `create_modulated_song` — Build a multi-section song with key modulation in one call. Sections format: "name:progression:bars:energy" comma-separated. Default: verse(Am,8b,0.7)→chorus(C,8b,1.0)→bridge(F,4b,0.6)→outro(Am,4b,0.5) = 24 bars. Each section auto-modulates via different progression. Inherits all 5 harmonic layers (pads+arp+bass+melody+counter-melody). Auto-calculates start_beat per section. Up to 12 sections.
- `create_bordun` — Continuously sustained drone chord as a textural layer. Open fifths, octaves, or custom intervals. Retrigger every N bars or one continuous note. Bagpipes, tanpura, hurdy-gurdy, ambient drone, folk.
- `create_hocket` — Single melodic line split between 2-4 voices. Three split modes: alternate (round-robin), pairs, phrase. Each voice plays only part of the melody. Medieval polyphony, African mbira, Balinese gamelan, Steve Reich.
- `create_isorhythm` — Repeating rhythm (talea) × repeating pitch (color) as independent cycles. Phase shift when lengths differ, realign at LCM. Medieval motets (Machaut), Messiaen, Boulez. Distinct from ostinato.
- `create_canon` — Strict melodic imitation with delayed voice entries. 2-6 voices, per-voice transposition, velocity decay, up/down entry order. Pachelbel, rounds, fugue subjects, film score layering.
- `create_comping` — Rhythmic chordal accompaniment. Chord JSON + rhythm grid (x/play, -/rest, ./ghost). Jazz piano, funk guitar, reggae skanks, country boom-chick, neo-soul. Syncopation, multi-chord progression.
- `create_ostinato` — Create a repeating melodic/rhythmic pattern as a foundation layer. Scale-based, 1-16 repeats. Common in minimalism, electronic, and film music.
- `create_crescendo` — Apply crescendo/decrescendo to existing notes. Linear, exponential, or logarithmic velocity curves. One call modifies all notes in a region.
- `scale_velocity` — Scale velocity of all notes in a region — MIDI dynamics gain. 5 modes: multiply (×1.2 louder), add (+0.1), set (uniform), normalize (scale to target max), compress (reduce dynamic range around 0.5 midpoint). Returns original + new velocity min/max/avg. Clamp range via min_velocity/max_velocity.
- `scale_durations` — Scale duration of all notes in a region — MIDI note length control. 5 modes: multiply (×0.5 staccato), add (+0.5 beats), set (uniform), quantize (snap to 16th/8th/quarter/half grid), legato (extend to next note with gap). Returns original + new duration min/max/avg. Clamp via min_duration/max_duration.
- `groove_transfer` — Transfer groove (timing + velocity feel) from a source region to a destination region. Extracts groove template (per-grid-slot timing offsets + velocity ratios) from source notes, then applies to destination notes. Groove cycles every groove_length beats (4=1 bar, 3=waltz). timing_strength + velocity_strength control blend. 16th/8th grid. NOT copying notes — transfers the feel.
- `time_warp_notes` — Warp note positions AND durations by a factor — true half-time (0.5×) or double-time (2.0×) feel without changing BPM. Unlike scale_durations (only duration), this moves notes in time. 1-bar pattern → 2 bars (half-time) or 1 bar (from 2-bar, double-time). origin: "start" (region start) or "zero" (absolute). Range 0.1-8.0.
- `force_scale_notes` — Force all notes into a specific scale — harmonic snap. Finds out-of-scale notes and moves them to nearest in-scale pitch. 13 scales (major/minor/dorian/phrygian/lydian/mixolydian/pentatonic/blues/harmonic_minor/melodic_minor). direction: nearest/up/down. preserve_octave: stay in octave or allow octave jumps. Harmonic equivalent of quantize_notes.
- `identify_chords` — Identify chords from existing notes in a region — harmonic analysis / reverse engineering. Groups notes by temporal overlap, matches pitch-class sets against 10 chord types (maj/min/dom7/maj7/min7/sus2/sus4/add9/dim/aug). Returns chord name, root, type, time position, alternate names, and note names. Subset matching for chords with extensions. Use after import/transcription to understand harmony.
- `diatonic_transpose_notes` — Transpose notes by scale steps instead of semitones. C major C→D = +1 step (2 semitones), E→F = +1 step (1 semitone) — preserves the scale. 13 scales. Skips out-of-scale notes. Octave wrapping. For creating variations, sequences, modal interchange, counterpoint.
- `extract_motifs` — Extract repeating melodic motifs from MIDI regions. Identifies short melodic phrases (3-8 notes) by their interval contour — the pattern of pitch changes. Same motif transposed still matches. Contour classification (ascending/descending/arch/V-shape/wave/static/mixed), rhythm pattern matching, significance scoring, deduplication. Returns occurrences with positions and pitches. Use to understand melodic structure, find repetitive patterns, build call-and-response."
- `analyze_song_structure` — Structural analysis of MIDI content. Scans all note tracks bar-by-bar, computes per-bar features (density, pitch range, velocity, active tracks, energy). Groups consecutive bars into segments and classifies as intro/verse/chorus/bridge/outro/breakdown. Returns form string (e.g. 'intro → verse → chorus → outro'). Use to understand existing arrangements, verify song form, plan variations."
- `classify_drum_pattern` — Rhythmic pattern classification from MIDI drum notes. Uses GM drum map (36=kick, 38=snare, 42=hat, 46=open hat, 49=crash, 51=ride). Classifies into 8 patterns: four-on-the-floor, boom-bap, trap, breakbeat, shuffle, half-time, amen, march. Confidence scoring, per-bar breakdown, syncopation/triplet/velocity analysis. Use to understand existing drum patterns, match genre expectations."
- `create_motif_variations` — Classical motif transformation from existing MIDI. Extracts a motif (start_note + note_count) and creates a variation: sequence (shifted repeats), inversion (mirrored intervals), retrograde (backwards), augmentation (stretched), diminution (compressed), fragmentation (first N notes repeated). Closes analysis→creation loop. Auto-creates target track/region."
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
- `add_vocal_chain` — One-call vocal processing: EQ + Compressor + Reverb (+ optional Delay). 5 presets (balanced/warm/bright/intimate/aggressive).
- `add_drum_chain` — One-call drum processing: Gate + EQ + Compressor (+ optional Reverb). 5 presets (punchy/deep/crisp/roomy/tight).
- `add_bass_chain` — One-call bass processing: EQ + Compressor (+ optional Waveshaper drive). 5 presets (deep/round/driven/clean/tight).
- `add_instrument_chain` — Universal instrument processing: EQ + Compressor + Reverb (+ optional Delay). 5 presets (clean/warm/bright/ambient/driven) for guitars, keys, synth leads, strings.
- `apply_full_mix` — One-call complete mix: genre-aware drum/bass/instrument chains on all tracks + mastering. Replaces 5-6 individual chain calls.
- `create_genre_track` — Create a full genre starting point (house/techno/lofi/dnb/trap/ambient/coldwave/hiphop) — synth, drums, bass, chords, BPM in one call.
- `create_song_structure` — Create arrangement markers (intro/verse/chorus/bridge/outro) from JSON section list. Enables agents to reason about song form.
- `automation_sweep` — Create smooth automation ramps (filter sweeps, volume fades) with linear/exp/log curves in one call. Replaces 10-30 create_automation_event calls.
- `apply_mix_preset` — Apply volume/pan/mute/solo to all units from JSON or named preset (lofi/house/balanced/wide). Replaces 10-30 individual mixer calls.

- `create_tempo_ramp` — Smooth tempo ramp (ritardando/accelerando). Series of ValueEventBox on tempo track. 3 curves (linear/exp/log), configurable steps. Auto-detects ramp type.
- `duplicate_section` — Duplicate all regions in a beat range to a new position. Scans all tracks across all AUs, copies each overlapping region with offset. Replaces N duplicate_region calls with one.
- `apply_velocity_pattern` — Cyclic velocity accent pattern on existing notes. JSON array of multipliers cycled across notes. 2 modes: cycle (repeat) and stretch (distribute). The groove tool — replaces manual per-note velocity editing.
- `move_section` — Move all regions in a beat range to a new position. Cut-and-paste for arrangement restructuring. Collect-then-move pattern avoids index invalidation. Pairs with duplicate_section.
- `delete_section` — Delete all regions in a beat range. Completes section CRUD trilogy: duplicate (copy), move (cut-paste), delete (remove). Collect-then-delete pattern.
- `clear_region_notes` — Erase all notes inside a region while keeping the region on the timeline. The "erase and rewrite" operation — different from delete_note_region (removes entire region) and delete_note (removes single note).

**Total: 396 tools**

## DSP Scripts (scripts/) — 110 scripts

### Werkstatt (Audio Effects) — 91 scripts
- `werkstatt_darksat.js` — Tape saturation (drive, bias, tone, mix, output)
- `werkstatt_tape_delay.js` — Tape delay (wow/flutter pitch modulation, feedback saturation, fractional read)
- `werkstatt_multitap_delay.js` — Multitap delay (4 independent taps from single buffer, per-tap time/level/pan/feedback, equal-power pan, spread modulation, feedback damping)
- `werkstatt_dimension_chorus.js` — Dimension chorus (Roland Dimension D: dual detuned delay lines, independent LFO rates, triangle wave, no feedback, mono-sum input, brightness filter, stereo width)
- `werkstatt_autowah.js` — Autowah (envelope-followed filter: 3 modes bandpass/peaking/lowpass, sensitivity, attack/release, up/down sweep direction, cutoff smoothing)
- `werkstatt_octaver.js` — Octaver (sub-octave generator: zero-crossing flip-flop /2 and /4, envelope tracking, hysteresis, square wave smoothing, Boss OC-2 style)
- `werkstatt_fuzz.js` — Fuzz (Big Muff Pi style: hard clipping with high gain, full-wave rectified octave-up, Muff tone stack LP/HP blend, noise gate, asymmetrical bias, foldback squash, dry blend)
- `werkstatt_tape_stop.js` — Tape stop (exponential slow-down to full stop with pitch drop, state machine playing/stopping/stopped, trigger/restart, wow/flutter, configurable curve, DJ Screw/trap/lo-fi)
- `werkstatt_tube_saturator.js` — Tube saturator (even harmonics, asymmetrical bias, warmth, tone, output, mix)
- `werkstatt_spring_reverb.js` — Spring reverb (dispersive, boing transient, tension, damp, mix)
- `werkstatt_bitcrusher.js` — Standalone bitcrusher (bits 1-16, rate reduction, drive, DC offset, mix)
- `werkstatt_graphic_eq.js` — 10-band graphic EQ (ISO freqs 32Hz–16kHz, ±12dB, biquad peaking, master ±6dB)
- `werkstatt_auto_pan.js` — Auto-pan (LFO stereo positioning, sine→tri→square morph, equal-power, rate/depth/phase/width/offset)
- `werkstatt_comb_filter.js` — Comb filter (delay-line feedback, ±polarity, damping LP, freq 10-8000Hz)
- `werkstatt_formant_filter.js` — Formant filter (3-band vocal tract, 5 vowel presets, manual F1/F2/F3, bandwidth, resonance)
- `werkstatt_harmonizer.js` — Dual-voice harmonizer (±12 semi + ±50 cent per voice, detune LFO, delay-based pitch shift)
- `werkstatt_multiband_comp.js` — 3-band multiband compressor (LR4 crossover, per-band threshold/ratio/attack/release/gain)
- `werkstatt_vocoder.js` — Channel vocoder (8-24 log-spaced bandpass bank, modulator→carrier spectral envelope mapping, saw/square/noise carrier, emphasis, output HPF)
- `werkstatt_reverse.js` — Real-time reverse playback (chunked circular buffer, variable speed 0.25x-4x, 3 trigger modes, 3 stereo modes, feedback, crossfade smoothing)
- `werkstatt_scratch.js` — DJ vinyl scratch (turntable physics: triangle LFO back-and-forth, friction-based velocity inertia, pullback yank, wow/flutter pitch wobble, random crackle pops)
- `werkstatt_looper.js` — Live looper with overdub (circular buffer, 3 play modes: auto/play/overdub, variable speed 0.25x-4x, reverse mode, crossfade at loop boundaries, input monitor)
- `werkstatt_spectral_gate.js` — Multiband spectral gate (4-16 log-spaced bandpass bank, per-band envelope followers, threshold gating, spectral tilt, output HPF)
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
- `werkstatt_vibrato.js` — Pitch vibrato (rate, depth, shape sine→tri, stereo spread)
- `werkstatt_stereo_delay.js` — Stereo delay with ping-pong (time_l, time_r, feedback, tone, mix, pingpong)
- `werkstatt_overdrive.js` — Asymmetric soft-clip overdrive (drive, tone, level, bias, dry)
- `werkstatt_multifilter.js` — Multi-mode SVF filter: LP/HP/BP/Notch (mode, cutoff, resonance, drive, mix)
- `werkstatt_compressor.js` — Soft-knee peak compressor (threshold, ratio, attack, release, makeup, mix, knee)
- `werkstatt_paraeq.js` — 3-band parametric EQ + HP/LP (band1/2/3 freq+gain+Q, hp_freq, lp_freq, mix)
- `werkstatt_limiter.js` — Brickwall limiter with lookahead + TPDF dither (ceiling, release, lookahead, dither, mix)
- `werkstatt_exciter.js` — Harmonic exciter, band-split architecture (freq, harmonics, drive, mix, output)
- `werkstatt_deesser.js` — De-esser, dynamic high-frequency compressor (freq, threshold, ratio, attack, release, mix, output)
- `werkstatt_transient.js` — Transient shaper, dual envelope (attack, sustain, mix, output)
- `werkstatt_stereowidth.js` — Stereo width M/S processor (width, lowTrim, lowFreq, mix, output)
- `werkstatt_multiband_imager.js` — Multiband stereo imager (3-band LR4 crossover, per-band M/S width control, mono bass default, bypass_low, link mode, iZotope Ozone Imager style)
- `werkstatt_convolution_reverb.js` — Convolution reverb (generated stereo IR, early reflections + decaying noise tail, room_size, decay, damping, predelay, early/late balance, width, mix, output)
- `werkstatt_gated_reverb.js` — Gated reverb (80s drum sound: Schroeder plate + envelope-followed gate on dry input, threshold/hold/release cut reverb tail, Phil Collins / In the Air Tonight style)
- `werkstatt_reverse_delay.js` — Reverse delay (reads delay buffer backwards, fade ramps at window boundaries, damped feedback creates cascading reverse repeats, The Edge / U2 style, time/feedback/levels/pan/fade/damping/mix/output)
- `werkstatt_freq_shifter.js` — SSB frequency shifter (single-sideband modulation via Hilbert transform allpass pair + complex carrier, shifts all frequencies by fixed Hz not ratio, breaks harmonic relationships, upper/lower sideband direction, feedback for spiraling, Buchla/banana synth style)
- `werkstatt_bass_enhancer.js` — Psychoacoustic bass enhancer (MaxxBass / Renaissance Bass: LPF isolates bass, full-wave rectification generates sub-harmonics, LPF smoothing + HPF DC removal, envelope follower, tanh harmonic saturation for presence, band replacement, brain perceives missing fundamental on small speakers)
- `werkstatt_tilt_eq.js` — Tilt EQ (single-knob spectral balance: low shelf cut + high shelf boost for brighten, reverse for darken, pivot frequency, steepness controls slope, biquad RBJ cookbook, coefficient caching, Ozone/FabFilter/Airwindows style)
- `werkstatt_svf.js` — State variable filter (Chamberlin topology: simultaneous LP/BP/HP, morph parameter for continuous LP→BP→HP blend, output mode notch/allpass, self-oscillation at high resonance with tanh soft-clip protection, Korg MS-20 / Oberheim SEM style)
- `werkstatt_dynamic_eq.js` — Dynamic EQ (3 bands, peaking biquad + envelope follower, per-band threshold/range, attack/release, mix, output)
- `werkstatt_modal_resonator.js` — Modal synthesis resonator bank (5 materials: marimba/bell/plate/string/glass, parallel bandpass biquads at modal frequency ratios, inharmonicity stretch, T60-based Q, brightness rolloff, stereo)
- `werkstatt_multiband_saturator.js` — Multiband saturator (LR4 crossover 3-band, per-band drive + character: tape/tube/transistor, asymmetric tube clip, band summation, dry/wet)
- `werkstatt_vinyl.js` — Vinyl simulator (crackle/pops via LCG-triggered envelopes, surface noise, wow/flutter pitch wobble via fractional delay, wear high-freq rolloff)
- `werkstatt_grain_delay.js` — Grain delay (Hann-windowed grains read from delay buffer with pitch shift, scatter, reverse, pan, feedback)
- `werkstatt_expander.js` — Downward expander (compressor complement: attenuates signals below threshold, ratio controls expansion strength, range caps max attenuation, soft knee, stereo linked detection, gate at ratio=∞)
- `werkstatt_binaural.js` — Binaural spatial panner (3D positioning via Woodworth ITD formula, frequency-dependent ILD head shadow, pinna elevation spectral notches, distance attenuation + air absorption, room reverb with decorrelation, azimuth/elevation/distance/head_size/room/mix/output)
- `werkstatt_harmonic_tremolo.js` — Harmonic tremolo (Fender '60s: LR4 crossover splits low/high bands, dual LFO modulates them in antiphase, bass↔treble spectral rocking not amplitude, shape sine→square, phase_offset, crossover/rate/depth/shape/phase_offset/mix/output)
- `werkstatt_spectral_compressor.js` — Spectral compressor (STFT per-bin dynamics: Cooley-Tukey FFT, Hann window, per-bin envelope follower + compression, tilt shifts threshold across frequency, gain smoothing, overlap-add, no crossover artifacts, Flux Syrah / FabFilter Pro-MB style)
- `apparat_bowed_string.js` — Bowed string (digital waveguide + bow friction: Stribeck stick-slip model, Helmholtz motion, two delay lines split at bow position, string damping filter, 3-resonator violin body, vibrato, noteOn MIDI trigger)
- `werkstatt_auto_tune.js` — Auto-tune pitch correction (autocorrelation pitch detection 60-1200Hz with parabolic interpolation, snap-to-scale: 7 scales × 12 roots, time-domain pitch shift via ring buffer, retune speed hard/soft, strength blend, detune offset, Cher/T-Pain style)
- `werkstatt_phase_vocoder.js` — Phase vocoder (FFT-based pitch shifter: 2048-point STFT + phase unwrapping + true frequency + accumulated output phase + identity phase lock, formant control, ±12 semitones, Élastique/Melodyne quality, no transient smearing)
- `werkstatt_time_stretch.js` — Phase vocoder time stretch (FFT-based: preserves pitch, changes duration 0.25x–4x, synthesis hop = analysis hop × ratio, transient detection + preservation, identity phase lock, Élastique-grade quality)
- `werkstatt_matching_eq.js` — Matching EQ (adaptive spectral balance: LTAS accumulation, pink/white/brown noise targets interpolated, per-bin correction gain = (target/actual)^match, smoothing, adaptation speed, tilt, gain clamp 0.1-10x, Ozone EQ Match style)
- `werkstatt_spectral_denoise.js` — Spectral denoiser (noise floor subtraction: 2-phase learn+denoise, Berouti spectral subtraction with oversubtraction 1-4x, spectral floor, half-wave rectification, gain smoothing, -30 dB max reduction, RX/CEDAR style, first restoration processor)
- `werkstatt_dereverb.js` — De-reverb (reverb tail suppression: per-band dual envelope followers, fast=direct/slow=tail, transient detection via ratio, tail dominance gain reduction -24 dB, decay estimation, RX De-reverb style, second restoration processor)
- `werkstatt_declicker.js` — De-clicker (click & crackle removal: median-filter detection with insertion sort, adaptive threshold via local energy, cubic Hermite (Catmull-Rom) interpolation, click length limit 8-128 samples, overlap expansion, delay buffer for look-back, RX De-click / CEDAR Declick style, third restoration processor)
- `werkstatt_decrackle.js` — De-crackle (continuous crackle removal: adaptive crackle modeling with separate crackle/signal energy tracking, adaptive threshold, crackle rate estimation 10-200/sec, extent finding 1-8 samples, Hermite/linear blend interpolation, strength blend, RX De-crackle / CEDAR Decrackle style, fourth restoration processor)
- `werkstatt_moog_ladder.js` — Moog ladder filter (4 cascaded 1-pole LP stages with internal feedback, resonant self-oscillation at max resonance, thermal saturation, drive, cutoff, resonance, output)
- `werkstatt_rotary_speaker.js` — Rotary speaker (Leslie: dual rotor Doppler, horn + baffle, amplitude modulation, tremolo, acceleration/deceleration ramp, distance, mix, output)
- `werkstatt_waveshaper.js` — Waveshaper (adjustable transfer curve: fold, clip, asymmetry, drive, DC bias, output, mix)
- `werkstatt_envelope_follower.js` — Envelope follower (amplitude tracking with attack/release coefficients, sidechain ducking output, building block for auto-wah, tremolo auto-depth, sidechain detection)
- `werkstatt_auto_wah.js` — Auto-wah (envelope-driven biquad bandpass sweep, Mu-Tron III style: attack/release envelope follower, resonance Q, sensitivity, up/down sweep)
- `werkstatt_mid_side_processor.js` — Mid/Side processor (independent M/S gain + filters + width control, M/S encoding/decoding, stereo mastering tool, mid_gain, side_gain, mid_freq, side_freq, width, mix)
- `werkstatt_haas_widener.js` — Haas stereo widener (short delay 1-30ms on one channel for precedence effect, pseudo-stereo from mono, delay, width, channel flip, feedback, mix)
- `werkstatt_glue_comp.js` — SSL-style glue compressor (auto-makeup gain, VCA warmth via tanh soft clip, 2:1 ratio / 10ms attack / 100ms release defaults, parallel mix New York compression, true stereo peak detection)
- `werkstatt_de_plosive.js` — De-plosive (adaptive highpass for vocal plosive removal, one-pole LP envelope follower + threshold, transient-triggered HPF sweep, strength, freq, attack, release, mix)
- `werkstatt_vowel_morph.js` — Vowel morph (3 cascaded formant biquad bandpass filters F1/F2/F3, A→E→I→O→U interpolation, auto-morph LFO with rate, spectral tilt, mix, output)
- `werkstatt_formant_shifter.js` — Formant shifter (LPC Levinson-Durbin reflection coefficients, lattice filter structure, formant frequency scaling independent of pitch, gender/age/size morphing, brightness, stereo width, 3-8 filter stages)
- `werkstatt_spectral_blur.js` — Spectral blur (STFT-based spectral smearing: Cooley-Tukey FFT, Hann window, frequency blur averages magnitude across neighboring bins, temporal blur averages across 4 previous frames, phase randomization for diffuse texture, overlap-add reconstruction, ambient/drone/sound design)
- `werkstatt_spectral_enhancer.js` — Spectral enhancer (STFT-based high-frequency "air" boost above crossover, spectral peak emphasis for sparkle, transient enhancement via magnitude delta detection, stereo widening on enhanced band, mastering/sheen)
- `werkstatt_karplus_strong.js` — Karplus-Strong string synthesis (delay-line with one-pole lowpass feedback loop, brightness controls feedback filtering, pluck damping controls excitation gain, stretch parameter for inharmonic/detuned strings, stereo processing)
- `werkstatt_waveguide_string.js` — Waveguide string synthesis (bidirectional delay lines, bridge one-pole lowpass termination, nut first-order allpass dispersion for inharmonicity, pick position splits excitation between waves, stereo processing)

### Apparat (Instruments) — 9 scripts
- `apparat_darkbass.js` — Dark bass synth (waveform, cutoff, resonance, envelope)
- `apparat_coldlead.js` — Cold lead synth (oscillator, envelope, filter)
- `apparat_subcrusher.js` — Sub crusher (distorted bass, oscillator, distortion)
- `apparat_fm.js` — FM synthesis (carrier, modulator, ratio, depth)
- `apparat_ringmod.js` — Ring modulation synth (carrier, modulator, depth)
- `apparat_pluck.js` — Karplus-Strong plucked string (decay, damping, brightness, attack, release, detune, volume)
- `apparat_wavetable.js` — Wavetable synth (8 tables, scan position + LFO, unison detune, ADSR, volume)
- `apparat_supersaw.js` — Supersaw synth (7 detuned saws, per-voice stereo pan, resonant lowpass, ADSR)
- `apparat_bowed_string.js` — Bowed string (digital waveguide + bow friction: Stribeck stick-slip model, Helmholtz motion, two delay lines split at bow position, string damping filter, 3-resonator violin body, vibrato, noteOn MIDI trigger)

### Spielwerk (MIDI Effects) — 10 scripts
- `spielwerk_arpeggiator.js` — MIDI arpeggiator (rate, octave, pattern)
- `spielwerk_chordmemory.js` — Chord memory (chord type 0-6)
- `spielwerk_mididelay.js` — MIDI delay (time, feedback, mix)
- `spielwerk_powerchord.js` — Power chord generator (interval, voicing)
- `spielwerk_strum.js` — Strummer (speed, direction)
- `spielwerk_velocity.js` — Velocity scaler (scale, offset)
- `spielwerk_scale_quantizer.js` — Scale quantizer (14 scales, 12 roots, snap direction)
- `spielwerk_harmonizer.js` — MIDI harmonizer (3 voices, diatonic/fixed mode, 14 scales, per-voice velocity)
- `spielwerk_prob_gate.js` — Probability gate (subtractive MIDI effect: LCG-based note dropping, 3 modes uniform/position/pitch, hold momentum, forced pass zones, velocity boost, seedable)
- `spielwerk_chorder.js` — Chord voicer (13 chord shapes, 5 voicing modes close/drop2/drop3/open/spread, 4 inversions, octave shift, spread spacing, strum delay)

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