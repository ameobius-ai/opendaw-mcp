# Show HN: opendaw-mcp — 262 MCP tools for agent-native DAW control

## Title (≤80 chars)
Show HN: opendaw-mcp – 262 MCP tools for AI agents to control a browser DAW

## Body

I built **opendaw-mcp**, an MCP (Model Context Protocol) server that gives AI agents full programmatic control over [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation.

**262 MCP tools** cover the entire production pipeline:
- Tracks, instruments (Vaporisateur synth, Playfield sampler, Tape/Nano/Soundfont)
- Effects (Compressor, Delay, Reverb, Maximizer, Waveshaper, Vocoder, NeuralAmp, + scriptable Werkstatt DSP)
- MIDI: note editing, drum patterns, chord progressions, arpeggiators
- Audio: loading, regions, clips, time/pitch stretch, fades
- Mixing: sends, buses, sidechain, automation, LUFS targeting
- Rendering: mix export, per-stem export, offline render
- **Stem splitter**: 7 SOTA open-source models (BS-Roformer, HTDemucs FT, SCNet, MelBand Roformer) running locally on GPU
- **Preset management**: save/load .opb preset bundles — encode any effect chain as a shareable file

**How it works:** A Playwright bridge drives a headless Chromium running openDAW's Vite dev server. The MCP server translates agent calls into DAW box-graph mutations via openDAW's internal API. Everything runs locally — no cloud, no per-call costs.

**Why:** AI music tools (Suno, Udio) generate audio but don't let you *produce* it. opendaw-mcp lets an agent take a generated stem, split it, import into a DAW, build a full arrangement, mix, master, and export — all programmatically. It turns a DAW into an agent-native environment.

**Agent skills:** 5 structured skill files teach agents genre-adaptive workflows — coldwave mixing, techno arrangements, mastering chains. Decision points let the agent adapt to any genre instead of following a rigid script.

**Links:**
- GitHub: https://github.com/AMEOBIUS/opendaw-mcp
- PyPI: https://pypi.org/project/opendaw-mcp/
- MCP Registry: io.github.AMEOBIUS/opendaw-mcp
- 26 DSP scripts (Werkstatt/Apparat/Spielwerk): https://github.com/AMEOBIUS/openDAW/tree/feat/werkstatt-examples/examples

**Tech:** Python 3.11+, Playwright, FastMCP, openDAW (TypeScript/React). 93 unit tests + 6 E2E tests. Apache-2.0.

Happy to answer questions about the architecture, the box-graph system, or how to build MCP tools for complex web apps.
