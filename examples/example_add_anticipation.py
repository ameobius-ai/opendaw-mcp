#!/usr/bin/env python3
"""Example: add_anticipation — add anticipation notes before strong beats.

Creates forward rhythmic motion by placing notes early on weak beats,
anticipating the pitch of upcoming strong-beat notes. Jazz syncopation,
pop vocal anticipations, salsa montuno, funk guitar stabs.

Usage:
    python3 examples/example_add_anticipation.py
"""

import asyncio
from server import mcp_opendaw_add_anticipation


async def main():
    # Classic jazz syncopation — same pitch anticipation
    result = await mcp_opendaw_add_anticipation(
        unit_index=0,
        track_index=0,
        scale="major",
        root="C",
        direction="auto",
        anticipation_offset=0.25,
        anticipation_fraction=0.33,
        anticipation_velocity=0.55,
        min_duration_beats=1.5,
    )
    print(f"Auto anticipations: {result}")

    # Funk guitar stabs — approach from previous note direction
    result2 = await mcp_opendaw_add_anticipation(
        unit_index=0,
        track_index=0,
        scale="minor",
        root="F",
        direction="approach",
        anticipation_offset=0.125,
        anticipation_fraction=0.5,
        anticipation_velocity=0.7,
        min_duration_beats=1.0,
        cross_track=1,
    )
    print(f"Approach anticipations (cross-track): {result2}")


if __name__ == "__main__":
    asyncio.run(main())
