"""Example: Filter notes by pitch, velocity, and time range.

filter_notes is a multi-criteria note filter with three actions:
- list: show matching notes (read-only)
- delete: remove matching notes
- keep: remove non-matching notes (inverse filter)
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_filter_notes,
)


async def main():
    # 1. Create track with notes spanning a wide range
    print("Creating track with varied notes...")
    await mcp_opendaw_create_synth_track("Piano", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 16, "Section", -1)

    notes = [
        # Low notes (sub-bass range)
        {"pitch": 24, "position": 0, "duration": 4, "velocity": 0.9},
        {"pitch": 30, "position": 4, "duration": 4, "velocity": 0.9},
        # Mid range
        {"pitch": 60, "position": 0, "duration": 1, "velocity": 0.8},
        {"pitch": 64, "position": 2, "duration": 1, "velocity": 0.2},  # ghost
        {"pitch": 67, "position": 4, "duration": 1, "velocity": 0.8},
        # High range
        {"pitch": 84, "position": 8, "duration": 2, "velocity": 0.9},
        {"pitch": 88, "position": 12, "duration": 2, "velocity": 0.7},
    ]
    await mcp_opendaw_create_notes_batch(notes, unit_index=0, track_index=0, region_index=0)

    # 2. List notes below C2 (pitch 36) — sub-bass rumble
    print("\nNotes below C2:")
    result = await mcp_opendaw_filter_notes(0, 0, max_pitch=35, action="list")
    print(result)

    # 3. Delete sub-bass rumble
    print("\nDeleting sub-bass rumble:")
    result = await mcp_opendaw_filter_notes(0, 0, max_pitch=35, action="delete")
    print(result)

    # 4. Delete ghost notes (velocity < 0.3)
    print("\nDeleting ghost notes:")
    result = await mcp_opendaw_filter_notes(0, 0, max_velocity=0.29, action="delete")
    print(result)

    # 5. Keep only notes in bars 3-4 (beats 8-16)
    print("\nKeeping only bars 3-4:")
    result = await mcp_opendaw_filter_notes(0, 0, from_beat=8, to_beat=16, action="keep")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
