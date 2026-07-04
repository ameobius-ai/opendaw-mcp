# New Tools 169-172 — Musical Grid, Signature, Fades

## Tools added

### ppqn_to_parts (169)
Converts PPQN position to musical parts (bars/beats/semiquavers/ticks) with time signature awareness.

**API path:** `p.rootBoxAdapter.timeline.signatureTrack.toParts(position)`
Returns `{bars, beats, semiquavers, ticks}` + `signatureAt(position)` for active time signature.

### get_bar_interval (170)
Returns bar boundaries (start/end/length in PPQN) for a given position.

**API path:**
- `sigTrack.getBarInterval(position)` -> `{position: start, complete: end}`
- `sigTrack.barLengthAt(position)` -> bar length in PPQN

### move_signature_event (171)
Moves a time signature change to a new PPQN position. Auto-recalculates relative positions of subsequent events.

**API path:** `sigTrack.adapterAt(index)` -> `Option<SignatureEventBoxAdapter>`, then `sigTrack.moveEvent(adapter, targetPpqn)` inside `editing.modify()`.

### copy_region_fades (172)
Copies fadeIn/fadeOut/fadeInSlope/fadeOutSlope from one audio region's Fading object to another.

**API path:** `region.fading.fadeIn.getValue()` / `.setValue()` — Fading is an ObjectField on AudioRegionBox.

## Key access patterns

### SignatureTrackAdapter access
```
p.rootBoxAdapter.timeline.signatureTrack
```
- `.toParts(ppqn)` -> `{bars, beats, semiquavers, ticks}`
- `.getBarInterval(ppqn)` -> `{position, complete}` (bar start/end)
- `.barLengthAt(ppqn)` -> ppqn (bar length)
- `.signatureAt(ppqn)` -> `[nominator, denominator]`
- `.adapterAt(index)` -> `Option<SignatureEventBoxAdapter>`
- `.moveEvent(adapter, targetPpqn)` — requires `editing.modify()`
- `.createEvent(position, nominator, denominator)` — requires `editing.modify()`
- `.deleteAdapter(adapter)` — requires `editing.modify()`

### Fading access
```
region.fading.fadeIn        // Float32Field
region.fading.fadeOut       // Float32Field
region.fading.fadeInSlope   // Float32Field
region.fading.fadeOutSlope  // Float32Field
```
Audio regions only. Note/value regions don't have `.fading`.

## Test results (E2E)
- `ppqn_to_parts(1920)` -> `{bars: 0, beats: 2, semiquavers: 0, ticks: 0, time_signature: [4, 4]}`
- `get_bar_interval(1920)` -> `{bar_start: 0, bar_end: 3840, bar_length: 3840, time_signature: [4, 4]}`
  - 3840 = 4 beats x 960 PPQN/beat (PPQN.Quarter = 960)
- `move_signature_event(99)` -> `{error: "No signature event at index 99"}` (error handling)
- `copy_region_fades(0,0,0,0,0,0)` -> `{error: "No track 0 on AU 0"}` (error handling)

## Remaining adapter coverage (kanban t_12620486)
- `PlayfieldSampleBoxAdapter.copyToIndex(index)` — copy drum pad sample
- `NoteEventBoxAdapter.copyAsNoteEvent()` — duplicate note event
- `NeuralAmpModelBoxAdapter.getModelJson()` — read NAM model JSON
- `TransientMarkerBoxAdapter` — list/read transient markers
- `SignatureTrackAdapter.deleteAdapter()` — delete signature event
- `get_signature_events()` — list all signature changes with positions
