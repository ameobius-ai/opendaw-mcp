# Bridge Response Contract

This document defines the response schema for all opendaw-mcp tools.
Agents and clients can use these contracts to validate tool responses.

## Response envelope

Every tool returns a JSON string. Two variants:

### Success
```json
{
  "success": true,
  ...tool-specific fields
}
```

### Error
```json
{
  "error": "<message>",
  "error_code": "<CODE>",       // optional, see error codes below
  "hint": "<actionable hint>"   // optional
}
```

## Error codes

| Code | Description | When |
|---|---|---|
| `BRIDGE_ERROR` | Bridge communication failed | Playwright timeout, page crash |
| `NOT_FOUND` | Entity not found | Invalid track/unit/region index |
| `INVALID_PARAMETER` | Bad parameter value | Out-of-range pitch, negative beat |
| `TIMEOUT` | Operation exceeded time limit | Render with complex project |

## Tool response schemas

### Read-only tools (readOnlyHint=True)

#### get_full_project_state / get_project_info
```typescript
{
  tracks: Array<{
    index: number
    name: string
    type: "audio" | "note" | "synth"
    volume: number    // 0-1
    panning: number   // -1 to 1
    muted: boolean
    solo: boolean
  }>
  bpm: number
  duration_beats: number
  sample_rate: number
}
```

#### list_tracks / list_note_regions / list_audio_regions / list_effects
```typescript
{
  items: Array<{
    index: number
    name: string
    [key: string]: any   // tool-specific
  }>
  count: number
}
```

#### read_meter
```typescript
{
  peak_db: number
  rms_db: number
  lufs: number
  crest_factor: number
}
```

### Write tools

#### create_synth_track / create_instrument_track
```typescript
{
  success: true
  unit_index: number
  track_index: number
  unit_name: string
}
```

#### create_note
```typescript
{
  success: true
  note_id: number
  pitch: number
  start_beat: number
  duration_beats: number
}
```

#### set_bpm / set_track_volume / set_track_panning
```typescript
{
  success: true
  previous_value: any
  new_value: any
}
```

### Destructive tools (destructiveHint=True)

#### delete_track / delete_note / delete_region
```typescript
{
  success: true
  deleted_index: number
}
```

### Render tools

#### render_full
```typescript
{
  success: true
  filename: string
  sample_rate: number
  samples: number
  duration_seconds: number
  max_sample: number      // peak amplitude 0-1
  channels: number
}
```

#### export_stems
```typescript
{
  success: true
  stems: Array<{
    track_name: string
    filename: string
    samples: number
  }>
  count: number
}
```

## Validation rules

1. **All responses are JSON strings** (not objects)
2. **success=true** indicates the operation completed
3. **error present** means failure — check error_code for category
4. **max_sample < 0.01** likely indicates silence (render bug)
5. **NaN/Inf in any numeric field** indicates DSP crash
6. **samples < 44100** indicates render too short (< 1s at 44.1kHz)
