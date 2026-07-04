"""
Example: Genre Template — Hip-Hop Track Skeleton

Demonstrates the opendaw-genres skill: 85 BPM boom-bap with 808 bass,
sample-like chord stab, punchy drums, vocal-ready mix.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_hiphop.py
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
        print("1. Setting BPM to 85...")
        await server.mcp_opendaw_set_bpm(85)
        print("   ✓ BPM = 85")

        # === 2. Create drum track ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_uid = json.loads(drums).get("unit_index")
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 40)
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # === 3. Create 808 bass track ===
        print("\n3. Creating 808 bass track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("808", "Vaporisateur")
        bass_uid = json.loads(bass).get("unit_index")
        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "808", 20)
        print(f"   ✓ 808 AU: unit_index={bass_uid}")

        # === 4. Create melody track ===
        print("\n4. Creating melody track (Vaporisateur)...")
        mel = await server.mcp_opendaw_create_synth_track("Melody", "Vaporisateur")
        mel_uid = json.loads(mel).get("unit_index")
        await server.mcp_opendaw_create_note_track(mel_uid)
        await server.mcp_opendaw_create_track_region(mel_uid, 0, 0, 16, "Melody", 60)
        print(f"   ✓ Melody AU: unit_index={mel_uid}")

        # === 5. Boom bap drum pattern ===
        print("\n5. Adding boom bap drum pattern...")
        pattern = {
            "kick":  "x.......x.x.....",
            "snare": "....x.......x...",
            "hihat": "o.o.o.o.o.o.o.o.",
        }
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            json.dumps(pattern), drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('total_notes', 0)} drum notes ({drum_r.get('lanes', {})})")

        # === 6. 808 bass — long gliding notes, low octave ===
        print("\n6. Adding 808 bass (long notes, gliding)...")
        # Root notes: Ab1(32), C2(36), Eb2(39), Gb2(42) — Ab minor pentatonic
        bass_notes = [
            {"pitch": 32, "start": 0.0,  "duration": 3.5, "velocity": 0.9},
            {"pitch": 32, "start": 3.75, "duration": 0.25, "velocity": 0.7},
            {"pitch": 36, "start": 4.0,  "duration": 3.5, "velocity": 0.85},
            {"pitch": 39, "start": 8.0,  "duration": 3.0, "velocity": 0.8},
            {"pitch": 36, "start": 11.0, "duration": 1.0, "velocity": 0.75},
            {"pitch": 42, "start": 12.0, "duration": 2.0, "velocity": 0.85},
            {"pitch": 39, "start": 14.0, "duration": 2.0, "velocity": 0.8},
        ]
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_created', 0)} 808 notes added")

        # === 7. Melody — dark minor pentatonic, sparse ===
        print("\n7. Adding dark melody (Ab minor pentatonic)...")
        # Ab minor pentatonic: Ab(56), B(59), C(60), Eb(63), F(65) — octave 3
        mel_notes = [
            {"pitch": 56, "start": 0.0,  "duration": 1.5, "velocity": 0.6},
            {"pitch": 59, "start": 1.5,  "duration": 0.5, "velocity": 0.55},
            {"pitch": 60, "start": 2.0,  "duration": 2.0, "velocity": 0.65},
            {"pitch": 63, "start": 4.0,  "duration": 1.0, "velocity": 0.5},
            {"pitch": 65, "start": 5.0,  "duration": 3.0, "velocity": 0.6},
            {"pitch": 63, "start": 8.0,  "duration": 2.0, "velocity": 0.55},
            {"pitch": 60, "start": 10.0, "duration": 1.0, "velocity": 0.5},
            {"pitch": 59, "start": 11.0, "duration": 1.0, "velocity": 0.55},
            {"pitch": 56, "start": 12.0, "duration": 4.0, "velocity": 0.6},
        ]
        mel_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(mel_notes), mel_uid, 0
        )
        mel_r = json.loads(mel_result)
        print(f"   ✓ {mel_r.get('notes_created', 0)} melody notes added")

        # === 8. Effects — Drums: Comp(4:1) → EQ ===
        print("\n8. Adding effects on drums...")
        comp = await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
        comp_idx = json.loads(comp).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "threshold", -12.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "ratio", 4.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "attack", 0.01)
        print(f"   ✓ Compressor (4:1, -12dB, att 10ms) at index {comp_idx}")

        eq = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        eq_idx = json.loads(eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ at index {eq_idx}")

        # === 9. Effects — 808: EQ → Comp ===
        print("\n9. Adding effects on 808...")
        bass_eq = await server.mcp_opendaw_add_effect(bass_uid, "Revamp")
        bass_eq_idx = json.loads(bass_eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ (HPF) at index {bass_eq_idx}")

        bass_comp = await server.mcp_opendaw_add_effect(bass_uid, "Compressor")
        bass_comp_idx = json.loads(bass_comp).get("effect_index", 1)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, bass_comp_idx, "ratio", 2.0)
        print(f"   ✓ Compressor (2:1) at index {bass_comp_idx}")

        # === 10. Effects — Melody: Revamp → Reverb ===
        print("\n10. Adding effects on melody...")
        mel_eq = await server.mcp_opendaw_add_effect(mel_uid, "Revamp")
        mel_eq_idx = json.loads(mel_eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ at index {mel_eq_idx}")

        mel_rev = await server.mcp_opendaw_add_effect(mel_uid, "DattorroReverb")
        mel_rev_idx = json.loads(mel_rev).get("effect_index", 1)
        await server.mcp_opendaw_set_effect_parameter(mel_uid, mel_rev_idx, "decay", 0.3)
        print(f"   ✓ DattorroReverb (decay=0.3, short) at index {mel_rev_idx}")

        # === 11. Track volumes ===
        print("\n11. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -3.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -4.0)
        await server.mcp_opendaw_set_track_volume(mel_uid, -8.0)
        print("   ✓ Drums: -3dB, 808: -4dB, Melody: -8dB")

        # === 12. Verify ===
        print("\n12. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ Hip-hop skeleton created!")
        print("   85 BPM, boom bap drums, 808 bass (Ab minor)")
        print("   Drum chain: Compressor(4:1,-12) → Revamp EQ")
        print("   808 chain: Revamp EQ → Compressor(2:1)")
        print("   Melody chain: Revamp EQ → DattorroReverb(0.3)")
        print("   Volumes: Drums -3, 808 -4, Melody -8")
        print("   Next: add vocal audio, sample chop, sidechain 808→bass")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
