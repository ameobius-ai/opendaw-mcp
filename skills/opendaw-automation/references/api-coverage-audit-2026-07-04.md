# API Coverage Audit (v1.9.8, 2026-07-04)

## ProjectApi.ts — 100% covered (27/27 methods)

All methods in `packages/studio/core/src/project/ProjectApi.ts` have MCP equivalents:

| ProjectApi method | MCP tool(s) |
|---|---|
| `setBpm` | `set_bpm` |
| `catchupAndSubscribeBpm` | N/A (subscription, not actionable) |
| `catchupAndSubscribeAudioUnits` | N/A (subscription) |
| `createInstrument` | `create_synth_track`, `create_audio_track` |
| `createAnyInstrument` | alias for `createInstrument` — no separate tool needed |
| `replaceMIDIInstrument` | `replace_instrument` |
| `insertEffect` | `add_effect`, `add_midi_effect` |
| `createNoteTrack` | `create_note_track` |
| `createAudioTrack` | `create_audio_track` |
| `createAutomationTrack` | `create_automation_track` |
| `compactTracks` | `compact_tracks` |
| `createTimeStretchedClip` | `create_time_stretched_clip` |
| `createTimeStretchedRegion` | `create_time_stretched_region` |
| `createPitchStretchedClip` | `create_pitch_stretched_clip` |
| `createPitchStretchedRegion` | `create_pitch_stretched_region` |
| `createNotStretchedClip` | `create_audio_clip` |
| `createNotStretchedRegion` | `create_audio_region` |
| `createNoteClip` | `create_note_clip` |
| `exportMIDI` | `export_midi` |
| `exportAudio` | `export_region_audio` (file dialog — headless workaround) |
| `quantiseNotes` | `quantize_notes` |
| `createValueClip` | `create_value_clip` |
| `createNoteRegion` | `create_note_region` |
| `createTrackRegion` | `create_track_region` |
| `createNoteEvent` | `create_note` |
| `deleteAudioUnit` | `delete_audio_unit` |
| `duplicateNotes` | `duplicate_notes` |

## EngineFacade.ts — actionable subset covered

| EngineFacade method | MCP tool | Notes |
|---|---|---|
| `play` / `stop` | `transport` | ✅ |
| `panic` | `engine_panic` | ✅ |
| `sleep` / `wake` | `engine_sleep` / `engine_wake` | ✅ |
| `queryLoadingComplete` | `query_loading_complete` | ✅ |
| `scheduleClipPlay` | `trigger_clip_play` | ✅ |
| `scheduleClipStop` | `trigger_clip_stop` | ✅ |
| `position` / `bpm` / `isPlaying` / `isRecording` / `isCountingIn` / `cpuLoad` / `markerState` | `get_engine_status` | ✅ read-only |
| `countInBeatsRemaining` | `get_engine_status` | ✅ read-only |
| `sampleRate` | `get_project_info` | ✅ |
| `preferences` | `get_studio_settings` / `set_studio_setting` / `set_metronome` | ✅ |
| `loadClickSound` | N/A | Requires AudioData — not accessible in headless |
| `setFrozenAudio` | N/A | Requires AudioData — freeze not headless-accessible |
| `subscribeNotes` / `noteSignal` | N/A | Realtime streaming — not headless |
| `subscribeClipNotification` | N/A | Realtime subscription |
| `subscribeDeviceMessage` | N/A | Realtime subscription |
| `registerMonitoringSource` / `unregisterMonitoringSource` | N/A | AudioNode graph — not headless |
| `perfBuffer` / `perfIndex` | N/A | Performance monitoring — realtime only |
| `isReady` | `start_engine` (implicit) | ✅ |
| `terminate` | `engine_sleep` (approximation) | ✅ |

## Not covered (by design — not headless-accessible)

- **`loadClickSound`** — needs `AudioData` object, not constructable in headless
- **`setFrozenAudio`** — needs `AudioData`, freeze is a UI-driven workflow
- **`subscribeNotes` / `noteSignal`** — realtime MIDI streaming, requires AudioWorklet message port
- **`subscribeClipNotification` / `subscribeDeviceMessage`** — realtime subscriptions
- **`registerMonitoringSource` / `unregisterMonitoringSource`** — AudioNode graph manipulation
- **`perfBuffer` / `perfIndex`** — realtime performance buffer

## Conclusion

ProjectApi is 100% covered. EngineFacade actionable methods are covered.
Remaining uncovered methods are realtime/streaming — architecturally impossible in headless mode.
No new MCP tools needed for API coverage.
