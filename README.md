<!-- mcp-name: io.github.AMEOBIUS/opendaw-mcp -->
# openDAW MCP

[![CI](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/AMEOBIUS/opendaw-mcp/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-207-brightgreen)](TOOL_CATALOG.md)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-Published-blue)](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.AMEOBIUS/opendaw-mcp)

**207 MCP tools for agent-native control of [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation.**

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

The `examples/` directory contains 7 Python scripts demonstrating the full workflow:

| Example | Description |
|---------|-------------|
| `create_beat.py` | Drum beat with Playfield |
| `create_chord_progression.py` | Chord progression with Vaporisateur |
| `mix_workflow.py` | Mixing: levels, effects, sends |
| `render_stems.py` | Stem export with LUFS targeting |
| `automation_sweep.py` | Filter cutoff automation |
| `modular_patch.py` | Modular system with patch cables |
| `full_production_pipeline.py` | Complete track: synth + drums + DSP + automation + render |

## Tool Catalog

See [`TOOL_CATALOG.md`](TOOL_CATALOG.md) for the complete list of 207 tools with parameters and descriptions.

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
