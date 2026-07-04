# Tracks & Audio Units

21 tools for track and audio unit management.

## Tracks (10)

| Tool | Description |
|------|-------------|
| `compact_tracks` | Remove empty tracks from an audio unit (or all AUs) |
| `create_audio_track` | Create a new audio track on the primary audio unit |
| `create_instrument_track` | Create a new instrument AU with a Tape device and audio track |
| `create_note_track` | Create a new note/MIDI track on an audio unit |
| `create_synth_track` | Create a new instrument AU with a synthesizer and note track |
| `delete_track` | Delete a track — removes all regions, clips, and notes |
| `get_track_info` | Detailed info about a track — type, regions, clips, enabled state |
| `list_tracks` | List all tracks across all AUs with type, effects, and regions |
| `move_track` | Move a track up or down within an audio unit |
| `set_track_enabled` | Enable or disable a track (track mute) |

## Audio Units (11)

| Tool | Description |
|------|-------------|
| `delete_audio_unit` | Delete an entire AU with all tracks, effects, and sends |
| `duplicate_audiounit` | Duplicate an AU with all content: instrument, effects, tracks, regions |
| `freeze_audiounit` | Freeze an AU — pre-render its output offline to save CPU |
| `get_device_chain_detail` | Detailed info about all devices on an AU — instrument, audio/MIDI effects |
| `get_unit_freeze_status` | Check if an AU is frozen and whether it can be frozen |
| `move_audio_unit` | Move an AU up or down in the mixer order |
| `rename_unit` | Rename an AU's instrument and optionally set its icon |
| `replace_from_preset` | Replace an AU's instrument/effects/timeline from a preset |
| `set_unit_minimized` | Minimize or expand an AU in the mixer view |
| `transfer_audiounit` | Transfer/copy an AU within the project |
| `unfreeze_audiounit` | Unfreeze a frozen AU — resume real-time processing |
