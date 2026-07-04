"""
Example: Genre Template — Drum & Bass Track Skeleton

Demonstrates the opendaw-genres skill: 174 BPM Amen-style drums,
reese bass, sub layer, aggressive sidechain-ready mix.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_dnb.py
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
        print("1. Setting BPM to 174...")
        await server.mcp_opendaw_set_bpm(174)
        print("   ✓ BPM = 174")

        # === 2. Create drum track ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_uid = json.loads(drums).get("unit_index")
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 280)
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # === 3. Create reese bass track ===
        print("\n3. Creating reese bass track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("Reese", "Vaporisateur")
        bass_uid = json.loads(bass).get("unit_index")
        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "Reese", 260)
        print(f"   ✓ Reese AU: unit_index={bass_uid}")

        # === 4. Create sub bass track ===
        print("\n4. Creating sub bass track (Vaporisateur)...")
        sub = await server.mcp_opendaw_create_synth_track("Sub", "Vaporisateur")
        sub_uid = json.loads(sub).get("unit_index")
        await server.mcp_opendaw_create_note_track(sub_uid)
        await server.mcp_opendaw_create_track_region(sub_uid, 0, 0, 16, "Sub", 240)
        print(f"   ✓ Sub AU: unit_index={sub_uid}")

        # === 5. Create lead track ===
        print("\n5. Creating lead track (Vaporisateur)...")
        lead = await server.mcp_opendaw_create_synth_track("Lead", "Vaporisateur")
        lead_uid = json.loads(lead).get("unit_index")
        await server.mcp_opendaw_create_note_track(lead_uid)
        await server.mcp_opendaw_create_track_region(lead_uid, 0, 0, 16, "Lead", 300)
        print(f"   ✓ Lead AU: unit_index={lead_uid}")

        # === 6. Amen-style break (simplified, 32 steps) ===
        print("\n6. Adding Amen-style drum break...")
        pattern = {
            "kick":  "x.....x.x.......x.....x.x.......",
            "snare": "....x.......x.......x.......x...",
            "hihat": "o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.",
        }
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            json.dumps(pattern), drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('total_notes', 0)} drum notes ({drum_r.get('lanes', {})})")

        # === 7. Reese bass — detuned, low, sustained notes ===
        print("\n7. Adding reese bass (detuned, sustained)...")
        # F1(29) and C2(36) — minor key feel
        bass_notes = [
            {"pitch": 29, "start": 0.0,  "duration": 7.5, "velocity": 0.75},
            {"pitch": 29, "start": 8.0,  "duration": 7.5, "velocity": 0.75},
            {"pitch": 36, "start": 16.0, "duration": 7.5, "velocity": 0.7},
            {"pitch": 29, "start": 24.0, "duration": 7.5, "velocity": 0.75},
        ]
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_created', 0)} reese notes added")

        # === 8. Sub bass — following reese roots, octave below ===
        print("\n8. Adding sub bass (octave below reese)...")
        sub_notes = [
            {"pitch": 17, "start": 0.0,  "duration": 7.5, "velocity": 0.8},  # F0
            {"pitch": 17, "start": 8.0,  "duration": 7.5, "velocity": 0.8},
            {"pitch": 24, "start": 16.0, "duration": 7.5, "velocity": 0.75}, # C1
            {"pitch": 17, "start": 24.0, "duration": 7.5, "velocity": 0.8},
        ]
        sub_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(sub_notes), sub_uid, 0
        )
        sub_r = json.loads(sub_result)
        print(f"   ✓ {sub_r.get('notes_created', 0)} sub notes added")

        # === 9. Lead — stabs, minor scale, sparse ===
        print("\n9. Adding lead stabs (F minor)...")
        # F minor: F(53), Ab(56), Bb(58), C(60), Db(61), Eb(63)
        lead_notes = [
            {"pitch": 60, "start": 0.0,  "duration": 0.5, "velocity": 0.65},
            {"pitch": 63, "start": 0.5,  "duration": 0.5, "velocity": 0.6},
            {"pitch": 65, "start": 1.0,  "duration": 1.0, "velocity": 0.7},
            {"pitch": 63, "start": 2.5,  "duration": 0.5, "velocity": 0.55},
            {"pitch": 60, "start": 3.0,  "duration": 0.5, "velocity": 0.6},
            {"pitch": 56, "start": 4.0,  "duration": 2.0, "velocity": 0.65},
            {"pitch": 58, "start": 6.0,  "duration": 1.0, "velocity": 0.55},
            {"pitch": 60, "start": 8.0,  "duration": 0.5, "velocity": 0.6},
            {"pitch": 63, "start": 8.5,  "duration": 1.5, "velocity": 0.7},
            {"pitch": 65, "start": 10.0, "duration": 2.0, "velocity": 0.6},
            {"pitch": 60, "start": 12.0, "duration": 0.5, "velocity": 0.55},
            {"pitch": 56, "start": 13.0, "duration": 3.0, "velocity": 0.65},
        ]
        lead_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(lead_notes), lead_uid, 0
        )
        lead_r = json.loads(lead_result)
        print(f"   ✓ {lead_r.get('notes_created', 0)} lead notes added")

        # === 10. Effects — Drums: Comp(8:1, aggressive) → EQ ===
        print("\n10. Adding effects on drums...")
        comp = await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
        comp_idx = json.loads(comp).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "threshold", -10.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "ratio", 8.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "attack", 0.001)
        print(f"   ✓ Compressor (8:1, -10dB, att 1ms — aggressive) at index {comp_idx}")

        eq = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        eq_idx = json.loads(eq).get("effect_index", 1)
        print(f"   ✓ Revamp EQ at index {eq_idx}")

        # === 11. Effects — Reese: Waveshaper → EQ → Comp ===
        print("\n11. Adding effects on reese...")
        ws = await server.mcp_opendaw_add_effect(bass_uid, "Waveshaper")
        ws_idx = json.loads(ws).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, ws_idx, "inputGain", 4.0)
        print(f"   ✓ Waveshaper (input +4dB) at index {ws_idx}")

        bass_eq = await server.mcp_opendaw_add_effect(bass_uid, "Revamp")
        bass_eq_idx = json.loads(bass_eq).get("effect_index", 1)
        print(f"   ✓ Revamp EQ at index {bass_eq_idx}")

        bass_comp = await server.mcp_opendaw_add_effect(bass_uid, "Compressor")
        bass_comp_idx = json.loads(bass_comp).get("effect_index", 2)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, bass_comp_idx, "ratio", 4.0)
        print(f"   ✓ Compressor (4:1) at index {bass_comp_idx}")

        # === 12. Effects — Sub: EQ (LPF) ===
        print("\n12. Adding effects on sub...")
        sub_eq = await server.mcp_opendaw_add_effect(sub_uid, "Revamp")
        sub_eq_idx = json.loads(sub_eq).get("effect_index", 0)
        print(f"   ✓ Revamp EQ (LPF ~120Hz) at index {sub_eq_idx}")

        # === 13. Effects — Lead: Waveshaper → Delay ===
        print("\n13. Adding effects on lead...")
        lead_ws = await server.mcp_opendaw_add_effect(lead_uid, "Waveshaper")
        lead_ws_idx = json.loads(lead_ws).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(lead_uid, lead_ws_idx, "inputGain", 2.0)
        print(f"   ✓ Waveshaper (+2dB) at index {lead_ws_idx}")

        lead_delay = await server.mcp_opendaw_add_effect(lead_uid, "Delay")
        lead_delay_idx = json.loads(lead_delay).get("effect_index", 1)
        print(f"   ✓ Delay at index {lead_delay_idx}")

        # === 14. Track volumes ===
        print("\n14. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -3.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -5.0)
        await server.mcp_opendaw_set_track_volume(sub_uid, -7.0)
        await server.mcp_opendaw_set_track_volume(lead_uid, -9.0)
        print("   ✓ Drums: -3dB, Reese: -5dB, Sub: -7dB, Lead: -9dB")

        # === 15. Verify ===
        print("\n15. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ DnB skeleton created!")
        print("   174 BPM, Amen break, reese+sub bass (F minor)")
        print("   Drum chain: Compressor(8:1,1ms) → Revamp EQ")
        print("   Reese chain: Waveshaper(+4dB) → Revamp EQ → Comp(4:1)")
        print("   Sub chain: Revamp EQ (LPF)")
        print("   Lead chain: Waveshaper(+2dB) → Delay")
        print("   Volumes: Drums -3, Reese -5, Sub -7, Lead -9")
        print("   Next: sidechain drums→bass, add reverb send, master chain")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
