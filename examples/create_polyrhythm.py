"""Example: create_polyrhythm — 3:4 cross-rhythm for jazz/electronic textures."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Polyrhythm", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Create a 3:4 polyrhythm (classic cross-rhythm)
    #    3 primary notes (low) vs 4 secondary notes (high) over 1 bar
    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=3,
        secondary_count=4,
        bars=1,
        unit_index=uid,
        track_index=0,
        start_beat=0,
        primary_pitch=48,   # C3
        secondary_pitch=60, # C4
    )
    data = json.loads(result)
    print(f"3:4 polyrhythm: {data['notes_created']} notes, ratio={data['ratio']}")

    # 3. Create a 2:3 hemiola (African/Latin feel) over 2 bars
    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=2,
        secondary_count=3,
        bars=2,
        unit_index=uid,
        track_index=0,
        start_beat=4,
        primary_pitch=55,   # G3
        secondary_pitch=67, # G4
    )
    data = json.loads(result)
    print(f"2:3 hemiola: {data['notes_created']} notes, ratio={data['ratio']}")

    # 4. Extreme: 5:7 polyrhythm (progressive/math rock)
    result = await server.mcp_opendaw_create_polyrhythm(
        primary_count=5,
        secondary_count=7,
        bars=2,
        unit_index=uid,
        track_index=0,
        start_beat=12,
        primary_pitch=36,
        secondary_pitch=72,
    )
    data = json.loads(result)
    print(f"5:7 polyrhythm: {data['notes_created']} notes, ratio={data['ratio']}")

    await server.bridge.stop()
    print("\nDone! Three polyrhythms layered across 6 bars.")


if __name__ == "__main__":
    asyncio.run(main())
