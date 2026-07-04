# openDAW Offline Effect "Bugs" — CORRECTED July 2, 2026

## TL;DR: These are NOT bugs

Previous analysis (July 1) hypothesized that Waveshaper, Tidal, Compressor, and Delay were broken in offline render. After reading the full render pipeline source code, **all four are NOT bugs**. The real problem was our MCP server lacking effect parameter control API.

## Corrected Analysis

### Waveshaper — NOT A BUG
- `WaveshaperDeviceProcessor.processAudio()` reads source, applies inputGain via Ramp, runs `Waveshaper.process()`, mixes wet/dry. All correct.
- `hardclip` clips at ±1.0. If audio is below 0dBFS (typical), NO samples exceed 1.0, so hardclip does NOTHING.
- **Fix: set inputGain > 0dB** (e.g. +12dB to +18dB) to push samples above 1.0, then hardclip clips them.
- The DSP math in `waveshaper.ts` (hardclip, tanh, sigmoid, arctan, cubicSoft, asymmetric) is all correct.

### Tidal — NOT A BUG
- `TidalDeviceProcessor.processAudio()` audio loop (lines 99-104) runs **unconditionally** — no transport gating.
- The `BlockFlag.transporting | BlockFlag.playing` check on line 106 only affects the **UI phase display** (`this.#phase` for `broadcastFloat`), NOT audio processing.
- `TidalComputer.compute()` with default params (depth=1.0, slope=0.0, symmetry=0.0) returns a full-depth tremolo. This IS audible.
- If silence occurred, likely causes: depth=0 parameter, or effect not wired into the audio chain.

### Delay — NOT A BUG
- `DelayDeviceProcessor.processAudio()` does NOT gate on transport flags. Processes unconditionally.
- `readAllParameters()` in constructor sets `#updateDelayTime=true`, so first block sets correct delay time.
- BPM is passed in the Block and is correct during offline render.

### Compressor — NOT A BUG (ProcessPhase timing is correct)
- `ProcessPhase.Before` fires on line 371 of `EngineProcessor.render()`.
- Then `processQueue` is checked/rebuilt on lines 372-374.
- If sidechain `registerEdge` invalidates queue (sets `#processQueue = Option.None`), the queue IS rebuilt on line 372-374 BEFORE `processors` is used on line 381.
- So the ordering is: `notify(Before)` → sidechain resolves → queue invalidated → queue rebuilt → processors run. This is correct.

## What Actually Works in Offline Render (ALL effects)
- **DattorroReverb** — source → process → output. Simple. ✓
- **Revamp (EQ)** — biquad stack, no transport dependency. ✓
- **Waveshaper** — works IF inputGain is set high enough. ✓
- **Tidal** — works unconditionally. ✓
- **Delay** — works unconditionally. ✓
- **Compressor** — works, sidechain resolves via ProcessPhase.Before. ✓
- **Volume/Pan** — trivial. ✓

## The Real Problem: Missing MCP Parameter API

Our `opendaw-mcp/server.py` had `mcp_opendaw_add_effect` which added effects with **default parameters** and no way to change them. Effects appeared "broken" because:
- Waveshaper default: inputGain=0dB → hardclip does nothing
- Tidal default: depth=0.75 → should work, but maybe wasn't wired into chain
- Delay default: wet=-6dB, dry=0dB → should work

**Solution**: Added 5 new MCP tools (see `references/effect-parameter-reference.md`):
- `mcp_opendaw_list_effect_parameters`
- `mcp_opendaw_set_effect_parameter`
- `mcp_opendaw_set_effect_parameter_string`
- `mcp_opendaw_remove_effect`
- `mcp_opendaw_get_effect_chain`

All tested and verified working (July 2, 2026).

## Source File Map (for reference)

| File | Path | Role |
|------|------|------|
| WaveshaperDeviceProcessor | `packages/studio/core-processors/src/devices/audio-effects/` | Effect processor — CORRECT |
| waveshaper.ts | `packages/lib/dsp/src/` | DSP math — CORRECT |
| TidalDeviceProcessor | `packages/studio/core-processors/src/devices/audio-effects/` | Tremolo — CORRECT (audio not gated) |
| CompressorDeviceProcessor | `packages/studio/core-processors/src/devices/audio-effects/` | Compressor — CORRECT |
| DelayDeviceProcessor | `packages/studio/core-processors/src/devices/audio-effects/` | Delay — CORRECT |
| AudioProcessor | `packages/studio/core-processors/src/` | Base class — block splitting |
| EngineProcessor | `packages/studio/core-processors/src/` | AudioWorkletProcessor impl |
| BlockRenderer | `packages/studio/core-processors/src/` | Block construction with flags |
| offline-engine-main.ts | `packages/studio/core-workers/src/` | Worker that runs offline render loop |
| OfflineEngineRenderer | `packages/studio/core/src/` | Main thread orchestration |

## Upstream Context

- GitHub issue #125 "Offline audio-engine renderer in worker" — andremichelle acknowledges offline needs work, but DSP effects themselves are functional.
- Fork: `AMEOBIUS/openDAW` — created for potential contributions.
- Contribution opportunity: headless SDK gaps that block agent usage (parameter control, effect chain manipulation), not DSP bug fixes.
