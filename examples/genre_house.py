"""
Example: Genre Template — House Track Skeleton

Demonstrates the opendaw-genres skill: 124 BPM 4-on-floor, stab chords,
rolling bass, open hats, delay on chords, classic house feel.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_house.py
"""
import asyncio
import json
import sys
sys.path.insert(0, ".")
import server


# House chord progression: Fmin9 - Cmin9 - Gmin9 - Dmin9 (minor 9 stabs)
CHORDS = [
    # Fmin9: F3(53) Ab3(56) C4(60) Eb4(63) G4(67)
    {"name": "Fmin9",  "pitches": [53, 56, 60, 63, 67]},
    # Cmin9: C3(48) Eb3(51) G3(55) Bb3(58) D4(62)
    {"name": "Cmin9",  "pitches": [48, 51, 55, 58, 62]},
    # Gmin9: G3(55) Bb3(58) D4(62) F4(65) A4(69)
    {"name": "Gmin9",  "pitches": [55, 58, 62, 65, 69]},
    # Dmin9: D3(50) F3(53) A3(57) C4(60) E4(64)
    {"name": "Dmin9",  "pitches": [50, 53, 57, 60, 64]},
]


async def main():
    await server.bridge.start()

    try:
        # === 1. Set BPM ===
        print("1. Setting BPM to 124...")
        await server.mcp_opendaw_set_bpm(124)
        print("   ✓ BPM = 124")

        # === 2. Create drum track ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_uid = json.loads(drums).get("unit_index")
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 180)
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # === 3. Create bass track ===
        print("\n3. Creating bass track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("Bass", "Vaporisateur")
        bass_uid = json.loads(bass).get("unit_index")
        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "Bass", 160)
        print(f"   ✓ Bass AU: unit_index={bass_uid}")

        # === 4. Create chord stab track ===
        print("\n4. Creating chord stab track (Vaporisateur)...")
        chords = await server.mcp_opendaw_create_synth_track("Chords", "Vaporisateur")
        chord_uid = json.loads(chords).get("unit_index")
        await server.mcp_opendaw_create_note_track(chord_uid)
        await server.mcp_opendaw_create_track_region(chord_uid, 0, 0, 16, "Chords", 200)
        print(f"   ✓ Chord AU: unit_index={chord_uid}")

        # === 5. Create lead track ===
        print("\n5. Creating lead track (Vaporisateur)...")
        lead = await server.mcp_opendaw_create_synth_track("Lead", "Vaporisateur")
        lead_uid = json.loads(lead).get("unit_index")
        await server.mcp_opendaw_create_note_track(lead_uid)
        await server.mcp_opendaw_create_track_region(lead_uid, 0, 0, 16, "Lead", 220)
        print(f"   ✓ Lead AU: unit_index={lead_uid}")

        # === 6. House drum pattern — 4-on-floor with open hats ===
        print("\n6. Adding house drum pattern...")
        pattern = {
            "kick":  "x...x...x...x...",
            "clap":  "....x.......x...",
            "hihat": "..o...o...o...o.",
        }
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            json.dumps(pattern), drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('total_notes', 0)} drum notes ({drum_r.get('lanes', {})})")

        # === 7. Bass — rolling 8th notes, root follows chord ===
        print("\n7. Adding rolling bass (8th notes)...")
        bass_roots = [41, 36, 43, 38]  # F1, C1, G1, D1
        bass_notes = []
        for bar, root in enumerate(bass_roots):
            for i in range(8):  # 8 eighth notes per bar
                bass_notes.append({
                    "pitch": root,
                    "start": bar * 4.0 + i * 0.5,
                    "duration": 0.375,  # slight gap
                    "velocity": 0.7 if i % 2 == 0 else 0.55
                })
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_created', 0)} bass notes added")

        # === 8. Chord stabs — off-beat, short, bright ===
        print("\n8. Adding chord stabs (off-beat)...")
        chord_notes = []
        for bar, chord in enumerate(CHORDS):
            for pitch in chord["pitches"]:
                # Stab pattern: &1, &2, &3 — classic house off-beat
                for offset in [0.5, 1.5, 2.5, 3.5]:
                    chord_notes.append({
                        "pitch": pitch,
                        "start": bar * 4.0 + offset,
                        "duration": 0.25,  # short stab
                        "velocity": 0.55
                    })
        chord_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(chord_notes), chord_uid, 0
        )
        chord_r = json.loads(chord_result)
        print(f"   ✓ {chord_r.get('notes_created', 0)} chord notes added")

        # === 9. Lead — simple top-line melody, sparse ===
        print("\n9. Adding lead melody (sparse top-line)...")
        # F minor pentatonic: F(65), Ab(68), Bb(70), C(72), Eb(75)
        lead_notes = [
            {"pitch": 72, "start": 0.0,  "duration": 1.0, "velocity": 0.55},
            {"pitch": 75, "start": 1.0,  "duration": 1.5, "velocity": 0.6},
            {"pitch": 72, "start": 3.0,  "duration": 0.5, "velocity": 0.5},
            {"pitch": 70, "start": 4.0,  "duration": 2.0, "velocity": 0.55},
            {"pitch": 68, "start": 6.0,  "duration": 1.0, "velocity": 0.5},
            {"pitch": 70, "start": 8.0,  "duration": 1.5, "velocity": 0.6},
            {"pitch": 72, "start": 10.0, "duration": 1.0, "velocity": 0.55},
            {"pitch": 75, "start": 12.0, "duration": 2.0, "velocity": 0.65},
            {"pitch": 72, "start": 14.0, "duration": 1.0, "velocity": 0.5},
        ]
        lead_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(lead_notes), lead_uid, 0
        )
        lead_r = json.loads(lead_result)
        print(f"   ✓ {lead_r.get('notes_created', 0)} lead notes added")

        # === 10. Effects — Drums: Comp(3:1) → EQ ===
        print("\n10. Adding effects on drums...")
        comp = await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
        comp_idx = json.loads(comp).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "threshold", -12.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "ratio", 3.0)
        print(f"   ✓ Compressor (3:1, -12dB) at index {comp_idx}")

        eq = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        eq_idx = json.loads(eq).get("effect_index", 1)
        print(f"   ✓ Revamp EQ at index {eq_idx}")

        # === 11. Effects — Bass: EQ → Waveshaper ===
        print("\n11. Adding effects on bass...")
        bass_eq = await server.mcp_opendaw_add_effect(bass_uid, "Revamp")
        bass_eq_idx = json.loads(bass_eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ (HPF) at index {bass_eq_idx}")

        bass_ws = await server.mcp_opendaw_add_effect(bass_uid, "Waveshaper")
        bass_ws_idx = json.loads(bass_ws).get("effect_index", 1)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, bass_ws_idx, "inputGain", 1.5)
        print(f"   ✓ Waveshaper (+1.5dB) at index {bass_ws_idx}")

        # === 12. Effects — Chords: Delay → Reverb ===
        print("\n12. Adding effects on chords...")
        chord_delay = await server.mcp_opendaw_add_effect(chord_uid, "Delay")
        chord_delay_idx = json.loads(chord_delay).get("effect_index", 0)
        print(f"   ✓ Delay at index {chord_delay_idx}")

        chord_rev = await server.mcp_opendaw_add_effect(chord_uid, "DattorroReverb")
        chord_rev_idx = json.loads(chord_rev).get("effect_index", 1)
        await server.mcp_opendaw_set_effect_parameter(chord_uid, chord_rev_idx, "decay", 0.5)
        print(f"   ✓ DattorroReverb (decay=0.5) at index {chord_rev_idx}")

        # === 13. Track volumes ===
        print("\n13. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -3.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -5.0)
        await server.mcp_opendaw_set_track_volume(chord_uid, -7.0)
        await server.mcp_opendaw_set_track_volume(lead_uid, -9.0)
        print("   ✓ Drums: -3dB, Bass: -5dB, Chords: -7dB, Lead: -9dB")

        # === 14. Verify ===
        print("\n14. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ House skeleton created!")
        print("   124 BPM, 4-on-floor, off-beat chord stabs")
        print("   Progression: Fmin9 - Cmin9 - Gmin9 - Dmin9")
        print("   Drum chain: Compressor(3:1) → Revamp EQ")
        print("   Bass chain: Revamp EQ → Waveshaper(+1.5)")
        print("   Chord chain: Delay → DattorroReverb(0.5)")
        print("   Volumes: Drums -3, Bass -5, Chords -7, Lead -9")
        print("   Next: sidechain drums→bass, add vocal, master chain")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
