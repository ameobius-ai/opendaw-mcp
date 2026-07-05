"""Example: expand_intervals — widen a melody's intervals.

Creates a simple stepwise melody (C-D-E-F), then expands all intervals
by factor 2.0 — each second becomes a third, creating a wider, more
expressive contour. Anchored on the first note so the melody starts
from the same pitch but reaches higher.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_expand_intervals


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="Expanded")
    print("Track:", track_result[:200])

    # 2. Create stepwise melody: C-D-E-F (all seconds)
    notes = [
        {"pitch": 60, "position": 0.0, "duration": 0.5, "velocity": 0.8},
        {"pitch": 62, "position": 0.5, "duration": 0.5, "velocity": 0.8},
        {"pitch": 64, "position": 1.0, "duration": 0.5, "velocity": 0.8},
        {"pitch": 65, "position": 1.5, "duration": 0.5, "velocity": 0.8},
    ]
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Original:", notes_result[:200])

    # 3. Expand intervals by 2.0, anchor on first, snap to major
    expand_result = await mcp_opendaw_expand_intervals(
        unit_index=0,
        track_index=0,
        region_index=-1,
        factor=2.0,
        anchor="first",
        snap_to_scale="major",
        root="C",
    )
    print("Expanded:", expand_result[:400])


if __name__ == "__main__":
    asyncio.run(main())
