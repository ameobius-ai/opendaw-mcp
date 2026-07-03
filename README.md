<!-- mcp-name: io.github.AMEOBIUS/opendaw-mcp -->
# openDAW MCP

[![CI](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-229-brightgreen)](TOOL_CATALOG.md)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-Published-blue)](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.AMEOBIUS/opendaw-mcp)

**229 MCP tools for agent-native control of [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation.**

This project wraps openDAW's internal box system and project API behind a [Model Context Protocol](https://modelcontextprotocol.io) server, allowing AI agents (Claude, GPT, Hermes, etc.) to create and manipulate music projects programmatically — tracks, instruments, effects, MIDI, automation, audio regions, rendering, and more.

## How It Works

```
AI Agent ──MCP──▶ Python Server ──Playwright──▶ Headless Chromium ──▶ openDAW (Vite dev server)
```

The MCP server launches a headless Chromium instance loaded with openDAW, then communicates via `page.evaluate()` calls into the DAW's V8 context. Every tool performs real operations on the live project — no stubs, no mocks.

## Features

- **Track & Region CRUD** — create/delete/move audio, note, and automation tracks with regions
- **Instrument Control** — Vaporisateur ( polysynth), Nano, Tape, Soundfont, Playfield (drum machine), MIDI output
- **Effects** — Delay, Reverb, Compressor, Equalizer, Saturation, Waveshaper, Stereo, Vocoder, NeuralAmp, Maximizer
- **MIDI Effects** — Arpeggio, Pitch, Velocity, Zeitgeist, Spielwerk (scriptable)
- **Scriptable Devices** — Apparat (instrument), Werkstatt (audio effect), Spielwerk (MIDI effect) with JS code compilation
- **Automation** — event creation, interpolation modes, tempo/signature changes
- **Audio Operations** — region fades, gain, time/pitch stretch, warp markers, play modes
- **Mixing** — send/return routing, buses, volume, solo/mute, mixer state inspection
- **Rendering** — offline stem export with LUFS targeting, full mix render
- **Clips** — session view clip CRUD, clone, consolidate, playback settings
- **Groove** — groove shuffle amount and duration control
- **Presets** — export/import audio unit presets, effect chain presets
- **Transfer** — move regions and audio units between projects
- **Project Info** — tempo map conversion (PPQN↔seconds), duration, validation, sample listing
- **Notes** — pitch range, overlapping detection, advanced properties (chance, cent, playCount, playCurve)
- **Modular System** — voltage modules (Gain, Delay, Multiplier, AudioInput, AudioOutput), patch cable connections
- **Piano Mode** — global transpose, keyboard type, note scale, time range
- **Project & Bus Metadata** — creation date, signature, AU/track count, bus labels and colors
- **Debugging & Control** — screenshots, condition polling, raw JS evaluation

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ (for openDAW dev server)
- Chromium (Playwright will install it)

### Install

```bash
git clone https://github.com/ameobius/opendaw-mcp.git
cd opendaw-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Set Up openDAW

Clone and build openDAW separately:

```bash
git clone https://github.com/andremichelle/openDAW.git
cd openDAW
npm install
npm run build   # or: npx turbo run build
```

Create a headless host page (see `headless-daw/` for reference implementation).

### Run

```bash
# Terminal 1: Start openDAW dev server
cd openDAW
npm run dev     # typically serves on http://localhost:5174

# Terminal 2: Start MCP server (stdio transport, default)
cd opendaw-mcp
source venv/bin/activate
python server.py
```

### SSE Transport

For remote deployments and registry introspection (e.g. [Glama](https://glama.ai)):

```bash
MCP_TRANSPORT=sse FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8080 python server.py
```

### Docker

```bash
docker build -t opendaw-mcp .
docker run -p 8080:8080 opendaw-mcp
# MCP server available at http://localhost:8080/sse
```

The Docker image bundles openDAW (built from source), Vite dev server, Chromium, and the MCP server. The entrypoint starts Vite, waits for it to be ready, then launches the MCP server in SSE mode.

### Claude Desktop / MCP Client Config

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "opendaw": {
      "command": "python",
      "args": ["path/to/opendaw-mcp/server.py"],
      "env": {
        "OPENDAW_HOST_DIR": "path/to/headless-daw",
        "OPENDAW_URL": "http://localhost:5174",
        "OPENDAW_EXPORT_DIR": "path/to/exports"
      }
    }
  }
}
```

See `mcp.json` in the repo for a reference config.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENDAW_HOST_DIR` | `../headless-daw` | Path to the headless openDAW host directory |
| `OPENDAW_URL` | `http://localhost:5174` | URL of the running openDAW instance |
| `OPENDAW_EXPORT_DIR` | `../exports` | Directory for rendered audio exports |
| `NODE_BIN_DIR` | *(from PATH)* | Path to Node.js binary directory (if not on PATH) |
| `MCP_TRANSPORT` | `stdio` | Transport protocol: `stdio` or `sse` |
| `FASTMCP_HOST` | `127.0.0.1` | SSE server bind host |
| `FASTMCP_PORT` | `8000` | SSE server bind port |

## Architecture

### HeadlessDawBridge

The `HeadlessDawBridge` class manages the Playwright lifecycle:

1. Launches headless Chromium with audio autoplay enabled
2. Navigates to the openDAW URL
3. Waits for `window.DAW` and factory globals to load
4. Injects `DAW_HELPERS` — JS utility functions that eliminate boilerplate across tools

### DAW_HELPERS

JavaScript helpers injected into the DAW context:

- `au(i)` — get audio unit adapter by index
- `track(auIdx, trackIdx)` — get track adapter
- `region(au, track, reg)` — get region adapter
- `instrumentAU()` — get the first instrument audio unit
- `modify(fn)` — wrapper around `editing.modify()` for box mutations
- `allAUs()` — list all audio unit adapters

### Tool Structure

Each MCP tool follows the pattern:

```python
@mcp.tool()
async def tool_name(param: str) -> str:
    """Description."""
    async def _run():
        result = await bridge.page.evaluate("""...JS...""")
        return json.dumps(result)
    return await bridge.run(_run)
```

The bridge is a singleton — state persists within a single Python process. All box mutations go through `editing.modify()` as required by openDAW's transactional model.

### Input Sanitization

All string parameters that are interpolated into JavaScript template literals are sanitized before evaluation — quotes, backslashes, and braces are stripped to prevent JS injection. Numeric parameters use proper `int`/`float` type annotations for FastMCP type coercion.

## DSP Scripts

The `scripts/` directory contains example Werkstatt and Apparat DSP scripts:

| Script | Device | Description |
|--------|--------|-------------|
| `werkstatt_darksat.js` | Werkstatt | Tape saturation with drive, bias, tone, mix, output gain |
| `werkstatt_coldfold.js` | Werkstatt | Wavefolding + bitcrush + slew rate reduction |
| `apparat_darkbass.js` | Apparat | Bass synth with sub oscillator and filter envelope |
| `apparat_coldlead.js` | Apparat | Lead synth with detune and vibrato |
| `spielwerk_powerchord.js` | Spielwerk | MIDI effect that generates power chord harmonies |
| `spielwerk_arpeggiator.js` | Spielwerk | MIDI arpeggiator with sync |

## Examples

The `examples/` directory contains 9 Python scripts demonstrating the full workflow:

| Example | Description |
|---------|-------------|
| `create_beat.py` | Drum beat with Playfield |
| `create_chord_progression.py` | Chord progression with Vaporisateur |
| `mix_workflow.py` | Mixing: levels, effects, sends |
| `render_stems.py` | Stem export with LUFS targeting |
| `automation_sweep.py` | Filter cutoff automation |
| `modular_patch.py` | Modular system with patch cables |
| `full_production_pipeline.py` | Complete track: synth + drums + DSP + automation + render |
| `scriptable_devices_demo.py` | All 3 scriptable device types: Apparat synth + Werkstatt DSP + Spielwerk MIDI |

## Tool Catalog

See [`TOOL_CATALOG.md`](TOOL_CATALOG.md) for the complete list of 229 tools with parameters and descriptions.

## Mastering

The MCP server includes a full mastering chain for streaming-ready output:

1. **Render** — `render_full` (full mixdown) or `export_stems` (per-track stems)
2. **Measure LUFS** — `measure_lufs` (ITU-R BS.1770-4 K-weighting, gated mean squares)
3. **Auto-gain** — `auto_gain` (iterative: render → measure → adjust Maximizer threshold + output volume → re-render, converges ±1 LUFS)

```python
# Render full mix
await server.mcp_opendaw_render_full("my_mix", 48000)

# Measure loudness
lufs = json.loads(await server.mcp_opendaw_measure_lufs("my_mix"))
# → {"lufs_integrated": -18.3, "true_peak_db": -3.71, ...}

# Auto-gain to Spotify target (-14 LUFS)
result = json.loads(await server.mcp_opendaw_auto_gain("-14", "mastered", 48000, "3"))
# → converges to -13.7 LUFS in 3 iterations
```

Platform targets: Spotify/YouTube -14 LUFS, Apple Music -16 LUFS, Tidal -14 LUFS.

## Limitations

- **Headless only** — some UI-dependent features (file dialogs, popup-based model loading) are not available
- **Single process** — bridge state doesn't persist across Python process restarts
- **Upstream coupling** — tools depend on openDAW's internal box system, which can change between versions
- **AU rename** — requires adapter context not available in headless mode

## Acknowledgments

- [andremichelle](https://github.com/andremichelle) — creator of openDAW, an incredible browser-based DAW
- [Model Context Protocol](https://modelcontextprotocol.io) — the protocol that makes agent-native tools possible

## License

Apache-2.0 — see [LICENSE](LICENSE)

## Changelog

### v1.7.4 (2026-07-03)

- **3 new tools: Engine Sleep/Wake + Loading Check** — `engine_sleep`, `engine_wake`, `query_loading_complete`
  - `engine_sleep()` — suspend audio processing to save CPU during non-audio operations
  - `engine_wake()` — resume audio processing
  - `query_loading_complete()` — check if all audio samples are loaded and ready
  - E2E: sleep ✅, wake ✅, loading (loaded=false, is_ready=true) ✅
- **Improvement: `get_effect_chain` + `get_midi_effect_chain`** — now return short type names (`Delay` instead of `DelayDeviceBox`), plus `class`, `minimized` fields

### v1.7.3 (2026-07-03)

- **2 new tools: Instrument Automation** — `add_instrument_automation`, `list_automatable_fields`
  - Automate any instrument parameter: Vaporisateur cutoff/volume/ADSR, Tape flutter/wow, Playfield sample mute
  - Per-sample targeting via `sample_index` for Playfield
  - `list_automatable_fields` introspects Pointers.Automation support (18/23 on Vaporisateur)
  - Addresses upstream #269 (playfield mute automation) via MCP
  - E2E: Vaporisateur cutoff automated (3 events) ✅, 18 automatable fields ✅

### v1.7.2 (2026-07-03)

- **3 new tools: Effect Duplication + Instrument Automation** — `duplicate_effect`, `add_instrument_automation`, `list_automatable_fields`
  - `duplicate_effect` — duplicate single effect in-place with all params copied (audio or MIDI chain)
  - `add_instrument_automation` — automate any instrument parameter (Vaporisateur cutoff/volume, Tape flutter, Playfield sample mute, etc). Supports per-sample targeting via sample_index
  - `list_automatable_fields` — introspect which fields support Pointers.Automation (18/23 on Vaporisateur)
  - Addresses upstream issue #273 (Ctrl+D for audio effects) and #269 (playfield mute automation) via MCP
  - E2E tested: Delay duplicated with params ✅, Vaporisateur cutoff automated (3 events) ✅, 18 automatable fields detected ✅
- **Bugfix: `transport(action)` now respects action parameter** — was always toggling, now correctly handles "play", "stop", "toggle"
- **Cleanup: removed unused `region_type` param** from `set_region_duration` and `set_region_mute`

### v1.7.1 (2026-07-03)

- **4 new tools: Engine Control** — `engine_panic()`, `get_engine_status()`, `schedule_clip_play(clip_ids)`, `schedule_clip_stop(track_ids)`
  - Panic button for stuck audio, real-time engine monitoring (CPU load, position, BPM, playing state), session view clip triggering
  - E2E tested: get_engine_status ✅, engine_panic ✅

### v1.7.0 (2026-07-03)

- **2 new tools: DawProject Interop** — `export_dawproject(filename)`, `import_dawproject(filename)`
  - Export/import projects in .dawproject format (Bitwig, Ableton, rePitch compatible)
  - ZIP containing project.xml, metadata.xml, and audio samples
  - Enables cross-DAW workflow: create in openDAW → export to Bitwig, or import Bitwig project → render in openDAW
  - DawProject + DawProjectImport exposed as globals in headless-daw
  - E2E tested: export (2442 bytes, valid ZIP) → import (7 boxes, round-trip OK)

### v1.6.2 (2026-07-03)

- **2 new tools: Studio Settings** — `get_studio_settings()`, `set_studio_setting(category, key, value)`
  - Read/write StudioPreferences: engine, visibility, editing, debug, storage, time-display, pointer
  - Control auto-create-output-maximizer, overlapping-regions-behaviour, enable-beta-features, auto-delete-orphaned-samples, note-audition-while-editing, and more
  - StudioPreferences exposed as `DAW_StudioPreferences` global in headless-daw

### v1.6.1 (2026-07-03)

- **4 new tools from DAW globals research** — `set_unit_minimized`, `list_aux_sends`, `capture_realtime`, `get_sample_info`
  - Mixer minimize, aux send listing, realtime audio capture, sample metadata

### v1.6.0 (2026-07-03)

- **DAW_HELPERS refactoring** — all 180 tools with `const p = window.DAW` migrated to `const h = window.DAW_HELPERS` pattern
  - Eliminated boilerplate: AU list enumeration, sort, editing.modify wrapping
  - Fixed 19+ pre-existing bugs: `setPosition` (api→engine), 8x missing `.sort()` on AU lists, 9x `Quarter=960` hardcode → `h.ppqn.Quarter`, 2x Python/JS scope leaks
  - DAW_HELPERS provides: `h.au(i)`, `h.track()`, `h.region()`, `h.modify()`, `h.allAUs()`, `h.ppqn`, `h.uuid`, `h.rootBox`, `h.api`, `h.editing`, `h.boxGraph`, `h.tempoMap`, `h.rootBoxAdapter`, `h.project`
- E2E verified: 23/23 tests passing

### v1.5.2 (2026-07-02)

- Sanitization: all string parameters sanitized against JS injection
- Documentation: README badges, Docker, SSE, examples, mastering
- CI: GitHub Actions with AST tool count verification

### v1.5.0 (2026-07-01)

- Modular system: 6 MCP tools for patchable modular synthesizer
- PianoMode: 6 MCP tools for piano roll view control
- Freeze/unfreeze: pre-render AU to save CPU
- Preset save/load: export/import AU as base64 preset
- Transfer regions/AUs: deep-copy with dependency tracking
