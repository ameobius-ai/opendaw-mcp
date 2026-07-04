# PianoMode Tools (193-194)

## PianoModeAdapter

Location: `packages/studio/adapters/src/PianoModeAdapter.ts`

Access: `p.rootBoxAdapter.pianoMode` — returns `PianoModeAdapter` instance.

## Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `keyboard` | FieldAdapter<int> | 88, 76, 61, 49 | Piano keyboard size |
| `timeRangeInQuarters` | FieldAdapter<float> | 1-64 (exponential) | Visible time range in quarter notes |
| `noteScale` | FieldAdapter<float> | 0.5-2.0 (exponential) | Vertical note scale factor |
| `noteLabels` | FieldAdapter<boolean> | true/false | Show note names (C, D, E...) |
| `transpose` | FieldAdapter<int> | -48 to +48 | Global transpose in semitones |

## Access pattern

```javascript
const pm = p.rootBoxAdapter.pianoMode;
// Read
const t = pm.transpose.getValue();           // 0
const kb = pm.keyboard.getValue();           // 88
// Write (inside editing.modify)
p.editing.modify(() => {
    pm.transpose.field.setValue(7);          // transpose up a 5th
});
```

## MCP tools

### `set_transpose(semitones: int)` — tool #193
- Range: -48 to +48 (validated in Python before JS injection)
- Uses `pm.transpose.field.setValue(val)` inside `editing.modify()`
- Returns `{success, old_transpose, new_transpose}`
- E2E verified: 0→7, then 0→-5

### `get_piano_mode()` — tool #194
- Returns `{keyboard, time_range_in_quarters, note_scale, note_labels, transpose}`
- Read-only, no `editing.modify()` needed
- E2E verified: keyboard=88, time_range=8, note_scale=1, note_labels=false, transpose=0

## Notes

- PianoMode is **UI state** — it does NOT affect audio playback. Transpose changes the piano roll display, not the actual pitches.
- The adapter wraps `PianoMode` box which lives on `RootBox.pianoMode`.
- `ValueMapping.exponential(1, 64)` for timeRange — values are in quarter notes.
- `ValueMapping.linearInteger(-48, 48)` for transpose — semitone steps.
