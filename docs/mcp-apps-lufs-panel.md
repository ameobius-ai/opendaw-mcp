# MCP Apps Prototype — LUFS Panel

## Overview

Sandboxed HTML panel displaying real-time LUFS and spectral data from
opendaw-mcp render results. This is a prototype for the MCP Apps
extension (2025-06-28 spec).

## How it works

```
MCP Host (Claude/IDE)
  └─ sandboxed iframe (allow-scripts, NOT allow-same-origin)
       └─ lufs-panel.html
            ← postMessage({ type: 'render_result', data: {...} })
```

1. Agent calls `render_full` → gets JSON result with LUFS, spectrum, etc.
2. MCP host renders `lufs-panel.html` in a sandboxed iframe
3. Host sends render data via `postMessage`
4. Panel displays LUFS, true peak, spectral bars — read-only

## Security model

| Threat | Mitigation |
|---|---|
| XSS via panel content | No `eval()`, no `Function()`, no external scripts |
| Data exfiltration | CSP: `connect-src 'none'` — no network requests |
| Parent DOM access | iframe sandbox: `allow-scripts` without `allow-same-origin` |
| Prompt injection in data | Data rendered as text, never as HTML (except spectrum bars via DOM API) |

The panel cannot:
- Access parent window DOM
- Make HTTP requests
- Load external resources
- Execute dynamically created code

## Display

Three panels:
1. **LUFS Measurement** — integrated LUFS (green/yellow/red vs -14 target), true peak, max sample
2. **Spectral Balance** — bar visualization of frequency bands
3. **Render Info** — duration, sample rate, total samples

## Future

When MCP Apps spec stabilizes (2026-07-28), this becomes a native
capability advertised via `server/discover`. For now it's a static
HTML prototype that any MCP host can embed.
