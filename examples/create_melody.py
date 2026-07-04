"""
Example: Create a melody using the create_melody orchestration tool.

Creates a C minor melody using scale degrees and rhythmic pattern.
Pattern syntax: 1-7 = scale degrees, 0 = rest, - = sustain previous note.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Melody", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Synth created: unit_index={uid}")

    # 2. Create a melody in C minor, 4th octave
    # Pattern: 1 3 5 - 4 2 0 1 (C Eb G . F D rest C)
    # Each step = 16th note (1 beat = 4 steps)
    result = await server.mcp_opendaw_create_melody(
        scale="minor",
        root="C",
        pattern="1 3 5 - 4 2 0 1 3 5 7 - 6 4 2 0",
        unit_index=uid,
        track_index=0,
        start_beat=0,
        octave=4,
        velocity=0.75
    )
    data = json.loads(result)
    print(f"Melody: {data.get('melody_notes', data.get('notes_created', 0))} notes")
    print(json.dumps(data, indent=2))

    # 3. Get project info to verify
    info = await server.mcp_opendaw_get_project_info()
    print(f"\nProject: {info}")

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
