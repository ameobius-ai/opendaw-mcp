"""merge_note_tracks — combine notes from two tracks into one.

Consolidates note data from a source track into a destination track,
resolving overlaps intelligently. Typical use cases:
- Merge doubled melody into main melody
- Flatten multi-track MIDI into single instrument
- Combine counterpoint into harmony track
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_merge_note_tracks


async def main():
    # Merge track 1 into track 0, keeping higher velocity notes on conflict
    result = await mcp_opendaw_merge_note_tracks(
        source_unit=0,
        source_track=1,
        dest_unit=0,
        dest_track=0,
        delete_source=True,
        resolve_overlaps="keep_higher_velocity",
    )
    print("Merge with keep_higher_velocity:")
    print(result)
    print()

    # Merge with transpose — octave up source, shorten earlier on overlap
    result = await mcp_opendaw_merge_note_tracks(
        source_unit=0,
        source_track=1,
        dest_unit=0,
        dest_track=0,
        delete_source=False,
        resolve_overlaps="shorten_earlier",
        transpose=12,
    )
    print("Merge with transpose +12, shorten_earlier:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
