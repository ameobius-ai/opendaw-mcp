"""E2E test: create_drum_fill, create_ostinato, create_crescendo."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Test", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Test drum_fill — build type, 1 bar
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="build", bars=1, start_beat=0, density="medium"
    )
    data = json.loads(result)
    assert data.get("success"), f"drum_fill failed: {data}"
    assert data["total_notes"] > 0, "drum_fill created 0 notes"
    print(f"drum_fill (build, 1 bar): {data['total_notes']} notes, lanes={data['lanes']}")

    # 3. Test drum_fill — roll type, 2 bars
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="roll", bars=2, start_beat=4, density="dense"
    )
    data = json.loads(result)
    assert data.get("success"), f"roll failed: {data}"
    print(f"drum_fill (roll, 2 bars): {data['total_notes']} notes")

    # 4. Test ostinato — C minor, pattern 1 5 3 5, 4 repeats
    result = await server.mcp_opendaw_create_ostinato(
        scale="minor", root="C", pattern="1 5 3 5",
        unit_index=uid, track_index=0, start_beat=0, repeats=4, octave=4, velocity=0.7
    )
    data = json.loads(result)
    assert data.get("success"), f"ostinato failed: {data}"
    print(f"ostinato (C minor 1-5-3-5 x4): {data}")

    # 5. Test crescendo on the ostinato region
    result = await server.mcp_opendaw_create_crescendo(
        unit_index=uid, track_index=0, region_index=-1,
        start_velocity=0.2, end_velocity=0.9, curve="exp"
    )
    data = json.loads(result)
    assert data.get("success"), f"crescendo failed: {data}"
    assert data["notes_modified"] > 0, "crescendo modified 0 notes"
    print(f"crescendo (exp, 0.2→0.9): {data['notes_modified']} notes modified")

    # 6. Test error handling
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="invalid", bars=1
    )
    assert "Error" in result, f"Expected error for invalid fill_type, got: {result}"
    print("Error handling: invalid fill_type ✅")

    result = await server.mcp_opendaw_create_ostinato(
        scale="minor", root="C", pattern="1 5 3 5", repeats=0
    )
    assert "Error" in result, f"Expected error for repeats=0, got: {result}"
    print("Error handling: repeats=0 ✅")

    await server.bridge.stop()
    print("\nAll E2E tests passed ✅")


if __name__ == "__main__":
    asyncio.run(main())
