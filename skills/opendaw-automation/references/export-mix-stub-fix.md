# export_mix stub fix + Maximizer field audit (2026-07-03)

## export_mix — was a stub

### Discovery
During a stub audit (`grep "Not yet|not implemented|not reconstructed"` returned 0 results), found `export_mix` by checking tools that return metadata-only results without producing files.

`export_mix` only computed project duration via `lastRegionAction()` + clip/event iteration and returned `{duration, lastPos, bpm}` — it never called `OfflineEngineRenderer`.

### Fix
Replaced 60-line stub with one-line delegate:
```python
async def mcp_opendaw_export_mix(filename, sample_rate=48000, method="offline"):
    return await mcp_opendaw_render_full(filename, sample_rate)
```

The `method` parameter ('offline'/'realtime'/'auto') is accepted for backward compat but always uses offline rendering.

### E2E
- 865KB WAV, 108128 samples, max_sample=0.531, stereo, 48kHz ✅

### Lesson
When auditing for stubs, don't just grep for error strings. Check tools that:
- Return only metadata (duration, bpm, position) without producing files
- Don't modify project state
- Have "method" or "mode" parameters that are accepted but never branched on
These are often unimplemented placeholders from the .pyc recovery era.

## Maximizer field audit

### MaximizerDeviceBox fields
| Field # | Name | Type | Default | Constraints |
|---------|------|------|---------|-------------|
| 1 | host | PointerField | — | AudioEffectHost |
| 2 | index | Int32Field | — | — |
| 3 | label | StringField | — | — |
| 4 | enabled | BooleanField | true | — |
| 5 | minimized | BooleanField | false | — |
| 10 | lookahead | BooleanField | true | — |
| 11 | threshold | Float32Field | 0 | min -30, max 0, linear, dB |

### No ceiling field
There is NO separate `ceiling` or `output_gain` parameter. The `threshold` IS the ceiling — it controls both the limiting point and the makeup gain:
- Lower threshold = more gain reduction = louder output (peaks capped at 0dB)
- Higher threshold (toward 0) = less gain reduction = quieter output

### Adapter mapping
`MaximizerDeviceBoxAdapter` wraps threshold with `ValueMapping.linear(-24.0, 0.0)` and `StringMapping.decible`. The box field allows -30..0 but the adapter maps -24..0.

### True peak targeting
For true peak targeting below 0dB (e.g. -1 dBTP for streaming):
1. Set Maximizer threshold to control loudness
2. Lower output AU volume (in dB) after Maximizer to pull peaks below target
3. Use `measure_lufs` to verify both LUFS and true peak

### Source files
- `packages/studio/boxes/src/MaximizerDeviceBox.ts` — box definition
- `packages/studio/adapters/src/devices/audio-effects/MaximizerDeviceBoxAdapter.ts` — adapter
