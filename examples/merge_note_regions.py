"""Example: Merge two note regions into one.

merge_note_regions is the inverse of split_note_region — combines two
regions on the same track. Notes from region B are copied into A's
collection with positions adjusted to the absolute timeline.
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_split_note_region,
    mcp_opendaw_merge_note_regions,
    mcp_opendaw_list_notes,
)


async def main():
    # 1. Create track with a 16-beat region
    print("Creating track with 16-beat region...")
    await mcp_opendaw_create_synth_track("Lead", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 16, "Full Section", -1)

    notes = [
        {"pitch": 60, "position": 0, "duration": 1, "velocity": 0.8},
        {"pitch": 64, "position": 8, "duration": 1, "velocity": 0.9},
    ]
    await mcp_opendaw_create_notes_batch(notes, unit_index=0, track_index=0, region_index=0)

    # 2. Split at beat 8
    print("\nSplitting at beat 8...")
    result = await mcp_opendaw_split_note_region(0, 0, 0, 8)
    print(f"Split: {result}")

    # 3. Merge back — should restore original 16-beat region
    print("\nMerging regions 0 and 1 back together...")
    result = await mcp_opendaw_merge_note_regions(0, 0, 0, 1)
    print(f"Merge: {result}")

    # 4. Verify — should have 2 notes in one region
    print("\nNotes in merged region:")
    print(await mcp_opendaw_list_notes(0, 0, 0))


if __name__ == "__main__":
    asyncio.run(main())
