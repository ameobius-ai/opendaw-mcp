#!/usr/bin/env python3
"""Example: add_neighbor_tones — embellish a melody with upper/lower neighbors.

Adds neighbor tones to existing notes in a region. The note is split into
three parts: first_part (original pitch) → neighbor (one scale step away)
→ return (original pitch). This creates melodic interest without changing
the underlying harmony.

Usage:
    python3 examples/example_add_neighbor_tones.py
"""

import asyncio
from server import mcp_opendaw_add_neighbor_tones


async def main():
    # Upper neighbors in C major — classic Bach ornament style
    result = await mcp_opendaw_add_neighbor_tones(
        unit_index=0,
        track_index=0,
        scale="major",
        root="C",
        direction="upper",
        neighbor_fraction=0.25,
        neighbor_offset=0.5,
        neighbor_velocity=0.6,
        min_duration_beats=1.0,
    )
    print(f"Neighbor tones: {result}")

    # Alternating neighbors in D minor — jazz ballad fill style
    result2 = await mcp_opendaw_add_neighbor_tones(
        unit_index=0,
        track_index=0,
        scale="minor",
        root="D",
        direction="alternating",
        neighbor_fraction=0.15,
        neighbor_offset=0.3,
        neighbor_velocity=0.55,
        min_duration_beats=0.5,
        cross_track=1,  # preserve original melody on track 0
    )
    print(f"Alternating neighbors (cross-track): {result2}")


if __name__ == "__main__":
    asyncio.run(main())
