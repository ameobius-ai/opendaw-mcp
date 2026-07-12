# opendaw-mcp 1.385: Agent-Native Music Production Without a DAW

**2026-07-12**

Most MCP servers for music production assume you own a DAW. Ableton Live ($99+), running on a desktop, with a GUI open. opendaw-mcp doesn't. It controls a browser-based DAW headlessly — no license, no desktop, no GUI. You can produce music in Docker, in CI, in the cloud.

This is the story of v1.385.0: 543 tools, 6139 tests, and real audio evals proving it works.

## The moat

[ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) (2.8k stars) wraps Ableton Live's Max for Live API. It gives agents ~322 tools — but only if Live is running on your machine. You pay for Live, you keep it open, you run on macOS or Windows.

opendaw-mcp gives agents 543 tools against [openDAW](https://github.com/andremichelle/openDAW) — a fully browser-based DAW. No license. No desktop. The agent talks to a headless Chromium instance running the DAW engine. You can run it in a Docker container, in CI, on a cloud GPU instance.

## What's in 543 tools

| Category | Tools | Example |
|----------|-------|---------|
| Transport | 12 | set_bpm, set_loop_region, play, stop |
| Tracks & Notes | 34 | create_track, create_note, create_chord |
| Effects | 89 | add_compressor, add_reverb, set_parameter |
| DSP Scripts | 134 | Custom JS audio processing |
| Mixing | 28 | set_volume, set_pan, create_send |
| Rendering | 8 | render_full, render_stems, export_dawproject |
| Analysis | 15 | measure_lufs, analyze_spectrum, detect_key |
| Genre Presets | 8 | techno, dnb, neurofunk, phonk, house, trap, synthwave, ambient |
| Suno Pipeline | 6 | import_suno, separate_stems, rebuild_project |

Plus 12 agent skills (reusable workflows) and 228 example scripts.

## Real evals, not vibes

The eval harness runs 5 scenarios in CI with objective audio metrics:

1. **Techno loop** — 128 BPM 4/4 kick, non-silence + finite checks
2. **DnB break** — 170 BPM Amen-style, stereo + duration
3. **Ambient pad** — sustained chord, 4+ second render
4. **LUFS measurement** — real ITU-R BS.1770-4 integrated loudness on rendered WAV
5. **Sidechain duck** — kick triggers volume duck on bass via `connect_sidechain` + automation

Scenarios 4 and 5 don't check "does it sound good" — they check measurable properties of the audio output. LUFS is computed from the WAV file using the actual ITU standard. The sidechain scenario creates a real compressor connection and beat-synced volume automation.

## Deterministic by design

Python's `hash()` uses `PYTHONHASHSEED` — randomized per process. Same input, different output every run. That's unacceptable for reproducible music generation.

opendaw-mcp uses `_stable_seed()` — SHA-256 based — at every generation site. Same parameters always produce the same notes, the same rhythms, the same fills.

## Observability

```bash
OPENDAW_MCP_LOG_JSON=1 python -m opendaw_mcp
```

Structured JSON logs: timestamp, tool name, duration in milliseconds, success/failure. Production-ready for latency monitoring and error tracking.

## MCP spec compliance

Protocol version `2025-06-18`. MCP Python SDK v1.28. Tool annotations (`readOnlyHint`, `destructiveHint`) on all safety-relevant tools. MCP Inspector validation in CI.

## Try it

```bash
pip install opendaw-mcp==1.385.0
python examples/showcase/01_techno_30s.py
```

Three showcase demos in [examples/showcase/](https://github.com/AMEBIUS-team/opendaw-mcp/tree/main/examples/showcase):

1. **Techno in 30 seconds** — genre preset to mastered WAV
2. **Ambient pad** — manual subtractive synthesis
3. **Suno → DAW** — stem separation and remix

## What's next

- MCP Tasks extension for long-running operations (render, stems)
- MCP Apps prototype: sandboxed LUFS/waveform UI
- Eval harness v1.2: more scenarios, score history
- Cloud deployment recipes

---

*opendaw-mcp is Apache-2.0 licensed. Contributions welcome at [github.com/AMEBIUS-team/opendaw-mcp](https://github.com/AMEBIUS-team/opendaw-mcp).*
