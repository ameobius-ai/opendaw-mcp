# MCP Tool Signature Reference (verified 2026-07-03)

Non-obvious parameter signatures for `mcp_opendaw_*` tools in `server.py`.
These caused example script failures when assumptions were wrong.

## Critical signatures

### create_synth_track(name: str, synth_type: str) → str
- TWO args: display name + device type
- Returns JSON: `{"success": true, "unit_index": N, "track_index": 0, "synth_type": "...", ...}`
- `unit_index` is DYNAMIC — output bus = 0, first instrument = 1
- synth_type: "Vaporisateur", "Nano", "Tape", "Soundfont", "Playfield", "Apparat", "MIDIOutput"

### create_note_track(unit_index: int) → str
- ONE arg only. No name parameter.
- Creates a note/MIDI track on the specified AU.

### create_track_region(unit_index, track_index, start_beat, duration_beats, name, hue) → str
- `start_beat` and `duration_beats` are in BEATS, not PPQN. 4 bars = 16 beats.
- `name`: display name string (can be empty "")
- `hue`: NUMBER 0-360 (or -1 for auto). NOT a hex color string.
  - `#4488ff` → JS SyntaxError (# is a comment char in JS template)
  - Use: 220 (blue), 15 (orange), 120 (green), 0 (red), 280 (purple)

### create_note(track_index, pitch, start_beat, duration_beats, velocity, unit_index) → str
- Parameter ORDER: track_index FIRST, unit_index LAST
- `start_beat` and `duration_beats` in BEATS (not PPQN). 1 beat = 1 quarter note.
- `velocity`: float 0.0-1.0 (not 0-127)
- `pitch`: MIDI note number (60 = C4, 69 = A4)

### set_track_volume(unit_index: int, volume_db: str) → str
- `volume_db` is a STRING: `"-4"` not `-4`
- Range: -96 dB (mute) to +6 dB. 0 dB = raw 0.768.

### set_script_param(device_type, unit_index, device_index, param_label, value) → str
- `device_type`: "Apparat", "Werkstatt", "Spielwerk" — case-insensitive (`.toLowerCase()` applied in JS). Any capitalization works.
- `value`: float/int. Passed directly to JS. For strings use json.dumps in Python.

### set_script_device_code(device_type, unit_index, device_index, code) → str
- `device_type`: case-insensitive. `.toLowerCase()` applied to both `dt` (device selection) and `headerTag` (regex/header generation).
- **Apparat box access**: `au.input.pointerHub.incoming()` + `find(b => b.constructor.name === "ApparatDeviceBox")`. NOT `au.input.targetVertex.unwrapOrNull()` — that API doesn't exist on AudioUnitBox and crashes with "Cannot read properties of undefined (reading 'unwrapOrNull')".
- Werkstatt/Spielwerk found via `au.audioEffects.pointerHub.incoming()` / `au.midiEffects.pointerHub.incoming()` + device_index.
- Compiles code: parses `@param` → creates WerkstattParameterBox, parses `@sample` → creates WerkstattSampleBox, validates JS via `new Function()`, registers AudioWorklet. All box mutations in one `editing.modify()` block.
- Returns: `{success, device, code_length, params_created, params, samples_created, samples, worklet_registered, worklet_error}`

### add_automation(unit_index, effect_index, param_name, points) → str
- `points`: JSON string of `[[position_beats, value_0_to_1], ...]` pairs — ARRAY OF ARRAYS, NOT array of objects
- Correct: `"[[0, 0.1], [4, 0.9], [8, 0.3], [16, 0.1]]"`
- WRONG: `json.dumps([{"position": 0, "value": 200, "interpolation": "curve"}])` → "object is not iterable" error
- `position` is BEATS not PPQN
- **Bug fixed 2026-07-03**: `{points_js}` → `{points}` in the f-string template (NameError — variable `points_js` didn't exist, only `points`)

### create_send(src_unit: str, name: str, send_level_db: str, routing: str) → str
- `src_unit`: STRING (not int). Pass `str(uid)`.
- `name`: display name for the FX bus (e.g. "Reverb Bus")
- `send_level_db`: STRING. e.g. `"-6"`, `"-9"`. Not a float.
- `routing`: `"pre"` or `"post"` (post-fader is default). NOT a bus index.
- **Creates a NEW AudioBusBox + AudioUnitBox automatically** — no need to `create_audio_bus` first.
- Returns: `{success, send_index, fx_unit_index}` — use `fx_unit_index` to add effects on the FX bus.
- Workflow: `create_send("1", "Reverb Bus", "-6", "post")` → `add_effect(fx_unit_index, "Reverb")`

### set_vaporisateur_osc_param(osc_index: str, param_name: str, value: float, unit_index: int) → str
- `osc_index`: STRING (not int). Pass `"0"`, `"1"`.
- `param_name`: "waveform" (0=Sine/1=Triangle/2=Saw/3=Square), "volume" (dB), "octave", "tune"
- `unit_index`: int, LAST parameter (not first)
- Example: `set_vaporisateur_osc_param("0", "waveform", 2, uid)`

### add_marker(position: int, label: str) → str
- `position` in BEATS (integer), not PPQN

### add_effect(unit_index: int, effect_type: str) → str
- effect_type: "Delay", "Reverb", "Compressor", "Equalizer", "Saturation", "Waveshaper", "Stereo", "Vocoder", "NeuralAmp", "Maximizer", "Modular", "Werkstatt"

### add_midi_effect(unit_index: int, effect_type: str) → str
- effect_type: "Arpeggio", "Pitch", "Velocity", "Zeitgeist", "Spielwerk"

### export_stems(filename_prefix: str, sample_rate: int) → str
- Does NOT need `start_engine()` — the offline renderer creates its own engine from a copied project. Calling `start_engine()` first causes "Already connected" error.
- Returns: `{success, frames, samples, max_sample, size, sample_rate}`. `frames=2` = stereo. `max_sample=0` = silent render (was caused by create_note creating overlapping regions — see `references/create-note-region-fix.md`, now FIXED).
- **UUID format**: `au.address.uuid.toString()` returns comma-separated bytes. Must use `window.DAW_UUID.toString(au.address.uuid)` for proper UUID strings.
- **ExportConfiguration**: `stems` must be `Record<uuid_string, ExportStemConfiguration>` — object keyed by UUID strings, NOT array of indices. Each value: `{includeAudioEffects: true, includeSends: true, useInstrumentOutput: true, fileName: "name"}`.
- **p.copy()**: Pass `p.copy()` to `OfflineEngineRenderer.start()`, not `p` directly. Upstream pattern from `AudioUnitFreeze.ts`.
- See `references/export-pipeline-fixes.md` for the full bug chain.

### get_full_project_state() → str
- Returns project snapshot: bpm, duration, AU list with tracks, effects, sends.
- Track region/clip counts accessed via `t.box.regions.pointerHub.incoming()` — NOT `t.regions.collection.asArray()` (track adapter doesn't have `.regions.collection`).

## Common pitfalls

1. Hardcoding `unit_index=0` — output bus is always index 0. Instruments start at 1.
2. Passing PPQN values where beats are expected — `create_note`, `create_track_region`, `add_automation`, `add_marker` all use beats.
3. Passing hex colors for hue — `create_track_region` expects 0-360 integer.
4. Passing numeric volume — `set_track_volume` expects string.
5. Wrong arg order in `create_note` — track_index is first, unit_index is last.
6. Passing objects to `add_automation` — points must be `[[pos, val], ...]` arrays, NOT `[{"position": 0, "value": 0.5}]` dicts.
7. Passing int to `create_send`/`set_vaporisateur_osc_param` — `src_unit` and `osc_index` are STRINGS. Use `str(uid)`.
8. Calling `create_audio_bus` before `create_send` — `create_send` auto-creates the FX bus. Don't double-create.
9. Calling `start_engine()` before `export_stems()` — causes "Already connected". Export uses OfflineEngineRenderer with `p.copy()`, doesn't need the live engine.
10. Using `au.address.uuid.toString()` for UUID strings — returns comma-separated bytes. Use `window.DAW_UUID.toString(au.address.uuid)`.
11. Using `t.regions.collection.asArray()` on track adapters — track adapter doesn't have `.regions.collection`. Use `t.box.regions.pointerHub.incoming()`.
12. Filtering AUs by `type == 1` (number) — `type.getValue()` returns string `"instrument"`/`"output"`, not 1/0.
