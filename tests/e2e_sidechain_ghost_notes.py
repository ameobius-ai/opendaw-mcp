"""E2E test: apply_sidechain and create_ghost_notes via headless DAW bridge."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Test", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create some notes for ghost notes test
    notes = [
        {"pitch": 38, "start": 0, "duration": 0.25, "velocity": 0.8},   # snare beat 1
        {"pitch": 38, "start": 2, "duration": 0.25, "velocity": 0.8},   # snare beat 3
    ]
    result = await server.mcp_opendaw_create_notes_batch(json.dumps(notes), uid, 0)
    data = json.loads(result)
    assert data.get("success"), f"notes_batch failed: {data}"
    print(f"Base notes: {data['notes_created']} notes")

    # 3. Test create_ghost_notes — add ghost snare hits
    result = await server.mcp_opendaw_create_ghost_notes(
        unit_index=uid, track_index=0, region_index=-1,
        density=0.4, velocity=0.3, seed=42,
    )
    data = json.loads(result)
    assert data.get("success"), f"ghost_notes failed: {data}"
    assert data["ghost_notes_added"] > 0, "Expected ghost notes to be added"
    print(f"ghost_notes: {data['ghost_notes_added']} added at density={data['density']}")

    # 4. Test ghost_notes error handling
    result = await server.mcp_opendaw_create_ghost_notes(
        unit_index=uid, density=1.5, velocity=0.3,
    )
    assert "Error" in result, f"Expected error for density=1.5, got: {result}"
    print("Error handling: density=1.5 ✅")

    result = await server.mcp_opendaw_create_ghost_notes(
        unit_index=uid, density=0.3, velocity=0.7,
    )
    assert "Error" in result, f"Expected error for velocity=0.7, got: {result}"
    print("Error handling: velocity=0.7 (>0.5) ✅")

    # 5. Test apply_sidechain
    result = await server.mcp_opendaw_apply_sidechain(
        unit_index=uid, bars=4, depth=0.6, attack=0.01, release=0.3, kick_interval=1.0,
    )
    data = json.loads(result)
    assert data.get("success"), f"apply_sidechain failed: {data}"
    assert data["total_events"] > 0, "Expected sidechain events to be created"
    assert data["num_kicks"] == 16, f"Expected 16 kicks (4 bars × 4), got {data['num_kicks']}"
    print(f"apply_sidechain: {data['total_events']} events, {data['num_kicks']} kicks over {data['bars']} bars")

    # 6. Test sidechain error handling
    result = await server.mcp_opendaw_apply_sidechain(
        unit_index=uid, bars=4, depth=1.5,
    )
    assert "Error" in result, f"Expected error for depth=1.5, got: {result}"
    print("Error handling: depth=1.5 ✅")

    result = await server.mcp_opendaw_apply_sidechain(
        unit_index=uid, bars=20, depth=0.6,
    )
    assert "Error" in result, f"Expected error for bars=20, got: {result}"
    print("Error handling: bars=20 ✅")

    await server.bridge.stop()
    print("\nAll E2E tests passed ✅")


if __name__ == "__main__":
    asyncio.run(main())
