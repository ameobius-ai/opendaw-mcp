# Social Promotion Posts — opendaw-mcp

Готовые посты. Копируй и вставляй.

---

## Hacker News (Show HN)

**Title:** Show HN: openDAW MCP — 250 tools for AI agents to control a browser-based DAW

**Body:**

I built an MCP server that lets AI agents (Claude, GPT, Hermes) create and manipulate music projects programmatically — tracks, instruments, effects, MIDI, automation, stem export, and custom DSP devices.

It wraps openDAW (a browser-based DAW by André Michelle) behind the Model Context Protocol. The server launches a headless Chromium instance with openDAW loaded, then communicates via Playwright `page.evaluate()` calls into the DAW's V8 context. Every tool performs real operations on a live project — no stubs, no mocks.

**250 tools cover:**
- Track & region CRUD, 6 instrument types (polysynth, drum machine, sampler, tape, soundfont, MIDI)
- 10+ audio effects (delay, reverb, compressor, EQ, saturation, waveshaper, vocoder, neural amp, maximizer)
- Scriptable DSP devices — write JS code that compiles to AudioWorklet (Apparat/Werkstatt/Spielwerk)
- Offline stem export with LUFS targeting, full mix render
- Modular synth system, MIDI effects, automation, warp markers
- DawProject interop (cross-DAW with Bitwig/Ableton)

**Links:**
- GitHub: https://github.com/AMEOBIUS/opendaw-mcp
- PyPI: `pip install opendaw-mcp`
- MCP Registry: io.github.AMEOBIUS/opendaw-mcp
- Docker: `ghcr.io/ameobius/opendaw-mcp:1.9.8`

Apache-2.0, 54 unit tests, CI green.

---

## Reddit r/MCP

**Title:** 250 MCP tools for agent-native DAW control — openDAW MCP

**Body:**

Built an MCP server that gives AI agents full control over openDAW (browser-based DAW). 250 tools — tracks, instruments, effects, MIDI, automation, stem export, scriptable DSP devices, modular synth, warp markers, DawProject interop.

Agents can create complete music projects from scratch: synth bass + drum beat + lead with arpeggiator + reverb sends + mastering chain → render to WAV with LUFS targeting.

Real operations via Playwright bridge into the DAW's V8 context. No stubs.

- GitHub: https://github.com/AMEOBIUS/opendaw-mcp
- PyPI: `pip install opendaw-mcp`
- Published to MCP Registry + Smithery + Glama
- Apache-2.0

---

## Reddit r/WeAreTheMusicMakers

**Title:** AI agents can now produce music in a browser DAW — 250 MCP tools for openDAW

**Body:**

I built an MCP (Model Context Protocol) server that lets AI agents like Claude and GPT control openDAW — a browser-based DAW — programmatically.

Think of it as "code-driven music production": an AI agent can create tracks, add synths, program MIDI, chain effects, set up sends, automate parameters, and render stems — all through 250 structured tool calls.

The cool part: it includes scriptable DSP devices where you write JavaScript that compiles to AudioWorklet processors in real-time. Tape saturation, wavefolding, bitcrushing — all from code.

Use cases:
- AI-assisted music production (agent as co-producer)
- Procedural music generation with full DAW control
- Batch rendering with LUFS targeting for streaming
- Cross-DAW workflow via DawProject export (Bitwig/Ableton compatible)

- GitHub: https://github.com/AMEOBIUS/opendaw-mcp
- `pip install opendaw-mcp`
- Apache-2.0, open source

---

## Twitter/X

openDAW MCP: 250 tools for AI agents to control a browser-based DAW.

Tracks, instruments, effects, MIDI, automation, stem export, scriptable DSP devices — all via Model Context Protocol.

`pip install opendaw-mcp`
https://github.com/AMEOBIUS/opendaw-mcp

#MCP #AI #MusicProduction #OpenSource

---

## Reddit r/LocalLLaMA

**Title:** 250 MCP tools for agent-native music production — works with any MCP-compatible LLM

**Body:**

Built an MCP server for openDAW (browser DAW) that exposes 250 tools to any MCP-compatible agent — Claude, GPT, Hermes, local LLMs with MCP support.

The server runs a headless Chromium with openDAW loaded, and agents communicate through structured tool calls via Playwright bridge. Everything is local — no cloud API, no per-call costs.

Includes scriptable DSP devices (write JS → compiles to AudioWorklet), offline stem export with LUFS targeting, modular synth, and DawProject interop for Bitwig/Ableton.

- GitHub: https://github.com/AMEOBIUS/opendaw-mcp
- `pip install opendaw-mcp`
- Docker: `ghcr.io/ameobius/opendaw-mcp:1.9.8`
- Apache-2.0
