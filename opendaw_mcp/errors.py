"""Central error catalog for opendaw-mcp — actionable guidance on error responses.

Maps the package's string error codes (the `error_code` field in tool
responses) to stable E-codes, categories, actionable hints and documentation
anchors. Foundation slice of issue #31 (DX: error messages with actionable
guidance).

Wire-up: wrap an error dict with enrich_error() before returning it.
The original message and error_code are preserved; the catalog only fills
in what is missing (hint) and adds error_ref + docs.
"""

from __future__ import annotations

from typing import Any

DOCS_BASE = "https://github.com/ameobius-ai/opendaw-mcp/blob/main/docs/error-codes.md"

# Stable E-codes by category (see docs/error-codes.md):
#   E1xxx configuration, E2xxx connection/bridge, E3xxx tool execution,
#   E4xxx filesystem, E5xxx audio processing
ERROR_CATALOG: dict[str, dict[str, str]] = {
    "BRIDGE_ERROR": {
        "ref": "E2001",
        "category": "connection",
        "hint": (
            "The headless openDAW browser bridge failed. Check that the host is "
            "served and reachable (OPENDAW_URL, default http://localhost:5174)."
        ),
        "docs": f"{DOCS_BASE}#e2001-bridge-error",
    },
    "INVALID_PARAMETER": {
        "ref": "E3001",
        "category": "tool_execution",
        "hint": (
            "A parameter failed validation. Check the tool schema for names, "
            "types, and allowed ranges; the response usually names the bad value."
        ),
        "docs": f"{DOCS_BASE}#e3001-invalid-parameter",
    },
    "TIMEOUT": {
        "ref": "E3002",
        "category": "tool_execution",
        "hint": (
            "The operation exceeded its time budget. Retry with a smaller scope "
            "or increase the timeout; on weak machines prefer OPENDAW_MCP_MODE=lite."
        ),
        "docs": f"{DOCS_BASE}#e3002-timeout",
    },
    "NOT_FOUND": {
        "ref": "E4001",
        "category": "filesystem",
        "hint": (
            "The requested file or object was not found. Verify the path/name; "
            "for audio, pass a WAV inside OPENDAW_EXPORT_DIR or an absolute path."
        ),
        "docs": f"{DOCS_BASE}#e4001-not-found",
    },
}


def enrich_error(err: dict[str, Any]) -> dict[str, Any]:
    """Fill in catalog guidance (hint, error_ref, docs) on an error response dict.

    Non-error dicts pass through unchanged. A specific hint already present in
    the response wins over the catalog default. Never raises.
    """
    if not isinstance(err, dict) or "error" not in err:
        return err
    code = err.get("error_code")
    entry = ERROR_CATALOG.get(code) if isinstance(code, str) else None
    if entry is None:
        return err
    out = dict(err)
    out.setdefault("hint", entry["hint"])
    out["error_ref"] = entry["ref"]
    out["docs"] = entry["docs"]
    return out
