"""
Example: Genre Template — Trap Track Skeleton

Demonstrates the opendaw-genres skill: 145 BPM dark trap, gliding 808,
fast hi-hat rolls, dark minor melody, hard compression on drums.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_trap.py
"""
import asyncio
import json
import sys
sys.path.insert(0, ".")
import server


async def main():
    await server.bridge.start()

    try:
        # === 1. Set BPM ===
        print("1. Setting BPM to 145...")
        await server.mcp_opendaw_set_bpm(145)
        print("   ✓ BPM = 145")

        # === 2. Create drum track ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_uid = json.loads(drums).get("unit_index")
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 280)
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # === 3. Create 808 track ===
        print("\n3. Creating 808 track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("808", "Vaporisateur")
        bass_uid = json.loads(bass).get("unit_index")
        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "808", 260)
        print(f"   ✓ 808 AU: unit_index={bass_uid}")

        # === 4. Create melody track ===
        print("\n4. Creating melody track (Vaporisateur)...")
        mel = await server.mcp_opendaw_create_synth_track("Melody", "Vaporisateur")
        mel_uid = json.loads(mel).get("unit_index")
        await server.mcp_opendaw_create_note_track(mel_uid)
        await server.mcp_opendaw_create_track_region(mel_uid, 0, 0, 16, "Melody", 300)
        print(f"   ✓ Melody AU: unit_index={mel_uid}")

        # === 5. Trap drum pattern — fast hi-hats ===
        print("\n5. Adding trap drum pattern (fast hats)...")
        # 32-step hi-hat for trap feel (16th+32nd rolls)
        pattern = {
            "kick":  "x.....x...x.x...",
            "snare": "....x.......x...",
            "hihat": "o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.",
        }
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            json.dumps(pattern), drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('total_notes', 0)} drum notes ({drum_r.get('lanes', {})})")

        # === 6. 808 bass — gliding notes, dark minor ===
        print("\n6. Adding 808 bass (gliding, F minor)...")
        # F minor: F(29), Ab(32), Bb(34), C(36), Db(37), Eb(39)
        bass_notes = [
            {"pitch": 29, "start": 0.0,  "duration": 3.5, "velocity": 0.9},
            {"pitch": 36, "start": 3.75, "duration": 0.25, "velocity": 0.7},
            {"pitch": 34, "start": 4.0,  "duration": 3.5, "velocity": 0.85},
            {"pitch": 32, "start": 8.0,  "duration": 2.0, "velocity": 0.8},
            {"pitch": 29, "start": 10.0, "duration": 1.0, "velocity": 0.75},
            {"pitch": 36, "start": 12.0, "duration": 2.0, "velocity": 0.85},
            {"pitch": 39, "start": 14.0, "duration": 2.0, "velocity": 0.8},
        ]
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_created', 0)} 808 notes added")

        # === 7. Melody — dark minor, sparse, atmospheric ===
        print("\n7. Adding dark melody (F minor)...")
        # F minor pentatonic: F(65), Ab(68), Bb(70), C(72), Eb(75)
        mel_notes = [
            {"pitch": 72, "start": 0.0,  "duration": 2.0, "velocity": 0.55},
            {"pitch": 68, "start": 2.0,  "duration": 1.0, "velocity": 0.5},
            {"pitch": 70, "start": 3.0,  "duration": 1.5, "velocity": 0.6},
            {"pitch": 72, "start": 4.5,  "duration": 0.5, "velocity": 0.45},
            {"pitch": 75, "start": 5.0,  "duration": 3.0, "velocity": 0.65},
            {"pitch": 72, "start": 8.0,  "duration": 1.0, "velocity": 0.5},
            {"pitch": 70, "start": 9.0,  "duration": 1.0, "velocity": 0.55},
            {"pitch": 68, "start": 10.0, "duration": 2.0, "velocity": 0.6},
            {"pitch": 65, "start": 12.0, "duration": 4.0, "velocity": 0.5},
        ]
        mel_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(mel_notes), mel_uid, 0
        )
        mel_r = json.loads(mel_result)
        print(f"   ✓ {mel_r.get('notes_created', 0)} melody notes added")

        # === 8. Effects — Drums: Comp(6:1, hard) → EQ ===
        print("\n8. Adding effects on drums...")
        comp = await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
        comp_idx = json.loads(comp).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "threshold", -8.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "ratio", 6.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "attack", 0.002)
        print(f"   ✓ Compressor (6:1, -8dB, att 2ms — hard) at index {comp_idx}")

        eq = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        eq_idx = json.loads(eq).get("effect_index", 1)
        print(f"   ✓ Revamp EQ at index {eq_idx}")

        # === 9. Effects — 808: Revamp EQ → Comp ===
        print("\n9. Adding effects on 808...")
        bass_eq = await server.mcp_opendaw_add_effect(bass_uid, "Revamp")
        bass_eq_idx = json.loads(bass_eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ (HPF 20) at index {bass_eq_idx}")

        bass_comp = await server.mcp_opendaw_add_effect(bass_uid, "Compressor")
        bass_comp_idx = json.loads(bass_comp).get("effect_index", 1)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, bass_comp_idx, "ratio", 2.0)
        print(f"   ✓ Compressor (2:1) at index {bass_comp_idx}")

        # === 10. Effects — Melody: DattorroReverb → Delay ===
        print("\n10. Adding effects on melody...")
        mel_rev = await server.mcp_opendaw_add_effect(mel_uid, "DattorroReverb")
        mel_rev_idx = json.loads(mel_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(mel_uid, mel_rev_idx, "decay", 0.4)
        print(f"   ✓ DattorroReverb (decay=0.4) at index {mel_rev_idx}")

        mel_delay = await server.mcp_opendaw_add_effect(mel_uid, "Delay")
        mel_delay_idx = json.loads(mel_delay).get("effect_index", 1)
        print(f"   ✓ Delay at index {mel_delay_idx}")

        # === 11. Track volumes ===
        print("\n11. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -3.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -4.0)
        await server.mcp_opendaw_set_track_volume(mel_uid, -9.0)
        print("   ✓ Drums: -3dB, 808: -4dB, Melody: -9dB")

        # === 12. Verify ===
        print("\n12. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ Trap skeleton created!")
        print("   145 BPM, fast hats, gliding 808 (F minor)")
        print("   Drum chain: Compressor(6:1,2ms) → Revamp EQ")
        print("   808 chain: Revamp EQ → Compressor(2:1)")
        print("   Melody chain: DattorroReverb(0.4) → Delay")
        print("   Volumes: Drums -3, 808 -4, Melody -9")
        print("   Next: add hi-hat rolls, 808 glide automation, master chain")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
