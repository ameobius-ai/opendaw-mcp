"""Example: Split a note region at a bar boundary.

split_note_region divides a note region into two — notes at/after the split
point move to a new region, original is trimmed. Common use case: splitting
a long region into verse and chorus sections.
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_split_note_region,
    mcp_opendaw_list_notes,
)


async def main():
    # 1. Create a synth track with a region spanning 16 beats (4 bars)
    print("Creating track...")
    await mcp_opendaw_create_synth_track("Lead", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 16, "Full Section", -1)

    # 2. Add notes across the full 16-beat region
    notes = [
        {"pitch": 60, "position": 0, "duration": 1, "velocity": 0.8},   # bar 1
        {"pitch": 62, "position": 4, "duration": 1, "velocity": 0.8},   # bar 2
        {"pitch": 64, "position": 8, "duration": 1, "velocity": 0.9},   # bar 3
        {"pitch": 65, "position": 12, "duration": 1, "velocity": 0.9},  # bar 4
    ]
    await mcp_opendaw_create_notes_batch(notes, unit_index=0, track_index=0, region_index=0)

    # 3. Split at beat 8 (bar 3) — verse (bars 1-2) and chorus (bars 3-4)
    print("\nSplitting at beat 8...")
    result = await mcp_opendaw_split_note_region(0, 0, 0, 8)
    print(f"Split result: {result}")

    # 4. Verify — original region has 2 notes, new region has 2 notes
    print("\nOriginal region notes:")
    print(await mcp_opendaw_list_notes(0, 0, 0))
    print("\nNew region notes:")
    print(await mcp_opendaw_list_notes(0, 0, 1))


if __name__ == "__main__":
    asyncio.run(main())
