# Project & Transport

32 tools for project management, transport control, tempo, time signatures, and groove.

## Project & Info (12)

| Tool | Description |
|------|-------------|
| `get_full_project_state` | Complete snapshot — all AUs, tracks, regions, effects, mixer state |
| `get_project_duration` | Total project duration — end position of last region |
| `get_project_info` | Quick overview: BPM, time signature, track/AU/effect counts, duration |
| `get_project_metadata` | Metadata: creation date, BPM, time signature, AU/track count |
| `get_project_state` | Full state: BPM, sample rate, playing status, track list, effects |
| `get_studio_settings` | All studio preferences (engine, visibility, editing, debug, storage) |
| `load_project` | Load a previously saved project from a `.odaw` file |
| `reset_project` | Reset to fresh state — removes all AUs, tracks, regions, effects |
| `save_project` | Save current project state to a binary file |
| `serialize` | Serialize current project state to JSON |
| `set_studio_setting` | Set a studio preference setting |
| `validate_project` | Check if project is valid — detects overlapping regions |

## Transport (5)

| Tool | Description |
|------|-------------|
| `set_bpm` | Set the project tempo in BPM |
| `set_loop_region` | Set the playback loop region |
| `set_position` | Set the playback position in beats |
| `set_time_signature` | Set the project time signature (4/4, 3/4, 6/8, 7/8) |
| `transport` | Control transport: play, stop, or toggle |

## Tempo & Signature (13)

| Tool | Description |
|------|-------------|
| `add_signature_change` | Add a time signature change at a specific position |
| `add_tempo_change` | Add a tempo (BPM) change at a specific position |
| `change_base_signature` | Change the base time signature of the project |
| `delete_signature_change` | Delete a time signature change from the timeline |
| `get_bar_interval` | Get start and end PPQN of the bar containing a position |
| `get_signature_events` | List all time signature change events |
| `get_tempo_at` | Get BPM at a specific position, accounting for tempo automation |
| `list_signature_changes` | List all time signature changes on the signature track |
| `list_tempo_changes` | List all tempo (BPM) changes on the tempo track |
| `move_signature_event` | Move a time signature change to a new PPQN position |
| `ppqn_to_parts` | Convert PPQN to musical parts: bars, beats, semiquavers, ticks |
| `ppqn_to_seconds` | Convert PPQN position to seconds using the tempo map |
| `seconds_to_beats` | Convert seconds to beats using the tempo map |

## Groove & Tuning (2)

| Tool | Description |
|------|-------------|
| `set_groove_shuffle` | Set groove/shuffle (swing) amount for the project |
| `set_tuning` | Set the A4 base frequency (concert pitch tuning) |
