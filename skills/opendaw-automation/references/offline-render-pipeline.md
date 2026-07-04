# openDAW Offline Render Pipeline — Internal Architecture

## Pipeline Chain

```
offline-engine-main.ts (Worker)
  → EngineProcessor.process() / render()
    → BlockRenderer.process() — constructs Block[] with flags
      → AudioProcessor.process() — splits blocks by events
        → DeviceProcessor.processAudio() — per-effect DSP
```

## Key Files

- `packages/studio/core-workers/src/offline-engine-main.ts` — Worker that runs the engine loop
- `packages/studio/core/src/OfflineEngineRenderer.ts` — Main-thread orchestrator, creates Worker + MessageChannel
- `packages/studio/core-processors/src/EngineProcessor.ts` — AudioWorkletProcessor, owns the audio graph
- `packages/studio/core-processors/src/BlockRenderer.ts` — Splits render quantum into blocks, handles loop/marker/tempo
- `packages/studio/core-processors/src/AudioProcessor.ts` — Base class, splits blocks by events, calls processAudio()
- `packages/studio/core-processors/src/processing.ts` — Block/BlockFlag/ProcessPhase definitions
- `packages/studio/core/src/AudioOfflineRenderer.ts` — DEPRECATED, uses OfflineAudioContext directly

## BlockFlag System

```typescript
export const enum BlockFlag {
    transporting = 1 << 0,   // timeInfo.transporting — set by play()
    discontinuous = 1 << 1,  // position leap (loop, marker, seek)
    playing = 1 << 2,        // !timeInfo.isCountingIn
    bpmChanged = 1 << 3,     // tempo automation event
    eventMask = discontinuous | bpmChanged
}
```

`BlockFlags.create(transporting, discontinuous, playing, bpmChanged)` — used by BlockRenderer.

When NOT transporting: `BlockFlags.create(false, false, false, bpmChanged)`.
When transporting: `BlockFlags.create(true, discontinuous, playing, bpmChanged)`.

## OfflineEngineRenderer Flow

1. `OfflineEngineRenderer.start(source, exportConfig, progress, abortSignal, sampleRate)`
2. Disables loop, computes start/end position
3. Creates Worker, MessageChannel, Communicator proxies
4. Loads script devices (Werkstatt/Spielwerk/Apparat)
5. `protocol.initialize(port, config)` — Worker constructs `EngineProcessor`
6. `await renderer.play()` → `engineCommands.play()` (dispatchAndForget) + `queryLoadingComplete()`
7. `protocol.render(config)` → Worker enters render loop
8. Worker: `while (running) { engine.processor.process([[]], outputs) }`
9. Silent-tail detection, chunk collection, final Float32Array[] return

## EngineProcessor.render() Order

```
1. notify(ProcessPhase.Before)     ← sidechain resolution happens here
2. if processQueue empty → rebuild via TopologicalSort
3. renderer.process() → BlockRenderer constructs blocks
4. processors.forEach(p => p.process(processInfo))
5. output to mainOutput / monitoringOutput / stemExports
6. notify(ProcessPhase.After)
7. stateSender.tryWrite() — position/bpm to main thread
```

## Effect Processing — All Unconditional

**DattorroReverb / Revamp**: simplest — `source.channels() → dsp.process() → output.channels()`. No flags, no sidechain, no transport gating. Always works.

**Waveshaper**: `processAudio` reads source, applies inputGain via Ramp, runs `Waveshaper.process(equation)`, mixes wet/dry. All unconditional. hardclip at 0dB inputGain = no-op on sub-0dBFS audio (correct). For distortion: set `inputGain` to +6...+12dB.

**Tidal**: audio loop (lines 99-104) runs unconditionally. `BlockFlag.transporting|playing` check on line 106 ONLY updates `this.#phase` for UI broadcast (`broadcastFloat`). Does NOT gate audio.

**Delay**: `processAudio` runs unconditionally. Uses `bpmChanged` flag to recompute delay time sync, but processes audio regardless.

**Compressor**: Most complex. Sidechain resolution via `ProcessPhase.Before` subscriber. `catchupAndSubscribe` on sidechain pointer → sets `#needsSideChainResolution=true` → resolved on next `ProcessPhase.Before`. The `registerEdge` call invalidates `processQueue` (sets to `Option.None`), but queue is rebuilt at step 2 before processors run. Potential timing issue: if sidechain edge creates a graph cycle, `TopologicalSort` fails → "graph error".

## Parameter Architecture

Effect parameters are `Float32Field` / `StringField` / `BooleanField` on the effect Box.

```
WaveshaperDeviceBox
  ├── equation: StringField (default "hardclip")
  ├── inputGain: Float32Field (0-40 dB, default 0)
  ├── outputGain: Float32Field (-24 to 24 dB, default 0)
  └── mix: Float32Field (unipolar 0-1, default 1)
```

Adapter layer (`WaveshaperDeviceBoxAdapter`) wraps these in `AutomatableParameterFieldAdapter` with:
- `ValueMapping` — maps unitValue (0-1) ↔ actual value (e.g. dB)
- `StringMapping` — display format
- `getValue()` / `setValue(value)` — direct field access
- `getUnitValue()` / `setUnitValue(0-1)` — mapped access

Set parameters: `p.editing.modify(() => { effectBox.inputGain.setValue(12.0) })`

## July 2 Bug Audit — False Positives

Initial diagnosis (July 1) claimed Waveshaper/Tidal/Delay were "broken in offline render". Deep code audit (July 2) proved this wrong:

| Effect | July 1 claim | July 2 reality |
|--------|-------------|----------------|
| Waveshaper | "silently skipped by offline engine" | DSP runs unconditionally; 0dB inputGain = no-op on sub-0dBFS audio (correct) |
| Tidal | "produces silence" | Audio loop unconditional; flags check only for UI phase |
| Delay | "no effect" | Processes unconditionally; parameter API was missing |
| Compressor | "sidechain broken" | ProcessPhase.Before fires correctly; potential graph cycle is separate issue |

**Root cause of all symptoms**: MCP server had `add_effect` but no `set_effect_parameter`. Effects were created with defaults and couldn't be changed.

## Contributing to Upstream

- Fork: `AMEOBIUS/openDAW` (github.com/AMEOBIUS/openDAW)
- Upstream: `andremichelle/openDAW` (github.com/andremichelle/openDAW)
- AGPL v3, README says "Keep pull requests small and focused"
- Issue #125 "Offline audio-engine renderer in worker" — andremichelle acknowledges offline needs work
- Issue #192 "waveshaper" — feature request for waveshaper device
- Real contribution opportunities: headless SDK agent-facing API, offline render test infrastructure, effect parameter documentation
