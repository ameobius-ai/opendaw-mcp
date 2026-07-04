"""
Example: Genre Template — Ambient Track Skeleton

Demonstrates the opendaw-genres skill: spacious, airy, no drums (or very sparse),
sustained pad chords, bell melody, long reverbs, transparent master.
70 BPM, Cmaj7 - Amin7 - Fmaj7 - Gmaj7 progression.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_ambient.py
"""
import asyncio
import json
import sys
sys.path.insert(0, ".")
import server


# Ambient chord progression: Cmaj7 - Amin7 - Fmaj7 - Gmaj7
# Wide voicings in octave 3-4 for airy feel
CHORDS = [
    # Cmaj7: C3(48) E3(52) G3(55) B3(59)
    {"name": "Cmaj7", "pitches": [48, 52, 55, 59]},
    # Amin7: A3(57) C4(60) E4(64) G4(67)
    {"name": "Amin7", "pitches": [57, 60, 64, 67]},
    # Fmaj7: F3(53) A3(57) C4(60) E4(64)
    {"name": "Fmaj7", "pitches": [53, 57, 60, 64]},
    # Gmaj7: G3(55) B3(59) D4(62) F#4(66)
    {"name": "Gmaj7", "pitches": [55, 59, 62, 66]},
]


async def main():
    await server.bridge.start()

    try:
        # === 1. Set BPM ===
        print("1. Setting BPM to 70...")
        await server.mcp_opendaw_set_bpm(70)
        print("   ✓ BPM = 70")

        # === 2. Create pad track ===
        print("\n2. Creating pad track (Vaporisateur)...")
        pad = await server.mcp_opendaw_create_synth_track("Pad", "Vaporisateur")
        pad_uid = json.loads(pad).get("unit_index")
        await server.mcp_opendaw_create_note_track(pad_uid)
        # 32-beat region for long ambient phrases
        await server.mcp_opendaw_create_track_region(pad_uid, 0, 0, 32, "Pad", 200)
        print(f"   ✓ Pad AU: unit_index={pad_uid}")

        # === 3. Create bell track ===
        print("\n3. Creating bell track (Vaporisateur)...")
        bell = await server.mcp_opendaw_create_synth_track("Bell", "Vaporisateur")
        bell_uid = json.loads(bell).get("unit_index")
        await server.mcp_opendaw_create_note_track(bell_uid)
        await server.mcp_opendaw_create_track_region(bell_uid, 0, 0, 32, "Bell", 180)
        print(f"   ✓ Bell AU: unit_index={bell_uid}")

        # === 4. Create texture track ===
        print("\n4. Creating texture track (Vaporisateur)...")
        texture = await server.mcp_opendaw_create_synth_track("Texture", "Vaporisateur")
        texture_uid = json.loads(texture).get("unit_index")
        await server.mcp_opendaw_create_note_track(texture_uid)
        await server.mcp_opendaw_create_track_region(texture_uid, 0, 0, 32, "Texture", 220)
        print(f"   ✓ Texture AU: unit_index={texture_uid}")

        # === 5. Pad — sustained chords, long duration, low velocity ===
        print("\n5. Adding pad chords (sustained, 8 beats each)...")
        pad_notes = []
        for bar, chord in enumerate(CHORDS):
            for pitch in chord["pitches"]:
                pad_notes.append({
                    "pitch": pitch,
                    "start": bar * 8.0,  # 8 beats per chord
                    "duration": 7.5,     # sustain with slight overlap
                    "velocity": 0.35
                })
        pad_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(pad_notes), pad_uid, 0
        )
        pad_r = json.loads(pad_result)
        print(f"   ✓ {pad_r.get('notes_created', 0)} pad notes added")

        # === 6. Bell — sparse melody, high octave, pentatonic from chord tones ===
        print("\n6. Adding bell melody (sparse, high octave)...")
        # Pick top note of each chord + octave up, sparse placement
        bell_melody = [
            # Cmaj7 — B3(59) → D4(62) → G4(67)
            {"pitch": 71, "start": 0.0,  "duration": 2.0, "velocity": 0.5},  # B4
            {"pitch": 72, "start": 2.5,  "duration": 1.5, "velocity": 0.4},  # C5
            # Amin7 — E4(64) → G4(67) → A4(69)
            {"pitch": 76, "start": 8.0,  "duration": 2.0, "velocity": 0.45}, # E5
            {"pitch": 79, "start": 10.5, "duration": 1.5, "velocity": 0.4},  # G5
            # Fmaj7 — A4(69) → C5(72) → E5(76)
            {"pitch": 81, "start": 16.0, "duration": 2.5, "velocity": 0.5},  # A5
            {"pitch": 84, "start": 19.0, "duration": 1.0, "velocity": 0.35}, # C6
            # Gmaj7 — B4(71) → D5(74) → F#5(78)
            {"pitch": 83, "start": 24.0, "duration": 2.0, "velocity": 0.45}, # B5
            {"pitch": 86, "start": 27.0, "duration": 1.5, "velocity": 0.4},  # D6
        ]
        bell_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bell_melody), bell_uid, 0
        )
        bell_r = json.loads(bell_result)
        print(f"   ✓ {bell_r.get('notes_created', 0)} bell notes added")

        # === 7. Texture — low drone, root notes, long sustained ===
        print("\n7. Adding texture drone (root notes, octave 1)...")
        roots = [36, 33, 29, 31]  # C2, A1, F1, G1
        texture_notes = []
        for bar, root in enumerate(roots):
            texture_notes.append({
                "pitch": root,
                "start": bar * 8.0,
                "duration": 8.0,
                "velocity": 0.3
            })
        texture_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(texture_notes), texture_uid, 0
        )
        texture_r = json.loads(texture_result)
        print(f"   ✓ {texture_r.get('notes_created', 0)} texture notes added")

        # === 8. Effects — Pad: DattorroReverb(long) ===
        print("\n8. Adding effects on pad...")
        pad_rev = await server.mcp_opendaw_add_effect(pad_uid, "DattorroReverb")
        pad_rev_idx = json.loads(pad_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(pad_uid, pad_rev_idx, "decay", 0.9)
        print(f"   ✓ DattorroReverb (decay=0.9, very long) at index {pad_rev_idx}")

        # === 9. Effects — Bell: Reverb → Delay(1/2) ===
        print("\n9. Adding effects on bell...")
        bell_rev = await server.mcp_opendaw_add_effect(bell_uid, "DattorroReverb")
        bell_rev_idx = json.loads(bell_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(bell_uid, bell_rev_idx, "decay", 0.95)
        print(f"   ✓ DattorroReverb (decay=0.95, extreme) at index {bell_rev_idx}")

        bell_delay = await server.mcp_opendaw_add_effect(bell_uid, "Delay")
        bell_delay_idx = json.loads(bell_delay).get("effect_index", 0)
        print(f"   ✓ Delay at index {bell_delay_idx}")

        # === 10. Effects — Texture: Reverb ===
        print("\n10. Adding effects on texture...")
        tex_rev = await server.mcp_opendaw_add_effect(texture_uid, "DattorroReverb")
        tex_rev_idx = json.loads(tex_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(texture_uid, tex_rev_idx, "decay", 0.85)
        print(f"   ✓ DattorroReverb (decay=0.85) at index {tex_rev_idx}")

        # === 11. Track volumes ===
        print("\n11. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(pad_uid, -6.0)
        await server.mcp_opendaw_set_track_volume(bell_uid, -9.0)
        await server.mcp_opendaw_set_track_volume(texture_uid, -15.0)
        print("   ✓ Pad: -6dB, Bell: -9dB, Texture: -15dB")

        # === 12. Verify ===
        print("\n12. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ Ambient skeleton created!")
        print("   70 BPM, no drums, sustained chords")
        print("   Progression: Cmaj7 - Amin7 - Fmaj7 - Gmaj7")
        print("   Pad chain: DattorroReverb(decay 0.9)")
        print("   Bell chain: DattorroReverb(decay 0.95) → Delay")
        print("   Texture chain: DattorroReverb(decay 0.85)")
        print("   Volumes: Pad -6, Bell -9, Texture -15")
        print("   Next: add field recordings, granular texture, stereo widen, master")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
