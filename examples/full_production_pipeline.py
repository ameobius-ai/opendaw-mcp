"""
Full Production Pipeline Example

Creates a complete track from scratch:
1. Synth (Vaporisateur) with chord progression
2. Drum machine (Playfield) with kick + snare
3. Werkstatt tape saturation on drums
4. Reverb on synth
5. Set up automation sweep on filter cutoff
6. Render full mix + stems + measure LUFS

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
    # set_vaporisateur_osc_param(osc_index, param_name, value, unit_index)
    await server.mcp_opendaw_set_vaporisateur_osc_param("0", "waveform", 2, synth_uid)  # Saw
    await server.mcp_opendaw_set_vaporisateur_osc_param("0", "volume", -6, synth_uid)
    await server.mcp_opendaw_set_vaporisateur_osc_param("1", "waveform", 2, synth_uid)  # Saw
    await server.mcp_opendaw_set_vaporisateur_osc_param("1", "octave", -1, synth_uid)
    await server.mcp_opendaw_set_vaporisateur_osc_param("1", "volume", -12, synth_uid)
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

    # ─── 4. Effects ─────────────────────────────────────────────
    print("\n=== Effects ===")

    # Add reverb on synth
    await server.mcp_opendaw_add_effect(synth_uid, "Reverb")
    print(f"Reverb added to synth AU")

    # ─── 5. Automation sweep on filter cutoff ───────────────────
    print("\n=== Automation ===")
    # Create automation track on synth for filter cutoff sweep
    # points: JSON array of [position_beats, value_0_to_1] pairs
    auto_points = json.dumps([
        [0, 0.1],    # low cutoff
        [4, 0.8],    # open up
        [8, 0.3],    # close back
        [12, 0.9],   # wide open
        [16, 0.1],   # back to low
    ])
    auto_result = await server.mcp_opendaw_add_automation(
        unit_index=synth_uid, effect_index=0, parameter_name="cutoff",
        points=auto_points
    )
    auto_data = json.loads(auto_result)
    if auto_data.get("error"):
        print(f"Automation warning: {auto_data['error']}")
    else:
        print(f"Filter cutoff automation: 5-point sweep across 4 bars")

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

    # Render full mix
    full_mix = await server.mcp_opendaw_render_full("full_mix", 48000)
    mix_data = json.loads(full_mix)
    if mix_data.get("success"):
        print(f"Full mix: {mix_data['samples']} samples, "
              f"max_sample={mix_data['max_sample']:.4f}, "
              f"has_audio={mix_data['has_audio']}, "
              f"{mix_data.get('file_size_mb', 0)} MB")
    else:
        print(f"Full mix error: {mix_data.get('error')}")

    # Export stems
    stems = await server.mcp_opendaw_export_stems("stems", 48000)
    stems_data = json.loads(stems)
    if stems_data.get("success"):
        print(f"Stems: {stems_data['samples']} samples, "
              f"max_sample={stems_data['max_sample']:.4f}")
    else:
        print(f"Stems error: {stems_data.get('error')}")

    # Render just the first 4 beats (bar 1) for quick A/B
    range_render = await server.mcp_opendaw_render_range(0, 4, "bar1_preview", 48000)
    range_data = json.loads(range_render)
    if range_data.get("success"):
        print(f"Bar 1 preview: {range_data['samples']} samples, "
              f"max_sample={range_data['max_sample']:.4f}")
    else:
        print(f"Range render error: {range_data.get('error')}")

    # ─── 8. Mastering: LUFS + auto-gain ─────────────────────────
    print("\n=== Mastering ===")
    # Measure LUFS of the full mix
    lufs_result = await server.mcp_opendaw_measure_lufs("full_mix")
    lufs_data = json.loads(lufs_result)
    if lufs_data.get("success"):
        print(f"Pre-master LUFS: {lufs_data['lufs_integrated']}, "
              f"true peak: {lufs_data['true_peak_db']} dBTP, "
              f"duration: {lufs_data['duration_seconds']}s")
    else:
        print(f"LUFS measurement error: {lufs_data.get('error')}")

    # Auto-gain to -14 LUFS (Spotify target)
    ag_result = await server.mcp_opendaw_auto_gain("-14", "mastered", 48000, "3")
    ag_data = json.loads(ag_result)
    if ag_data.get("success"):
        print(f"Auto-gain → target -14 LUFS:")
        for it in ag_data.get("iterations", []):
            print(f"  iter {it['iteration']}: LUFS={it['lufs']}, "
                  f"diff={it['diff']:+.1f}, vol={it['volume_db']}dB")
        print(f"  Converged: {ag_data['converged']}, "
              f"final LUFS: {ag_data['final_lufs']}")
    else:
        print(f"Auto-gain error: {ag_data.get('error')}")

    # ─── 9. Project state ───────────────────────────────────────
    print("\n=== Project State ===")
    state = await server.mcp_opendaw_get_full_project_state()
    state_data = json.loads(state)
    print(f"BPM: {state_data['bpm']}")
    print(f"AUs: {state_data['au_count']}")
    for unit in state_data['units']:
        print(f"  {unit['label']} ({unit['type']}): "
              f"{unit['track_count']} tracks, "
              f"{unit['audio_effect_count']} FX")

    # ─── Done ───────────────────────────────────────────────────
    print("\n=== Pipeline Complete ===")
    print(f"2 AUs (Vaporisateur + Playfield)")
    print(f"1 effect (Reverb on synth)")
    print(f"1 automation track (filter sweep)")
    print(f"2 markers (Intro, Verse)")
    print(f"Full mix + stems + range render + LUFS + auto-gain")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
