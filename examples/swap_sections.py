"""swap_sections — exchange two sections on the timeline.

Demonstrates swapping a verse (beats 0-8) with a chorus (beats 16-32)
to try a different song structure.
"""
import asyncio
from server import (
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_swap_sections,
    mcp_opendaw_list_tracks,
)
import json


async def main():
    # 1. list tracks
    tracks = await mcp_opendaw_list_tracks()
    print("Tracks:", tracks[:200])

    # 2. create a note track
    result = await mcp_opendaw_create_note_track(unit_index=0, name="song")
    print("Created track:", result[:200])

    # 3. create verse notes (beats 0-8) and chorus notes (beats 16-32)
    verse_notes = [
        {"pitch": 60, "position": 0,      "duration": 480, "velocity": 0.7},
        {"pitch": 64, "position": 960,    "duration": 480, "velocity": 0.7},
        {"pitch": 67, "position": 1920,   "duration": 480, "velocity": 0.7},
        {"pitch": 72, "position": 2880,   "duration": 480, "velocity": 0.7},
        {"pitch": 60, "position": 3840,   "duration": 480, "velocity": 0.7},
        {"pitch": 64, "position": 4800,   "duration": 480, "velocity": 0.7},
        {"pitch": 67, "position": 5760,   "duration": 480, "velocity": 0.7},
        {"pitch": 72, "position": 6720,   "duration": 480, "velocity": 0.7},
    ]
    chorus_notes = [
        {"pitch": 65, "position": 15360,  "duration": 480, "velocity": 0.9},
        {"pitch": 69, "position": 16320,  "duration": 480, "velocity": 0.9},
        {"pitch": 72, "position": 17280,  "duration": 480, "velocity": 0.9},
        {"pitch": 77, "position": 18240,  "duration": 480, "velocity": 0.9},
        {"pitch": 65, "position": 19200,  "duration": 480, "velocity": 0.9},
        {"pitch": 69, "position": 20160,  "duration": 480, "velocity": 0.9},
        {"pitch": 72, "position": 21120,  "duration": 480, "velocity": 0.9},
        {"pitch": 77, "position": 22080,  "duration": 480, "velocity": 0.9},
        {"pitch": 65, "position": 23040,  "duration": 480, "velocity": 0.9},
        {"pitch": 69, "position": 24000,  "duration": 480, "velocity": 0.9},
        {"pitch": 72, "position": 24960,  "duration": 480, "velocity": 0.9},
        {"pitch": 77, "position": 25920,  "duration": 480, "velocity": 0.9},
        {"pitch": 65, "position": 26880,  "duration": 480, "velocity": 0.9},
        {"pitch": 69, "position": 27840,  "duration": 480, "velocity": 0.9},
        {"pitch": 72, "position": 28800,  "duration": 480, "velocity": 0.9},
        {"pitch": 77, "position": 29760,  "duration": 480, "velocity": 0.9},
    ]

    all_notes = verse_notes + chorus_notes
    batch = await mcp_opendaw_create_notes_batch(
        unit_index=0, track_index=0, notes_json=json.dumps(all_notes)
    )
    print("Created notes:", batch[:200])

    # 4. swap verse (0-8) with chorus (16-32)
    result = await mcp_opendaw_swap_sections(
        section1_start=0, section1_end=8,
        section2_start=16, section2_end=32
    )
    print("Swap result:", result[:300])


if __name__ == "__main__":
    asyncio.run(main())
