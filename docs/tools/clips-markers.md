# Clips & Markers

22 tools for session view clips, clip launcher, and timeline markers.

## Clips (16)

| Tool | Description |
|------|-------------|
| `clone_clip` | Clone a clip (note or value) on the same track, optionally consolidate |
| `consolidate_clip` | Make a clip's event collection unique (not shared/mirrored) |
| `create_audio_clip` | Create an audio clip in the session view (clip launcher) |
| `create_note_clip` | Create a note clip in the session view (clip launcher) |
| `create_pitch_stretched_clip` | Create a pitch-stretched audio clip in session view |
| `create_time_stretched_clip` | Create a time-stretched audio clip in session view |
| `create_value_clip` | Create a value clip (automation clip) on an automation track |
| `delete_clip` | Delete a clip from a track (session view) |
| `list_clips` | List clips (session view / clip launcher) on tracks |
| `schedule_clip_play` | Schedule clips to play in session view (live triggering) |
| `schedule_clip_stop` | Schedule clips to stop on specified tracks |
| `set_clip_hue` | Set the color (hue) of a clip in the session view |
| `set_clip_label` | Set the label (name) of a clip in the session view |
| `set_clip_mute` | Mute or unmute a clip in the session view |
| `set_clip_playback` | Set clip playback parameters (loop, reverse, speed) |
| `set_clip_properties` | Set properties on a clip: label, color, mute, duration |

### Clip playback parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| loop | bool | Loop the clip |
| reverse | bool | Play in reverse |
| speed | float | Playback speed ratio |
| quantise | int | Quantize setting for triggering |

## Markers (6)

| Tool | Description |
|------|-------------|
| `add_marker` | Add a timeline marker at a position |
| `delete_marker` | Delete a timeline marker by index |
| `list_markers` | List all timeline markers with positions and labels |
| `set_marker_label` | Rename a timeline marker |
| `set_marker_position` | Move a timeline marker to a new position |
| `set_marker_repeat` | Set repeat count on a marker (0=infinite, 1-16=N repeats) |

### Example: song structure

```python
# Create arrangement markers
await server.mcp_opendaw_create_song_structure(
    sections=[
        {"name": "Intro",   "length": 8},
        {"name": "Verse 1", "length": 16},
        {"name": "Chorus",  "length": 16},
        {"name": "Verse 2", "length": 16},
        {"name": "Chorus",  "length": 16},
        {"name": "Outro",   "length": 8},
    ]
)
```

### Marker repeat

`set_marker_repeat` with 0 = infinite loop, 1 = play once, 2-16 = play N times.
Useful for live performance looping via the clip launcher.
