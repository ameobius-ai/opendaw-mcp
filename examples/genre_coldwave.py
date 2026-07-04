"""
Example: Genre Template — Coldwave Track Skeleton

Demonstrates the opendaw-genres skill: dark, dense, scooped-mids coldwave
with 100 BPM, sparse drums, detuned bass, minor chord progression,
Dattorro reverb on lead, hardclip on bass.

Uses MCP tools directly — same as an agent would.

Usage:
    # Start Vite first:
    #   cd headless-daw && npx vite --port 5174
    #
    source venv/bin/activate
    OPENDAW_URL=http://localhost:5174 python3 examples/genre_coldwave.py
"""
import asyncio
import json
import sys
sys.path.insert(0, ".")
import server


# Chord progression: Am - Fmaj7 - Cmaj - Gdom7
# Pitches in octave 2-3 for dark voicing
CHORDS = [
    # Am:  A2(45) C3(48) E3(52)
    {"name": "Am",     "pitches": [45, 48, 52]},
    # Fmaj7: F2(41) A2(45) C3(48) E3(52)
    {"name": "Fmaj7",  "pitches": [41, 45, 48, 52]},
    # Cmaj: C3(48) E3(52) G3(55)
    {"name": "Cmaj",   "pitches": [48, 52, 55]},
    # Gdom7: G2(43) B2(47) D3(50) F3(53)
    {"name": "Gdom7",  "pitches": [43, 47, 50, 53]},
]


async def main():
    await server.bridge.start()

    try:
        # === 1. Set BPM ===
        print("1. Setting BPM to 100...")
        await server.mcp_opendaw_set_bpm(100)
        print("   ✓ BPM = 100")

        # === 2. Create drum track ===
        print("\n2. Creating drum track (Playfield)...")
        drums = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
        drum_uid = json.loads(drums).get("unit_index")
        await server.mcp_opendaw_create_note_track(drum_uid)
        await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 260)
        print(f"   ✓ Drum AU: unit_index={drum_uid}")

        # === 3. Create bass track ===
        print("\n3. Creating bass track (Vaporisateur)...")
        bass = await server.mcp_opendaw_create_synth_track("Bass", "Vaporisateur")
        bass_uid = json.loads(bass).get("unit_index")
        await server.mcp_opendaw_create_note_track(bass_uid)
        await server.mcp_opendaw_create_track_region(bass_uid, 0, 0, 16, "Bass", 240)
        print(f"   ✓ Bass AU: unit_index={bass_uid}")

        # === 4. Create lead track ===
        print("\n4. Creating lead track (Vaporisateur)...")
        lead = await server.mcp_opendaw_create_synth_track("Lead", "Vaporisateur")
        lead_uid = json.loads(lead).get("unit_index")
        await server.mcp_opendaw_create_note_track(lead_uid)
        await server.mcp_opendaw_create_track_region(lead_uid, 0, 0, 16, "Lead", 280)
        print(f"   ✓ Lead AU: unit_index={lead_uid}")

        # === 5. Create pad track ===
        print("\n5. Creating pad track (Vaporisateur)...")
        pad = await server.mcp_opendaw_create_synth_track("Pad", "Vaporisateur")
        pad_uid = json.loads(pad).get("unit_index")
        await server.mcp_opendaw_create_note_track(pad_uid)
        await server.mcp_opendaw_create_track_region(pad_uid, 0, 0, 16, "Pad", 300)
        print(f"   ✓ Pad AU: unit_index={pad_uid}")

        # === 6. Drum pattern — sparse, cold ===
        print("\n6. Adding drum pattern (sparse coldwave)...")
        pattern = {
            "kick":  "x.......x.......",
            "snare": "....x.......x...",
            "hihat": "o.o.o.o.o.o.o.o.",
        }
        pattern_json = json.dumps(pattern)
        drum_result = await server.mcp_opendaw_create_drum_pattern(
            pattern_json, drum_uid
        )
        drum_r = json.loads(drum_result)
        print(f"   ✓ {drum_r.get('total_notes', 0)} drum notes added ({drum_r.get('lanes', {})})")

        # === 7. Bass — root notes following chord progression ===
        print("\n7. Adding bass line (root notes, A1 octave)...")
        bass_roots = [33, 29, 36, 31]  # A1, F1, C2, G1
        bass_notes = []
        for bar, root in enumerate(bass_roots):
            # Two long notes per bar, slight gap
            bass_notes.append({
                "pitch": root,
                "start": bar * 4.0,
                "duration": 3.5,
                "velocity": 0.8
            })
            bass_notes.append({
                "pitch": root,
                "start": bar * 4.0 + 3.75,
                "duration": 0.25,
                "velocity": 0.6
            })
        bass_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(bass_notes), bass_uid, 0
        )
        bass_r = json.loads(bass_result)
        print(f"   ✓ {bass_r.get('notes_created', 0)} bass notes added")

        # === 8. Lead — chord stabs, detuned, dark ===
        print("\n8. Adding lead chords (Am-Fmaj7-Cmaj-Gdom7 stabs)...")
        lead_notes = []
        for bar, chord in enumerate(CHORDS):
            for pitch in chord["pitches"]:
                # Stab: short attack, held note
                lead_notes.append({
                    "pitch": pitch,
                    "start": bar * 4.0 + 0.5,  # slight offset
                    "duration": 3.0,
                    "velocity": 0.65
                })
        lead_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(lead_notes), lead_uid, 0
        )
        lead_r = json.loads(lead_result)
        print(f"   ✓ {lead_r.get('notes_created', 0)} lead notes added")

        # === 9. Pad — sustained chords, wider, lower velocity ===
        print("\n9. Adding pad chords (sustained, wide)...")
        pad_notes = []
        for bar, chord in enumerate(CHORDS):
            for pitch in chord["pitches"]:
                pad_notes.append({
                    "pitch": pitch + 12,  # octave up for pad layer
                    "start": bar * 4.0,
                    "duration": 4.0,
                    "velocity": 0.4
                })
        pad_result = await server.mcp_opendaw_create_notes_batch(
            json.dumps(pad_notes), pad_uid, 0
        )
        pad_r = json.loads(pad_result)
        print(f"   ✓ {pad_r.get('notes_created', 0)} pad notes added")

        # === 10. Effects — Drums: EQ(HPF60,+4k) → Comp(3:1) → Rev ===
        print("\n10. Adding effects on drums...")
        comp = await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
        comp_idx = json.loads(comp).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "threshold", -18.0)
        await server.mcp_opendaw_set_effect_parameter(drum_uid, comp_idx, "ratio", 3.0)
        print(f"   ✓ Compressor (threshold=-18dB, ratio=3:1) at index {comp_idx}")

        revamp = await server.mcp_opendaw_add_effect(drum_uid, "Revamp")
        revamp_idx = json.loads(revamp).get("effect_index", 0)
        print(f"   ✓ Revamp EQ at index {revamp_idx}")

        # === 11. Effects — Bass: Waveshaper(hardclip) → EQ ===
        print("\n11. Adding effects on bass...")
        ws = await server.mcp_opendaw_add_effect(bass_uid, "Waveshaper")
        ws_idx = json.loads(ws).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(bass_uid, ws_idx, "inputGain", 6.0)
        print(f"   ✓ Waveshaper (input +6dB, hardclip) at index {ws_idx}")

        # === 12. Effects — Lead: DattorroReverb → Delay ===
        print("\n12. Adding effects on lead...")
        lead_rev = await server.mcp_opendaw_add_effect(lead_uid, "DattorroReverb")
        rev_idx = json.loads(lead_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(lead_uid, rev_idx, "decay", 0.7)
        print(f"   ✓ DattorroReverb (decay=0.7) at index {rev_idx}")

        lead_delay = await server.mcp_opendaw_add_effect(lead_uid, "Delay")
        delay_idx = json.loads(lead_delay).get("effect_index", 0)
        print(f"   ✓ Delay at index {delay_idx}")

        # === 13. Effects — Pad: Reverb ===
        print("\n13. Adding effects on pad...")
        pad_rev = await server.mcp_opendaw_add_effect(pad_uid, "DattorroReverb")
        pad_rev_idx = json.loads(pad_rev).get("effect_index", 0)
        await server.mcp_opendaw_set_effect_parameter(pad_uid, pad_rev_idx, "decay", 0.9)
        print(f"   ✓ DattorroReverb (decay=0.9, long) at index {pad_rev_idx}")

        # === 14. Track volumes ===
        print("\n14. Setting track volumes...")
        await server.mcp_opendaw_set_track_volume(drum_uid, -4.0)
        await server.mcp_opendaw_set_track_volume(bass_uid, -5.0)
        await server.mcp_opendaw_set_track_volume(lead_uid, -8.0)
        await server.mcp_opendaw_set_track_volume(pad_uid, -12.0)
        print("   ✓ Drums: -4dB, Bass: -5dB, Lead: -8dB, Pad: -12dB")

        # === 15. Verify ===
        print("\n15. Verifying project state...")
        state = await server.mcp_opendaw_get_project_info()
        state_data = json.loads(state)
        print(f"   BPM: {state_data.get('bpm')}")
        print(f"   AUs: {state_data.get('au_count', state_data.get('audio_units', 'N/A'))}")

        print("\n✅ Coldwave skeleton created!")
        print("   100 BPM, sparse drums, detuned bass")
        print("   Progression: Am - Fmaj7 - Cmaj - Gdom7")
        print("   Drum chain: Compressor(3:1) → Revamp EQ")
        print("   Bass chain: Waveshaper(hardclip +6dB)")
        print("   Lead chain: DattorroReverb(decay 0.7) → Delay")
        print("   Pad chain: DattorroReverb(decay 0.9)")
        print("   Volumes: Drums -4, Bass -5, Lead -8, Pad -12")
        print("   Next: add vocal audio, noise riser, set pan, master chain")

    finally:
        await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
