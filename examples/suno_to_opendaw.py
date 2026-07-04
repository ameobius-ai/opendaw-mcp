"""Suno → openDAW pipeline — import an AI-generated track and enhance it.

Demonstrates a real-world workflow for AI musicians:
1. Load a Suno-generated WAV/MP3 into openDAW
2. Create an audio track + clip from the imported file
3. Add mastering-grade effects (Werkstatt DarkSat tape sat + lookahead comp)
4. Set up a reverb send bus for spatial depth
5. Add a MIDI arp layer on top (Apparat SubCrusher + Spielwerk arp)
6. Render the enhanced mix to WAV
7. Export stems for further processing

Usage:
    source venv/bin/activate
    python examples/suno_to_opendaw.py /path/to/suno_track.wav

If no file is provided, uses a placeholder and skips audio import.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_get_project_state,
    mcp_opendaw_create_audio_track,
    mcp_opendaw_load_audio,
    mcp_opendaw_create_audio_clip,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_note,
    mcp_opendaw_add_effect,
    mcp_opendaw_add_midi_effect,
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_set_bpm,
    mcp_opendaw_create_send,
    mcp_opendaw_render_full,
    mcp_opendaw_export_stems,
    mcp_opendaw_measure_lufs,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def load_script(name: str) -> str:
    with open(os.path.join(SCRIPTS_DIR, name)) as f:
        return f.read()


async def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    print("=" * 60)
    print("Suno → openDAW Enhancement Pipeline")
    print("=" * 60)
    if audio_path:
        print(f"\nInput: {audio_path}")
    else:
        print("\nNo input file — running in demo mode (audio import skipped)")

    await bridge.start()

    # ─── 1. Start engine + set tempo ──────────────────────────
    print("\n[1/7] Starting engine and setting BPM...")
    state = json.loads(await mcp_opendaw_get_project_state())
    print(f"  Project loaded: {state.get('track_count', 0)} tracks")

    await mcp_opendaw_set_bpm(bpm=120)
    print("  BPM set to 120")

    # ─── 2. Load Suno track ───────────────────────────────────
    sample_id = None
    if audio_path and os.path.exists(audio_path):
        print("\n[2/7] Loading Suno track...")
        result = json.loads(await mcp_opendaw_load_audio(file_path=audio_path, name="suno_track"))
        if result.get("success"):
            sample_id = result["id"]
            print(f"  Loaded: {result['name']} ({result['duration']:.1f}s, "
                  f"{result['sample_rate']}Hz, {result['channels']}ch)")
        else:
            print(f"  Load failed: {result.get('error', 'unknown')}")
            return
    else:
        print("\n[2/7] Skipping audio load (no file)")

    # ─── 3. Create audio track + clip ─────────────────────────
    audio_unit_idx = 0  # primary audio unit
    if sample_id:
        print("\n[3/7] Creating audio track with imported clip...")
        track = json.loads(await mcp_opendaw_create_audio_track())
        track_idx = track.get("track_index", 0)
        print(f"  Audio track created: index {track_idx}")

        clip = json.loads(await mcp_opendaw_create_audio_clip(
            sample_id=sample_id, unit_index=audio_unit_idx,
            clip_index=0, track_index=track_idx, bpm=120
        ))
        if clip.get("success"):
            print("  Clip placed at bar 0")
        else:
            print(f"  Clip creation issue: {clip.get('error', 'check logs')}")
    else:
        print("\n[3/7] Skipping track creation (no audio)")

    # ─── 4. Add mastering effects on audio track ──────────────
    print("\n[4/7] Adding mastering chain (tape sat + lookahead comp)...")
    # Werkstatt DarkSat for tape warmth
    sat = json.loads(await mcp_opendaw_add_effect(unit_index=audio_unit_idx, effect_type="Werkstatt"))
    if sat.get("success"):
        fx_idx = sat.get("effect_index", 0)
        await mcp_opendaw_set_script_device_code(
            device_type="werkstatt", unit_index=audio_unit_idx,
            device_index=fx_idx, code=load_script("werkstatt_darksat.js")
        )
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "drive", 0.25)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "tone", 0.6)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "mix", 0.7)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "output", -2)
        print("  DarkSat tape saturation: drive=0.25, tone=0.6, mix=0.7, out=-2dB")

    # Werkstatt Lookahead for transparent leveling
    comp = json.loads(await mcp_opendaw_add_effect(unit_index=audio_unit_idx, effect_type="Werkstatt"))
    if comp.get("success"):
        fx_idx = comp.get("effect_index", 1)
        await mcp_opendaw_set_script_device_code(
            device_type="werkstatt", unit_index=audio_unit_idx,
            device_index=fx_idx, code=load_script("werkstatt_lookahead.js")
        )
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "threshold", -14)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "ratio", 3)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "attack", 0.005)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "release", 0.15)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "makeup", 3)
        await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, fx_idx, "mix", 1)
        print("  Lookahead compressor: thresh=-14dB, ratio=3:1, makeup=+3dB")

    # ─── 5. Reverb send bus ───────────────────────────────────
    print("\n[5/7] Setting up reverb send bus...")
    # Create a send from audio track to a new FX bus
    send = json.loads(await mcp_opendaw_create_send(
        src_unit=audio_unit_idx, name="reverb_send",
        send_level_db=-9, routing="primary"
    ))
    if send.get("success"):
        print(f"  Send created: {send}")
        # Add Werkstatt Reverb on the send
        rev = json.loads(await mcp_opendaw_add_effect(unit_index=audio_unit_idx, effect_type="Werkstatt"))
        if rev.get("success"):
            rev_fx = rev.get("effect_index", 2)
            await mcp_opendaw_set_script_device_code(
                device_type="werkstatt", unit_index=audio_unit_idx,
                device_index=rev_fx, code=load_script("werkstatt_reverb.js")
            )
            await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, rev_fx, "decay", 0.5)
            await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, rev_fx, "damping", 0.6)
            await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, rev_fx, "width", 0.9)
            await mcp_opendaw_set_script_param("werkstatt", audio_unit_idx, rev_fx, "mix", 1)
            print("  Reverb: decay=0.5, damping=0.6, width=0.9")
    else:
        print(f"  Send creation: {send}")

    # ─── 6. Add MIDI arp layer ────────────────────────────────
    print("\n[6/7] Adding MIDI arpeggio layer (Apparat SubCrusher + Spielwerk)...")
    # Synth track with Apparat instrument
    synth = json.loads(await mcp_opendaw_create_synth_track(name="arp_synth", synth_type="Apparat"))
    if synth.get("success"):
        synth_idx = synth.get("unit_index", 1)
        await mcp_opendaw_set_script_device_code(
            device_type="apparat", unit_index=synth_idx,
            device_index=0, code=load_script("apparat_subcrusher.js")
        )
        await mcp_opendaw_set_script_param("apparat", synth_idx, 0, "cutoff", 800)
        await mcp_opendaw_set_script_param("apparat", synth_idx, 0, "resonance", 0.3)
        await mcp_opendaw_set_script_param("apparat", synth_idx, 0, "volume", 0.5)
        print(f"  SubCrusher synth on unit {synth_idx}: cutoff=800Hz")

        # MIDI arpeggiator
        arp = json.loads(await mcp_opendaw_add_midi_effect(unit_index=synth_idx, effect_type="Spielwerk"))
        if arp.get("success"):
            arp_idx = arp.get("effect_index", 0)
            await mcp_opendaw_set_script_device_code(
                device_type="spielwerk", unit_index=synth_idx,
                device_index=arp_idx, code=load_script("spielwerk_arpeggiator.js")
            )
            await mcp_opendaw_set_script_param("spielwerk", synth_idx, arp_idx, "rate", 0.125)
            await mcp_opendaw_set_script_param("spielwerk", synth_idx, arp_idx, "octaves", 2)
            await mcp_opendaw_set_script_param("spielwerk", synth_idx, arp_idx, "direction", 0)
            await mcp_opendaw_set_script_param("spielwerk", synth_idx, arp_idx, "swing", 0.15)
            print("  Arpeggiator: rate=1/8, octaves=2, swing=15%")

        # Note track for arp notes
        note_track = json.loads(await mcp_opendaw_create_note_track(unit_index=synth_idx))
        if note_track.get("success"):
            nt_idx = note_track.get("track_index", 0)
            region = json.loads(await mcp_opendaw_create_track_region(
                unit_index=synth_idx, track_index=nt_idx,
                start_beat=0, duration_beats=16
            ))
            if region.get("success"):
                # Place bass notes for the arp to pick up
                notes = [
                    (0, 36, 4),   # C2, 4 beats
                    (4, 39, 4),   # D#2, 4 beats
                    (8, 41, 4),   # F2, 4 beats
                    (12, 36, 4),  # C2, 4 beats
                ]
                for beat, pitch, dur in notes:
                    await mcp_opendaw_create_note(
                        track_index=nt_idx, pitch=pitch,
                        start_beat=beat, duration_beats=dur,
                        velocity=0.8, unit_index=synth_idx
                    )
                print(f"  Note track {nt_idx}: 4 bass notes (C2-D#2-F2-C2)")

    # ─── 7. Render + export stems + measure LUFS ──────────────
    print("\n[7/7] Rendering enhanced mix...")
    render = json.loads(await mcp_opendaw_render_full(filename="suno_enhanced", sample_rate=48000))
    if render.get("success"):
        print(f"  Rendered: {render.get('file_path', 'unknown')}")
    else:
        print(f"  Render: {render.get('error', 'check engine')}")

    # Measure LUFS
    lufs = json.loads(await mcp_opendaw_measure_lufs())
    if lufs.get("success") or "lufs" in lufs:
        print(f"  LUFS: {lufs.get('lufs', '?')} dB "
              f"(Spotify target: -14, Apple: -16)")

    # Export stems
    print("\n  Exporting stems for further processing...")
    stems = json.loads(await mcp_opendaw_export_stems(filename="suno_stem", sample_rate=48000))
    if stems.get("success"):
        print(f"  Stems: {stems.get('stem_count', 0)} exported")
    else:
        print(f"  Stem export: {stems.get('error', 'may need render first')}")

    await bridge.stop()
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)
    print("\nThe Suno track has been enhanced with:")
    print("  • Tape saturation (analog warmth)")
    print("  • Lookahead compression (transparent leveling)")
    print("  • Reverb send bus (spatial depth)")
    print("  • MIDI arpeggio layer (harmonic enhancement)")
    print("  • LUFS measurement (streaming-ready check)")
    print("  • Stem export (for external mastering)")


if __name__ == "__main__":
    asyncio.run(main())
