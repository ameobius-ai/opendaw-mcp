"""
Example: Create an ostinato — repeating melodic pattern as foundation.

Ostinatos are short patterns (2-8 notes) that repeat throughout a section,
providing a rhythmic/harmonic anchor. Common in minimalism, electronic, and film music.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Ostinato", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Synth: unit_index={uid}")

    # 2. Classic minimalist ostinato: C minor 1-5-3-5, 8 repeats
    result = await server.mcp_opendaw_create_ostinato(
        scale="minor", root="C", pattern="1 5 3 5",
        unit_index=uid, track_index=0, start_beat=0,
        repeats=8, octave=4, velocity=0.7
    )
    data = json.loads(result)
    print(f"Ostinato (C minor 1-5-3-5 ×8): {data.get('notes_created', 0)} notes")

    # 3. Longer melodic cell: D dorian 1-3-5-6-5-3, 4 repeats
    result = await server.mcp_opendaw_create_ostinato(
        scale="dorian", root="D", pattern="1 3 5 6 5 3",
        unit_index=uid, track_index=0, start_beat=8,
        repeats=4, octave=3, velocity=0.65
    )
    data = json.loads(result)
    print(f"Ostinato (D dorian 1-3-5-6-5-3 ×4): {data.get('notes_created', 0)} notes")

    # 4. Pentatonic pattern: E minor pentatonic 1-3-5-7, 6 repeats
    # Note: pentatonic has 5 notes, degree 7 wraps to next octave
    result = await server.mcp_opendaw_create_ostinato(
        scale="minor", root="E", pattern="1 1 5 1 3 1",
        unit_index=uid, track_index=0, start_beat=14,
        repeats=6, octave=4, velocity=0.8
    )
    data = json.loads(result)
    print(f"Ostinato (E minor 1-1-5-1-3-1 ×6): {data.get('notes_created', 0)} notes")

    await server.bridge.stop()
    print("\nDone — 3 ostinato patterns created")


if __name__ == "__main__":
    asyncio.run(main())
