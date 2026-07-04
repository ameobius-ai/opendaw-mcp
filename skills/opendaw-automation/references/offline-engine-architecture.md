# openDAW Offline Engine Architecture (traced July 2026)

Deep-dive into the offline render path. Read this before debugging offline render issues or contributing upstream fixes to the render engine.

## Render Path (top to bottom)

```
OfflineEngineRenderer.start()        (studio-core, main thread)
  → OfflineEngineRenderer.create()   (spawns Worker, sets up MessageChannel)
    → protocol.initialize(port, config)   → offline-engine-main.ts (Worker)
      → setupWorkletGlobals({sampleRate})
      → import(processorsUrl)             → loads EngineProcessor
      → new EngineProcessor({processorOptions})
        → ProjectSkeleton.decode(project) → BoxGraph
        → BlockRenderer(context)          → creates audio blocks
        → AudioUnit instances             → AudioDeviceChain → effect processors
  → engineCommands.play()                → timeInfo.transporting = true
  → protocol.render(config)              → offline-engine-main.ts render loop
    → engine.processor.process([[]], outputs)  per RenderQuantum chunk
      → EngineProcessor.render()
        → notifier.notify(ProcessPhase.Before)  ← sidechain resolution happens here
        → BlockRenderer.process(procedure)
          → creates Block[] with flags = transporting|playing
          → procedure({blocks}) → processors.forEach(p => p.process(processInfo))
            → AudioProcessor.process({blocks})
              → for each block: split at UpdateEvent boundaries → processAudio(chunk)
```

## Key Files

| File | Role |
|------|------|
| `packages/studio/core/src/OfflineEngineRenderer.ts` | Main-thread orchestrator. Spawns Worker, sets up EngineToClient callbacks (fetchAudio, fetchSoundfont), calls play() + render(). |
| `packages/studio/core-workers/src/offline-engine-main.ts` | Worker entry point. Implements OfflineEngineProtocol: initialize, addModule, step, render, stop. The render loop calls `engine.processor.process()` per RenderQuantum. |
| `packages/studio/core-workers/src/worklet-env.ts` | Polyfill for AudioWorkletProcessor in Worker context. Sets globalThis.sampleRate, currentFrame, currentTime. |
| `packages/studio/core-processors/src/EngineProcessor.ts` | The engine. Inherits AudioWorkletProcessor. Implements EngineContext. render() → BlockRenderer.process() → processors.forEach(process). Fires ProcessPhase.Before/After. |
| `packages/studio/core-processors/src/BlockRenderer.ts` | Creates Block[] from timeInfo. When transporting=true: splits RenderQuantum into sub-blocks at loop/marker/tempo/callback boundaries. Each block gets flags=BlockFlags.create(transporting, discontinuous, playing, bpmChanged). When NOT transporting: single block with flags=0 (all false). |
| `packages/studio/core-processors/src/processing.ts` | Block/BlockFlag/ProcessPhase definitions. BlockFlag: transporting=1, discontinuous=2, playing=4, bpmChanged=8. eventMask = discontinuous|bpmChanged. |
| `packages/studio/core-processors/src/AudioProcessor.ts` | Splits blocks at UpdateEvent boundaries. Mutable chunk copy with sliding s0/s1/p0/p1. Clears eventMask flags after first chunk. Calls processAudio(chunk) per sub-chunk. |

## Block Flag Flow

```
BlockRenderer.process()
  ├─ transporting=true  → blocks with flags = transporting|playing (or transporting alone if counting in)
  └─ transporting=false → single block, flags=0 (NO transporting, NO playing)
```

**Processors that check flags:**
- `TidalDeviceProcessor.processAudio({p0, s0, s1, bpm, flags})` — phase advances only if `Bits.every(flags, BlockFlag.transporting | BlockFlag.playing)`. But the tremolo gain computation runs regardless of flags — it uses `p0` (block position) and `bpm`, not the phase. **If transporting=false, audio still passes through with tremolo applied**, only the phase tracking variable stops updating.
- `DelayDeviceProcessor` — reads `bpm` and `flags` for sync
- `VaporisateurDeviceProcessor` — reads full block

## Sidechain Resolution (Compressor)

Compressor sidechain connects via `ProcessPhase.Before` subscription:
```typescript
context.subscribeProcessPhase(phase => {
    if (phase === ProcessPhase.Before && this.#needsSideChainResolution) {
        // resolve sideChain.targetVertex → audioOutputBufferRegistry → registerEdge
    }
})
```
`ProcessPhase.Before` fires at the START of every `EngineProcessor.render()` call. In offline mode, this fires every RenderQuantum chunk. **Sidechain resolution works in offline mode** as long as the EngineProcessor is constructed properly (which it is via the Worker path).

AudioDeviceChain wiring also uses ProcessPhase.Before:
```typescript
context.subscribeProcessPhase(phase => {
    if (phase === ProcessPhase.Before && this.#needsWiring) {
        this.#wire()  // connect effects, aux sends, channel strip, output
    }
})
```

## Critical Insight: "Offline Bugs" Were Likely Bridge Issues

Our reported bugs (Tidal silence, Waveshaper dead, Compressor sidechain broken in offline render) are **NOT reproducible in the core engine**:

1. **Tidal**: `processAudio` applies tremolo from `p0` and `bpm` regardless of transport flags. Only phase tracking stops when not transporting. Audio flows through.
2. **Waveshaper**: `processAudio({s0, s1})` doesn't check flags at all. It processes source → gain → waveshape → mix. If source is empty (`#source.isEmpty()`), it returns early. **The issue is likely source wiring, not the processor.**
3. **Compressor**: Sidechain resolves via ProcessPhase.Before which fires every chunk. If sidechain target is set, it connects. If not, it uses input signal as sidechain (default).

**Root cause hypothesis**: Our headless Playwright bridge constructs the project differently than the normal UI path. The AudioDeviceChain wiring (`#wire()`) depends on `ProcessPhase.Before` + `#needsWiring` flag, which is set when effects are added via `catchupAndSubscribe`. If our bridge adds effects after the engine is already running (or in a different order), wiring may not trigger correctly.

**Debugging approach for future sessions**:
- Check if `AudioDeviceChain.#needsWiring` is true when render starts
- Check if `AudioUnit.input()` returns a valid processor (not empty Option)
- Check if `context.registerEdge()` was called for the effect chain
- The audio graph is a `Graph<Processor>` with `TopologicalSort` — if edges are missing, processors run but produce silence (no input source connected)

## block-fix.md — ALREADY IMPLEMENTED

André wrote a plan (`plans/block-fix.md`) for fixing per-chunk block state. The fix is **already in the current code**:
- `AudioProcessor` uses `Object.assign(this.#chunk, block)` for mutable copy
- Sliding window: `chunk.s0 = toIndex`, `chunk.p0 = event.position` after each event
- Event flag clearing: `chunk.flags &= ~BlockFlag.eventMask` after first chunk
- All 22 processors use `block.s0`/`block.s1` (not separate fromIndex/toIndex params)

Do NOT submit a PR for this — it's already done.

## Upstream Sync — VERIFIED PROCEDURE (July 2026)

Our fork (`AMEOBIUS/openDAW`) was synced to upstream on 2026-07-02 (162 commits, fast-forward, zero conflicts). PR branch `fix/delay-dsp-lazy-init` rebased onto fresh main and force-pushed.

### Sync procedure

```bash
git fetch upstream
git rev-list --count main..upstream/main   # how far behind
git checkout main && git merge --ff-only upstream/main
git checkout fix/delay-dsp-lazy-init && git rebase main
git push origin fix/delay-dsp-lazy-init --force-with-lease
```

**Conflict pre-check**: `git diff main...<branch> --name-only` then compare against `git log main..upstream/main --name-only -- <those files>`. If upstream didn't touch our files, rebase is clean.

### Regression testing WITHOUT npm install

`npm install` is forbidden. `node_modules/` in openDAW repo is empty. **Use the MCP bridge as the test stand** — headless-daw has its own `node_modules/` with vite:

```bash
cd headless-daw && node node_modules/.bin/vite --port 5174  # background
cd opendaw-mcp && source venv/bin/activate
```

Bridge API gotchas:
- `evaluate(script)` wraps as `async () => { return await (script)(); }` — pass arrow functions, NOT bare expressions
- `start()` takes NO args, `stop()` closes browser (not `terminate()`)
- Bridge waits for `window.DAW` (not `DAW_project`) + `DAW_EffectFactories` + `DAW_InstrumentFactories`
- All box mutations MUST be inside `p.editing.modify(() => { ... })` or get `Modification only prohibited in transaction mode`

**Regression checklist** (run after every sync):
1. Bridge starts → `DAW engine ready!`
2. `list_tracks` → returns units with correct structure
3. `createNoteTrack` via `editing.modify()` → track created
4. `createInstrument(IF.Vaporisateur)` via `editing.modify()` → instrument attached
5. `insertEffect(au.audioEffects, EF.Delay)` via `editing.modify()` → effect added

### Upstream changes observed (post-sync July 2026)

- **Maximizer is now default on Output unit** — fresh projects start with MaximizerDeviceBox. MCP tools counting effects should expect this.
- **Scriptable devices**: Apparat, Spielwerk, Werkstatt — new instrument types with Rust WASM crates. `DAW_ApparatDeviceBox` available as window global. `DAW_WerkstattParameterBox` and `DAW_WerkstattSampleBox` also available (added to headless-daw globals July 2026).
- **block-fix.md** plan is fully implemented in current code.
- **Tempo rendering fixes** at timeline edges.
- **New effects**: StereoTool, Waveshaper, Vocoder, NeuralAmp (Tone3000 NAM). All work via existing `add_effect`/`set_effect_parameter` MCP tools. NeuralAmp model loading requires popup flow (unavailable in headless).

## Contribution Strategy

1. **PR #280** (Delay DSP lazy init) — awaiting review. Pinged 2026-07-02.
2. **No AI-generated issues** — André closed #278/#281/#282 with "Please do not submit AI generated issues." Only submit real code fixes as small focused PRs.
3. **README rule**: "Keep pull requests small and focused. Large PRs will not be reviewed"
4. **Communication tone**: Short, human, code-focused. "gentle ping, is there anything to change?" — not multi-paragraph AI writeups.
5. **Fresh territory**: Scriptable devices (Apparat/Spielwerk/Werkstatt) are new code with tests but coverage may have gaps. Good area for contribution.
6. **Test contributions**: André values tests (many test files in repo). Writing tests for offline render edge cases would be valuable.
