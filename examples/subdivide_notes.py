"""Example: subdivide_notes — rhythmic fragmentation of a melody.

Creates a simple 4-note melody (quarter notes), then subdivides each
into 4 sixteenth notes with an ascending pitch pattern and decrescendo
velocity — creating a flowing passagework from sustained notes.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_subdivide_notes


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="Fragmented")
    print("Track:", track_result[:200])

    # 2. Create 4 quarter notes: C-D-E-F
    notes = [
        {"pitch": 60, "position": 0.0, "duration": 1.0, "velocity": 0.8},  # C4
        {"pitch": 62, "position": 1.0, "duration": 1.0, "velocity": 0.8},  # D4
        {"pitch": 64, "position": 2.0, "duration": 1.0, "velocity": 0.8},  # E4
        {"pitch": 65, "position": 3.0, "duration": 1.0, "velocity": 0.8},  # F4
    ]
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Original:", notes_result[:200])

    # 3. Subdivide each into 4 parts, ascending pitch, decrescendo
    sub_result = await mcp_opendaw_subdivide_notes(
        unit_index=0,
        track_index=0,
        region_index=-1,
        subdivisions=4,
        pitch_pattern="scale_up",
        velocity_pattern="decrescendo",
        accent_first=True,
    )
    print("Subdivided:", sub_result[:300])


if __name__ == "__main__":
    asyncio.run(main())
