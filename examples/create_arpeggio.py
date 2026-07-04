"""
Example: Create an arpeggio using the create_arpeggio orchestration tool.

Creates arpeggios from chord names with different patterns and rates.
Supports: up, down, updown, downup, random, chord patterns.
Rates: 32, 16, 8, 4 (note values), 16t, 32t (triplets).
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track
    result = await server.mcp_opendaw_create_synth_track("Arp", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Arp synth: unit_index={uid}")

    # 2. Up arpeggio from Cmin7 — 16 steps at 16th note rate
    result = await server.mcp_opendaw_create_arpeggio(
        chord="Cmin7",
        pattern="up",
        rate="16",
        octave=4,
        steps=16,
        unit_index=uid,
        track_index=0,
        start_beat=0,
        velocity=0.65
    )
    data = json.loads(result)
    print(f"Up arpeggio: {data.get('total_notes', data.get('notes_created', 0))} notes")
    print(json.dumps(data, indent=2))

    # 3. Down arpeggio from F#maj — starts at beat 4
    result = await server.mcp_opendaw_create_arpeggio(
        chord="F#maj",
        pattern="down",
        rate="16",
        octave=4,
        steps=16,
        unit_index=uid,
        track_index=0,
        start_beat=4,
        velocity=0.65
    )
    data = json.loads(result)
    print(f"\nDown arpeggio: {data.get('total_notes', data.get('notes_created', 0))} notes")

    # 4. Chord (block chords) from Abdim — starts at beat 8
    result = await server.mcp_opendaw_create_arpeggio(
        chord="Abdim",
        pattern="chord",
        rate="8",
        octave=4,
        steps=8,
        unit_index=uid,
        track_index=0,
        start_beat=8,
        velocity=0.7
    )
    data = json.loads(result)
    print(f"\nChord pattern: {data.get('total_notes', data.get('notes_created', 0))} notes")

    await server.bridge.stop()
    print("\nDone")


if __name__ == "__main__":
    asyncio.run(main())
