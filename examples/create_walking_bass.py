"""Example: create_walking_bass — jazz walking bass over chord progression."""
import asyncio
import json
import server


async def main():
    await server.bridge.start()

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("WalkingBass", "Vaporisateur")
    uid = json.loads(result)["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Classic ii-V-I in C major
    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["D","min7"],["G","dom7"],["C","maj7"]]',
        unit_index=uid, track_index=0, start_beat=0,
        octave=2, velocity=0.7, bars_per_chord=1,
    )
    data = json.loads(result)
    print(f"ii-V-I: {data['notes_created']} notes, {data['total_bars']} bars")

    # 3. 12-bar blues progression (simplified)
    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["C","dom7"],["C","dom7"],["C","dom7"],["C","dom7"],["F","dom7"],["F","dom7"],["C","dom7"],["C","dom7"],["G","dom7"],["F","dom7"],["C","dom7"],["G","dom7"]]',
        unit_index=uid, track_index=0, start_beat=4,
        octave=2, velocity=0.7, bars_per_chord=1,
    )
    data = json.loads(result)
    print(f"12-bar blues: {data['notes_created']} notes, {data['total_bars']} bars")

    # 4. Jazz standard with 2 bars per chord
    result = await server.mcp_opendaw_create_walking_bass(
        chords='[["C","maj7"],["A","min7"],["D","min7"],["G","dom7"]]',
        unit_index=uid, track_index=0, start_beat=16,
        octave=2, velocity=0.7, bars_per_chord=2,
    )
    data = json.loads(result)
    print(f"Jazz standard (2 bars/chord): {data['notes_created']} notes, {data['total_bars']} bars")

    await server.bridge.stop()
    print("\nDone! Three walking bass lines: ii-V-I, 12-bar blues, jazz standard.")


if __name__ == "__main__":
    asyncio.run(main())
