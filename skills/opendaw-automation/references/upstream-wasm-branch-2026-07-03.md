# upstream/wasm — Experimental WASM Rewrite (2026-07-03)

## What it is

`upstream/wasm` is andremichelle's experimental branch — a massive WASM-based engine rewrite. 498 files changed, 47,880 insertions vs upstream/main. NOT main, NOT stable, NOT for MCP integration.

## Contents (from `git log upstream/wasm --oneline`)

- Vocoder (incomplete → fixes)
- Soundfont support
- PerformancePage.tsx
- Note sequencer fixes
- Topological sort fixes
- Dattorro reverb fixes
- Fable (storybook?) fixes
- Scriptable devices (already in main, wasm branch extends)
- Tape.od format
- Audio-region playback: time-stretch play-mode + tempo-correct timeline
- Load bundle option
- All devices ported

## plans/wasm-audio/ directory (new in this branch)

Major planning docs: build-order, composite-unification, device-contract, device-engine-interface (778 lines), device-plugins, device-processing, diary, engine-updates, feature-inventory, integration, open-questions, playfield-composite, processor-port-map, sample-disposal, scriptable-devices.

## Key takeaway for future sessions

- **Do NOT sync to upstream/wasm** — it's experimental, not main
- **Do NOT attempt to cover wasm-branch features in MCP tools** — they may not exist in main
- **When upstream fetches show `wasm -> upstream/wasm` updates**, ignore them unless explicitly asked
- **If andremichelle merges wasm → main**, then re-evaluate: the vocoder, soundfont, and performance page would become new MCP tool targets
- **upstream/main static since 2026-06-30** — 10 commits since Jun 25, all bug fixes. No new features.

## How to check

```bash
cd /home/ameobius/projects/creative-studio/agent-daw/openDAW
git fetch upstream
git log upstream/main --oneline -5   # main branch (stable)
git log upstream/wasm --oneline -10  # wasm branch (experimental)
git diff --stat upstream/main..upstream/wasm | tail -5  # size of divergence
```
