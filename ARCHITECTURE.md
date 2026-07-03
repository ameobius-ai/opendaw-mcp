# Architecture

## Overview

```
┌──────────┐     MCP (stdio/SSE)     ┌──────────────┐     Playwright     ┌─────────────────┐     Vite :5174     ┌──────────────┐
│ AI Agent │ ◀─────────────────────▶ │ Python Server│ ◀───────────────▶ │ Headless Chromium│ ◀───────────────▶ │   openDAW    │
│ Claude,  │    JSON-RPC 2.0         │  (FastMCP)   │   page.evaluate()  │   (Chromium)     │   WebSocket HMR   │  (TypeScript) │
│ GPT, etc │                         │  server.py   │                    │                  │                   │              │
└──────────┘                         └──────────────┘                    └─────────────────┘                   └──────────────┘
```

## Components

### 1. MCP Server (`server.py`)

The entry point. Implements the [Model Context Protocol](https://modelcontextprotocol.io) using Python's `FastMCP` framework.

- **250 tools** — each a function decorated with `@mcp.tool()`
- **Transport**: stdio (default) or SSE (`MCP_TRANSPORT=sse`)
- **Lazy bridge init** — Chromium only launches when first tool is called
- **DAW_HELPERS** — 17 JavaScript helper functions injected into the DAW's V8 context to reduce boilerplate
- **Pure Python utilities** — WAV parsing, LUFS computation, MIDI conversion, filename sanitization

### 2. Playwright Bridge (`HeadlessDawBridge`)

Manages the headless Chromium lifecycle:

1. Launches Chromium with `--no-sandbox`, `--disable-web-security`, COOP/COEP headers
2. Navigates to the Vite dev server URL (default: `http://localhost:5174`)
3. Waits for DAW globals (`DAW_InstrumentFactories`, `DAW_EffectFactories`, etc.)
4. Exposes `evaluate(script)` — runs JS in the DAW's V8 context via `page.evaluate()`

**Important**: The bridge is a singleton within a single Python process. State (loaded project, created tracks, effects) persists across tool calls as long as the process lives. Between separate processes, state is lost.

### 3. Headless Chromium + openDAW

- `headless-daw/` — a minimal HTML/JS host page that imports openDAW's compiled modules
- Exposes DAW internals as `window.DAW_*` globals: `DAW_BoxGraph`, `DAW_ProjectApi`, `DAW_InstrumentFactories`, `DAW_EffectFactories`, etc.
- **COOP/COEP**: Required for `SharedArrayBuffer` (AudioWorklet support)
- **Cross-origin isolation**: `crossOriginIsolated === true`

### 4. openDAW (upstream)

[openDAW](https://github.com/andremichelle/openDAW) by André Michelle — a browser-based DAW built with TypeScript, IndexedDB (Yjs), and Web Audio API.

- **Box system**: All state lives in immutable boxes (`AudioUnitBox`, `TrackBox`, `EffectBox`, etc.)
- **ProjectApi**: 27 methods for high-level operations (`createInstrument`, `insertEffect`, `duplicateRegion`, etc.)
- **editing.modify()**: All box mutations must go through `editing.modify()` blocks for proper Yjs synchronization
- **PPQN**: 960 pulses per quarter note
- **Scriptable devices**: Apparat (instrument), Werkstatt (audio effect), Spielwerk (MIDI effect) — user JS code compiled at runtime

## Data Flow

### Tool call → DAW operation

```python
# 1. AI agent calls MCP tool
result = await mcp_opendaw_create_synth_track(unit_index=0, oscillator=1)

# 2. Tool builds JS code with parameters
js_code = f"""() => {{
    const h = window.DAW_HELPERS;
    const au = h.au({unit_index});
    // ... create synth ...
    return {{ success: true, name: "{name}" }};
}}"""

# 3. Bridge executes in Chromium V8 context
result = await bridge.evaluate(js_code)

# 4. Result returned to agent as JSON string
return result
```

### Rendering pipeline

```
export_stems(unit_index=0, target_lufs=-14)
  → offline engine renderer (48kHz, 32-bit float)
  → per-stem WAV files
  → LUFS measurement (_compute_lufs)
  → gain adjustment if target_lufs specified
  → files saved to OPENDAW_EXPORT_DIR
```

## Tool Categories

| Category | Count | Description |
|----------|-------|-------------|
| Project | 7 | State, transport, engine control |
| Transport | 9 | Play, stop, position, BPM, loop |
| Tracks | 5 | Create/delete/move tracks |
| Audio | 9 | Load audio, regions, fades, gain, stretch |
| Effects | 12 | Add/remove/move/clone effects, parameters |
| Notes | 10 | Create/edit/delete notes, MIDI import/export |
| Regions | 8 | Position, duration, mute, label, color, duplicate |
| Markers | 4 | Add/delete/move/label markers |
| MIDI | 2 | Import/export MIDI files |
| Export | 6 | Mix render, stems, range, dry stems, format options |
| Sends | 6 | Create/remove/route/pan sends |
| Buses | 3 | Create/delete/label/color buses |
| Mixing | 4 | Volume, pan, mute, solo, mixer state |
| Automation | 3 | Add/delete/move/update automation events |
| Editing | 3 | Undo, redo, serialize |
| Groove | 2 | Shuffle amount, groove duration |
| Clips | 6 | Create/delete/clone/consolidate clips |
| MIDI Effects | 6 | Arpeggio, pitch, velocity, zeitgeist, spielwerk |
| Scriptable Devices | 5 | Compile/list/set code and parameters |
| Instrument Params | 2 | Universal Vaporisateur/Tape/Nano/Soundfont control |
| Playfield | 3 | Drum machine sample management |
| Stretch Clips | 2 | Time/pitch stretched audio clips |
| Modular | 6 | Voltage modules and patch cables |
| Piano Mode | 5 | Transpose, keyboard, scale, labels, time range |
| Audio Conversion | 1 | WAV→MP3/FLAC via ffmpeg |
| DawProject | 2 | Export/import .dawproject format |
| Debugging | 3 | Screenshots, condition polling, raw JS eval |
| Project Info | 5 | Duration, tempo, validation, samples, metadata |
| Warp Markers | 3 | Create/delete/update warp markers |
| Metronome | 1 | Enable/gain/subdivision control |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENDAW_HOST_DIR` | `../headless-daw` | Path to headless DAW host directory |
| `OPENDAW_URL` | `http://localhost:5174` | Vite dev server URL |
| `OPENDAW_EXPORT_DIR` | `../exports` | Directory for rendered audio files |
| `NODE_BIN_DIR` | — | Node.js binary directory (for Vite) |
| `MCP_TRANSPORT` | `stdio` | Transport type: `stdio` or `sse` |
| `FASTMCP_HOST` | `127.0.0.1` | SSE host |
| `FASTMCP_PORT` | `8000` | SSE port |

## Testing

- **Unit tests** (`tests/test_utils.py`): 54 tests covering pure Python utilities
- **CI** (GitHub Actions): 7 checks — syntax, AST tool count ≥250, smoke test, pytest, ruff, DSP script validation, hardcoded path check
- **E2E tests**: Manual via bridge (requires running Vite + Chromium)

## Docker

```bash
docker run --rm -i \
  -e OPENDAW_HOST_DIR=/app/headless-daw \
  -e OPENDAW_URL=http://localhost:5174 \
  ghcr.io/ameobius/opendaw-mcp:1.9.8
```

Image includes: Python 3.11, Playwright + Chromium, openDAW headless host, all dependencies.

## Limitations

- **Project serialization**: Uses IndexedDB/OPFS in browser, not accessible in headless mode. Projects are saved via `toArrayBuffer()` workaround.
- **`api.exportAudio`**: Triggers a file dialog, not available in headless. Use `export_mix` or `render_full` instead.
- **AU rename**: Requires adapter context not available in headless mode.
- **Realtime streaming**: `capture_realtime`, `subscribeNotes`, `noteSignal` are realtime-only.
- **Adapter state**: `au.audioEffects.adapters()` may not reflect changes made in a previous `evaluate()` call due to Yjs sync timing. Box-level access (`h.effectBoxes(auBox)`) is used for mutators.
