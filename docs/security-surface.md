# Security Surface

Companion to [SECURITY.md](../SECURITY.md) — covers tool safety, sandboxing,
and supply chain protections in opendaw-mcp.

## Tool annotations

All 543 tools carry MCP annotations for agent safety:

| Annotation | Count | Examples |
|---|---|---|
| `readOnlyHint=True` | 88 | `get_*`, `list_*`, `read_*`, `detect_*`, `analyze_*` |
| `destructiveHint=True` | 23 | `delete_track`, `delete_note`, `delete_region`, `clear_*` |
| (unannotated, safe) | 432 | `create_*`, `set_*`, `add_*`, `render_*` |

Agents use these hints to decide which tools require user confirmation.

## File sandbox

All file operations (render, export, import) are constrained to:
- `OPENDAW_EXPORT_DIR` (env var, defaults to `../exports`)
- `OPENDAW_HOST_DIR` (env var, defaults to `../headless-daw`)

No tool reads or writes outside these directories. Path traversal
attempts (`../`) are rejected by `_safe_path()`.

## JavaScript execution

`evaluate` and `evaluate_raw` tools execute JavaScript in the DAW's V8
context. These are development tools, not agent-facing. They are:

- Not annotated as `readOnly` (agents treat them as potentially destructive)
- Documented as dev-only in tool descriptions
- Blocked in lite agent profile (39 tools, no raw evaluate)

## Agent anti-injection

Tool descriptions are factual, not instructional. No tool description
contains prompts, role-play instructions, or "ignore previous instructions"
text. Agents receive tool descriptions as untrusted metadata.

## Supply chain

| Protection | Status |
|---|---|
| SBOM (CycloneDX) | ✅ Generated in CI, uploaded as artifact |
| pip-audit | ✅ Runs in CI on every push |
| OpenSSF Scorecard | ✅ Weekly scan, badge in README |
| Dependabot | ✅ Active (12 PRs pending) |
| Branch protection | ✅ Required CI checks, no direct push |
| PyPI trusted publishing | ✅ OIDC, no stored tokens |

## Logging

Structured logging via stderr (JSON when `OPENDAW_MCP_LOG_JSON=1`).
No secrets, tokens, or user data in logs. Tool call duration and
success/failure only.
