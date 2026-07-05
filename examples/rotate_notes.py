"""Example: rotate_notes — cyclic permutation of a melody.

Creates a 4-note melody (C-E-G-C), then rotates it by 1 position
on the pitch axis — the first pitch moves to the end, creating
a new melodic variation while keeping the same rhythmic positions.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_rotate_notes


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="Rotated")
    print("Track:", track_result[:200])

    # 2. Create a 4-note melody: C-E-G-C
    notes = [
        {"pitch": 60, "position": 0.0, "duration": 0.5, "velocity": 0.8},
        {"pitch": 64, "position": 0.5, "duration": 0.5, "velocity": 0.8},
        {"pitch": 67, "position": 1.0, "duration": 0.5, "velocity": 0.8},
        {"pitch": 72, "position": 1.5, "duration": 0.5, "velocity": 0.8},
    ]
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Original:", notes_result[:200])

    # 3. Rotate by 1 on pitch axis
    rotate_result = await mcp_opendaw_rotate_notes(
        unit_index=0,
        track_index=0,
        region_index=-1,
        rotate_by=1,
        axis="pitch",
        preserve_pitch_contour=False,
    )
    print("Rotated:", rotate_result[:300])


if __name__ == "__main__":
    asyncio.run(main())
