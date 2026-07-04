# Export Stems WAV Save + num_stems Fix — 2026-07-03

## Problem

`export_stems` returned `num_stems: null` and never saved a WAV file to disk.
`export_single_stem` also never saved a WAV file.
`export_mix` was a stub that only computed duration.

All 3 tools returned audio metadata (max_sample, size, sample_rate) but either
had wrong field access (`Record.length`) or were missing the base64 round-trip
that `render_full` and `render_range` already had.

## Root Causes

### 1. `num_stems: null` — Record.length doesn't exist

```js
// BUG: stemsConfig is Record<string, ExportStemConfiguration>, not an array
num_stems: stemsConfig.length  // → undefined → null in JSON

// FIX:
num_stems: Object.keys(stemsConfig).length  // → 1 (correct)
```

### 2. Missing WAV save block

`render_full` had this pattern (pattern #46 in SKILL.md):
```python
if isinstance(result, dict) and result.get("success"):
    import base64 as b64mod
    export_dir = os.environ.get("OPENDAW_EXPORT_DIR", ...)
    os.makedirs(export_dir, exist_ok=True)
    b64 = await bridge.evaluate("() => window.__lastExportB64")
    if isinstance(b64, str) and b64:
        wav_bytes = b64mod.b64decode(b64)
        filepath = os.path.join(export_dir, f"{safe_name}.wav")
        with open(filepath, "wb") as f:
            f.write(wav_bytes)
        result["filepath"] = filepath
        result["file_size_mb"] = round(os.path.getsize(filepath) / (1024*1024), 2)
```

`export_stems` and `export_single_stem` were missing this entirely.

### 3. `export_mix` was a stub

Only computed project duration via `lastRegionAction()` + clip/event iteration.
Never called `OfflineEngineRenderer`. Fixed by delegating to `render_full()`.

## Fix Applied

- `export_stems`: `Object.keys(stemsConfig).length` + added save block with `filename_prefix` → `{prefix}_stems.wav`
- `export_single_stem`: added save block with `safe_name` → `{name}.wav`
- `export_mix`: delegates to `render_full(filename, sample_rate)`

## E2E Results

- `export_stems`: num_stems=1, filepath saved, 0.82MB WAV, max_sample=0.486 ✅
- `export_single_stem`: filepath saved, max_sample=0.486 ✅
- `export_mix`: 865KB WAV, max_sample=0.531 ✅

## Audit Heuristic

If an export tool returns `success: true` with `max_sample`/`size` but no
`filepath`/`file_size_mb` field, it's missing the save block. All 5 export
tools must save WAV files to `OPENDAW_EXPORT_DIR`.
