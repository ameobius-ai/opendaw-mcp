"""Example: create_scale_run — ascending/descending scale sequences for fills."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("ScaleRun", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Ascending C minor run — 1 octave, 8th notes
    result = await server.mcp_opendaw_create_scale_run(
        scale="minor", root="C", direction="up", octaves=1,
        unit_index=uid, track_index=0, start_beat=0,
        step_duration=0.125, velocity=0.7,
    )
    data = json.loads(result)
    print(f"Up C minor 1 oct: {data['notes_created']} notes, range={data['pitch_range']}")

    # 3. Descending A blues run — 2 octaves, fast 32nd notes
    result = await server.mcp_opendaw_create_scale_run(
        scale="blues", root="A", direction="down", octaves=2,
        unit_index=uid, track_index=0, start_beat=4,
        step_duration=0.0625, velocity=0.65, octave=4,
    )
    data = json.loads(result)
    print(f"Down A blues 2 oct: {data['notes_created']} notes, range={data['pitch_range']}")

    # 4. Ascending D dorian — 3 octaves, 16th notes (long build-up)
    result = await server.mcp_opendaw_create_scale_run(
        scale="dorian", root="D", direction="up", octaves=3,
        unit_index=uid, track_index=0, start_beat=8,
        step_duration=0.0625, velocity=0.8, octave=3,
    )
    data = json.loads(result)
    print(f"Up D dorian 3 oct: {data['notes_created']} notes, range={data['pitch_range']}")

    await server.bridge.stop()
    print("\nDone! Three scale runs: build-up, fill, and transition.")


if __name__ == "__main__":
    asyncio.run(main())
