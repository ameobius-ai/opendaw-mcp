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
    import server

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
