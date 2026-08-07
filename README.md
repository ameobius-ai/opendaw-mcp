# opendaw-mcp

<!-- REPO-METRICS: tools=557 skills=12 dsp=134 examples=226 -->

[![CI](https://github.com/ameobius-ai/opendaw-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/ameobius-ai/opendaw-mcp/actions/workflows/ci.yml)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-557-brightgreen)](TOOL_CATALOG.md)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-12-blue)](skills/)
[![DSP Scripts](https://img.shields.io/badge/DSP%20Scripts-134-orange)](scripts/)
[![Examples](https://img.shields.io/badge/Examples-226-blue)](examples/)

MCP server for agent-native control of [openDAW](https://github.com/andremichelle/openDAW) — a browser-based digital audio workstation. Exposes 550+ tools (tracks, notes, effects, mixing, rendering) over the Model Context Protocol for AI agents (Claude, GPT, etc.).

```
AI agent ── MCP (stdio/SSE) ──▶ Python server ── Playwright ──▶ headless Chromium ──▶ openDAW
```

The server drives a real openDAW instance in headless Chromium via `page.evaluate()`. All project state lives in the browser's V8 context. Chromium starts lazily on the first tool call.

## Quick start

Requirements: Python 3.10+, Node.js 20+ (to serve the openDAW host), Chromium via Playwright.

```bash
pip install -r requirements.txt
playwright install chromium

# Serve the openDAW headless host on http://localhost:5174 in a separate terminal
# (see https://github.com/andremichelle/openDAW)

python server.py   # stdio transport
```

Client config example:

```json
{
  "mcpServers": {
    "opendaw": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "OPENDAW_URL": "http://localhost:5174",
        "OPENDAW_MCP_MODE": "lite"
      }
    }
  }
}
```

## Lite mode — recommended for weak machines

Full mode registers 557 tools; every tool schema costs tokens on each agent turn. Lite mode registers a curated set of 39 essential tools — about 92% less schema payload and a faster startup:


> **Note:** Lite mode is now the default. You only need to set `OPENDAW_MCP_MODE=full` if you want all tools.

```bash
OPENDAW_MCP_MODE=lite python server.py
```

Lite covers: project state, tracks, instruments, notes, regions, effects, mixing, BPM, markers, scriptable devices, render/export, and core composition helpers (drum pattern, bassline, melody, chord progression, mix preset).

## Low-memory tuning

Chromium is launched with low-RAM flags by default: `--disable-dev-shm-usage` (safe on Docker's 64 MB `/dev/shm`), `--disable-gpu`, `--mute-audio`, a V8 heap cap, and no background networking. Offline rendering is unaffected.

In Docker, `OPENDAW_SERVE_MODE=static` replaces the Vite dev server with a zero-dependency Python static server (`scripts/serve_static.py`, ~10 MB RAM instead of ~300–500 MB for Node + Vite). Requires a pre-built host directory; Vite remains the default until the image builds one (see issue #12).

| Variable | Default | Description |
|---|---|---|
| `OPENDAW_V8_HEAP_MB` | `512` | V8 heap cap for the DAW page (`--max-old-space-size`) |
| `OPENDAW_CHROMIUM_ARGS` | — | Extra Chromium args, space-separated |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | — | Use system Chromium instead of the bundled one |

## Environment variables

> **Note:** As of this update, `OPENDAW_MCP_MODE=lite` is now the default mode for better token efficiency. Use `OPENDAW_MCP_MODE=full` to enable all 500+ tools.


| Variable | Default | Description |
|---|---|---|
| `OPENDAW_URL` | `http://localhost:5174` | URL of the served openDAW host |
| `OPENDAW_HOST_DIR` | `../headless-daw` | Path to headless DAW host directory |
| `OPENDAW_EXPORT_DIR` | `../exports` | Rendered audio output directory |
| `OPENDAW_MCP_MODE` | `lite` | `lite` = 39 tools (default), `full` = all tools |
| `OPENDAW_SERVE_MODE` | `vite` | Docker: `static` = serve a pre-built host via `scripts/serve_static.py` (no Node) |
| `OPENDAW_STATIC_DIR` | `/opendaw/headless-daw/dist` | Directory served in static mode |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `FASTMCP_HOST` / `FASTMCP_PORT` | `127.0.0.1` / `8000` | SSE bind address |
| `NODE_BIN_DIR` | — | Prepended to PATH for Vite lookup |

## Docker

```bash
docker build -t opendaw-mcp .
docker run --rm -p 8080:8080 opendaw-mcp
```

The image builds openDAW from source, serves the headless host, and runs the server in SSE mode on `:8080`. Node's heap is capped via `NODE_OPTIONS` for small containers; give the container at least 1 GB RAM for comfortable rendering.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
ruff check server.py opendaw_mcp
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for internals and [TOOL_CATALOG.md](TOOL_CATALOG.md) for the full tool list.

## License

Apache-2.0 — see [LICENSE](LICENSE).
