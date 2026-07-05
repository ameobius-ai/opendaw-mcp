"""E2E test: create_scale_run via headless DAW bridge."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("ScaleRun", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create ascending C minor scale run, 1 octave
    result = await server.mcp_opendaw_create_scale_run(
        scale="minor", root="C", direction="up", octaves=1,
        unit_index=uid, track_index=0, start_beat=0,
        step_duration=0.125, velocity=0.7, octave=4,
    )
    data = json.loads(result)
    assert data.get("success"), f"scale_run up failed: {data}"
    # C minor 1 octave: 7 notes + octave root = 8
    assert data["notes_created"] == 8, f"Expected 8 notes, got {data['notes_created']}"
    assert data["direction"] == "up"
    assert data["scale"] == "minor"
    assert data["root"] == "C"
    print(f"scale_run up (C minor, 1 oct): {data['notes_created']} notes, range={data['pitch_range']}")

    # 3. Create descending A blues scale run, 2 octaves
    result = await server.mcp_opendaw_create_scale_run(
        scale="blues", root="A", direction="down", octaves=2,
        unit_index=uid, track_index=0, start_beat=4,
        step_duration=0.0625, velocity=0.65, octave=4,
    )
    data = json.loads(result)
    assert data.get("success"), f"scale_run down failed: {data}"
    # A blues 2 octaves: 6+6+1 = 13 notes
    assert data["notes_created"] == 13, f"Expected 13 notes, got {data['notes_created']}"
    assert data["direction"] == "down"
    print(f"scale_run down (A blues, 2 oct): {data['notes_created']} notes, range={data['pitch_range']}")

    # 4. Test error handling
    result = await server.mcp_opendaw_create_scale_run(
        scale="invalid_scale", root="C", direction="up", octaves=1, unit_index=uid
    )
    assert "Error" in result, f"Expected error for invalid scale, got: {result}"
    print("Error handling: invalid scale ✅")

    result = await server.mcp_opendaw_create_scale_run(
        scale="minor", root="C", direction="sideways", octaves=1, unit_index=uid
    )
    assert "Error" in result, f"Expected error for invalid direction, got: {result}"
    print("Error handling: invalid direction ✅")

    result = await server.mcp_opendaw_create_scale_run(
        scale="minor", root="C", direction="up", octaves=5, unit_index=uid
    )
    assert "Error" in result, f"Expected error for octaves=5, got: {result}"
    print("Error handling: octaves=5 ✅")

    await server.bridge.stop()
    print("\nAll E2E tests passed ✅")


if __name__ == "__main__":
    asyncio.run(main())
