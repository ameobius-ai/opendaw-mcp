"""
Orchestration Tools Demo — build a full track in 3 calls instead of 30+.

This example demonstrates the high-level orchestration tools:
1. create_genre_track — synth + drums + bass + chords in one call
2. add_mastering_chain — EQ + compressor + maximizer in one call
3. render_full — render to WAV

Total: 3 API calls to produce a complete track.
Without orchestration tools, the same result requires 30-50 low-level calls.
"""

import json
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


async def main():
    params = StdioServerParameters(
        command="python", args=["server.py"],
        env={"OPENDAW_URL": "http://localhost:5174"}
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Connected: {len(tools.tools)} tools available\n")

            # === Step 1: Create a lofi track in ONE call ===
            print("=== Step 1: create_genre_track('lofi') ===")
            result = await session.call_tool("create_genre_track", {
                "genre": "lofi",
            })
            print(result.content[0].text)
            print()

            # === Step 2: Add mastering chain in ONE call ===
            print("=== Step 2: add_mastering_chain(style='warm') ===")
            result = await session.call_tool("add_mastering_chain", {
                "target_lufs": -14,
                "style": "warm",
            })
            print(result.content[0].text)
            print()

            # === Step 3: Render the full mix ===
            print("=== Step 3: render_full('lofi_demo') ===")
            result = await session.call_tool("render_full", {
                "filename": "lofi_demo",
            })
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
