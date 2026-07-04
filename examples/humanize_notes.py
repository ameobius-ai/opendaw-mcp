"""
Example: Humanize MIDI notes for natural feel.

Adds velocity, timing, duration variation and swing to programmed notes.
Uses seeded PRNG (mulberry32) for reproducible results.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Humanized", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create some robotic notes first
    notes = json.dumps([
        [60, 0.0, 0.25, 0.75],
        [62, 0.25, 0.25, 0.75],
        [64, 0.5, 0.25, 0.75],
        [65, 0.75, 0.25, 0.75],
        [67, 1.0, 0.25, 0.75],
        [69, 1.25, 0.25, 0.75],
        [71, 1.5, 0.25, 0.75],
        [72, 1.75, 0.25, 0.75],
    ])
    await server.mcp_opendaw_create_notes_batch(notes, uid, 0)
    print("Created 8 robotic notes (uniform velocity 0.75)")

    # 3. Humanize with seed=42, moderate variation + swing
    result = await server.mcp_opendaw_humanize_notes(
        unit_index=uid,
        track_index=0,
        region_index=0,
        velocity_range=0.15,
        timing_range=0.02,
        duration_range=0.05,
        swing=0.5,
        seed=42
    )
    data = json.loads(result)
    print(f"\nHumanized: {json.dumps(data, indent=2)}")

    # 4. Different seed = different result (reproducible)
    result = await server.mcp_opendaw_humanize_notes(
        unit_index=uid,
        track_index=0,
        region_index=0,
        velocity_range=0.2,
        timing_range=0.03,
        duration_range=0.08,
        swing=0.6,
        seed=1337
    )
    data = json.loads(result)
    print(f"\nDifferent seed: {json.dumps(data, indent=2)}")

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
