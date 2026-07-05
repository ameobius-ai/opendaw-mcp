"""E2E test: create_call_response and create_walking_bass via headless DAW bridge."""
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

    # 2. Test create_call_response — blues call and response
    result = await server.mcp_opendaw_create_call_response(
        scale="blues", root="A",
        call_pattern="1 3 5 3",
        response_pattern="5 4 3 2",
        unit_index=uid, track_index=0, start_beat=0,
        repeats=2, octave=4, velocity=0.7, step_duration=0.25,
    )
    data = json.loads(result)
    assert data.get("success"), f"call_response failed: {data}"
    # 4 call + 4 response = 8 per repeat, × 2 = 16
    assert data["notes_created"] == 16, f"Expected 16 notes, got {data['notes_created']}"
    assert data["call_response"] is True
    assert data["repeats"] == 2
    print(f"call_response: {data['notes_created']} notes, structure={data['phrase_structure']}")

    # 3. Test create_call_response with 1 repeat
    result = await server.mcp_opendaw_create_call_response(
        scale="minor", root="C",
        call_pattern="1 5 3",
        response_pattern="2 4 6",
        unit_index=uid, track_index=0, start_beat=8,
        repeats=1,
    )
    data = json.loads(result)
    assert data.get("success"), f"call_response 1 repeat failed: {data}"
    assert data["notes_created"] == 6, f"Expected 6 notes (3+3), got {data['notes_created']}"
    print(f"call_response (1 repeat): {data['notes_created']} notes")

    # 4. Test error handling
    result = await server.mcp_opendaw_create_call_response(
        scale="minor", root="C",
        call_pattern="1 3", response_pattern="5 2",
        repeats=0, unit_index=uid,
    )
    assert "Error" in result, f"Expected error for repeats=0, got: {result}"
    print("Error handling: repeats=0 ✅")

    result = await server.mcp_opendaw_create_call_response(
        scale="minor", root="C",
        call_pattern="0 0", response_pattern="1 3",  # all rests in call
        unit_index=uid,
    )
    assert "Error" in result, f"Expected error for empty call, got: {result}"
    print("Error handling: empty call pattern ✅")

    # 5. Test create_walking_bass — ii-V-I in C
    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["D","min7"],["G","dom7"],["C","maj7"]]',
        unit_index=uid, track_index=0, start_beat=12,
        octave=2, velocity=0.7, bars_per_chord=1,
    )
    data = json.loads(result)
    assert data.get("success"), f"walking_bass failed: {data}"
    # 3 chords × 4 notes = 12
    assert data["notes_created"] == 12, f"Expected 12 notes, got {data['notes_created']}"
    assert data["walking_bass"] is True
    assert data["total_bars"] == 3
    print(f"walking_bass (ii-V-I): {data['notes_created']} notes, {data['total_bars']} bars")

    # 6. Test walking_bass with 2 bars per chord
    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["C","maj7"],["A","min7"]]',
        unit_index=uid, track_index=0, start_beat=20,
        bars_per_chord=2,
    )
    data = json.loads(result)
    assert data.get("success"), f"walking_bass 2 bars failed: {data}"
    # 2 chords × 8 notes = 16
    assert data["notes_created"] == 16, f"Expected 16 notes, got {data['notes_created']}"
    print(f"walking_bass (2 bars/chord): {data['notes_created']} notes")

    # 7. Test error handling
    result = await server.mcp_opendaw_create_walking_bass(
        chords='[]', unit_index=uid,
    )
    assert "Error" in result, f"Expected error for empty chords, got: {result}"
    print("Error handling: empty chords ✅")

    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["C","maj7"]]', bars_per_chord=5, unit_index=uid,
    )
    assert "Error" in result, f"Expected error for bars_per_chord=5, got: {result}"
    print("Error handling: bars_per_chord=5 ✅")

    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["X","maj7"]]', unit_index=uid,
    )
    assert "Error" in result, f"Expected error for invalid root, got: {result}"
    print("Error handling: invalid root ✅")

    await server.bridge.stop()
    print("\nAll E2E tests passed ✅")


if __name__ == "__main__":
    asyncio.run(main())
