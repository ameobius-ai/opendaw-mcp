# naomiaro/opendaw-test — SDK Documentation Goldmine

**Repo:** https://github.com/naomiaro/opendaw-test (543 commits)
**Author:** Naomi Aro — documents the openDAW SDK extensively

## Why This Matters

This repo is the **most comprehensive independent documentation** of the openDAW SDK. It covers everything our MCP tools touch, with working demo code for each feature area. When our docs or tool behavior diverges from reality, cross-check against naomiaro's docs.

## Documentation Structure (17+ chapters)

### Core Handbook
- **Quick Start** — 5-min "hello, sound" walkthrough
- **Ch. 00** System Architecture — high-level map, package layout, engine threads
- **Ch. 01** Introduction — DAW concepts, OpenDAW architecture
- **Ch. 02** Timing & Tempo — PPQN, BPM, tempo automation, time signatures
- **Ch. 03** AnimationFrame — Observable updates, UI sync
- **Ch. 04** Box System & Reactivity — data model, subscriptions, reactive lifecycle
- **Ch. 05** Samples, Peaks & Looping — audio loading, waveforms, region tiling
- **Ch. 06** Timeline & Rendering — PPQN-to-pixels, grid, playhead, render pipeline
- **Ch. 07** Building a Complete App — full example, mixer groups, routing

### Feature Guides
- **Ch. 08** Recording — audio/MIDI capture, takes, monitoring, live peaks
- **Ch. 09** Editing, Fades & Automation — region editing, clip fades, track automation, comp lanes
- **Ch. 10** Export & Offline Rendering — **most relevant to our render tools**
- **Ch. 11** Effects — effect types, creation, parameters, **Werkstatt**, Tone3000, Waveshaper
- **Ch. 16** MIDI Deep Dive — note creation, hardware capture, MIDI effects
- **Ch. 17** Modular Devices — Apparat/Werkstatt/Spielwerk scripting
- **Ch. 18** Time & Pitch — play modes, warp markers, transients, pitch stretch

### Appendix
- **Ch. 12** Browser Compatibility — COOP/COEP, iframe embedding
- **Ch. 13** Troubleshooting & FAQ
- **Ch. 14** Glossary — 80+ terms
- **Ch. 15** Performance & Debugging

## Key Patterns Confirmed (cross-reference with our tools)

### Export (Ch. 10)
- `AudioOfflineRenderer` is **deprecated** (since studio-core@0.0.93) — use `OfflineEngineRenderer`
- Both take `(project, Option<ExportConfiguration>, progress, abortSignal?, sampleRate?)`
- Stems export: `ExportConfiguration.stems` is `Record<uuid, ExportStemConfiguration>`
- `useInstrumentOutput: false` → channel strip routing (effects, sends, volume/pan in render)
- `useInstrumentOutput: true` → dry instrument signal (for freeze/flatten)
- Stems come back interleaved: `[stem1_L, stem1_R, stem2_L, stem2_R, ...]`
- `WavFile.encodeFloats()` accepts both `AudioBuffer` and `AudioData`
- `encodeInts16()` for 16-bit PCM

### Effects (Ch. 11)
- **16 audio effects**: Compressor, Delay, Reverb, Revamp (EQ), Crusher, Fold, StereoTool, DattorroReverb, Tidal, Maximizer, Gate, Tone3000 (NeuralAmp), Vocoder, Waveshaper, Modular, **Werkstatt**
- **5 MIDI effects**: Arpeggio, Pitch, Velocity, Zeitgeist, **Spielwerk**
- `project.api.insertEffect(au.audioEffects, factory)` — third arg = insertIndex (position in chain)
- `effectBox.enabled` BooleanField = bypass toggle

### Werkstatt (Ch. 11/17)
- Insert at chain position 0 (third arg to `insertEffect`): `insertEffect(au.audioEffects, EffectFactories.Werkstatt, 0)`
- **Compile OUTSIDE `editing.modify()`**: `await compiler.compile(audioContext, project.editing, box, script)` — the compiler calls `editing.modify()` internally
- `@param` declarations → `WerkstattParameterBox` children (automatable)
- Engine validates output: NaN or ±1000 (~60dB) → device silenced

### Recording (Ch. 08)
- `probeDeviceChannels(deviceId)` — getUserMedia stream → `getSettings().channelCount`
- `enumerateOutputDevices()` — excludes "default" device
- `audioBufferToAudioData(audioBuffer)` — browser AudioBuffer → openDAW AudioData (SharedArrayBuffer)

### Project Setup (src/lib/projectSetup.ts)
- `AnimationFrame.start(window)` — **CRITICAL** before any observable work
- `Workers.install(WorkersUrl)` + `AudioWorklets.install(WorkletsUrl)` + `OfflineEngineRenderer.install(OfflineEngineUrl)`
- `Project.new({audioContext, sampleManager, soundfontManager, audioWorklets, sampleService, soundfontService})`
- `project.startAudioWorklet()` then `await project.engine.isReady()`
- `localStorage.removeItem("engine-preferences")` — clear before fresh project
- `SoundfontService` constructor fetches from `api.opendaw.studio` (CORS in dev) — proxy guard pattern if unused

## audio-verify Skill (Claude Code)

naomiaro built a `.claude/skills/audio-verify/SKILL.md` for automated testing:
- Renders warp scenarios via offline engine to WAVs
- Asserts beat alignment numerically via audio-analyzer MCP
- Uses Playwright MCP to navigate to demo pages
- Polls `#verify-state` element for render status
- Calibrated thresholds: locked scenarios 30-46ms median, unaligned 120-180ms
- Pattern: **replace "needs human ears" with numbers**

## SDK Changelogs

`changelogs/` directory — one file per release range. Critical for tracking API changes between SDK versions that affect our MCP tools.

## SDK Upgrade Audit Procedure

From their CLAUDE.md:
1. Bump `@opendaw/studio-sdk` only — sub-packages resolve transitively
2. NEVER install sub-packages as local `file:` references (breaks Cloudflare CI)
3. After upgrade: `rm -rf node_modules/.vite` (dev server pre-bundles old SDK)
4. Audit `documentation/*.md` for stale API signatures
5. Verify SDK exports in `node_modules/@opendaw/*/dist/*.d.ts`
6. SDK version in `node_modules/@opendaw/studio-sdk/package.json`, NOT sub-packages
