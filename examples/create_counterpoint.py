"""
Example: Generate counter-melody in contrary motion.

Creates a counter-melody that moves in the opposite direction of the source melody.
When the melody goes up, the counterpoint goes down — classic contrapuntal technique.
Mirrors the melody around a center pitch.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a melody synth track
    result = await server.mcp_opendaw_create_synth_track("Melody", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Melody synth: unit_index={uid}")

    # 2. Create an ascending melody (C major scale)
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
    print("Created 8-note ascending melody (C4 → C5)")

    # 3. Generate counterpoint — contrary motion
    # The counterpoint will descend while the melody ascends
    result = await server.mcp_opendaw_create_counterpoint(
        unit_index=uid,
        track_index=0,
        region_index=0,
        center=59,  # B3 — center of the mirror
        interval=7  # max interval from center
    )
    data = json.loads(result)
    print(f"\nCounterpoint: {json.dumps(data, indent=2)}")

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
