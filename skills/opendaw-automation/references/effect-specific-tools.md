# Effect-Specific Tool Reference

Details for the 6 effect-specific MCP tools added in v1.9.6–v1.9.7.

## Tidal vs Delay fraction arrays (CRITICAL)

Tidal `rate` and Delay `delayMusical` are both integer indices into fraction arrays, but the arrays DIFFER:

- **Tidal RateFractions**: 17 entries, largest-to-smallest (index 0 = 1/1 whole, index 3 = 1/4, index 16 = 1/128).
- **Delay Fractions**: 21 entries, smallest-to-largest + "off" (index 0 = off, index 1 = 1/128, index 14 = 1/4, index 20 = 1/1).

The same fraction string maps to DIFFERENT indices. `set_tidal_rate` and `set_delay_sync` handle this mapping internally — always use the MCP tools, never raw `set_effect_parameter_int`.

**Module-level constants** (v1.9.7+): `TIDAL_RATE_MAP` and `DELAY_SYNC_MAP` are defined at the top of `server.py` as typed `dict[str, int]` constants, imported by unit tests. See `references/inline-to-module-constants-2026-07-04.md` for the extraction pattern.

Source: naomiaro/opendaw-test documentation/11-effects.md.

## Revamp (Parametric EQ) box field names

Box schema uses kebab-case (`high-pass`, `low-shelf`, `low-bell`, `mid-bell`, `high-bell`, `high-shelf`, `low-pass`), but generated box fields are **camelCase**: `highPass`, `lowShelf`, `lowBell`, `midBell`, `highBell`, `highShelf`, `lowPass`.

Sub-objects have: `enabled` (boolean), `frequency` (float32, 20-20000 Hz exp), `gain` (float32, -24 to 24 dB linear, shelves/bells only), `q` (float32, 0.01-10 exp, bells/LPF only), `order` (int32, 1-4, HPF/LPF only).

## ScriptCompiler @param mappings

Valid mapping tokens: `linear`, `exp`, `int`, `bool`. `unipolar` is NOT a valid explicit mapping — it's the default when only name + value are given (tokens ≤ 2). If you write `// @param gain 0.5 0 1 unipolar`, compilation fails with "unknown mapping 'unipolar'". Use `linear` instead for 0-1 ranges.

## Waveshaper equations

6 transfer functions: `hardclip`, `cubicSoft`, `tanh`, `sigmoid`, `arctan`, `asymmetric`. Equation is a StringField set via dropdown, not automatable. `set_waveshaper_equation` wraps this with validation.

## Crusher crush inversion

Processor inverts crush value internally (`setCrush(1.0 - value)`) then applies `exponential(20, 20000, invertedValue)`. Box value 0.0 = clean (20kHz), 0.25 = AM radio (~3.5kHz), 0.55 = glitchy (~500Hz), 1.0 = inaudible (20Hz).

## Effect-specific tools use box-level access

All effect-specific tools (`set_waveshaper_equation`, `set_crusher_crush`, `set_revamp_filter`, `set_tidal_rate`, `set_delay_sync`, `set_fold_oversampling`, `set_stereo_tool_panning`, `set_crusher_bits`) use `h.auBox(i)` + `h.effectBoxes(au)` for box-level access. This is critical because adapter-level access (`h.au(i).audioEffects.adapters()`) does not see effects created in previous `bridge.evaluate()` calls — Yjs sync doesn't update adapter collections across evaluate boundaries.

## Dry stem export

`export_dry_stem` captures raw instrument output before effects/channel strip via `useInstrumentOutput: True`, `includeAudioEffects: False`. Contrast with `export_single_stem` which routes through channel strip (`useInstrumentOutput: False`) to include effects, sends, volume/pan.
