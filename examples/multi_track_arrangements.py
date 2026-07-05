"""
Example: Multi-Track Genre Arrangements — 12 genres in one file

Demonstrates all 12 multi-track arrangement tools:
  create_dnb_arrangement      — DnB (Amen breakbeat + Reese + pad)
  create_house_arrangement    — House (four-on-floor + off-beat bass + stabs)
  create_trap_arrangement     — Trap (trap rolls + 808 slides + bell)
  create_techno_arrangement   — Techno (four-on-floor + sub drone + stabs)
  create_dubstep_arrangement  — Dubstep (half-time + wobble + arp)
  create_afrobeat_arrangement — Afrobeat (polyrhythm + ostinato + horns + chanka)
  create_rock_arrangement     — Rock (rock beat + walking bass + power chords + keys)
  create_jazz_arrangement     — Jazz (swing ride + walking bass + comping + horn)
  create_pop_arrangement      — Pop (song structure: verse-chorus-bridge)
  create_funk_arrangement     — Funk (Funky Drummer + slap bass + scratch + stabs)
  create_reggae_arrangement   — Reggae (one-drop + melodic bass + skank + organ)
  create_synthwave_arrangement — Synthwave (retro drums + arp bass + pads + lead)

Each arrangement creates a complete genre section across 3-4 tracks in one call.
One call replaces 100+ individual create_note calls.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/multi_track_arrangements.py
"""
import asyncio
import json
import sys
sys.path.insert(0, ".")
import server


async def run_arrangement(name, tool_fn, **kwargs):
    """Run a single arrangement tool and print results."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    result = await tool_fn(**kwargs)
    try:
        data = json.loads(result)
        if "error" in str(data):
            print(f"  ✗ Error: {data}")
            return

        tracks = data.get("tracks", {})
        total = data.get("total_notes", 0)
        print(f"  BPM: {data.get('bpm', '?')} | Key: {data.get('root', '?')} | Bars: {data.get('bars', '?')}")
        for track_name, track_info in tracks.items():
            print(f"    {track_name:10s}: track {track_info['track']}, {track_info['notes']} notes")
        print(f"  Total: {total} notes")

        # Print harmony/type info
        harmony = data.get("harmony", data.get("bass_pattern", ""))
        structure = data.get("song_structure", [])
        if structure:
            print(f"  Structure: {' → '.join(structure)}")
        if harmony:
            print(f"  Harmony: {harmony}")
    except Exception:
        print(f"  Raw: {result[:200]}")


async def main():
    await server.bridge.start()

    try:
        # === Setup: create 4 note tracks per arrangement ===
        # Each arrangement needs 3-4 note tracks on a single AU
        print("Setting up DAW...")
        await server.mcp_opendaw_set_bpm(120)

        # Create a synth unit with note tracks
        synth = await server.mcp_opendaw_create_synth_track("Arrangement Demo", "Playfield")
        synth_data = json.loads(synth)
        unit_index = synth_data.get("unit_index", 0)

        # Create 4 note tracks
        for i in range(4):
            await server.mcp_opendaw_create_note_track(unit_index)
        print(f"  ✓ Created AU (unit_index={unit_index}) with 4 note tracks")

        # Create a 32-bar region on each track
        for i in range(4):
            await server.mcp_opendaw_create_track_region(unit_index, i, 0, 32, f"Track {i}", 200 + i * 40)

        # === Run each arrangement ===
        # Note: In a real session, you'd run ONE arrangement per AU.
        # Here we demonstrate each tool's parameters and output format.

        arrangements = [
            ("DnB Arrangement (Amen breakbeat + Reese + pad)",
             server.mcp_opendaw_create_dnb_arrangement,
             {"bpm": 174, "bars": 8, "root": "F", "octave": 1, "unit_index": unit_index}),

            ("House Arrangement (four-on-floor + off-beat bass + stabs)",
             server.mcp_opendaw_create_house_arrangement,
             {"bpm": 124, "bars": 8, "root": "C", "octave": 2, "unit_index": unit_index}),

            ("Trap Arrangement (trap rolls + 808 slides + bell)",
             server.mcp_opendaw_create_trap_arrangement,
             {"bpm": 140, "bars": 8, "root": "F#", "octave": 1, "unit_index": unit_index}),

            ("Techno Arrangement (four-on-floor + sub drone + stabs)",
             server.mcp_opendaw_create_techno_arrangement,
             {"bpm": 130, "bars": 8, "root": "C", "octave": 2, "unit_index": unit_index}),

            ("Dubstep Arrangement (half-time + wobble + arp)",
             server.mcp_opendaw_create_dubstep_arrangement,
             {"bpm": 140, "bars": 8, "root": "G", "octave": 1, "unit_index": unit_index}),

            ("Afrobeat Arrangement (polyrhythm + ostinato + horns + chanka)",
             server.mcp_opendaw_create_afrobeat_arrangement,
             {"bpm": 120, "bars": 8, "root": "F", "octave": 2, "unit_index": unit_index}),

            ("Rock Arrangement (rock beat + walking bass + power chords + keys)",
             server.mcp_opendaw_create_rock_arrangement,
             {"bpm": 120, "bars": 8, "root": "E", "octave": 2, "unit_index": unit_index}),

            ("Jazz Arrangement (swing ride + walking bass + comping + horn)",
             server.mcp_opendaw_create_jazz_arrangement,
             {"bpm": 120, "bars": 8, "root": "F", "octave": 2, "unit_index": unit_index}),

            ("Pop Arrangement (verse-chorus-bridge song structure)",
             server.mcp_opendaw_create_pop_arrangement,
             {"bpm": 120, "bars": 16, "root": "C", "octave": 2, "unit_index": unit_index}),

            ("Funk Arrangement (Funky Drummer + slap bass + scratch + stabs)",
             server.mcp_opendaw_create_funk_arrangement,
             {"bpm": 100, "bars": 8, "root": "D", "octave": 2, "unit_index": unit_index}),

            ("Reggae Arrangement (one-drop + melodic bass + skank + organ)",
             server.mcp_opendaw_create_reggae_arrangement,
             {"bpm": 80, "bars": 8, "root": "A", "octave": 2, "unit_index": unit_index}),

            ("Synthwave Arrangement (retro drums + arp bass + pads + lead)",
             server.mcp_opendaw_create_synthwave_arrangement,
             {"bpm": 110, "bars": 8, "root": "A", "octave": 2, "unit_index": unit_index}),
        ]

        for name, fn, kwargs in arrangements:
            await run_arrangement(name, fn, **kwargs)

        print(f"\n{'='*60}")
        print("  All 12 arrangements demonstrated!")
        print(f"{'='*60}")
        print("\nKey differences:")
        print("  • DnB:       Amen breakbeat, Reese bass, 140-200 BPM")
        print("  • House:     Four-on-floor, off-beat bass, 110-140 BPM")
        print("  • Trap:      Triplet rolls, 808 slides, 120-170 BPM")
        print("  • Techno:    Four-on-floor, sub drone, 120-150 BPM, min 8 bars")
        print("  • Dubstep:   Half-time (snare on 3), wobble bass, 130-155 BPM")
        print("  • Afrobeat:  12/8 polyrhythm, ostinato, horns+guitar, 95-135 BPM")
        print("  • Rock:      Rock beat (kick 1&3), power chords, I-IV-V, 80-180 BPM")
        print("  • Jazz:      Swing ride, walking bass, ii-V-I, 50-220 BPM")
        print("  • Pop:       Song structure (verse-chorus-bridge), I-V-vi-IV, min 16 bars")
        print("  • Funk:      Vamp (one chord), Funky Drummer, 16th syncopation, 85-120 BPM")
        print("  • Reggae:    One-drop (kick+snare on 3), melodic bass lead, skank guitar, 65-100 BPM")
        print("  • Synthwave: Arpeggiated 16th bass, i-VI-III-VII, dreamy pads, 90-130 BPM")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
