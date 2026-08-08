#!/usr/bin/env python3
"""Verify the MCP tool registry rather than the layout of ``server.py``.

This replaces the former "AST tool count verification" CI step, which parsed
``server.py`` and counted ``async def mcp_opendaw_*`` nodes. That approach
measured *where the source text lived* rather than what the server actually
exposes, which made the monolith self-perpetuating: any change moving tool
definitions into modules failed the gate regardless of correctness.

Counting what FastMCP registered is strictly stronger. A function can be
defined and never registered -- which the AST scan would happily count -- but
it cannot be registered and missing here.

Run locally with::

    python scripts/check_tool_registry.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# ``server.py`` lives at the repository root, but running this file as
# ``python scripts/check_tool_registry.py`` puts *this* directory on sys.path
# rather than the working directory. Resolve the root from __file__ so the
# script behaves identically from any CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Kept identical to the threshold the old AST gate enforced, so this change is
# behaviour-preserving. Raise it in a reviewed commit rather than by editing a
# literal buried in workflow YAML.
MIN_REGISTERED_TOOLS = 520

# A count alone does not prove the important tools survived a refactor, so pin
# the entry points that everything else builds on.
REQUIRED_TOOLS = (
    "mcp_opendaw_get_project_info",
    "mcp_opendaw_create_synth_track",
    "mcp_opendaw_add_effect",
    "mcp_opendaw_export_mix",
    "mcp_opendaw_transport",
)


def main() -> int:
    try:
        import server
    except ModuleNotFoundError as exc:
        if exc.name != "server":
            raise
        print(
            f"FAIL: could not import server.py from {REPO_ROOT}. "
            "Run this from a checkout of the repository.",
            file=sys.stderr,
        )
        return 1

    tools = asyncio.run(server.mcp.list_tools())
    names = {tool.name for tool in tools}

    if len(names) != len(tools):
        print(
            f"warning: {len(tools) - len(names)} duplicate tool name(s) registered",
            file=sys.stderr,
        )

    print(f"Registered MCP tools: {len(names)} (threshold: {MIN_REGISTERED_TOOLS})")

    failures: list[str] = []

    if len(names) < MIN_REGISTERED_TOOLS:
        failures.append(
            f"tool count regressed: {len(names)} registered, "
            f"expected at least {MIN_REGISTERED_TOOLS}"
        )

    missing = [name for name in REQUIRED_TOOLS if name not in names]
    if missing:
        failures.append("missing required tools: " + ", ".join(sorted(missing)))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Tool registry verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
