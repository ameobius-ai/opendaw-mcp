"""Example: create_call_response — antecedent/consequent phrase structure."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("CallResponse", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Blues call and response — 4 repeats
    result = await server.mcp_opendaw_create_call_response(
        scale="blues", root="A",
        call_pattern="1 3 5 3",
        response_pattern="5 4 3 2",
        unit_index=uid, track_index=0, start_beat=0,
        repeats=4, octave=4, velocity=0.7, step_duration=0.25,
    )
    data = json.loads(result)
    print(f"Blues call-response ×4: {data['notes_created']} notes, {data['phrase_structure']}")

    # 3. Minor key call and response — contrasting phrases
    result = await server.mcp_opendaw_create_call_response(
        scale="minor", root="D",
        call_pattern="1 - - 5",
        response_pattern="3 2 1 0",
        unit_index=uid, track_index=0, start_beat=16,
        repeats=2, octave=5, velocity=0.65, step_duration=0.125,
    )
    data = json.loads(result)
    print(f"Minor call-response ×2: {data['notes_created']} notes")

    await server.bridge.stop()
    print("\nDone! Classic antecedent/consequent phrases.")


if __name__ == "__main__":
    asyncio.run(main())
