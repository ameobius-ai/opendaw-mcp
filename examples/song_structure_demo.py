"""
Song Structure + Automation Sweep Demo.

Shows how to build a complete song arrangement in 4 orchestration calls
instead of 40+ low-level calls:

1. create_song_structure — arrangement markers (intro/verse/chorus/outro)
2. create_genre_track — full track with synth, drums, bass, chords
3. automation_sweep — filter sweep on the synth
4. add_mastering_chain — EQ + compressor + maximizer

Total: 4 API calls to produce a complete, mastered, structured track.
Without orchestration: 60-100+ low-level calls.
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

            # === Step 1: Create song structure markers ===
            print("=== Step 1: create_song_structure ===")
            result = await session.call_tool("create_song_structure", {
                "sections": json.dumps([
                    {"name": "Intro", "bars": 4},
                    {"name": "Verse", "bars": 8},
                    {"name": "Chorus", "bars": 8},
                    {"name": "Verse 2", "bars": 8},
                    {"name": "Chorus", "bars": 8},
                    {"name": "Outro", "bars": 4},
                ]),
            })
            print(result.content[0].text)
            print()

            # === Step 2: Create a lofi genre track ===
            print("=== Step 2: create_genre_track('lofi') ===")
            result = await session.call_tool("create_genre_track", {
                "genre": "lofi",
            })
            print(result.content[0].text)
            print()

            # === Step 3: Add a filter sweep on the synth ===
            print("=== Step 3: automation_sweep (filter cutoff) ===")
            result = await session.call_tool("automation_sweep", {
                "unit_index": 0,
                "parameter_name": "cutoff",
                "start_beat": 0,
                "end_beat": 16,  # sweep over the intro
                "start_value": 0.1,  # closed filter
                "end_value": 0.9,   # open filter
                "steps": 32,
                "curve": "exp",  # exponential = natural filter opening
            })
            print(result.content[0].text)
            print()

            # === Step 4: Master the output ===
            print("=== Step 4: add_mastering_chain ===")
            result = await session.call_tool("add_mastering_chain", {
                "target_lufs": -14,
                "style": "warm",
            })
            print(result.content[0].text)
            print()

            # === Step 5: Render ===
            print("=== Step 5: render_full ===")
            result = await session.call_tool("render_full", {
                "filename": "structured_lofi",
            })
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
