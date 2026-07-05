"""Example: repeat_notes — repeat a motif with ascending transposition.

Creates a 4-note motif, then repeats it 4 times going up a perfect fifth
(7 semitones) each cycle with slight velocity decay — a classic sequence
pattern used in baroque music and film scores.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_repeat_notes


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="Sequence")
    print("Track:", track_result[:200])

    # 2. Create a 4-note motif: C-E-G-C (ascending arpeggio)
    notes = [
        {"pitch": 60, "position": 0.0, "duration": 0.5, "velocity": 0.8},  # C4
        {"pitch": 64, "position": 0.5, "duration": 0.5, "velocity": 0.8},  # E4
        {"pitch": 67, "position": 1.0, "duration": 0.5, "velocity": 0.8},  # G4
        {"pitch": 72, "position": 1.5, "duration": 0.5, "velocity": 0.8},  # C5
    ]
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Motif:", notes_result[:200])

    # 3. Repeat 4 times, up a fifth each cycle, slight velocity decay
    repeat_result = await mcp_opendaw_repeat_notes(
        unit_index=0,
        track_index=0,
        region_index=-1,
        repeats=4,
        transpose_semitones=7,
        velocity_decay=0.85,
        time_gap_beats=0.0,
        direction="up",
    )
    print("Repeat:", repeat_result[:300])


if __name__ == "__main__":
    asyncio.run(main())
