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

PPQN = 960  # 1 quarter note = 960 PPQN

async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a Playfield (drum machine) instrument
    result = await server.mcp_opendaw_create_synth("Playfield")
    data = json.loads(result)
    print(f"Playfield created: {data}")
    au_index = 0

    # 2. Create a note track
    result = await server.mcp_opendaw_create_note_track(au_index)
    data = json.loads(result)
    print(f"Note track: {data}")
    track_index = 0

    # 3. Create a 4-bar region (4 bars × 4 beats × 960 PPQN = 15360)
    result = await server.mcp_opendaw_create_note_region(au_index, track_index, 0, 15360)
    data = json.loads(result)
    print(f"Region: {data}")
    region_index = 0

    # 4. Add kick notes (pitch 36 = C1 in GM drum map)
    for beat in range(16):  # 16 beats = 4 bars
        pos = beat * PPQN
        result = await server.mcp_opendaw_create_note_event(
            au_index, track_index, region_index,
            position=pos, duration=PPQN // 2, pitch=36, velocity=0.9
        )
        print(f"  Kick at beat {beat}: {json.loads(result).get('success', '')}")

    # 5. Add snare notes (pitch 38 = D1) on beats 2 and 4 of each bar
    for bar in range(4):
        for beat in [1, 3]:  # beats 2 and 4 (0-indexed)
            pos = (bar * 4 + beat) * PPQN
            result = await server.mcp_opendaw_create_note_event(
                au_index, track_index, region_index,
                position=pos, duration=PPQN // 2, pitch=38, velocity=0.8
            )
            print(f"  Snare at bar {bar} beat {beat+1}: {json.loads(result).get('success', '')}")

    # 6. Add hi-hat notes (pitch 42 = F#1) on every 8th note
    for i in range(32):  # 32 eighth notes = 4 bars
        pos = i * PPQN // 2
        velocity = 0.5 if i % 2 == 0 else 0.3  # accent downbeats
        result = await server.mcp_opendaw_create_note_event(
            au_index, track_index, region_index,
            position=pos, duration=PPQN // 4, pitch=42, velocity=velocity
        )
        print(f"  Hi-hat {i}: {json.loads(result).get('success', '')}")

    print("\n4-bar drum beat created!")
    print("Kick: every beat | Snare: beats 2,4 | Hi-hat: every 8th")

    await server.bridge.stop()

if __name__ == "__main__":
    asyncio.run(main())
