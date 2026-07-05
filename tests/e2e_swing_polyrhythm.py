"""E2E test: apply_swing and create_polyrhythm tools via headless DAW bridge."""
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

    # 2. Create a 16th note grid for swing test
    notes = []
    for i in range(8):
        notes.append({
            "pitch": 60 + (i % 4) * 3,
            "start": i * 0.25,
            "duration": 0.25,
            "velocity": 0.7,
        })
    result = await server.mcp_opendaw_create_notes_batch(
        json.dumps(notes), uid, 0
    )
    data = json.loads(result)
    assert data.get("success"), f"notes_batch failed: {data}"
    print(f"Grid notes: {data['notes_created']} notes created")

    # 3. Test apply_swing with 0.5 swing on 16th grid
    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=0.5, grid="16th"
    )
    data = json.loads(result)
    assert data.get("success"), f"apply_swing failed: {data}"
    assert data["total_notes_shifted"] > 0, "swing shifted 0 notes"
    print(f"apply_swing (0.5, 16th): {data['total_notes_shifted']} notes shifted")

    # 4. Test apply_swing with 0.0 (no shift)
    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=0.0, grid="16th"
    )
    data = json.loads(result)
    assert data.get("success"), f"apply_swing 0.0 failed: {data}"
    assert data["total_notes_shifted"] == 0, "0.0 swing should shift 0 notes"
    print("apply_swing (0.0, 16th): 0 notes shifted ✅")

    # 5. Test apply_swing with 8th grid
    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=0.58, grid="8th"
    )
    data = json.loads(result)
    assert data.get("success"), f"apply_swing 8th failed: {data}"
    print(f"apply_swing (0.58, 8th): {data['total_notes_shifted']} notes shifted")

    # 6. Test error handling
    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=1.5, grid="16th"
    )
    assert "Error" in result, f"Expected error for swing=1.5, got: {result}"
    print("Error handling: swing_amount=1.5 ✅")

    result = await server.mcp_opendaw_apply_swing(
        unit_index=uid, track_index=0, swing_amount=0.5, grid="32nd"
    )
    assert "Error" in result, f"Expected error for grid=32nd, got: {result}"
    print('Error handling: grid="32nd" ✅')

    # 7. Test create_polyrhythm 3:4
    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=3,
        secondary_count=4,
        bars=1,
        unit_index=uid,
        track_index=0,
        start_beat=4,
        primary_pitch=60,
        secondary_pitch=72,
    )
    data = json.loads(result)
    assert data.get("success"), f"polyrhythm 3:4 failed: {data}"
    assert data["notes_created"] == 7, f"Expected 7 notes (3+4), got {data['notes_created']}"
    assert data["ratio"] == "3:4", f"Expected ratio 3:4, got {data['ratio']}"
    print(f"create_polyrhythm 3:4: {data['notes_created']} notes, ratio={data['ratio']}")

    # 8. Test create_polyrhythm 2:3 (hemiola)
    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=2,
        secondary_count=3,
        bars=2,
        unit_index=uid,
        track_index=0,
        start_beat=8,
        primary_pitch=48,
        secondary_pitch=55,
    )
    data = json.loads(result)
    assert data.get("success"), f"polyrhythm 2:3 failed: {data}"
    assert data["notes_created"] == 5, f"Expected 5 notes (2+3), got {data['notes_created']}"
    assert data["ratio"] == "2:3", f"Expected ratio 2:3, got {data['ratio']}"
    print(f"create_polyrhythm 2:3: {data['notes_created']} notes, ratio={data['ratio']}")

    # 9. Test error handling
    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=4, secondary_count=4, bars=1, unit_index=uid
    )
    assert "Error" in result, f"Expected error for 4:4, got: {result}"
    print("Error handling: 4:4 (equal counts) ✅")

    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=1, secondary_count=4, bars=1, unit_index=uid
    )
    assert "Error" in result, f"Expected error for primary=1, got: {result}"
    print("Error handling: primary_count=1 ✅")

    await server.bridge.stop()
    print("\nAll E2E tests passed ✅")


if __name__ == "__main__":
    asyncio.run(main())
