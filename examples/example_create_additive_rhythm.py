"""Example: create_additive_rhythm — additive rhythm.

Bartok/Messiaen-style additive rhythm: unequal groupings within a bar.
3+2+2 = 7 eighth notes with accents on notes 1, 4, 6 — Bulgarian rhythm.
"""

import asyncio

from server import mcp_opendaw_create_additive_rhythm


async def main():
    # Bulgarian rhythm 3+2+2 in eighth notes
    result = await mcp_opendaw_create_additive_rhythm(
        grouping="3+2+2",
        unit="eighth",
        repeats=4,
        pitch="scale_up",
        scale="minor",
        root="A",
        octave=3,
        accent_velocity=0.95,
        normal_velocity=0.6,
        decay=0.08,
    )
    print("Bulgarian 3+2+2:", result)

    # Math rock 2+3+2 shifting accent
    result = await mcp_opendaw_create_additive_rhythm(
        grouping="2+3+2",
        unit="eighth",
        repeats=2,
        pitch="octave_bounce",
        root="D",
        octave=4,
    )
    print("Math rock 2+3+2:", result)

    # Stravinsky 5+3 with sixteenths
    result = await mcp_opendaw_create_additive_rhythm(
        grouping="5+3",
        unit="sixteenth",
        repeats=2,
        pitch="alternating",
        scale="phrygian",
        root="E",
    )
    print("Stravinsky 5+3:", result)


if __name__ == "__main__":
    asyncio.run(main())
