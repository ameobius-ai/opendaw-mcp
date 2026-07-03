"""
Example: Create a 4-bar drum beat with Playfield.

This script creates a basic four-on-the-floor pattern:
- Kick on every beat
- Snare on beats 2 and 4
- Hi-hat on every 8th note

Prerequisites:
- openDAW running on localhost:5174
- Vite dev server started
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a Playfield (drum machine) instrument
    result = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Playfield created: unit_index={uid}")

    # 2. Create a note track
    await server.mcp_opendaw_create_note_track(uid)
    print("Note track created")

    # 3. Create a 4-bar region (16 beats)
    await server.mcp_opendaw_create_track_region(uid, 0, 0, 16, "Beat", 15)
    print("Region created (4 bars)")

    # 4. Add kick notes (pitch 36 = C1 in GM drum map)
    # create_note(track_index, pitch, start_beat, duration_beats, velocity, unit_index)
    for beat in range(16):
        result = await server.mcp_opendaw_create_note(
            0, 36, beat, 0.5, 0.9, uid
        )
        print(f"  Kick at beat {beat}: {json.loads(result).get('success', '')}")

    # 5. Add snare notes (pitch 38 = D1) on beats 2 and 4 of each bar
    for bar in range(4):
        for beat in [1, 3]:
            pos = bar * 4 + beat
            result = await server.mcp_opendaw_create_note(
                0, 38, pos, 0.5, 0.8, uid
            )
            print(f"  Snare at bar {bar} beat {beat+1}: {json.loads(result).get('success', '')}")

    # 6. Add hi-hat notes (pitch 42 = F#1) on every 8th note
    for i in range(32):
        velocity = 0.5 if i % 2 == 0 else 0.3
        result = await server.mcp_opendaw_create_note(
            0, 42, i * 0.5, 0.25, velocity, uid
        )
        print(f"  Hi-hat {i}: {json.loads(result).get('success', '')}")

    print("\n4-bar drum beat created!")
    print("Kick: every beat | Snare: beats 2,4 | Hi-hat: every 8th")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
