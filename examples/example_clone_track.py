#!/usr/bin/env python3
"""Example: clone_track — full track duplication with transforms.

Creates a new track with all regions and notes from a source track.
Optional transpose, velocity_scale, time_offset, and new_unit for
separate audio unit creation.

Usage:
    python3 examples/example_clone_track.py
"""

import asyncio
from server import mcp_opendaw_clone_track


async def main():
    # Octave doubling — same notes one octave higher
    result = await mcp_opendaw_clone_track(
        unit_index=0,
        track_index=0,
        transpose=12,
        velocity_scale=0.8,
    )
    print(f"Octave doubling: {result}")

    # Parallel harmony — fifth above, time-shifted for call-and-response
    result2 = await mcp_opendaw_clone_track(
        unit_index=0,
        track_index=0,
        transpose=7,
        velocity_scale=0.6,
        time_offset_beats=2.0,
    )
    print(f"Parallel harmony: {result2}")

    # Full clone to new audio unit for layering with different instrument
    result3 = await mcp_opendaw_clone_track(
        unit_index=0,
        track_index=0,
        new_unit=True,
    )
    print(f"New unit clone: {result3}")


if __name__ == "__main__":
    asyncio.run(main())
