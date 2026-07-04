# Session Patterns — July 2026 Extension

New patterns verified in the 87→94 tool expansion session.

## InstrumentBox access — CORRECT pattern

`au.input` is a **Field (hook)**, NOT a PointerField. Get InstrumentBox via:
```js
const instBox = [...au.input.pointerHub.incoming()][0].box;
```
DO NOT use `au.input.targetVertex.unwrap()` — `targetVertex` is undefined on Field hooks, throws "Cannot read properties of undefined (reading 'unwrap')".

InstrumentBox has `label` (StringField) and `icon` (StringField). Used by `rename_unit` tool (unit_index >= 1, not output AU).

## TempoTrack BPM automation

TempoTrack uses ValueEventBox with **normalized** values (0..1), not raw BPM. Conversion:
```js
const minBpm = tempoTrack.minBpm.getValue();  // default 60
const maxBpm = tempoTrack.maxBpm.getValue();  // default 240
const normalized = (targetBpm - minBpm) / (maxBpm - minBpm);
```
Pattern:
1. Check if collection exists: `tempoTrack.events.targetVertex.isEmpty()`
2. If empty: `collection = ValueEventCollectionBox.create(boxGraph, UUID.generate()); tempoTrack.events.refer(collection.owners);`
3. If exists: `collection = tempoTrack.events.targetVertex.unwrap().box;`
4. `tempoTrack.enabled.setValue(true);`
5. Create ValueEventBox: `box.events.refer(collection.events); box.position.setValue(ppqn); box.value.setValue(normalized); box.interpolation.setValue(1=linear / 0=hold);`

Tools: `add_tempo_change`, `list_tempo_changes`.

## NoteEventBox fields

- `position` (Int32Field, ppqn ticks)
- `duration` (Int32Field, ppqn ticks, default 240 = quarter note)
- `pitch` (Int32Field, MIDI 0-127, default 60 = C4)
- `velocity` (Float32Field, 0-1, default ~0.787)
- `cent` (Float32Field, cents offset, default 0)
- `chance` (Int32Field, 0-100, default 100)
- `playCount` (Int32Field, default 1)
- `playCurve` (Float32Field, default 0)

Access: `region.events.targetVertex.unwrap().box` → `collection.events.pointerHub.incoming()` → NoteEventBox array.

Tools: `list_notes`, `set_note_properties` (-1=skip per param), `delete_note`.

## Region/clip hue

Regions (NoteRegionBox, AudioRegionBox, ValueRegionBox) and clips (NoteClipBox, AudioClipBox, ValueClipBox) have `hue` (Int32Field, 0-360 HSL). NOT on TrackBox or AudioUnitBox. Set via `region.hue.setValue(240)` inside `editing.modify()`.

Tools: `set_region_color`, `set_clip_properties` (includes hue).

## SignatureEventBox

Fields: `relativePosition` (Int32Field, in **bars** not ppqn), `nominator` (Int32Field), `denominator` (Int32Field). Note: field is spelled `nominator` not `numerator` in the codebase.

Create:
```js
SignatureEventBox.create(boxGraph, UUID.generate(), box => {
    box.events.refer(sigTrack.events);
    box.index.setValue(idx);
    box.relativePosition.setValue(bars);
    box.nominator.setValue(n);
    box.denominator.setValue(d);
});
```

Tools: `add_signature_change`, `list_signature_changes`, `delete_signature_change`.

## Clip CRUD

Clips live on `trackBox.clips` (ClipCollection). Three types: NoteClipBox, AudioClipBox, ValueClipBox. Each has: `index`, `duration`, `mute`, `label`, `hue`, `triggerMode` (loop/reverse/speed).

- `set_clip_properties` — label/hue/mute/duration. Pass empty string for label to skip, -1 for hue/duration, None for mute.
- `delete_clip` — `clips[clipIdx].delete()` inside `editing.modify()`.
- `set_clip_playback` — triggerMode.loop/reverse/speed.

## delete_region

`regions[regionIdx].delete()` inside `editing.modify()`. Works for all region types (note/audio/value). Optional `region_type` filter: note=1, audio=2, value=3 (TrackType enum).

## f-string escaping reminder

ALL JavaScript `{` and `}` inside Python f-strings must be doubled to `{{` and `}}`. This includes object literals, try-catch blocks, and function bodies. A single unescaped `}` causes `SyntaxError: f-string: single '}' is not allowed`.

Common gotcha: `return { success: true };` in an f-string JS block must be `return {{ success: true }};` — the closing `};` needs `}};`.

## New tools added (87→94)

| Tool | Category | Purpose |
|------|----------|---------|
| `add_tempo_change` | tempo | BPM automation point on TempoTrack |
| `list_tempo_changes` | tempo | List tempo events with BPM/interpolation |
| `list_signature_changes` | signature | List time signature events |
| `delete_signature_change` | signature | Remove signature event by index/position |
| `set_region_color` | regions | Set hue (0-360) on regions |
| `list_notes` | notes | List all note events in a region |
| `set_note_properties` | note-edit | Edit single note (position/duration/pitch/velocity/cent/chance) |
| `delete_note` | note-edit | Delete single note by index |
| `delete_region` | regions | Delete region + contents |
| `set_clip_properties` | clips | Set clip label/hue/mute/duration |
| `delete_clip` | clips | Delete clip from track |
| `rename_unit` | tracks | Rename InstrumentBox.label + icon |
