"""
Example: Create a bassline using the create_bassline orchestration tool.

Creates a C minor bassline with root-fifth pattern and octave movement.
Low octave (C2=36) default, high velocity (0.9) for punch.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track for bass
    result = await server.mcp_opendaw_create_synth_track("Bass", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Bass synth: unit_index={uid}")

    # 2. Create a bassline: C _ _ _ G _ _ _ F _ _ _ C _ _ _
    # Pattern uses scale degrees: 1=root, 5=fifth, 4=fourth
    # _ = sustain (holds the note), 0 = rest
    result = await server.mcp_opendaw_create_bassline(
        root="C",
        pattern="1 0 0 0 5 0 0 0 4 0 0 0 1 0 1 0",
        unit_index=uid,
        track_index=0,
        start_beat=0,
        octave=2,
        velocity=0.9,
        scale="minor"
    )
    data = json.loads(result)
    print(f"Bassline: {data.get('bassline_notes', data.get('notes_created', 0))} notes")
    print(json.dumps(data, indent=2))

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
