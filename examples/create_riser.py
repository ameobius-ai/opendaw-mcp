"""
Example: Build-up riser using create_riser.

Demonstrates three riser styles:
1. Long exponential riser (4 bars, 32 steps, C2→C6) — classic EDM build-up
2. Short linear snare-rush style (1 bar, 16 steps) — quick transition
3. Logarithmic riser (2 bars, 64 steps) — fast start, slow landing

Run: python examples/create_riser.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_riser,
    mcp_opendaw_save_project,
)


async def main():
    await bridge.start()

    # Create a synth track for the riser
    r = await mcp_opendaw_create_synth_track("riser_synth", "vaporisateur")
    print(f"Synth track: {r}")

    # 1. Long exponential riser — 4 bars, C2→C6, 32 steps
    #    Slow start, accelerating toward the drop
    r1 = await mcp_opendaw_create_riser(
        unit_index=-1,
        start_beat=0,
        length_beats=16,
        start_pitch=36,
        end_pitch=84,
        steps=32,
        curve="exp",
        velocity=0.7,
    )
    print(f"1. Long exp riser (4 bars, C2→C6): {r1}")

    # 2. Short linear riser — 1 bar, 16 steps, tight range
    #    Quick transition fill between sections
    r2 = await mcp_opendaw_create_riser(
        unit_index=-1,
        start_beat=16,
        length_beats=4,
        start_pitch=48,
        end_pitch=72,
        steps=16,
        curve="linear",
        velocity=0.8,
    )
    print(f"2. Short linear riser (1 bar, C3→C5): {r2}")

    # 3. Logarithmic riser — 2 bars, 64 steps
    #    Fast start, slow landing — reversed feel
    r3 = await mcp_opendaw_create_riser(
        unit_index=-1,
        start_beat=20,
        length_beats=8,
        start_pitch=40,
        end_pitch=79,
        steps=64,
        curve="log",
        velocity=0.65,
    )
    print(f"3. Log riser (2 bars, 64 steps): {r3}")

    # Save
    r4 = await mcp_opendaw_save_project("riser_demo")
    print(f"\nSaved: {r4}")

    await bridge.stop()
    print("\n✅ Riser demo complete — 3 curves across 7 bars")


if __name__ == "__main__":
    asyncio.run(main())
