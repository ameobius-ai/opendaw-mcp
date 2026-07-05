"""Example: apply_swing — add groove to a straight 16th-note hi-hat pattern."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Swung Beat", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create a straight 16th-note pattern (8 notes on the grid)
    notes = [
        {"pitch": 42, "start": i * 0.25, "duration": 0.125, "velocity": 0.6}
        for i in range(8)
    ]
    result = await server.mcp_opendaw_create_notes_batch(json.dumps(notes), uid, 0)
    print(f"Created {json.loads(result)['notes_created']} straight 16th notes")

    # 3. Apply classic hip-hop swing (0.58 on 16th grid)
    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=0.58, grid="16th"
    )
    data = json.loads(result)
    print(f"Swing applied: {data['total_notes_shifted']} notes shifted (0.58, 16th)")

    # 4. Try light swing on 8th grid
    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=0.4, grid="8th"
    )
    data = json.loads(result)
    print(f"8th swing: {data['total_notes_shifted']} notes shifted (0.4, 8th)")

    await server.bridge.stop()
    print("\nDone! The hi-hats now have that classic laid-back groove.")


if __name__ == "__main__":
    asyncio.run(main())
