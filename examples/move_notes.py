"""move_notes — move MIDI notes from one track/region to another.

Demonstrates moving notes from a source track to a destination track,
with optional transpose and velocity scaling. Source notes are deleted
by default (delete_source=True).
"""
import asyncio
import json
from server import (
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_move_notes,
    mcp_opendaw_list_tracks,
)


async def main():
    # 1. list tracks
    tracks = await mcp_opendaw_list_tracks()
    print("Tracks:", tracks[:200])

    # 2. create source note track with notes
    src = await mcp_opendaw_create_note_track(unit_index=0, name="source")
    print("Source track:", src[:200])

    notes = [
        {"pitch": 60, "position": 0,    "duration": 480, "velocity": 0.8},
        {"pitch": 64, "position": 480,  "duration": 480, "velocity": 0.7},
        {"pitch": 67, "position": 960,  "duration": 480, "velocity": 0.9},
        {"pitch": 72, "position": 1440, "duration": 960, "velocity": 0.85},
    ]
    batch = await mcp_opendaw_create_notes_batch(
        unit_index=0, track_index=0, notes_json=json.dumps(notes)
    )
    print("Source notes:", batch[:200])

    # 3. create dest track
    dest = await mcp_opendaw_create_note_track(unit_index=0, name="dest")
    print("Dest track:", dest[:200])

    # 4. move notes: source track 0 → dest track 1, transpose +12, velocity 0.9
    result = await mcp_opendaw_move_notes(
        source_unit=0, source_track=0, source_region=0,
        dest_unit=0, dest_track=1,
        transpose=12, velocity_scale=0.9, delete_source=True
    )
    print("Move result:", result[:300])

    # 5. move without deleting (copy mode)
    # First re-add notes to source
    notes2 = [
        {"pitch": 55, "position": 0, "duration": 960, "velocity": 0.7},
    ]
    await mcp_opendaw_create_notes_batch(
        unit_index=0, track_index=0, notes_json=json.dumps(notes2)
    )

    result2 = await mcp_opendaw_move_notes(
        source_unit=0, source_track=0, source_region=1,
        dest_unit=0, dest_track=1,
        delete_source=False  # copy mode
    )
    print("Copy-mode result:", result2[:300])


if __name__ == "__main__":
    asyncio.run(main())
