"""add_suspension — suspension-resolution non-chord tone technique.

Adds preparation → suspension → resolution structures to existing notes
on strong beats. One of the most expressive devices in Western music:
Bach chorales, jazz ballads, film scores all rely on suspensions for
emotional tension-release.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_add_suspension


async def main():
    # C major, down resolution (classic 4-3 suspension)
    result = await mcp_opendaw_add_suspension(
        unit_index=0,
        track_index=0,
        region_index=0,
        scale="major",
        root="C",
        resolution="down",
        suspension_offset=2,
        preparation_beats=0.5,
        suspension_velocity=0.75,
        resolution_velocity=0.65,
    )
    print("C major suspensions, down resolution:")
    print(result)
    print()

    # A minor, both directions, cross-track
    result = await mcp_opendaw_add_suspension(
        unit_index=0,
        track_index=0,
        region_index=0,
        scale="minor",
        root="A",
        resolution="both",
        cross_track=1,
    )
    print("A minor suspensions, alternating directions, cross-track:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
