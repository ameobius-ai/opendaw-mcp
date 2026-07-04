"""
Example: Genre Template — Techno Track Skeleton

Demonstrates the opendaw-genres skill: creates a complete techno track skeleton
with BPM, drum pattern, rolling bass, and effect chain.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_techno.py
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
        print("1. Setting BPM to 130...")
        await server.mcp_opendaw_set_bpm(130)
        print("   ✓ BPM = 130")

        # === 2. Create drum track (Playfield) ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_data = json.loads(drums)
        drum_uid = drum_data.get("unit_index")
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # Create note track + region
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 190)
        print("   ✓ Note track + 16-beat region")

        # === 3. Create bass track (Vaporisateur) ===
        print("\n3. Creating bass track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("Bass", "Vaporisateur")
        bass_data = json.loads(bass)
        bass_uid = bass_data.get("unit_index")
        print(f"   ✓ Bass AU: unit_index={bass_uid}")

        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "Bass", 210)
        print("   ✓ Note track + 16-beat region")

        # === 4. Add drum pattern (4-on-the-floor) ===
        print("\n4. Adding drum pattern (4-on-the-floor)...")
        pattern = {
            "kick":  "x...x...x...x...",
            "clap":  "....x.......x...",
            "hihat": "o.o.o.o.o.o.o.o.",
        }
        pattern_json = json.dumps(pattern)
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            pattern_json, drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('notes_added', drum_r.get('total', 0))} drum notes added")

        # === 5. Add rolling bass (16th notes, A1 = 33) ===
        print("\n5. Adding rolling bass (16th notes, A1)...")
        bass_notes = []
        for i in range(64):  # 4 bars × 16 sixteenths
            bass_notes.append({
                "pitch": 33,      # A1
                "start": i * 0.25, # 16th note spacing
                "duration": 0.125, # short
                "velocity": 0.7
            })
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_added', 0)} bass notes added")

        # === 6. Add effects on drums ===
        print("\n6. Adding effects on drums...")
        comp = await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
        comp_data = json.loads(comp)
        comp_idx = comp_data.get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "threshold", -15.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "ratio", 4.0)
        print(f"   ✓ Compressor (threshold=-15dB, ratio=4:1) at index {comp_idx}")

        eq = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        eq_data = json.loads(eq)
        eq_idx = eq_data.get("effect_index", 0)
        print(f"   ✓ Revamp EQ at index {eq_idx}")

        # === 7. Add Waveshaper on bass ===
        print("\n7. Adding Waveshaper on bass...")
        ws = await server.mcp_opendaw_add_effect(bass_uid, "Waveshaper")
        ws_data = json.loads(ws)
        ws_idx = ws_data.get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, ws_idx, "inputGain", 3.0)
        print(f"   ✓ Waveshaper (input +3dB) at index {ws_idx}")

        # === 8. Set track volumes ===
        print("\n8. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -3.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -6.0)
        print("   ✓ Drums: -3 dB, Bass: -6 dB")

        # === 9. Verify project state ===
        print("\n9. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")
        print(f"   Tracks: {state_data.get('track_count', 'N/A')}")

        print("\n✅ Techno skeleton created!")
        print("   130 BPM, 4-on-floor drums, rolling A1 bass")
        print("   Drum chain: Compressor → Revamp EQ")
        print("   Bass chain: Waveshaper")
        print("   Next: add pad/lead synth, create send reverb, master chain")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
