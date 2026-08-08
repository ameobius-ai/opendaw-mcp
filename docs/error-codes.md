# Error Code Reference

Stable error codes returned by opendaw-mcp tools (foundation slice of
[#31](https://github.com/ameobius-ai/opendaw-mcp/issues/31)).

Tool error responses are JSON objects with:

- `error` — human-readable message (what went wrong)
- `error_code` — string code (`INVALID_PARAMETER`, `NOT_FOUND`, `BRIDGE_ERROR`, `TIMEOUT`)
- `error_ref` — stable E-code for lookup in this document (when covered by the catalog)
- `hint` — actionable guidance on how to fix it
- `docs` — deep link to the relevant section below

| E-code | error_code | Category | Meaning |
|---|---|---|---|
| E2001 | `BRIDGE_ERROR` | connection | Headless openDAW bridge failed |
| E3001 | `INVALID_PARAMETER` | tool execution | Parameter failed validation |
| E3002 | `TIMEOUT` | tool execution | Operation exceeded its time budget |
| E4001 | `NOT_FOUND` | filesystem | File or object not found |

## E2001: Bridge error

The server drives a real openDAW instance in headless Chromium via Playwright;
this error means the browser page or the DAW host is unreachable or crashed.

Possible causes:

1. The openDAW host is not being served (static dir or Vite dev server down)
2. Wrong URL in `OPENDAW_URL` (default `http://localhost:5174`)
3. The V8 page crashed (e.g. OOM on a weak machine)

To fix:

1. Start the host: `OPENDAW_STATIC_DIR=../headless-daw/dist python scripts/serve_static.py`
2. Verify `curl -I $OPENDAW_URL` answers
3. The bridge auto-relaunches a crashed target once; repeated failures mean the
   host itself is down — check RAM (`OPENDAW_V8_HEAP_MB`) and Chromium flags

## E3001: Invalid parameter

A tool parameter failed validation (unknown name, out of range, wrong type).

To fix:

1. Check the response — it usually names the offending value
2. Compare against the tool schema in `TOOL_CATALOG.md`
3. For enums (platforms, genres, effect types), the `hint` lists valid options

## E3002: Timeout

The operation exceeded its time budget (render, analysis, browser startup).

To fix:

1. Retry with a smaller scope (shorter render, fewer stems)
2. On weak machines prefer `OPENDAW_MCP_MODE=lite` and a lower `OPENDAW_V8_HEAP_MB`
3. For long operations use the tasks API (`OPENDAW_MCP_TASKS=1`) and poll instead

## E4001: Not found

A file (WAV export, preset, lineage node) or object could not be located.

To fix:

1. For audio, pass a filename inside `OPENDAW_EXPORT_DIR` or an absolute path
2. List available exports before referencing them
3. For lineage nodes, record parents before attaching children
