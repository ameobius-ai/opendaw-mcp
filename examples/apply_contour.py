"""apply_contour — reshape melodic direction of existing notes.

Takes notes in a region and redistributes their pitches to follow
a specified contour shape. Complements analyze_melody (which extracts
contour from existing notes).
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_apply_contour


async def main():
    # Arch contour: rise then fall, 1 octave range, C major snap
    result = await mcp_opendaw_apply_contour(
        unit_index=0,
        track_index=0,
        region_index=0,
        contour="arch",
        range_semitones=12,
        snap_to_scale="major",
        root="C",
    )
    print("Arch contour, C major, 1 octave:")
    print(result)
    print()

    # Wave contour: sinusoidal, 2 octave range
    result = await mcp_opendaw_apply_contour(
        unit_index=0,
        track_index=0,
        region_index=0,
        contour="wave",
        range_semitones=24,
        preserve_first=True,
        preserve_last=True,
    )
    print("Wave contour, 2 octaves, preserve endpoints:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
