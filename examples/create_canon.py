#!/usr/bin/env python3
"""Example: create_canon — strict melodic imitation with delayed voice entries.

Creates a 4-voice canon (Pachelbel-style) with fifth and octave transpositions.
Each voice enters 4 beats after the previous one, creating overlapping imitative
counterpoint — the foundation of rounds, fugues, and film score layering.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_canon,
)


async def main():
    await bridge.start()

    # Create a synth track for the canon
    r = await mcp_opendaw_create_synth_track(name="Canon Voices", synth_type="vaporisateur")
    print(f"Track: {r[:80]}")

    # 4-voice canon: unison → fifth → octave → octave+fifth
    # Each voice enters one bar (4 beats) after the previous
    r = await mcp_opendaw_create_canon(
        melody="60,62,64,65,67,65,64,62",  # C-D-E-F-G-F-E-D
        voices=4,
        entry_delay_beats=4,
        transposition="0,7,12,19",  # unison, fifth, octave, octave+fifth
        velocity_decay=0.1,
        direction="up",
    )
    print(f"Canon: {r}")


if __name__ == "__main__":
    asyncio.run(main())
