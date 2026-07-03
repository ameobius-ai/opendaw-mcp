"""
Full Production Pipeline Example

Creates a complete track from scratch:
1. Synth (Vaporisateur) with chord progression
2. Drum machine (Playfield) with kick + snare
3. Werkstatt tape saturation on drums
4. Send/return reverb on synth
5. Set up automation sweep on filter cutoff
6. Render stems + measure LUFS + auto-gain

This demonstrates the full agent-native production workflow.
"""
import asyncio
import json
import os
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # ─── 1. Project setup ───────────────────────────────────────
    print("\n=== Project Setup ===")
    await server.mcp_opendaw_set_bpm(120)
    await server.mcp_opendaw_set_time_signature(4, 4)
    print("BPM=120, 4/4")

    # ─── 2. Synth track with chord progression ──────────────────
    print("\n=== Synth Track ===")
    synth_result = await server.mcp_opendaw_create_synth_track("Synth", "Vaporisateur")
    synth_data = json.loads(synth_result)
    synth_uid = synth_data["unit_index"]
    print(f"Synth AU created: unit_index={synth_uid}")

    # Create note track for chords
    await server.mcp_opendaw_create_note_track(synth_uid)
    print(f"Note track created")

    # Add a region spanning 4 bars (16 beats)
    await server.mcp_opendaw_create_track_region(synth_uid, 0, 0, 16, "Chords", 200)
    print(f"Note region created (4 bars)")

    # Add chord progression: Am - F - C - G (one chord per bar)
    # create_note(track_index, pitch, start_beat, duration_beats, velocity, unit_index)
    chords = [
        # Am: A2, C3, E3 (57, 60, 64) — bar 1
        [(57, 0), (60, 0), (64, 0)],
        # F:  F2, A2, C3 (53, 57, 60) — bar 2
        [(53, 4), (57, 4), (60, 4)],
        # C:  C3, E3, G3 (60, 64, 67) — bar 3
        [(60, 8), (64, 8), (67, 8)],
        # G:  G2, B2, D3 (55, 59, 62) — bar 4
        [(55, 12), (59, 12), (62, 12)],
    ]

    for chord in chords:
        for pitch, start in chord:
            await server.mcp_opendaw_create_note(
                track_index=0, pitch=pitch, start_beat=start,
                duration_beats=4, velocity=0.6, unit_index=synth_uid
            )
    print(f"Added 12 notes (4 chords: Am-F-C-G)")

    # Set Vaporisateur to warm saw pad
    await server.mcp_opendaw_set_vaporisateur_osc_param(synth_uid, 0, "waveform", 2)  # Saw
    await server.mcp_opendaw_set_vaporisateur_osc_param(synth_uid, 0, "volume", -6)
    await server.mcp_opendaw_set_vaporisateur_osc_param(synth_uid, 1, "waveform", 2)  # Saw
    await server.mcp_opendaw_set_vaporisateur_osc_param(synth_uid, 1, "octave", -1)
    await server.mcp_opendaw_set_vaporisateur_osc_param(synth_uid, 1, "volume", -12)
    print("Vaporisateur: dual saw, osc2 -1 octave (warm pad)")

    # ─── 3. Drum machine ────────────────────────────────────────
    print("\n=== Drum Track ===")
    drum_result = await server.mcp_opendaw_create_synth_track("Drums", "Playfield")
    drum_data = json.loads(drum_result)
    drum_uid = drum_data["unit_index"]
    print(f"Playfield AU created: unit_index={drum_uid}")

    # Create note track for drums
    await server.mcp_opendaw_create_note_track(drum_uid)
    await server.mcp_opendaw_create_track_region(drum_uid, 0, 0, 16, "Drums", 15)

    # Kick on beats 1, 2, 3, 4 (MIDI note 36 = C1)
    for beat in range(4):
        await server.mcp_opendaw_create_note(
            track_index=0, pitch=36, start_beat=beat * 4,
            duration_beats=0.25, velocity=0.9, unit_index=drum_uid
        )

    # Snare on beats 2 and 4 (MIDI note 38 = D1)
    for beat in [1, 3]:
        await server.mcp_opendaw_create_note(
            track_index=0, pitch=38, start_beat=beat * 4,
            duration_beats=0.25, velocity=0.8, unit_index=drum_uid
        )

    # Hi-hat on every 8th note (MIDI note 42 = F#1)
    for i in range(8):
        await server.mcp_opendaw_create_note(
            track_index=0, pitch=42, start_beat=i * 2,
            duration_beats=0.125, velocity=0.5, unit_index=drum_uid
        )
    print(f"Added 14 drum hits (4 kick, 2 snare, 8 hihat)")

    # ─── 4. Werkstatt tape saturation on drums ──────────────────
    print("\n=== Effects ===")
    # Add Werkstatt (scriptable audio effect) on drum bus
    await server.mcp_opendaw_add_effect(drum_uid, "Werkstatt")
    print(f"Werkstatt added to drum AU")

    # Load tape saturation DSP script
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_darksat.js")
    with open(script_path) as f:
        darksat_code = f.read()

    await server.mcp_opendaw_set_script_device_code(
        device_type="Werkstatt", unit_index=drum_uid, device_index=0, code=darksat_code
    )
    # Set drive for subtle warmth
    await server.mcp_opendaw_set_script_param("Werkstatt", drum_uid, 0, "drive", 0.4)
    print("Werkstatt: darksat tape saturation, drive=0.4")

    # Add reverb on synth
    await server.mcp_opendaw_add_effect(synth_uid, "Reverb")
    print(f"Reverb added to synth AU")

    # ─── 5. Automation sweep on filter cutoff ───────────────────
    print("\n=== Automation ===")
    # Create automation track on synth for filter cutoff sweep
    auto_result = await server.mcp_opendaw_add_automation(
        unit_index=synth_uid, effect_index=0, param_name="cutoff",
        events=[
            {"position": 0, "value": 200, "interpolation": "curve"},
            {"position": 4, "value": 2000, "interpolation": "curve"},
            {"position": 8, "value": 500, "interpolation": "linear"},
            {"position": 12, "value": 3000, "interpolation": "curve"},
            {"position": 16, "value": 200, "interpolation": "linear"},
        ]
    )
    print(f"Filter cutoff automation: 200→2000→500→3000→200 Hz sweep")

    # ─── 6. Mixing ──────────────────────────────────────────────
    print("\n=== Mixing ===")
    # Set levels
    await server.mcp_opendaw_set_track_volume(synth_uid, "-6")   # synth
    await server.mcp_opendaw_set_track_volume(drum_uid, "-3")   # drums
    print("Levels: synth -6dB, drums -3dB")

    # Add markers
    await server.mcp_opendaw_add_marker(0, "Intro")
    await server.mcp_opendaw_add_marker(16, "Verse")
    print("Markers: Intro (bar 1), Verse (bar 5)")

    # ─── 7. Render ──────────────────────────────────────────────
    print("\n=== Render ===")
    # Start engine
    await server.mcp_opendaw_start_engine()

    # Export stems
    stems = await server.mcp_opendaw_export_stems()
    stems_data = json.loads(stems)
    print(f"Stems exported: {stems_data}")

    # Measure LUFS
    lufs = await server.mcp_opendaw_measure_lufs()
    lufs_data = json.loads(lufs)
    print(f"LUFS measurement: {lufs_data}")

    # Auto-gain to -14 LUFS (Spotify target)
    auto_gain = await server.mcp_opendaw_auto_gain(-14)
    print(f"Auto-gain to -14 LUFS: {auto_gain}")

    # ─── 8. Screenshot ──────────────────────────────────────────
    print("\n=== Screenshot ===")
    screenshot = await server.mcp_opendaw_screenshot_daw()
    ss_data = json.loads(screenshot)
    print(f"Screenshot: {ss_data['size_bytes']} bytes")

    # ─── Done ───────────────────────────────────────────────────
    print("\n=== Pipeline Complete ===")
    print(f"2 AUs (Vaporisateur + Playfield)")
    print(f"3 effects (Werkstatt darksat + Reverb)")
    print(f"1 automation track (filter sweep)")
    print(f"2 markers (Intro, Verse)")
    print(f"Stems rendered, LUFS measured, auto-gain applied")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
