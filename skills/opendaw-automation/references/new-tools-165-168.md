# New Tools 165-168 — Note Advanced + Device Management

Added in session extending 164→168. All use DAW_HELPERS pattern.

## 165. set_note_advanced(unit_index, track_index, region_index, note_index, chance, cent, play_count, play_curve)

Sets NoteEventBox advanced properties:
- **chance**: 0-100% probability note plays (100 = always)
- **cent**: micro-tuning in cents (-50 to +50, 0 = exact pitch)
- **play_count**: repeats (1-16, 1 = single note)
- **play_curve**: repeat curve (-1 to +1, 0 = even spacing)

Sentinel values: pass -1 for int fields, -999 for float fields to skip (leave unchanged).

JS pattern — conditional field setting:
```python
js_lines = []
if chance >= 0: js_lines.append(f"noteBox.chance.setValue({chance});")
if cent > -999: js_lines.append(f"noteBox.cent.setValue({cent});")
js_body = " ".join(js_lines)
# then: h.modify(() => { {js_body} });
```

Access: `events[note_index].box` → NoteEventBox fields directly (NOT adapter getters).

## 166. consolidate_note(unit_index, track_index, region_index, note_index)

Expands a repeated note (playCount > 1) into N individual notes via playCurve.
- `note.consolidate()` returns array of new NoteEventBoxAdapter
- Original note is deleted
- Each new note has playCount=1, positioned according to curve
- E2E: playCount=4 → 4 notes created, original deleted

**Pitfall**: `note.playCount` is on the adapter (getter), but `consolidate()` must be called inside `editing.modify()`. Result captured via outer `let`:
```js
let created;
h.modify(() => { created = note.consolidate(); });
// created.length = N new notes
```

## 167. set_device_label(unit_index, effect_index, label, is_midi_effect)

Renames an audio or MIDI effect device via `device.labelField.setValue()`.
- `au.audioEffects.adapters()` for audio chain
- `au.midiEffects.adapters()` for MIDI chain
- `is_midi_effect` boolean selects chain

## 168. get_device_chain_detail(unit_index)

Full device chain inspection in one call:
- **instrument**: `au.input.adapter()` → label, type (constructor.name), enabled
- **audio_effects**: index, label, type, enabled, minimized
- **midi_effects**: index, label, type, enabled

```js
const input = au.input.adapter();
const instrument = input.isEmpty() ? null : {
    label: input.unwrap().labelField.getValue(),
    type: input.unwrap().box.constructor.name,
};
```

## Key API patterns discovered

### NoteEventBox fields (beyond basic)
- `box.chance` — IntField 0-100
- `box.cent` — FloatField -50..+50
- `box.playCount` — IntField 1-16
- `box.playCurve` — IntField -1..+1
- Adapter getters: `note.chance`, `note.cent`, `note.playCount`, `note.playCurve`
- `note.canConsolidate()` → `playCount > 1`
- `note.consolidate()` → expands to N notes, deletes original

### DeviceBoxAdapter interface
- `labelField` — StringField (rename)
- `enabledField` — BooleanField (bypass)
- `minimizedField` — BooleanField (UI collapse)
- `box.constructor.name` — device type string (e.g. "DelayDeviceBox")

### Interpolation types (for automation events)
```js
{type: "none"}     // step/hold
{type: "linear"}   // straight ramp
{type: "curve", slope: 0.0-1.0}  // custom curve (0.5 = linear)
```
Set via: `event.interpolation = interpolationObject`
Read via: `event.interpolation.type` (and `.slope` for curve)

### ValueEventCollectionBoxAdapter.createEvent()
```js
collection.createEvent({
    position: ppqn_val,
    index: 0,
    value: 0.0-1.0,
    interpolation: {type: "linear"}
});
```
If event exists at same position+index, value is updated (no duplicate).
