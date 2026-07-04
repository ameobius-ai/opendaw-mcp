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
    mcp_opendaw_create_audio_bus,
    mcp_opendaw_add_send,
    mcp_opendaw_render_full,
    mcp_opendaw_export_stems,
    mcp_opendaw_measure_lufs,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def load_script(name: str) -> str:
    with open(os.path.join(SCRIPTS_DIR, name)) as f:
        return f.read()


async def main():
    # ─── Parse args ──────────────────────────────────────────
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    print("=" * 60)
    print("Suno → openDAW Enhancement Pipeline")
    print("=" * 60)
    if audio_path:
        print(f"\nInput: {audio_path}")
    else:
        print("\nNo input file — running in demo mode (audio import skipped)")

    # ─── 1. Start engine + set tempo ──────────────────────────
    print("\n[1/7] Starting engine and setting BPM...")
    state = json.loads(await mcp_opendaw_get_project_state())
    print(f"  Project loaded: {state.get('track_count', 0)} tracks")

    await mcp_opendaw_set_bpm(120)
    print("  BPM set to 120")

    # ─── 2. Load Suno track ───────────────────────────────────
    sample_id = None
    if audio_path and os.path.exists(audio_path):
        print("\n[2/7] Loading Suno track...")
        result = json.loads(await mcp_opendaw_load_audio(audio_path, "suno_track"))
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
    if sample_id:
        print("\n[3/7] Creating audio track with imported clip...")
        track = json.loads(await mcp_opendaw_create_audio_track())
        track_idx = track.get("track_index", 0)
        print(f"  Audio track created: index {track_idx}")

        clip = json.loads(await mcp_opendaw_create_audio_clip(
            sample_id, track_idx, 0, 0, 120
        ))
        if clip.get("success"):
            print("  Clip placed at bar 0")
        else:
            print(f"  Clip creation issue: {clip.get('error', 'check logs')}")
    else:
        print("\n[3/7] Skipping track creation (no audio)")
        track_idx = 0

    # ─── 4. Add mastering effects on audio track ──────────────
    print("\n[4/7] Adding mastering chain (tape sat + lookahead comp)...")
    # Werkstatt DarkSat for tape warmth
    sat = json.loads(await mcp_opendaw_add_effect(track_idx, "Werkstatt"))
    if sat.get("success"):
        fx_idx = sat.get("effect_index", 0)
        await mcp_opendaw_set_script_device_code(fx_idx, load_script("werkstatt_darksat.js"), "werkstatt")
        await mcp_opendaw_set_script_param(fx_idx, "drive", 0.25)
        await mcp_opendaw_set_script_param(fx_idx, "tone", 0.6)
        await mcp_opendaw_set_script_param(fx_idx, "mix", 0.7)
        await mcp_opendaw_set_script_param(fx_idx, "output", -2)
        print("  DarkSat tape saturation: drive=0.25, tone=0.6, mix=0.7, out=-2dB")

    # Werkstatt Lookahead for transparent leveling
    comp = json.loads(await mcp_opendaw_add_effect(track_idx, "Werkstatt"))
    if comp.get("success"):
        fx_idx = comp.get("effect_index", 0)
        await mcp_opendaw_set_script_device_code(fx_idx, load_script("werkstatt_lookahead.js"), "werkstatt")
        await mcp_opendaw_set_script_param(fx_idx, "threshold", -14)
        await mcp_opendaw_set_script_param(fx_idx, "ratio", 3)
        await mcp_opendaw_set_script_param(fx_idx, "attack", 0.005)
        await mcp_opendaw_set_script_param(fx_idx, "release", 0.15)
        await mcp_opendaw_set_script_param(fx_idx, "makeup", 3)
        await mcp_opendaw_set_script_param(fx_idx, "mix", 1)
        print("  Lookahead compressor: thresh=-14dB, ratio=3:1, makeup=+3dB")

    # ─── 5. Reverb send bus ───────────────────────────────────
    print("\n[5/7] Setting up reverb send bus...")
    bus = json.loads(await mcp_opendaw_create_audio_bus("reverb_bus"))
    if bus.get("success"):
        bus_idx = bus.get("bus_index", 0)
        # Add Werkstatt Reverb on the bus
        rev = json.loads(await mcp_opendaw_add_effect(bus_idx, "Werkstatt"))
        if rev.get("success"):
            rev_fx = rev.get("effect_index", 0)
            await mcp_opendaw_set_script_device_code(rev_fx, load_script("werkstatt_reverb.js"), "werkstatt")
            await mcp_opendaw_set_script_param(rev_fx, "decay", 0.5)
            await mcp_opendaw_set_script_param(rev_fx, "damping", 0.6)
            await mcp_opendaw_set_script_param(rev_fx, "width", 0.9)
            await mcp_opendaw_set_script_param(rev_fx, "mix", 1)
            print("  Reverb bus: decay=0.5, damping=0.6, width=0.9")

        # Send from audio track to reverb bus
        send = json.loads(await mcp_opendaw_add_send(track_idx, bus_idx, 0.35))
        if send.get("success"):
            print(f"  Send: track {track_idx} → bus {bus_idx} (level 0.35)")
        else:
            print(f"  Send issue: {send.get('error', 'check routing')}")
    else:
        print(f"  Bus creation issue: {bus.get('error', 'unknown')}")

    # ─── 6. Add MIDI arp layer ────────────────────────────────
    print("\n[6/7] Adding MIDI arpeggio layer (Apparat SubCrusher + Spielwerk)...")
    # Synth track
    synth = json.loads(await mcp_opendaw_create_synth_track("Apparat", "arp_synth"))
    if synth.get("success"):
        synth_idx = synth.get("track_index", 1)
        await mcp_opendaw_set_script_device_code(synth_idx, load_script("apparat_subcrusher.js"), "apparat")
        await mcp_opendaw_set_script_param(synth_idx, "cutoff", 800)
        await mcp_opendaw_set_script_param(synth_idx, "resonance", 0.3)
        await mcp_opendaw_set_script_param(synth_idx, "volume", 0.5)
        print(f"  SubCrusher synth on track {synth_idx}: cutoff=800Hz")

        # MIDI arpeggiator
        arp = json.loads(await mcp_opendaw_add_midi_effect(synth_idx, "Spielwerk"))
        if arp.get("success"):
            arp_idx = arp.get("effect_index", 0)
            await mcp_opendaw_set_script_device_code(arp_idx, load_script("spielwerk_arpeggiator.js"), "spielwerk")
            await mcp_opendaw_set_script_param(arp_idx, "rate", 0.125)
            await mcp_opendaw_set_script_param(arp_idx, "octaves", 2)
            await mcp_opendaw_set_script_param(arp_idx, "direction", 0)
            await mcp_opendaw_set_script_param(arp_idx, "swing", 0.15)
            print("  Arpeggiator: rate=1/8, octaves=2, swing=15%")

    # Note track for arp notes
    note_track = json.loads(await mcp_opendaw_create_note_track("arp_notes"))
    if note_track.get("success"):
        nt_idx = note_track.get("track_index", 2)
        region = json.loads(await mcp_opendaw_create_track_region(nt_idx, 0, 16))
        if region.get("success"):
            # Place a few bass notes for the arp to pick up
            notes = [
                (0, 36, 4),   # C2, 4 beats
                (4, 39, 4),   # D#2, 4 beats
                (8, 41, 4),   # F2, 4 beats
                (12, 36, 4),  # C2, 4 beats
            ]
            for beat, pitch, dur in notes:
                await mcp_opendaw_create_note(nt_idx, 0, beat, pitch, dur, 0.8)
            print(f"  Note track {nt_idx}: 4 bass notes (C2-D#2-F2-C2)")

    # ─── 7. Render + export stems + measure LUFS ──────────────
    print("\n[7/7] Rendering enhanced mix...")
    render = json.loads(await mcp_opendaw_render_full("suno_enhanced", 48000))
    if render.get("success"):
        print(f"  Rendered: {render.get('file_path', 'unknown')}")
    else:
        print(f"  Render issue: {render.get('error', 'check engine')}")

    # Measure LUFS
    lufs = json.loads(await mcp_opendaw_measure_lufs())
    if lufs.get("success"):
        print(f"  LUFS: {lufs.get('lufs', '?')} dB "
              f"(Spotify target: -14, Apple: -16)")

    # Export stems
    print("\n  Exporting stems for further processing...")
    stems = json.loads(await mcp_opendaw_export_stems("suno_stem", 48000))
    if stems.get("success"):
        print(f"  Stems: {stems.get('stem_count', 0)} exported")
    else:
        print(f"  Stem export: {stems.get('error', 'may need render first')}")

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
