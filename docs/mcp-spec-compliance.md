# MCP Spec Compliance

opendaw-mcp complies with MCP specification 2025-06-18 (latest stable).

## Protocol version

`2025-06-18` — negotiated via `initialize` handshake.

## Transport

- **stdio** (default) — for CLI agent integration
- **Streamable HTTP** — via `uvicorn` for remote deployments

## Capabilities

| Capability | Status |
|---|---|
| Tools | ✅ 543 tools |
| Resources | ☐ (planned: project state as resource) |
| Prompts | ☐ (planned: genre templates) |
| Logging | ✅ structured JSON (OPENDAW_MCP_LOG_JSON=1) |
| Tool annotations | ✅ readOnlyHint + destructiveHint (88 annotated) |

## Tool annotations

All destructive tools marked with `destructiveHint=True`:
- `delete_track`, `delete_note`, `delete_region`, `clear_*`

All read-only tools marked with `readOnlyHint=True`:
- `get_*`, `list_*`, `read_*`, `detect_*`, `analyze_*`, `evaluate_*`

## Structured output

Tools return JSON strings. The MCP SDK 1.x client parses these as
text content. For structured content (2025-06-18), tools can optionally
return `structuredContent` alongside text — planned for v1.386.

## JSON Schema

Tool input schemas use JSON Schema draft 2020-12 (via pydantic + FastMCP).

## Tasks extension (experimental)

Render and export operations are long-running (5-30s). These are
candidates for MCP Tasks extension when it stabilizes.

## Security

- No OAuth (stdio transport, local trust model)
- Tool descriptions are honest (no prompt injection surface)
- File operations sandboxed to OPENDAW_EXPORT_DIR
