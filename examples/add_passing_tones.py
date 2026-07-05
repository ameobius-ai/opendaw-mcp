"""add_passing_tones — diatonic passing tones for smoother melodic lines.

Inserts scale-tone passing notes between existing notes where the
interval is larger than a 2nd. Fundamental counterpoint technique:
Bach inventions, jazz walking lines, pop melismas.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_add_passing_tones


async def main():
    # C major, auto direction, max interval = perfect 5th
    result = await mcp_opendaw_add_passing_tones(
        unit_index=0,
        track_index=0,
        region_index=0,
        scale="major",
        root="C",
        max_interval=7,
        velocity=0.6,
        duration_fraction=0.5,
        direction="auto",
    )
    print("C major passing tones, auto direction:")
    print(result)
    print()

    # D minor, nearest direction, cross-track to preserve original
    result = await mcp_opendaw_add_passing_tones(
        unit_index=0,
        track_index=0,
        region_index=0,
        scale="minor",
        root="D",
        max_interval=5,
        direction="nearest",
        cross_track=1,
    )
    print("D minor passing tones, nearest, cross-track:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
