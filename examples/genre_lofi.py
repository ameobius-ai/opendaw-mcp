"""
Example: Genre Template — Lofi Track Skeleton

Demonstrates the opendaw-genres skill: 82 BPM swung drums, jazzy chords,
warm bass, darksat tape saturation on drums, lazy feel. No aggressive
compression — keep it breathing.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_lofi.py
"""
import asyncio
import json
import sys
sys.path.insert(0, ".")
import server


# Jazzy ii-V-I progression: Dmin7 - Gdom7 - Cmaj7 - Fmaj7
CHORDS = [
    # Dmin7: D3(50) F3(53) A3(57) C4(60)
    {"name": "Dmin7", "pitches": [50, 53, 57, 60]},
    # Gdom7: G3(55) B3(59) D4(62) F4(65)
    {"name": "Gdom7", "pitches": [55, 59, 62, 65]},
    # Cmaj7: C3(48) E3(52) G3(55) B3(59)
    {"name": "Cmaj7", "pitches": [48, 52, 55, 59]},
    # Fmaj7: F3(53) A3(57) C4(60) E4(64)
    {"name": "Fmaj7", "pitches": [53, 57, 60, 64]},
]


async def main():
    await server.bridge.start()

    try:
        # === 1. Set BPM ===
        print("1. Setting BPM to 82...")
        await server.mcp_opendaw_set_bpm(82)
        print("   ✓ BPM = 82")

        # === 2. Create drum track ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_uid = json.loads(drums).get("unit_index")
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 150)
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # === 3. Create bass track ===
        print("\n3. Creating bass track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("Bass", "Vaporisateur")
        bass_uid = json.loads(bass).get("unit_index")
        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "Bass", 130)
        print(f"   ✓ Bass AU: unit_index={bass_uid}")

        # === 4. Create chord track ===
        print("\n4. Creating chord track (Vaporisateur)...")
        chords = await server.mcp_opendaw_create_synth_track("Chords", "Vaporisateur")
        chord_uid = json.loads(chords).get("unit_index")
        await server.mcp_opendaw_create_note_track(chord_uid)
        await server.mcp_opendaw_create_track_region(chord_uid, 0, 0, 16, "Chords", 170)
        print(f"   ✓ Chord AU: unit_index={chord_uid}")

        # === 5. Swung drum pattern (laid-back) ===
        print("\n5. Adding swung drum pattern...")
        # Swing feel via shifted hihat pattern (gaps create laid-back feel)
        pattern = {
            "kick":  "x.......x.x.....",
            "snare": "....x.......x...",
            "hihat": "o..o..o..o..o..o.",
        }
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            json.dumps(pattern), drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('total_notes', 0)} drum notes ({drum_r.get('lanes', {})})")

        # === 6. Bass — root notes, lazy, slightly behind ===
        print("\n6. Adding lazy bass (root notes)...")
        bass_roots = [38, 31, 36, 29]  # D2, G1, C2, F1
        bass_notes = []
        for bar, root in enumerate(bass_roots):
            bass_notes.append({
                "pitch": root,
                "start": bar * 4.0 + 0.1,  # slightly behind beat
                "duration": 3.5,
                "velocity": 0.55
            })
            # light passing note
            bass_notes.append({
                "pitch": root + 7,  # fifth
                "start": bar * 4.0 + 2.5,
                "duration": 1.0,
                "velocity": 0.4
            })
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_created', 0)} bass notes added")

        # === 7. Chords — sustained, low velocity, jazzy voicings ===
        print("\n7. Adding jazzy chords (Dmin7-Gdom7-Cmaj7-Fmaj7)...")
        chord_notes = []
        for bar, chord in enumerate(CHORDS):
            for pitch in chord["pitches"]:
                chord_notes.append({
                    "pitch": pitch,
                    "start": bar * 4.0,
                    "duration": 3.8,
                    "velocity": 0.35  # soft, warm
                })
        chord_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(chord_notes), chord_uid, 0
        )
        chord_r = json.loads(chord_result)
        print(f"   ✓ {chord_r.get('notes_created', 0)} chord notes added")

        # === 8. Effects — Drums: Revamp EQ (LPF 8k) ===
        print("\n8. Adding effects on drums...")
        eq = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        eq_idx = json.loads(eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ (LPF ~8k for warm tape feel) at index {eq_idx}")

        # === 9. Effects — Bass: Revamp EQ (HPF+LPF) ===
        print("\n9. Adding effects on bass...")
        bass_eq = await server.mcp_opendaw_add_effect(bass_uid, "Revamp")
        bass_eq_idx = json.loads(bass_eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ (HPF 50, LPF 2k) at index {bass_eq_idx}")

        # === 10. Effects — Chords: DattorroReverb (short, warm) ===
        print("\n10. Adding effects on chords...")
        chord_rev = await server.mcp_opendaw_add_effect(chord_uid, "DattorroReverb")
        chord_rev_idx = json.loads(chord_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(chord_uid, chord_rev_idx, "decay", 0.3)
        print(f"   ✓ DattorroReverb (decay=0.3, short warm) at index {chord_rev_idx}")

        # === 11. Track volumes ===
        print("\n11. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -6.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -8.0)
        await server.mcp_opendaw_set_track_volume(chord_uid, -10.0)
        print("   ✓ Drums: -6dB, Bass: -8dB, Chords: -10dB")

        # === 12. Verify ===
        print("\n12. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ Lofi skeleton created!")
        print("   82 BPM, swung drums, jazzy ii-V-I progression")
        print("   Progression: Dmin7 - Gdom7 - Cmaj7 - Fmaj7")
        print("   Drum chain: Revamp EQ (LPF 8k)")
        print("   Bass chain: Revamp EQ (HPF+LPF)")
        print("   Chord chain: DattorroReverb (0.3)")
        print("   Volumes: Drums -6, Bass -8, Chords -10")
        print("   Next: add Werkstatt darksat on drums, vinyl crackle, master")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
