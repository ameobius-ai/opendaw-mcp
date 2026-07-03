# Security Policy

## Reporting a Vulnerability

If you discover a security issue in openDAW MCP, please **do not** open a public issue.

Instead, email: **security@ameobius.dev** (or use GitHub's private vulnerability reporting).

Include:
- Description of the issue
- Steps to reproduce
- Potential impact

You will receive a response within 48 hours.

## Scope

This policy covers the MCP server (`server.py`), the Playwright bridge, and the headless Chromium integration.

## Architecture Notes

- The server launches a **headless Chromium** instance with openDAW loaded from a local Vite dev server.
- `evaluate_raw` and `evaluate` tools execute arbitrary JavaScript in the DAW's V8 context — these are powerful debugging tools intended for development use only.
- No credentials, API keys, or personal data are stored or transmitted by the server itself.
- Environment variables (`OPENDAW_HOST_DIR`, `OPENDAW_URL`, etc.) are read at startup and not persisted.
