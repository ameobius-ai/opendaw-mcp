"""Example: insert_rests — create syncopation by removing notes.

Creates a steady 8th-note pattern (8 notes), then inserts rests on
the offbeats (0.5, 1.5, 2.5, 3.5) — removing those notes and creating
a syncopated rhythm from what was previously a straight pattern.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_insert_rests


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="Rests")
    print("Track:", track_result[:200])

    # 2. Create 8 eighth notes
    notes = []
    for i in range(8):
        notes.append({
            "pitch": 60,
            "position": float(i) * 0.5,
            "duration": 0.5,
            "velocity": 0.7,
        })
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Original:", notes_result[:200])

    # 3. Insert rests on offbeats
    rest_result = await mcp_opendaw_insert_rests(
        unit_index=0,
        track_index=0,
        region_index=-1,
        rest_positions="0.5,1.5,2.5,3.5",
        tolerance_beats=0.05,
        mode="delete",
        shorten_neighbors=False,
    )
    print("Rests:", rest_result[:300])


if __name__ == "__main__":
    asyncio.run(main())
