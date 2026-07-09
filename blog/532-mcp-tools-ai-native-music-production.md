---
title: "532 MCP Tools for AI-Native Music Production"
published: false
description: "How I built the largest MCP server for music production — 532 tools controlling a browser-based DAW through AI agents"
tags: mcp, ai, music, audio
cover_image: https://github.com/aaameobius-crypto/opendaw-mcp/raw/main/assets/social-preview.png
---

## The pitch

What if your AI agent could produce music? Not "generate a song from a prompt" — actually *produce*: lay down tracks, dial in compressors, write MIDI, route effects, mix, master, export stems.

That's what **[opendaw-mcp](https://github.com/aaameobius-crypto/opendaw-mcp)** does. **532 MCP tools** that give any LLM agent full control of [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation.

```bash
pip install opendaw-mcp
```

## Why?

AI music tools fall into two camps:

1. **End-to-end generators** (Suno, Udio) — amazing output, zero control. You get a track. You can't tweak the bass.
2. **Plugin wrappers** (Ableton MCP, Reaper MCP) — real control, but locked to a specific DAW and platform.

opendaw-mcp sits in between. A browser-based DAW means no install, no platform lock. 532 tools means granular control — not "make a beat" but "put a kick on beat 1, sidechain the bass at -6dB, add a low-pass filter at 200Hz Q 0.7."

## What's in the box

### 532 tools across 14 categories

| Category | Tools | What you can do |
|----------|-------|-----------------|
| Tracks & Audio Units | 45 | Create synth/audio/MIDI tracks, route, reorder |
| Instruments & Synths | 38 | Tape, Nano, Vaporisateur, Soundfont, MIDI output |
| Effects & MIDI Effects | 52 | Add, reorder, bypass, set parameters |
| Notes & Regions | 67 | Place notes, chords, scales, basslines |
| Clips & Markers | 31 | Loop, reverse, stretch, quantize |
| Mixer & Sends | 24 | Volume, pan, sends, buses |
| Automation | 28 | Write automation curves, value regions |
| Export & Rendering | 19 | Full mix, per-stem, region export, LUFS |
| Scriptable Devices | 15 | Compile custom DSP code in real-time |
| Drums & Modular | 22 | Drum patterns, modular synth patches |
| Stems & Presets | 8 | Stem separation, preset save/load |
| Orchestration | 7 | Song structure, chord progressions, mastering |
| Transport & Project | 12 | Play, stop, tempo, time signature |
| Utility | 84 | Color, rename, duplicate, navigate |

### 134 DSP scripts

Three scriptable device families with real JavaScript DSP compilation:

- **Werkstatt** (103 scripts) — studio-grade effects: compressors, EQs, reverbs, saturators, multiband processors, spectral tools, binaural, vocoder, tape delay, harmonic tremolo...
- **Apparat** (9 scripts) — synth voices: sub bass, cold lead, wavetable, supersaw, pluck, bowed string
- **Spielwerk** (10 scripts) — MIDI processors: arpeggiator, chord generator, scale quantizer, harmonizer, probability gate

Agents can write new DSP code, compile it, and hear the result — all through MCP tool calls.

### 12 Agent Skills

Pre-built workflows that teach agents *how* to produce music:

- `adaptive-mix-mastering` — full mix→master pipeline with decision points
- `suno-to-opendaw` — Suno generation → download → remix in openDAW
- `dsp-script-authoring` — write custom DSP scripts
- `opendaw-automation`, `opendaw-track-architecture`, `opendaw-sound-design`, `opendaw-effect-routing`, `opendaw-genres`
- `coldwave-mix-mastering`, `stem-splitter-local`, `songsee` (audio analysis), `ai-audio-postprocessing`

### Framework integration

Works with LangChain, AutoGen, and CrewAI out of the box. Example files included.

## How it works

```
Agent (LLM) → MCP Protocol → opendaw-mcp server → Playwright → openDAW (Chromium)
```

The MCP server translates tool calls into Playwright browser automation. openDAW runs in a headless Chromium instance — the agent never sees a GUI, just calls tools and gets JSON back.

Rendering uses openDAW's `OfflineEngineRenderer` — same audio engine as the browser DAW, but offline. A 5-minute track renders in ~30 seconds.

## Quick start

```python
from opendaw_mcp.bridge import HeadlessDawBridge
import asyncio

async def main():
    bridge = HeadlessDawBridge()
    await bridge.start()
    
    # Your agent would call these MCP tools:
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_add_effect,
        mcp_opendaw_set_instrument_param,
        mcp_opendaw_render_full,
    )
    
    # Create a synth track
    track = await mcp_opendaw_create_synth_track(name="bass")
    
    # Add a low-pass filter
    fx = await mcp_opendaw_add_effect(
        effect_type="Werkstatt",
        unit_index=track["unit_index"]
    )
    
    # Render
    result = await mcp_opendaw_render_full(filename="my_track")
    print(f"Rendered: {result['path']}")
    
    await bridge.stop()

asyncio.run(main())
```

## The numbers

- **532** MCP tools (533 async functions)
- **134** DSP scripts
- **5,500+** unit + E2E tests
- **12** agent skills
- **681** commits
- **20** releases (v1.0.0 → v1.11.1)
- CI green, Apache-2.0, Python 3.11+

## What's next

- Suno integration pipeline (generate → download → remix → master)
- Real-time audio analysis through `songsee` skill
- More genre templates (techno, DnB, ambient, lofi)
- Collaborative agent workflows (multiple agents on one project)

---

**Links:**
- GitHub: https://github.com/aaameobius-crypto/opendaw-mcp
- PyPI: https://pypi.org/project/opendaw-mcp/
- Docs: https://aaameobius-crypto.github.io/opendaw-mcp/
- MCP Registry: `io.github.aaameobius-crypto/opendaw-mcp`

If you're building AI agents that need to make music — this is your toolkit. ⭐ the repo if it's useful.
