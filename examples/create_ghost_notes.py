"""Example: create_ghost_notes — add groove with quiet grace notes."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("FunkDrums", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create a basic backbeat — snare on 2 and 4
    notes = [
        {"pitch": 38, "start": 1, "duration": 0.25, "velocity": 0.85},
        {"pitch": 38, "start": 3, "duration": 0.25, "velocity": 0.85},
        {"pitch": 36, "start": 0, "duration": 0.25, "velocity": 0.9},
        {"pitch": 36, "start": 2, "duration": 0.25, "velocity": 0.9},
    ]
    result = await server.mcp_opendaw_create_notes_batch(json.dumps(notes), uid, 0)
    print(f"Backbeat: {json.loads(result)['notes_created']} notes")

    # 3. Add ghost notes — sparse funk feel
    result = await server.mcp_opendaw_create_ghost_notes(
        unit_index=uid, density=0.3, velocity=0.25, seed=42,
    )
    data = json.loads(result)
    print(f"Funk ghosts: {data['ghost_notes_added']} ghost notes added")

    # 4. Add denser ghosts for R&B/neo-soul
    result = await server.mcp_opendaw_create_ghost_notes(
        unit_index=uid, density=0.45, velocity=0.35, seed=77,
    )
    data = json.loads(result)
    print(f"R&B ghosts: {data['ghost_notes_added']} ghost notes added")

    await server.bridge.stop()
    print("\nDone! Backbeat with ghost notes for groove.")


if __name__ == "__main__":
    asyncio.run(main())
