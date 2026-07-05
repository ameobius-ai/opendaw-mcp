"""Example: merge_consecutive_notes — convert staccato to sustained.

Creates 8 staccato notes of the same pitch (C4) with small gaps,
then merges consecutive notes with a gap threshold of 0.25 beats
into fewer sustained notes — demonstrating cleanup of busy passages.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_merge_consecutive_notes


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="Merged")
    print("Track:", track_result[:200])

    # 2. Create 4 staccato C4 notes with 16th-note gaps
    notes = [
        {"pitch": 60, "position": 0.0, "duration": 0.375, "velocity": 0.8},  # C4 staccato
        {"pitch": 60, "position": 0.5, "duration": 0.375, "velocity": 0.8},  # C4 staccato
        {"pitch": 60, "position": 1.0, "duration": 0.375, "velocity": 0.8},  # C4 staccato
        {"pitch": 60, "position": 1.5, "duration": 0.375, "velocity": 0.8},  # C4 staccato
    ]
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Staccato:", notes_result[:200])

    # 3. Merge with 0.25 beat gap threshold
    merge_result = await mcp_opendaw_merge_consecutive_notes(
        unit_index=0,
        track_index=0,
        region_index=-1,
        same_pitch_only=True,
        max_gap_beats=0.25,
        velocity_mode="avg",
    )
    print("Merged:", merge_result[:300])


if __name__ == "__main__":
    asyncio.run(main())
