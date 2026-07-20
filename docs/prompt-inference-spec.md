# Prompt inference — songsee → suno package (P4)

Depends on lineage P1 for storing analysis→prompt edges.

**Status: implemented in 1.389.0**

## Goal

`infer_suno_prompt(filename)` → style package + optional lineage `kind=prompt`.

## Module

- `opendaw_mcp/prompt_inference.py` — scoring + packaging
- MCP: `mcp_opendaw_infer_suno_prompt` in `server.py`
- Tests: `tests/test_prompt_inference.py`

## Inputs

- WAV path (exports or absolute) **or** precomputed metrics dict
- optional genre hint (`coldwave`, `folk`, `cloud`, `lofi`, …)
- `compact` (default True) — short vs full Style block
- `record_lineage` — write analysis→prompt edges

## Pipeline

1. detect_bpm + detect_key + analyze_spectrum + analyze_dynamics + LUFS (existing pure-python helpers)
2. map metrics → style tags + negatives (KB packages when available)
3. return:

```json
{
  "success": true,
  "bpm": 110,
  "key": "A minor",
  "style": "[deep husky baritone], darksynth, coldwave, overdriven-bass, gated-snare, 110 BPM, mono-low-end, no-scream",
  "negatives": "no screaming, no shouting, no high-pitched vocals, ...",
  "confidence": 0.72,
  "package_id": "darksynth_coldwave",
  "low_confidence": false,
  "ranking": [{"id": "darksynth_coldwave", "score": 0.81}, ...],
  "analysis": {...}
}
```

4. optional lineage: `kind=analysis` + `op=analyze` → `kind=prompt` + `op=prompt_infer`

## Packages (KB)

| id | BPM prior | Style source |
|----|-----------|--------------|
| `darksynth_coldwave` | 100–125 (110) | `suno/packages/darksynth_coldwave.md` |
| `folk_horror` | 75–105 (90) | `suno/packages/folk_horror.md` |
| `cloud_bedroom` | 68–100 (82) | `suno/packages/cloud_bedroom.md` |

Low package score without hint → generic tags (still no quality-soup hype).

## Acceptance

- [x] pure analysis path works without DAW bridge
- [x] unit tests with fixture metrics → expected tag buckets
- [x] no hallucinated vendor hype; label low-confidence fields
- [x] optional lineage `prompt_infer`

## Kanban

`t_7d93062d`
