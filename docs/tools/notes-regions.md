# Notes & Regions

48 tools for MIDI notes, note regions, and audio regions.

## Notes (11)

| Tool | Description |
|------|-------------|
| `create_note` | Create a MIDI note on a note track |
| `delete_note` | Delete a single note from a region |
| `duplicate_note_event` | Duplicate a note event with optional position/pitch offset |
| `duplicate_notes` | Duplicate all notes within a region, shifting after the last |
| `find_overlapping_notes` | Find notes overlapping a given pitch and time range |
| `get_note_range` | Get pitch range and max duration of notes in a region |
| `list_notes` | List all note events within a region |
| `quantize_notes` | Quantize note positions to a grid division |
| `set_note_advanced` | Set advanced note properties — chance, cent, playCount, playCurve |
| `set_note_properties` | Edit properties of a single note within a region |
| `transpose_notes` | Transpose all notes by a number of semitones |

### Note properties

Notes use PPQN positioning (`PPQN.Quarter = 960`). Pitch is MIDI standard (60 = C4).

| Property | Range | Default |
|----------|-------|---------|
| position | PPQN (0, 960, 1920...) | required |
| pitch | 0–127 (60 = C4) | required |
| duration | PPQN (960 = quarter) | required |
| velocity | 0.0–1.0 | 0.787 |
| cent | cents (0 = no detune) | 0 |
| chance | 0–100 (% play probability) | 100 |
| playCount | 1–16 (repeats) | 1 |

## Note Editing (2)

| Tool | Description |
|------|-------------|
| `consolidate_note` | Consolidate a repeated note (playCount > 1) into individual notes |
| `flatten_note_regions` | Merge multiple overlapping note regions into one |

## Regions (20)

| Tool | Description |
|------|-------------|
| `consolidate_region` | Make a region's event collection unique (not shared/mirrored) |
| `list_note_regions` | List all note regions with position, duration, and note count |
| `copy_region_fades` | Copy fade in/out settings from one audio region to another |
| `copy_region_to_track` | Copy a region to a different track (or same track at new position) |
| `create_track_region` | Create a region on any track (note or value) via generic API |
| `delete_audio_region` | Delete an audio region from the timeline |
| `delete_note_region` | Delete a note region from the timeline |
| `delete_region` | Delete a region from a track |
| `duplicate_note_region` | Duplicate a note region to a new position |
| `duplicate_region` | Duplicate any region (audio, note, or value) via DAW's duplicateRegion |
| `get_region_info` | Detailed info about a region — position, duration, loop, mute, content |
| `move_region_content` | Shift content start of a region without moving the region |
| `move_region_to_track` | Move a region from one track to another (possibly different AU) |
| `set_region_color` | Set the color (hue) of a region or clip |
| `set_region_duration` | Set the duration of a region |
| `set_region_label` | Rename a region's label (display name) |
| `set_region_loop` | Set loop parameters for a note region |
| `set_region_mute` | Mute or unmute a specific region |
| `set_region_position` | Move a region to a new position on the timeline |
| `transfer_region` | Transfer/copy a region to another track at a specific position |

## Audio Regions (8)

| Tool | Description |
|------|-------------|
| `get_audio_file_info` | Get metadata about the audio file referenced by an audio region |
| `get_region_play_mode` | Get play mode — stretch type, playback rate, cents, transient mode |
| `list_audio_regions` | List all audio regions with file name, position, and duration |
| `place_audio_region` | Place a previously loaded audio sample as a region on a track |
| `set_audio_region_fade` | Set fade in/out on an audio region |
| `set_audio_region_gain` | Set gain (in dB) on an audio region |
| `set_audio_region_time_base` | Set the time base of an audio region |
| `set_audio_region_waveform_offset` | Set waveform display offset of an audio region |

## Audio Stretch & Warp (7)

| Tool | Description |
|------|-------------|
| `create_pitch_stretched_region` | Place a pitch-stretched audio region on a track |
| `create_time_stretched_region` | Place a time-stretched audio region on a track |
| `create_warp_marker` | Add a warp marker to a time/pitch-stretched audio region |
| `delete_warp_marker` | Delete a warp marker from a time/pitch-stretched region |
| `list_transient_markers` | List transient markers for an audio region's audio file |
| `list_warp_markers` | List warp markers on a time/pitch-stretched audio region |
| `update_warp_marker` | Update a warp marker's position and/or seconds value |
