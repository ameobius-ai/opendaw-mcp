"""
Example: Generate harmony parts from existing melody.

Creates diatonic thirds harmony above a C major melody.
Auto-creates a target synth track for the harmony.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a melody synth track
    result = await server.mcp_opendaw_create_synth_track("Lead", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Lead synth: unit_index={uid}")

    # 2. Create a simple melody in C major
    notes = json.dumps([
        [60, 0.0, 0.5, 0.75],  # C4
        [62, 0.5, 0.5, 0.75],  # D4
        [64, 1.0, 0.5, 0.75],  # E4
        [65, 1.5, 0.5, 0.75],  # F4
        [67, 2.0, 0.5, 0.75],  # G4
        [69, 2.5, 0.5, 0.75],  # A4
        [71, 3.0, 0.5, 0.75],  # B4
        [72, 3.5, 0.5, 0.75],  # C5
    ])
    await server.mcp_opendaw_create_notes_batch(notes, uid, 0)
    print("Created 8-note melody (C major scale ascending)")

    # 3. Generate harmony — diatonic thirds UP
    result = await server.mcp_opendaw_create_harmony(
        unit_index=uid,
        track_index=0,
        region_index=0,
        interval="thirds",
        direction="up"
    )
    data = json.loads(result)
    print(f"\nHarmony (thirds up): {json.dumps(data, indent=2)}")

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
