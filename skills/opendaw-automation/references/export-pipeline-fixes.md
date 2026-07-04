# export_stems Pipeline Fixes (2026-07-03)

Three critical bugs in `export_stems` prevented WAV generation. All fixed in commit `4c6b465`.

## Bug 1: UUID Format

**Symptom**: "Invalid UUID format (0)" or "Invalid UUID format (244,80,80,114,229,239,64,166,...)"

**Cause**: `au.address.uuid.toString()` returns comma-separated byte array string like `"244,80,80,114,229,239,64,166,147,82,111,59,139,49,144,40"`. The `uuid` field on a box is a `Uint8Array`-like object, and its native `toString()` joins elements with commas.

**Fix**: Use `window.DAW_UUID.toString(au.address.uuid)` which formats as proper UUID string: `"94f4dbdd-711e-4c31-88af-9bf51546873c"`.

```js
// WRONG
uuid: au.address.uuid.toString()  // → "244,80,80,114,..."

// RIGHT
uuid: window.DAW_UUID.toString(au.address.uuid)  // → "94f4dbdd-..."
```

This applies to ALL places where box UUIDs are extracted for use in string-keyed maps or external APIs.

## Bug 2: ExportConfiguration Format

**Symptom**: "Invalid UUID format (0)" — OfflineEngineRenderer tries to `UUID.parse("0")` on the stems key.

**Cause**: Code passed `stems` as an array of AU indices: `[1]`. But `ExportConfiguration.stems` is `Record<string, ExportStemConfiguration>` — an object where keys are UUID strings and values are config objects.

**Upstream definition** (from `EngineProcessorAttachment.ts`):
```typescript
export type ExportStemConfiguration = {
    includeAudioEffects: boolean
    includeSends: boolean
    useInstrumentOutput: boolean
    skipChannelStrip?: boolean
    fileName: string
}

export type ExportConfiguration = {
    stems?: Record<string, ExportStemConfiguration>  // keyed by UUID string
    range?: ExportRange
}
```

**Fix**: Build a dict in Python, pass as JSON object:
```python
stems_map[u['uuid']] = {
    "includeAudioEffects": True,
    "includeSends": True,
    "useInstrumentOutput": True,
    "fileName": u.get('name', f"stem_{u['index']}")
}
stems_js = json.dumps(stems_map)  # → {"uuid1": {...}, "uuid2": {...}}
```

## Bug 3: p.copy() Required

**Symptom**: "Already connected" error when calling export_stems after start_engine().

**Cause**: `OfflineEngineRenderer.start()` expects a COPIED project, not the live `p` object. Passing `p` directly connects to the live engine graph, which is already connected if `start_engine()` was called.

**Upstream pattern** (from `AudioUnitFreeze.ts` line 79):
```typescript
const copiedProject = this.#project.copy()
const renderResult = await OfflineEngineRenderer.start(
    copiedProject, Option.wrap(exportConfig), progress, abortController.signal, engine.sampleRate
)
```

**Fix**:
```js
const copiedProject = p.copy();
const audioData = await OfflineEngineRenderer.start(
    copiedProject, Option.wrap(exportConfig), progress, undefined, sample_rate
);
```

**Important**: Do NOT call `start_engine()` before `export_stems()`. The offline renderer creates its own engine context from the copied project. `start_engine()` + `export_stems()` = "Already connected".

## Result After Fixes

```json
{
  "success": true,
  "frames\": 2,           // stereo
  "samples\": 132192,      // ~2.75 seconds @ 48kHz (4-beat chord)
  "max_sample\": 0.877,    // AUDIO CONFIRMED — non-silent
  "size\": 11520044,       // ~11.5MB WAV (full export was 30s)
  "sample_rate\": 48000
}
```

**RESOLVED**: The silent render (max_sample=0) was caused by `create_note` creating a new NoteRegionBox per note call, resulting in overlapping regions that OfflineEngineRenderer couldn't render. Fixed by making `create_note` accumulate notes in a single region. See `references/create-note-region-fix.md` for the full root cause analysis.

## get_full_project_state Fix (same session)

**Symptom**: "Cannot read properties of undefined (reading 'asArray')" when calling `get_full_project_state`.

**Cause**: Track adapter objects (`t`) from `au.tracks.collection.adapters()` don't have `.regions.collection` — that property is on the BOX, not the adapter. The code used `t.regions.collection.asArray()` which failed.

**Fix**: Use `t.box.regions.pointerHub.incoming()` and `t.box.clips.pointerHub.incoming()`:
```js
tracks: tracks.map(t => {
    const tbox = t.box;
    const regCount = [...tbox.regions.pointerHub.incoming()].length;
    const clipCount = [...tbox.clips.pointerHub.incoming()].length;
    return { type: ..., region_count: regCount, clip_count: clipCount };
})
```

## Also Fixed: AU Type Filter

`au.type.getValue()` returns string `"instrument"` / `"output"`, NOT numeric 1/0. The Python filter was:
```python
if u.get('type') == 1:  # NEVER matches because type is "instrument" string
```

Fixed to:
```python
if u.get('type') == 1 or u.get('type') == 'instrument':
```

## Known: export_single_stem likely has same bugs

`export_single_stem` (line ~4747) uses `stems_config = json.dumps([unit_index])` — the same array-of-indices format that was broken in `export_stems`. It also passes `p` directly instead of `p.copy()`. These bugs were NOT fixed in this session — only `export_stems` was patched. If `export_single_stem` is needed, apply the same three fixes:
1. Use `window.DAW_UUID.toString(au.address.uuid)` for UUID extraction
2. Build `Record<uuid, ExportStemConfiguration>` dict instead of `[unit_index]` array
3. Pass `p.copy()` to `OfflineEngineRenderer.start()`
