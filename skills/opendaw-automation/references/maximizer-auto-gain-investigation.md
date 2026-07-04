# Maximizer / Auto-Gain Investigation (July 2026)

## Maximizer threshold mapping

`MaximizerDeviceBoxAdapter` wraps `threshold` with `ValueMapping.linear(-24.0, 0.0)`.
Raw 0 → -24 dB, raw 1 → 0 dB. NOT -30..0 (the BoxSchema constraints say min=-30 but the adapter maps -24..0).

## Maximizer in offline render — WORKS CORRECTLY when field gets dB

**Initial test (BUGGY — was passing 0..1 instead of dB):**
- Maximizer threshold "0.75" (= 0.75 dB, nearly no limiting) → max=0.5858 (appeared quieter)
- This was because `setValue(0.75)` set threshold to 0.75 dB, not -6dB as intended

**Corrected test (passing dB directly):**
- threshold=0dB → max=0.6386 (passthrough, ≈baseline 0.6387) ✅
- threshold=-6dB → max=0.9999 (boost! peaks capped at 0dB) ✅
- threshold=-12dB → max=0.9999 (more boost) ✅
- threshold=-24dB → max=0.9999 (max boost) ✅

**Root cause of "quiet" result:** MCP code computed `thresholdRaw = (thresholdDb + 24.0) / 24.0` and passed that to `setValue()`. But field stores dB, so `setValue(0.75)` = 0.75 dB threshold (nearly no limiting). Fix: `setValue(thresholdDb)` directly.

The `headroomGain = dbToGain(-0.001 - threshold)` boosts correctly when threshold is in dB. For threshold=-6dB: headroomGain = dbToGain(5.999) ≈ 2x boost, limiter caps peaks at 0dB.

## RESOLVED: getValue() returns FIELD value (physical units, NOT 0..1)

**Resolution (July 2, session 3):** `AutomatableParameter.getValue()` returns `this.#adapter.getValue()` which is `field.getValue()` — the **stored field value in physical units** (dB, Hz, ms). `getUnitValue()` does the mapping to 0..1 for UI/automation only.

The confusion arose because `MaximizerDeviceBox` schema has `constraints: {min: -30.0, max: 0.0}` — the field stores values in the -30..0 dB range. `ValueMapping.linear(-24.0, 0.0)` in the adapter converts this dB value → 0..1 unitValue for UI sliders.

**The DSP code is CORRECT** — `getValue()` returns dB, `gainToDb(envelope)` returns dB, the subtraction is dimensionally consistent. No bug.

**The bug was in our MCP code** — we were passing `thresholdRaw = (thresholdDb + 24.0) / 24.0` (a 0..1 value) to `maxiBox.threshold.setValue()`, but the field expects dB. Fix: `maxiBox.threshold.setValue(thresholdDb)` directly.

Verified with test: threshold=0dB → max=0.6386 (passthrough), threshold=-6dB → max=0.9999 (boost!), threshold=-12dB → max=0.9999. Maximizer works correctly when field gets dB.

**This applies to ALL effect parameters** — Compressor threshold stores dB, Delay time stores ms/PPQN, Reverb decay stores seconds. `set_effect_parameter` must always pass physical units. See Issue #282.

Key files:
- `packages/studio/core-processors/src/AutomatableParameter.ts` — `getValue()` returns field value (physical units), `getUnitValue()` returns mapped 0..1
- `packages/studio/adapters/src/AutomatableParameterFieldAdapter.ts` — `getValue()` = `field.getValue()`, `getUnitValue()` = `valueMapping.x(fieldValue)`
- `packages/studio/core-processors/src/devices/audio-effects/MaximizerDeviceProcessor.ts` — DSP uses `getValue()` = dB, correct
- `packages/studio/adapters/src/devices/audio-effects/MaximizerDeviceBoxAdapter.ts` — `ValueMapping.linear(-24.0, 0.0)` converts dB→0..1 for UI

## Auto-gain convergence — RESOLVED with Maximizer (July 2 session 3)

With the corrected dB field values, auto_gain converges on ALL signal types:

| Signal type | Start LUFS | Target | Iterations | Maximizer threshold |
|------------|-----------|--------|-----------|-------------------|
| Dense (16 notes, -12dB synth) | -14.7 | -14.0 | 2 | -0.7 dB |
| Sparse (4 notes, -8dB synth) | -19.1 | -14.0 | 2 | -5.1 dB |
| Extreme (2 notes, -20dB synth) | -21.8 | -14.0 | 2 | -7.8 dB |

**Previous convergence issues** were caused by passing 0..1 to threshold field (which expects dB), not by the Maximizer itself. With correct dB values, Maximizer's makeup gain compensates for any amount of quietness.

## Auto-gain Maximizer integration (server.py, CORRECTED July 2 session 3)

When outputAU is at +6dB (max) and `remaining_diff > 0.5`:
1. Add Maximizer to output AU (unit 0) if not already present
2. Set `threshold` **directly in dB**: `maxiBox.threshold.setValue(thresholdDb)` where `thresholdDb = max(-24.0, -abs(remaining_diff))`
3. Enable `lookahead` (boolean true, NOT raw 1)

**CRITICAL**: Do NOT convert to 0..1. Field stores dB. Previous code used `thresholdRaw = (thresholdDb + 24.0) / 24.0` which passed 0.75 for -6dB — wrong, field got 0.75 dB instead of -6 dB.

The Maximizer approach replaces the previous stem-boost method (distributing remaining_diff / sqrt(N) across instrument AUs). Stem boost is no longer needed — Maximizer handles all cases.

## PR #280 — DelayDeviceDsp lazy FilterMapping

Fix for issue #279: static initializer `ValueMapping.exponential(20.0/sampleRate, 20000.0/sampleRate)` crashes with "Exponential is inverse" when sampleRate=0 (Node.js/test contexts). 

Fix: lazy getter with `DEFAULT_SAMPLE_RATE = 48000` fallback. Coderabbit review nitpick (extract constant) applied. Branch: `fix/delay-dsp-lazy-init` on AMEOBIUS/openDAW fork.

## Issue #281 — InstrumentFactories required for headless synth creation

Raw `VaporisateurDeviceBox.create()` without `setInitValue` on oscillator waveforms/volumes produces NaN in the audio buffer → `assertSanity` crash → engine restart → silence. `InstrumentFactories.Vaporisateur.create(graph, host, name, icon)` sets all required init values. This is the root cause of all "silence" bugs in headless mode.
