#!/usr/bin/env python3
"""Example: repeat_phrase — repeat a melodic phrase with transposition.

Copies all notes from a source region and repeats them N times, each
time transposed by a fixed interval. Diatonic (scale-preserving) or
chromatic transposition. Velocity patterns and time stretch available.

Usage:
    python3 examples/example_repeat_phrase.py
"""

import asyncio
from server import mcp_opendaw_repeat_phrase


async def main():
    # Ascending diatonic sequence in C major — 4 reps, up 2 scale steps each
    result = await mcp_opendaw_repeat_phrase(
        unit_index=0,
        track_index=0,
        repetitions=4,
        transpose_semitones=2,
        transpose_mode="diatonic",
        scale="major",
        root="C",
        velocity_pattern="crescendo",
        velocity_start=0.6,
        velocity_end=0.9,
    )
    print(f"Diatonic ascending sequence: {result}")

    # Descending chromatic with fade — film score build
    result2 = await mcp_opendaw_repeat_phrase(
        unit_index=0,
        track_index=0,
        repetitions=6,
        transpose_semitones=-3,
        transpose_mode="chromatic",
        velocity_pattern="fade_out",
        velocity_start=0.8,
        time_stretch=0.75,  # accelerating
        cross_track=1,
    )
    print(f"Chromatic descending (cross-track): {result2}")


if __name__ == "__main__":
    asyncio.run(main())
