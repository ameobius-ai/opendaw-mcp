# New Tools 173-182 — Adapter Coverage + GitHub Publication

## Tools added

### copy_playfield_sample (173)
Duplicates a Playfield drum sample slot with all parameters (mute, solo, pitch, attack, release, sampleStart, sampleEnd, gate, exclude, polyphone) to a new index.

**API path:** `PlayfieldSampleBoxAdapter.copyToIndex(targetIndex)` — creates new PlayfieldSampleBox via `PlayfieldSampleBox.create()`, copies all param fields, refers file+device pointers.

**Access pattern:**
```js
const inst = au.input.adapter().unwrap();
if (!inst.box.constructor.name.includes('Playfield')) return {error: "Not a Playfield"};
const samples = [...inst.box.samples.pointerHub.incoming()];
const sampleAdapter = samples.find(s => s.box.index.getValue() === sampleIndex);
const adapter = p.boxAdapters.adapterFor(sampleAdapter.box, inst.constructor);
p.editing.modify(() => adapter.copyToIndex(targetIndex));
```

### duplicate_note_event (174)
Copies a note event within the same region with optional position/pitch offset. Uses `NoteEventBoxAdapter.copyTo({position, pitch})`.

**API path:** `NoteEventBoxAdapter.copyTo(options)` — creates new NoteEventBox with position/duration/pitch/playCount/velocity/cent/chance. Options: `{position?, duration?, pitch?, playCount?, events?}`.

**Access pattern:**
```js
const events = reg.events.targetVertex.unwrap("events").box;
const noteAdapters = [...events.events.pointerHub.incoming()]
    .map(({box}) => box)
    .sort((a, b) => a.position.getValue() - b.position.getValue());
const adapter = p.boxAdapters.adapterFor(srcBox, p.NoteEventBoxAdapter || class {});
p.editing.modify(() => {
    newAdapter = adapter.copyTo({position: origPos + offset, pitch: origPitch + pitchOffset});
});
```

### get_neuralamp_model (175)
Reads NAM model JSON from a NeuralAmp effect. Returns model size and truncated preview.

**API path:** `NeuralAmpDeviceBoxAdapter.getModelJson()` — delegates to `NeuralAmpModelBoxAdapter.getModelJson()` if model pointer is set, else falls back to `box.modelJson.getValue()`.

**Access pattern:**
```js
const fx = au.audioEffects.adapters();
if (!fxAdapter.getModelJson) return {error: "Effect is not a NeuralAmp"};
const modelJson = fxAdapter.getModelJson();
```

### list_transient_markers (176)
Lists auto-detected transient hit points from an audio region's audio file.

**API path:** `AudioFileBoxAdapter.transients` — `EventCollection<TransientMarkerBoxAdapter>`. Each marker has `.position` (sample offset) and `.uuid`.

**Access pattern:**
```js
const audioContent = reg.audioContent || reg.box.audioContent;
const fileVertex = audioContent.targetVertex || audioContent.file?.targetVertex;
const fileAdapter = p.boxAdapters.adapterFor(fileBox, p.AudioFileBoxAdapter || class {});
const transients = Array.from(fileAdapter.transients.iterate());
```

### get_signature_events (177)
Lists all time signature changes with accumulated PPQN positions and bar counts.

**API path:** `SignatureTrackAdapter.iterateAll()` — generator yielding `{index, accumulatedPpqn, accumulatedBars, nominator, denominator}`. First entry (index=-1) is the base signature.

**Access pattern:**
```js
const sigTrack = p.rootBoxAdapter.timeline.signatureTrack;
const events = Array.from(sigTrack.iterateAll());
// events[0] = base signature (index=-1), events[1+] = changes
```

### delete_signature_event (178)
Deletes a time signature change event. Auto-recalculates subsequent event positions.

**API path:** `SignatureTrackAdapter.deleteAdapter(adapter)` — recalculates relativePosition of all subsequent events to preserve absolute positions.

### change_base_signature (179)
Changes the project's base time signature (default 4/4). Recalculates all existing signature change events.

**API path:** `SignatureTrackAdapter.changeSignature(nominator, denominator)` — sets `signature.nominator/denominator`, then recalculates each event's `relativePosition` to preserve approximate absolute positions.

**Test:** 4/4 → 3/4 → verified via `get_signature_events` → 4/4 back. ✅

### reset_playfield_params (180)
Resets all Playfield drum sample parameters to defaults.

**API path:** `PlayfieldSampleBoxAdapter.resetParameters()` — resets mute, solo, exclude, polyphone, pitch, attack, release, sampleStart, sampleEnd, gate via `.reset()` on each field.

### duplicate_automation_event (181)
Duplicates an automation event within the same region with optional position/value override.

**API path:** `ValueEventBoxAdapter.copyTo({position, value})` — creates new ValueEventBox with position/value/interpolation.

**Access pattern:** Same as duplicate_note_event but with `ValueEventBoxAdapter` and `value` field instead of `pitch`.

**Pitfall:** `value_override` is `Optional[float]` in Python — use `"null" if value_override is None else str(value_override)` to pass through to JS.

### copy_region_to_track (182)
Copies a region (note/audio/automation) to a different track at an optional new position.

**API path:** `RegionBoxAdapter.copyTo({target, position})` — `target` is a `Field<Pointers.RegionCollection>` (i.e., `dstTrack.box.regions`). Creates new region box with all content.

**Access pattern:**
```js
const srcReg = h.region(h.au(srcUnit), h.track(srcUnit, srcTrack), srcRegion);
const dstTrack = h.track(dstUnit, dstTrack);
p.editing.modify(() => {
    newAdapter = srcReg.copyTo({target: dstTrack.box.regions, position: pos});
});
```

## GitHub Publication

Published at https://github.com/AMEOBIUS/opendaw-mcp (Apache-2.0). See `references/packaging-for-github.md` for the full packaging procedure.

**Key steps:**
1. Replace hardcoded paths with env vars (`OPENDAW_HOST_DIR`, `OPENDAW_URL`, `OPENDAW_EXPORT_DIR`, `NODE_BIN_DIR`)
2. Orphan branch to clean git history (0 personal paths, 0 secrets)
3. Remove `test_*.py` from git tracking (contain local paths)
4. LICENSE (Apache-2.0), README.md, requirements.txt
5. `gh repo create` + push

## ProjectApi.ts Coverage

**100% covered** — all 27 methods have MCP equivalents:
- setBpm, catchupAndSubscribeBpm (observable, N/A), catchupAndSubscribeAudioUnits (observable, N/A)
- createAnyInstrument, insertEffect, createNoteTrack, createAudioTrack, createAutomationTrack
- compactTracks, createTimeStretchedClip/Region, createPitchStretchedClip/Region
- createNotStretchedClip/Region, createNoteClip, exportMIDI, exportAudio (file dialog, N/A headless)
- quantiseNotes, createValueClip, createNoteRegion, createTrackRegion, createNoteEvent
- deleteAudioUnit, duplicateNotes

## Remaining adapter coverage (low priority)
- `ValueEventBoxAdapter.copyFrom()` — reverse copy, rarely needed
- `AutomatableParameterFieldAdapter.setPrintValue()` — text-based param setting
- `IndexedBoxAdapterCollection.getAdapterById()` — UUID-based lookup
- `NoteEventBoxAdapter.copyAsNoteEvent()` — returns plain object, not adapter (limited utility for MCP)
