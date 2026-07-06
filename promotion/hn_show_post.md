# Show HN: opendaw-mcp — 520 MCP tools for agent-native DAW control

## Title (≤80 chars)
Show HN: opendaw-mcp – 520 MCP tools for AI agents to produce music in a browser DAW

## Body

I built **opendaw-mcp**, an MCP (Model Context Protocol) server that gives AI agents full programmatic control over [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation.

**520 MCP tools** cover the entire production pipeline:
- Tracks, instruments (Vaporisateur synth, Playfield sampler, Tape/Nano/Soundfont)
- Effects (Compressor, Delay, Reverb, Maximizer, Waveshaper, Vocoder, NeuralAmp, + scriptable Werkstatt DSP)
- MIDI: note editing, drum patterns, chord progressions, arpeggiators, descants, counter-melodies
- Audio: loading, regions, clips, time/pitch stretch, fades
- Mixing: sends, buses, sidechain, automation, LUFS targeting
- Rendering: mix export, per-stem export, offline render
- **134 DSP scripts**: hardware compressor emulations (LA-2A, 1176, SSL G-bus), true peak limiter, LUFS meter (ITU-R BS.1770-4), stereo correlation meter, FFT spectrum analyzer, psychoacoustic bass enhancer, spring reverb, vocoder, stereo air exciter, and more
- **8 structural section generators**: intro, prechorus, interlude, transition, bridge, outro, coda — each with 5 style variants
- **Meta-tools**: `arrange_full_song` (one call = MIDI skeleton), `produce_full_track` (one call = full track), `produce_and_master` (one call = produced + mastered track, 7 steps: BPM → arrange → drums → bass → genre FX → mastering → render), `auto_master` (one call = adaptive mastering)
- **39 genre arrangements**: house, techno, DnB, trap, dubstep, synthwave, jazz, rock, metal, ambient, lofi, industrial, breakbeat, K-pop, J-pop, and more
- **Stem splitter**: 7 SOTA open-source models (BS-Roformer, HTDemucs FT, SCNet, MelBand Roformer) running locally on GPU
- **Preset management**: save/load .opb preset bundles

**How it works:** A Playwright bridge drives a headless Chromium running openDAW's Vite dev server. The MCP server translates agent calls into DAW box-graph mutations via openDAW's internal API. Everything runs locally — no cloud, no per-call costs.

**The one-call pipeline:**
```python
await server.mcp_opendaw_produce_and_master(
    structure="intro:4,verse:8,prechorus:2,chorus:8,bridge:4,chorus:8,outro:4",
    key_root="A", scale_type="minor", genre="house", bpm=124,
    platform="spotify", master_style="balanced", render=True
)
# → Complete mastered track rendered to WAV, -14 LUFS, -1 dBTP
```

**Why this matters:** AI music generation is solved (Suno, Udio, MusicGen). But production — mixing, arranging, mastering — is still manual. opendaw-mcp bridges that gap: an agent can take a raw AI-generated track, split it into stems, add effects, build an arrangement, and master to -1 dBTP for streaming.

**Links:**
- GitHub: https://github.com/AMEOBIUS/opendaw-mcp
- Docs: https://ameobius.github.io/opendaw-mcp/
- PyPI: `pip install opendaw-mcp`

Built on [openDAW](https://github.com/andremichelle/openDAW) by André Michelle. MCP tools, DSP scripts, and examples by AMEOBIUS.

## Submission notes
- Post timing: Tuesday-Thursday 8-10 AM PT (best engagement)
- First comment: technical details about the Playwright bridge architecture
- Be ready to answer: "How does this compare to Suno/Udio?" → "They generate audio. We produce it inside a real DAW."
- Be ready to answer: "Why MCP?" → "Standardized protocol for LLM tool use. Works with Claude, GPT, Hermes, any MCP-compatible agent."
