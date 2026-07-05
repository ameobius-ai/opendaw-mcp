#!/usr/bin/env python3
"""Example: create_phase_shift — Steve Reich phasing technique.

Copies a source phrase and places it on a parallel track with a
gradually accumulating time offset. Each bar, the copy drifts further,
creating the classic "slipping" phase pattern of minimalism.

Usage:
    python3 examples/example_create_phase_shift.py
"""

import asyncio
from server import mcp_opendaw_create_phase_shift


async def main():
    # Slow forward phasing — 1/16 note drift per bar, 8 bars
    result = await mcp_opendaw_create_phase_shift(
        unit_index=0,
        track_index=0,
        shift_per_bar=0.0625,
        bars=8,
        direction="forward",
        cross_track=1,
        velocity_scale=0.85,
    )
    print(f"Forward phasing: {result}")

    # Fast backward phasing — 1/8 note drift, 4 bars
    result2 = await mcp_opendaw_create_phase_shift(
        unit_index=0,
        track_index=0,
        shift_per_bar=0.125,
        bars=4,
        direction="backward",
        cross_track=1,
        velocity_scale=0.7,
    )
    print(f"Backward phasing: {result2}")


if __name__ == "__main__":
    asyncio.run(main())
