"""
Example: Classic drum breaks using create_break.

Demonstrates four iconic breaks with different variations:
1. Amen Break — the most sampled break in history (jungle/DnB foundation)
2. Think Break — 2 bars with fill variation (hip-hop/breakbeat)
3. Funky Drummer — humanized (James Brown/Clyde Stubblefield)
4. When the Levee Breaks — with swing (boom-bap/hip-hop)

Run: python examples/create_break.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_break,
    mcp_opendaw_save_project,
)


async def main():
    await bridge.start()

    # Create a synth track for drums
    r = await mcp_opendaw_create_synth_track("break_drum", "vaporisateur")
    print(f"Synth track: {r}")

    # 1. Amen Break — 1 bar, the foundation of jungle/DnB
    r1 = await mcp_opendaw_create_break(
        break_type="amen",
        bars=1,
        unit_index=-1,
        start_beat=0,
    )
    print(f"\n1. Amen Break: {r1}")

    # 2. Think Break — 2 bars with fill on last bar
    r2 = await mcp_opendaw_create_break(
        break_type="think",
        bars=2,
        variation="fill",
        unit_index=-1,
        start_beat=4,
    )
    print(f"2. Think Break (2 bars, fill): {r2}")

    # 3. Funky Drummer — humanized for organic feel
    r3 = await mcp_opendaw_create_break(
        break_type="funky_drummer",
        bars=1,
        variation="humanize",
        unit_index=-1,
        start_beat=12,
    )
    print(f"3. Funky Drummer (humanized): {r3}")

    # 4. Synthetic break — with classic hip-hop swing
    r4 = await mcp_opendaw_create_break(
        break_type="synthetic",
        bars=2,
        variation="drop",
        swing=0.58,
        unit_index=-1,
        start_beat=16,
    )
    print(f"4. Synthetic (swing + drop): {r4}")

    # Save
    r5 = await mcp_opendaw_save_project("break_demo")
    print(f"\nSaved: {r5}")

    await bridge.stop()
    print("\n✅ Break demo complete — 4 classic breaks across 6 bars")


if __name__ == "__main__":
    asyncio.run(main())
