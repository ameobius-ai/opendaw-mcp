"""apply_velocity_lfo — periodic velocity modulation along note positions.

Demonstrates sine-wave velocity LFO on a drum track, creating a
"breathing" pumping effect synced to beat positions.
"""
import asyncio
import json
from server import (
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_apply_velocity_lfo,
    mcp_opendaw_list_tracks,
)


async def main():
    # 1. list tracks
    tracks = await mcp_opendaw_list_tracks()
    print("Tracks:", tracks[:200])

    # 2. create a note track with 16th-note hats
    result = await mcp_opendaw_create_note_track(unit_index=0, name="hats")
    print("Created track:", result[:200])

    notes = []
    for i in range(16):
        notes.append({
            "pitch": 42,
            "position": i * 240,  # 16th notes at 960 PPQN
            "duration": 120,
            "velocity": 0.7,
        })
    batch = await mcp_opendaw_create_notes_batch(
        unit_index=0, track_index=0, notes_json=json.dumps(notes)
    )
    print("Created 16 hats:", batch[:200])

    # 3. apply sine LFO: 1 cycle per beat, depth 0.4, center 0.7
    result = await mcp_opendaw_apply_velocity_lfo(
        unit_index=0, track_index=0,
        rate=1.0, depth=0.4, shape="sine", center=0.7
    )
    print("Sine LFO:", result[:300])

    # 4. try triangle at 0.5 cycles/beat (slow breathing)
    result2 = await mcp_opendaw_apply_velocity_lfo(
        unit_index=0, track_index=0,
        rate=0.5, depth=0.5, shape="triangle", center=0.6
    )
    print("Triangle LFO:", result2[:300])

    # 5. square wave for stutter effect
    result3 = await mcp_opendaw_apply_velocity_lfo(
        unit_index=0, track_index=0,
        rate=2.0, depth=0.8, shape="square", center=0.5
    )
    print("Square LFO:", result3[:300])


if __name__ == "__main__":
    asyncio.run(main())
