"""Example: randomize_note_durations — generative duration variation.

Creates 8 equal quarter notes, then randomizes their durations with
jitter distribution — small perturbations that add organic feel
without destroying the phrase structure.
"""
import asyncio
import os

os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")

from server import mcp_opendaw_create_note_track, mcp_opendaw_create_notes_batch, mcp_opendaw_randomize_note_durations


async def main():
    # 1. Create a note track
    track_result = await mcp_opendaw_create_note_track(name="RandDur")
    print("Track:", track_result[:200])

    # 2. Create 8 quarter notes (scale ascending)
    notes = []
    for i in range(8):
        notes.append({
            "pitch": 60 + i,
            "position": float(i),
            "duration": 1.0,
            "velocity": 0.7,
        })
    notes_result = await mcp_opendaw_create_notes_batch(
        pattern=str(notes),
        unit_index=0,
        track_index=0,
    )
    print("Original:", notes_result[:200])

    # 3. Randomize durations with jitter
    rand_result = await mcp_opendaw_randomize_note_durations(
        unit_index=0,
        track_index=0,
        region_index=-1,
        variation=0.4,
        distribution="jitter",
        min_duration_beats=0.125,
        max_duration_beats=2.0,
        preserve_total=False,
        seed=123,
    )
    print("Randomized:", rand_result[:300])


if __name__ == "__main__":
    asyncio.run(main())
