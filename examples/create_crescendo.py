"""
Example: Apply crescendo and decrescendo to notes.

Gradually changes note velocities across a region. Useful for:
- Building tension (crescendo: low → high velocity)
- Fading out (decrescendo: high → low velocity)
- Three curve types: linear, exponential (starts slow), logarithmic (starts fast)
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Dynamics", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create a uniform-velocity melody (8 notes, all at 0.5)
    notes = json.dumps([
        {"pitch": 60, "start": 0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 62, "start": 0.5, "duration": 0.5, "velocity": 0.5},
        {"pitch": 64, "start": 1.0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 65, "start": 1.5, "duration": 0.5, "velocity": 0.5},
        {"pitch": 67, "start": 2.0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 69, "start": 2.5, "duration": 0.5, "velocity": 0.5},
        {"pitch": 71, "start": 3.0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 72, "start": 3.5, "duration": 0.5, "velocity": 0.5},
    ])
    await server.mcp_opendaw_create_notes_batch(notes, uid, 0)
    print("Created 8-note melody (uniform velocity 0.5)")

    # 3. Apply exponential crescendo (starts quiet, builds rapidly at end)
    result = await server.mcp_opendaw_create_crescendo(
        unit_index=uid, track_index=0, region_index=-1,
        start_velocity=0.2, end_velocity=0.95, curve="exp"
    )
    data = json.loads(result)
    print(f"Exp crescendo (0.2→0.95): {data['notes_modified']} notes modified")

    # 4. Create another melody for decrescendo demo
    notes2 = json.dumps([
        {"pitch": 72, "start": 0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 71, "start": 0.5, "duration": 0.5, "velocity": 0.5},
        {"pitch": 69, "start": 1.0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 67, "start": 1.5, "duration": 0.5, "velocity": 0.5},
        {"pitch": 65, "start": 2.0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 64, "start": 2.5, "duration": 0.5, "velocity": 0.5},
        {"pitch": 62, "start": 3.0, "duration": 0.5, "velocity": 0.5},
        {"pitch": 60, "start": 3.5, "duration": 0.5, "velocity": 0.5},
    ])

    # Need another track for the second melody
    await server.mcp_opendaw_create_note_track(uid)
    await server.mcp_opendaw_create_notes_batch(notes2, uid, 1)
    print("Created descending melody on track 1")

    # 5. Apply logarithmic decrescendo (starts loud, fades slowly)
    result = await server.mcp_opendaw_create_crescendo(
        unit_index=uid, track_index=1, region_index=-1,
        start_velocity=0.9, end_velocity=0.15, curve="log"
    )
    data = json.loads(result)
    print(f"Log decrescendo (0.9→0.15): {data['notes_modified']} notes modified")

    await server.bridge.stop()
    print("\nDone — crescendo and decrescendo applied")


if __name__ == "__main__":
    asyncio.run(main())
