# AU Sorting + Render Pipeline Fixes (2026-07-03)

## Problem 1: AU pointerHub.incoming() unordered

`pointerHub.incoming()` returns AudioUnitBox objects in INSERTION ORDER, not sorted by `index` field. `DAW_HELPERS.au(i)` uses `adapters()` which sorts by index — but 80+ tools accessed AUs via raw `pointerHub.incoming()` without sorting.

**Symptom**: `units[1]` returns undefined or wrong AU. `create_note(unit_index=1)` fails with "Cannot read properties of undefined (reading 'tracks')".

**Fix**: All 80+ occurrences of:
```js
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);
```
Changed to:
```js
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
```

Applied via `patch(mode='replace', replace_all=true)` — single operation fixing all 80+ sites.

**Commits**: `a68d501` (sorting fix), `f52a974` (create_note + export_single_stem + render_range)

## Problem 2: export_single_stem triple bug

Same 3 bugs as export_stems (already fixed in prior session):
1. UUID: `au.address.uuid.toString()` → byte array. Fix: `window.DAW_UUID.toString(au.address.uuid)`
2. ExportConfiguration: `[unit_index]` array → `Record<uuid, ExportStemConfiguration>` object
3. Project: `p` (live) → `p.copy()` (copied)

## Problem 3: render_range was stub

`render_range` only returned BPM — no actual rendering. Rewrote to use `OfflineEngineRenderer.start()` with `ExportConfiguration.range = {start: ppqn, end: ppqn}`.

```js
const exportConfig = { range: { start: startPos, end: endPos } };
const copiedProject = p.copy();
const audioData = await OfflineEngineRenderer.start(
    copiedProject, Option.wrap(exportConfig), progress, undefined, sampleRate
);
```

## New tool: render_full (#209)

Full mixdown — simplest render call:
```js
const audioData = await OfflineEngineRenderer.start(
    p.copy(), Option.None, progress, undefined, sampleRate
);
```

`Option.None` → `countStems` returns 1 → full mix (all AUs summed into stereo).

## E2E verification

```
create_synth_track → create_note ×3 → render_range(0,4) → export_stems → export_single_stem → render_full
```

All produce audio:
- render_range: max_sample=0.531, 865KB WAV
- export_stems: max_sample=0.486, 865KB WAV  
- export_single_stem: max_sample=0.486, 865KB WAV
- render_full: max_sample=0.531, 865KB WAV

## OfflineEngineRenderer API reference

```typescript
static async start(
    source: Project,           // MUST be p.copy(), not live p
    optExportConfiguration: Option<ExportConfiguration>,
    progress: DefaultObservableValue<number>,
    abortSignal?: AbortSignal,
    sampleRate: int = 48000
): Promise<AudioData>
```

`ExportConfiguration`:
```typescript
{
    stems?: Record<string, ExportStemConfiguration>,  // keyed by UUID string
    range?: ExportRange  // "full" | {start: ppqn, end: ppqn}
}
```

`ExportStemConfiguration`:
```typescript
{
    includeAudioEffects?: boolean,
    includeSends?: boolean,
    useInstrumentOutput?: boolean,
    skipChannelStrip?: boolean,
    fileName: string
}
```

`AudioData`:
```typescript
{
    frames: Float32Array[],  // one per channel (2 for stereo)
    sampleRate: int
}
```

## WAV saving pattern

JS side:
```js
const wav = WavFile.encodeFloats(audioData);
const bytes = new Uint8Array(wav);
let binary = "";
for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
window.__lastExportB64 = btoa(binary);
```

Python side:
```python
b64 = await bridge.evaluate("() => window.__lastExportB64")
wav_bytes = base64.b64decode(b64)
filepath = os.path.join(export_dir, f"{safe_name}.wav")
with open(filepath, "wb") as f:
    f.write(wav_bytes)
```
