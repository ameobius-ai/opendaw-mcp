#!/usr/bin/env python3
"""Example: create_melodic_polyrhythm — N notes across M beats.

Creates a melodic polyrhythm: numerator notes evenly spaced across
denominator beats. Notes ascend/descend through a scale or use custom
pitches. 3:4 = triplet feel, 5:4 = quintuplet, 7:4 = septuplet.

Usage:
    python3 examples/example_create_melodic_polyrhythm.py
"""

import asyncio
from server import mcp_opendaw_create_melodic_polyrhythm


async def main():
    # 3:4 polyrhythm — triplet feel ascending C major
    result = await mcp_opendaw_create_melodic_polyrhythm(
        unit_index=0,
        track_index=0,
        numerator=3,
        denominator=4,
        bars=2,
        scale="major",
        root="C",
        direction="up",
        velocity_pattern="accent",
    )
    print(f"3:4 triplet polyrhythm: {result}")

    # 5:4 quintuplet — descending D minor
    result2 = await mcp_opendaw_create_melodic_polyrhythm(
        unit_index=0,
        track_index=0,
        numerator=5,
        denominator=4,
        bars=1,
        scale="minor",
        root="D",
        direction="down",
        velocity_pattern="fade",
    )
    print(f"5:4 quintuplet: {result2}")

    # 7:4 septuplet — custom pitches, wave velocity
    result3 = await mcp_opendaw_create_melodic_polyrhythm(
        unit_index=0,
        track_index=0,
        numerator=7,
        denominator=4,
        bars=1,
        pitches="60,62,64,67,69,72,74",
        velocity_pattern="wave",
        start_beat=8.0,
    )
    print(f"7:4 septuplet (custom): {result3}")


if __name__ == "__main__":
    asyncio.run(main())
