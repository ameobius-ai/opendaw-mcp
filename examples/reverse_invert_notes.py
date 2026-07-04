"""
Example: Reverse and invert melodies — melodic variation tools.

reverse_notes: retrograde — reverses the order of notes in a region.
  Positions are mirrored, durations/velocities preserved.

invert_notes: mirror inversion around an axis pitch.
  newPitch = 2 * axis - oldPitch. Double inversion restores the original.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Variations", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create a melody to work with
    notes = json.dumps([
        [60, 0.0, 0.5, 0.75],  # C4
        [62, 0.5, 0.5, 0.75],  # D4
        [64, 1.0, 0.5, 0.75],  # E4
        [65, 1.5, 0.5, 0.75],  # F4
        [67, 2.0, 0.5, 0.75],  # G4
    ])
    await server.mcp_opendaw_create_notes_batch(notes, uid, 0)
    print("Created 5-note melody: C D E F G")

    # 3. Reverse the melody (retrograde)
    result = await server.mcp_opendaw_reverse_notes(
        unit_index=uid,
        track_index=0,
        region_index=0
    )
    data = json.loads(result)
    print(f"\nReversed: {json.dumps(data, indent=2)}")

    # 4. Invert around C4 (axis=60)
    # [60,62,64,65,67] → [60,58,56,55,53] (mirror around C4)
    result = await server.mcp_opendaw_invert_notes(
        unit_index=uid,
        track_index=0,
        region_index=0,
        axis=60  # C4
    )
    data = json.loads(result)
    print(f"\nInverted around C4: {json.dumps(data, indent=2)}")

    # 5. Invert again to restore the original
    result = await server.mcp_opendaw_invert_notes(
        unit_index=uid,
        track_index=0,
        region_index=0,
        axis=60
    )
    data = json.loads(result)
    print(f"\nDouble inversion (restored): {json.dumps(data, indent=2)}")

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
