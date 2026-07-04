# PR #280 — andremichelle Discussion + OfflineEngineRenderer Architecture (2026-07-03)

## Breakthrough: andremichelle replied

After 2 days of silence, André responded to PR #280 with: "What is wrong with OfflineEngineRenderer.ts?"

This implies he thinks the fix might belong in the renderer, not in `DelayDeviceDsp.ts`.

## OfflineEngineRenderer Worker Architecture (key insight)

### How the offline engine works:

```
Main Thread                    Worker (offline-engine-main.ts)
─────────────                  ──────────────────────────────
OfflineEngineRenderer          setupWorkletGlobals({sampleRate: 48000})
  .create(project, ...)   →    ← sets globalThis.sampleRate = 48000
  .start(...)                   await import(config.processorsUrl)
                                ← processor modules load WITH sampleRate set
                                new ProcessorClass({...})
                                ← FilterMapping evaluates correctly here
```

**Critical sequence in `offline-engine-main.ts` (line 21-24):**
```typescript
async initialize(enginePort, config) {
    setupWorkletGlobals({sampleRate: config.sampleRate})  // ← FIRST
    globals.__workletPort__ = enginePort
    await import(config.processorsUrl)                     // ← THEN import
    // ... processor modules load with sampleRate already = 48000
}
```

`setupWorkletGlobals()` (worklet-env.ts) sets `globalThis.sampleRate = config.sampleRate` BEFORE `import(config.processorsUrl)`. So when `DelayDeviceDsp`'s `static readonly FilterMapping` initializer runs during module import, `sampleRate` is already 48000.

### Why the crash happens on main thread:

When `import("@opendaw/studio-core")` is called in headless-daw's `main.ts`, the bundler eagerly evaluates the full module graph including `@opendaw/studio-core-processors` → `DelayDeviceDsp.ts`. At that point:
- No AudioContext exists on the main thread
- `globalThis.sampleRate` is `0` (or undefined)
- `static readonly FilterMapping = ValueMapping.exponential(20.0/sampleRate, 20000.0/sampleRate)` → division by zero → `NaN` or crash

The worker is isolated — its `sampleRate` global is set by `setupWorkletGlobals` before any processor import. The main-thread import is the problem.

### Our reply to André:

Explained that the crash is on the **main thread** (import-time), not in the worker. The worker correctly sets `sampleRate` before importing processors. But `import("@opendaw/studio-core")` on the main thread transitively loads `DelayDeviceDsp`, where `sampleRate=0`.

Offered to adjust approach if he prefers a different fix (e.g., deferring main-thread import, making `sampleRate` safe in non-audio contexts).

### Status: andremichelle's verdict (Jul 3)

André responded: "Sounds like a misconfig in the bundler, and maybe there are more locations popping up where your setup could break."

He's right — the root cause is our headless setup importing device processors on the main thread where `sampleRate` hasn't been set. In the normal browser flow, processors are only imported inside the audio worklet context where `sampleRate` is already configured via `setupWorkletGlobals`.

We replied acknowledging this is our setup issue, not an upstream bug. The lazy-init in PR #280 is a defensive guard for that edge case. Offered to close the PR if he prefers.

**Status**: PR #280 CLOSED (2026-07-03). André's final verdict: "Please close this. As I said, I suspect more issues popping up after 'fixing' this one. It is better to fix your bundler. The main thread should not be polluted with unused/unnecessary JavaScript."

We closed the PR with: "You're right, Andre — this is a bundler issue on our side, not an upstream bug. The main thread shouldn't be importing device processors. Closing this PR. Thanks for the explanation 🦀"

**Lesson**: Do not open PRs against andremichelle/openDAW for headless-setup-specific issues. He considers them our bundler problem, not upstream bugs. The lazy-init guard was correct defensively but rejected as upstream policy. Future headless issues should be fixed locally in headless-daw, not submitted upstream. The correct fix is to configure the bundler to not eagerly import `@opendaw/studio-core-processors` on the main thread — device processors should only load inside the audio worklet context where `setupWorkletGlobals` has already set `sampleRate`.

## Upstream files examined

- `packages/studio/core/src/OfflineEngineRenderer.ts` (355 lines) — `create()`, `start()`, worker lifecycle, script device loading
- `packages/studio/core-workers/src/offline-engine-main.ts` (121 lines) — worker entry: `initialize()`, `step()`, `render()`
- `packages/studio/core-workers/src/worklet-env.ts` (34 lines) — `setupWorkletGlobals()`, `AudioWorkletProcessor` stub, `updateFrameTime()`

## Upstream effects audit (same session)

Researched Vocoder, Waveshaper, AudioUnitFreeze, ClipboardUtils/BoxGraphCopy — all either already covered by MCP tools or not applicable:

- **Vocoder** (`EffectFactories.AudioNamed.Vocoder`): carrierMinFreq, carrierMaxFreq, modulatorMinFreq, modulatorMaxFreq, qMin, qMax, envAttack, envRelease, gain, mix + sideChain + modulatorMode. Fully accessible via `add_effect` + `set_effect_parameter` + `set_effect_string_parameter`.
- **Waveshaper** (`EffectFactories.AudioNamed.Waveshaper`): inputGain (0-40 dB), outputGain (-24 to +24 dB), mix (0-1), equation (string). Same — fully accessible via existing tools.
- **ClipboardUtils/BoxGraphCopy**: pure serialization (`serializeBoxes`/`deserializeBoxes`). ClipboardManager is UI-layer. Copy/paste covered by `transfer_audiounit` + `export_preset`/`import_preset`.

## v1.5.0 Published

- 211 MCP tools (freeze/unfreeze + export fixes)
- Docker: `ghcr.io/ameobius/opendaw-mcp:1.5.0` ✅
- MCP Registry: `io.github.AMEOBIUS/opendaw-mcp@1.5.0` ✅
- GitHub Release v1.5.0 ✅
- CI threshold bumped to ≥210
