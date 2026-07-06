"""Example: Tuplet groups — irrational rhythm subdivisions.

This example demonstrates create_tuplet_group — dividing a time span into
N equal parts instead of the normal subdivision.
"""

import asyncio

from opendaw_mcp.server import mcp_opendaw_create_tuplet_group


async def main():
    # 1. Classic triplet — 3 notes in 1 beat (quarter note triplets)
    print("=== Triplet (3:2) ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="C",
        scale="major",
        tuplet_number=3,
        span_beats=1.0,
        base_division=2,
        repeats=4,
        pitch_mode="scale_asc",
        velocity=0.7,
        accent_first=True,
    )
    print(result)

    # 2. Quintuplet — 5 notes in 1 beat
    print("\n=== Quintuplet (5:4) ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="D",
        scale="minor",
        tuplet_number=5,
        span_beats=1.0,
        base_division=4,
        repeats=4,
        pitch_mode="chord",
        velocity=0.65,
    )
    print(result)

    # 3. Septuplet — 7 notes in 1 beat
    print("\n=== Septuplet (7:4) ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="A",
        scale="dorian",
        tuplet_number=7,
        span_beats=1.0,
        base_division=4,
        repeats=2,
        pitch_mode="scale_desc",
        velocity=0.6,
    )
    print(result)

    # 4. Triplet with rests — skip positions 1 and 3
    print("\n=== Triplet with Rests ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="E",
        scale="minor",
        tuplet_number=3,
        span_beats=2.0,
        base_division=2,
        repeats=4,
        pitch_mode="alternating",
        rest_positions="1",
        velocity=0.7,
    )
    print(result)

    # 5. Half-note triplets — 3 notes in 2 beats
    print("\n=== Half-note Triplet ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="G",
        scale="major",
        tuplet_number=3,
        span_beats=2.0,
        base_division=2,
        repeats=2,
        pitch_mode="scale_asc",
        velocity=0.7,
    )
    print(result)

    # 6. Repeated pitch septuplet — drum-roll feel
    print("\n=== Repeated Septuplet ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="C",
        scale="major",
        tuplet_number=7,
        span_beats=0.5,
        base_division=4,
        repeats=8,
        pitch_mode="repeated",
        velocity=0.6,
        accent_first=True,
    )
    print(result)

    # 7. Extreme: 11-tuplet in a quarter note
    print("\n=== Undecuplet (11:4) ===")
    result = await mcp_opendaw_create_tuplet_group(
        root="F#",
        scale="major",
        tuplet_number=11,
        span_beats=1.0,
        base_division=4,
        repeats=2,
        pitch_mode="scale_asc",
        velocity=0.55,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
