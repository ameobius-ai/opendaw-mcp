"""Suno → Stem Split → openDAW pipeline — full E2E AI track enhancement.

Demonstrates the complete agent-native workflow:
1. Split a Suno-generated track into stems (bs6: 6 stems, local GPU)
2. Import each stem into openDAW as a separate audio track
3. Add per-stem effects (saturation on bass, reverb send on vocals, etc.)
4. Set volume/pan per stem
5. Add a MIDI arp layer (Apparat + Spielwerk)
6. Render the enhanced mix

This is the "full production" pipeline — from raw AI generation to mixed track.

Requirements:
    - openDAW Vite dev server running on localhost:5174
    - Stem splitter installed: ~/projects/creative-studio/stem-splitter/
      (venv + models + sota_splitter.py)
    - GPU (CUDA) for stem separation

Usage:
    source venv/bin/activate
    python examples/suno_stems_to_opendaw.py /path/to/suno_track.wav

    # Use ensemble mode (max quality, slower)
    python examples/suno_stems_to_opendaw.py /path/to/suno_track.wav --mode ensemble

    # Skip stem split (if already separated)
    python examples/suno_stems_to_opendaw.py --stems-dir /tmp/stems_mytrack
"""

import asyncio
import json
import sys
import os
import argparse

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
    mcp_opendaw_add_midi_effect,
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_set_bpm,
    mcp_opendaw_set_track_volume,
    mcp_opendaw_set_track_panning,
    mcp_opendaw_create_send,
    mcp_opendaw_render_full,
    mcp_opendaw_export_stems,
    mcp_opendaw_measure_lufs,
    mcp_opendaw_split_stems,
    mcp_opendaw_list_split_modes,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def load_script(name: str) -> str:
    with open(os.path.join(SCRIPTS_DIR, name)) as f:
        return f.read()


async def main():
    parser = argparse.ArgumentParser(description="Suno → Stem Split → openDAW pipeline")
    parser.add_argument("input", nargs="?", help="Input audio file (Suno WAV/MP3)")
    parser.add_argument("--mode", default="bs6", help="Stem split mode (default: bs6)")
    parser.add_argument("--stems-dir", help="Skip split, use existing stems directory")
    parser.add_argument("--output", default="/tmp/opendaw_enhanced", help="Output directory")
    args = parser.parse_args()

    print("=" * 60)
    print("Suno → Stem Split → openDAW Enhancement Pipeline")
    print("=" * 60)

    await bridge.start()

    # ─── 0. Check available split modes ─────────────────────
    modes = json.loads(await mcp_opendaw_list_split_modes())
    print(f"\nStem split modes available: {len(modes['modes'])}")
    print(f"Using mode: {args.mode}")

    # ─── 1. Split stems (or use existing) ────────────────────
    stems = []
    result = None
    if args.stems_dir and os.path.isdir(args.stems_dir):
        print(f"\n[1/6] Using existing stems from {args.stems_dir}")
        for f in sorted(os.listdir(args.stems_dir)):
            if f.endswith(".wav"):
                stems.append({
                    "name": os.path.splitext(f)[0],
                    "path": os.path.join(args.stems_dir, f),
                })
        print(f"  Found {len(stems)} stems")
    elif args.input and os.path.exists(args.input):
        print(f"\n[1/6] Splitting stems (mode={args.mode})...")
        print(f"  Input: {args.input}")
        print("  This runs locally on GPU — may take 15-90s depending on mode...")
        result = json.loads(await mcp_opendaw_split_stems(
            file_path=args.input, mode=args.mode, import_to_daw=True
        ))
        if result.get("success"):
            stems = result.get("stems", [])
            imported = result.get("imported", [])
            print(f"  Split complete: {result['stem_count']} stems in {result['output_dir']}")
            for s in stems:
                print(f"    {s['name']:12s} {s.get('size_mb', 0):.1f} MB")
            if imported:
                print(f"  Auto-imported {len(imported)} stems into DAW")
        else:
            print(f"  Split failed: {result.get('error', 'unknown')}")
            return
    else:
        print("\n[1/6] No input file and no stems dir — running in demo mode")

    # ─── 2. Set up project ───────────────────────────────────
    print("\n[2/6] Setting up project...")
    state = json.loads(await mcp_opendaw_get_project_state())
    print(f"  Project: {state.get('track_count', 0)} tracks")

    await mcp_opendaw_set_bpm(bpm=120)
    print("  BPM set to 120")

    # ─── 3. Create tracks for each stem ──────────────────────
    print(f"\n[3/6] Creating tracks for {len(stems)} stems...")

    stem_tracks = {}  # stem_name → {unit_idx, track_idx, sample_id}
    primary_unit = 0

    # If stems were auto-imported, use those sample IDs
    if result and result.get("imported"):
        for imp in result["imported"]:
            if "sample_id" in imp:
                track = json.loads(await mcp_opendaw_create_audio_track())
                tidx = track.get("track_index", 0)
                json.loads(await mcp_opendaw_create_audio_clip(
                    sample_id=imp["sample_id"], unit_index=primary_unit,
                    clip_index=0, track_index=tidx, bpm=120
                ))
                stem_tracks[imp["name"]] = {"track_idx": tidx, "sample_id": imp["sample_id"]}
                print(f"  {imp['name']:12s} → track {tidx}")
    elif stems:
        for stem in stems:
            load_result = json.loads(await mcp_opendaw_load_audio(
                file_path=stem["path"], name=stem["name"]
            ))
            if load_result.get("success"):
                track = json.loads(await mcp_opendaw_create_audio_track())
                tidx = track.get("track_index", 0)
                json.loads(await mcp_opendaw_create_audio_clip(
                    sample_id=load_result["id"], unit_index=primary_unit,
                    clip_index=0, track_index=tidx, bpm=120
                ))
                stem_tracks[stem["name"]] = {"track_idx": tidx, "sample_id": load_result["id"]}
                print(f"  {stem['name']:12s} → track {tidx}")

    # ─── 4. Mix: volume, pan, effects per stem ───────────────
    print("\n[4/6] Mixing stems...")

    # Genre-adaptive mix presets (coldwave/darksynth defaults)
    mix_presets = {
        "bass":          {"volume_db": -3, "pan": 0.0, "send_reverb": False},
        "drums":         {"volume_db": 0,  "pan": 0.0, "send_reverb": False},
        "vocals":        {"volume_db": -6, "pan": 0.0, "send_reverb": True},
        "other":         {"volume_db": -8, "pan": -0.3, "send_reverb": False},
        "guitar":        {"volume_db": -8, "pan": 0.4, "send_reverb": False},
        "piano":         {"volume_db": -10, "pan": -0.2, "send_reverb": False},
        "dry":           {"volume_db": -6, "pan": 0.0, "send_reverb": True},
        "clean":         {"volume_db": 0,  "pan": 0.0, "send_reverb": False},
        "instrumental":  {"volume_db": -12, "pan": 0.0, "send_reverb": False},
    }

    for stem_name, info in stem_tracks.items():
        tidx = info["track_idx"]
        preset = mix_presets.get(stem_name, {"volume_db": -8, "pan": 0.0, "send_reverb": False})

        await mcp_opendaw_set_track_volume(unit_index=primary_unit, volume_db=preset["volume_db"])
        await mcp_opendaw_set_track_panning(unit_index=primary_unit, panning=preset["pan"])
        print(f"  {stem_name:12s} vol={preset['volume_db']:+d}dB pan={preset['pan']:+.1f}")

        # Add reverb send for vocals
        if preset["send_reverb"]:
            send = json.loads(await mcp_opendaw_create_send(
                src_unit=primary_unit, name=f"reverb_{stem_name}",
                send_level_db=-9, routing="primary"
            ))
            print(f"    → reverb send: {send.get('success', False)}")

    # ─── 5. Add MIDI layer ───────────────────────────────────
    print("\n[5/6] Adding MIDI arp layer...")
    try:
        synth = json.loads(await mcp_opendaw_create_synth_track(
            name="ArpSynth", synth_type="Apparat"
        ))
        if synth.get("success"):
            synth_idx = synth.get("unit_index", 1)

            # Load Apparat sub crusher synth
            await mcp_opendaw_set_script_device_code(
                device_type="apparat", unit_index=synth_idx,
                device_index=0, code=load_script("apparat_subcrusher.js")
            )
            await mcp_opendaw_set_script_param("apparat", synth_idx, 0, "cutoff", 800)
            await mcp_opendaw_set_script_param("apparat", synth_idx, 0, "volume", 0.5)

            # Create note track
            note_track = json.loads(await mcp_opendaw_create_note_track(unit_index=synth_idx))
            if note_track.get("success"):
                note_tidx = note_track.get("track_index", 0)

                # Create a region
                json.loads(await mcp_opendaw_create_track_region(
                    unit_index=synth_idx, track_index=note_tidx,
                    start_beat=0, duration_beats=16
                ))

                # Add arpeggiator MIDI effect
                arp = json.loads(await mcp_opendaw_add_midi_effect(
                    unit_index=synth_idx, effect_type="Spielwerk"
                ))
                if arp.get("success"):
                    arp_idx = arp.get("effect_index", 0)
                    await mcp_opendaw_set_script_device_code(
                        device_type="spielwerk", unit_index=synth_idx,
                        device_index=arp_idx, code=load_script("spielwerk_arpeggiator.js")
                    )
                    await mcp_opendaw_set_script_param("spielwerk", synth_idx, arp_idx, "rate", 0.125)
                    await mcp_opendaw_set_script_param("spielwerk", synth_idx, arp_idx, "octaves", 2)

                # Add bass notes
                notes = [
                    (0, 36, 4),   # C2
                    (4, 43, 4),   # G2
                    (8, 48, 4),   # C3
                    (12, 43, 4),  # G2
                ]
                for beat, pitch, dur in notes:
                    await mcp_opendaw_create_note(
                        track_index=note_tidx, pitch=pitch,
                        start_beat=beat, duration_beats=dur,
                        velocity=0.8, unit_index=synth_idx
                    )
                print(f"  Arp synth on unit {synth_idx}, {len(notes)} notes")
    except Exception as e:
        print(f"  MIDI layer skipped: {e}")

    # ─── 6. Render + export ──────────────────────────────────
    print("\n[6/6] Rendering final mix...")
    os.makedirs(args.output, exist_ok=True)

    render = json.loads(await mcp_opendaw_render_full(filename="enhanced_mix", sample_rate=48000))
    if render.get("success"):
        print(f"  Rendered: {render.get('file_path', 'unknown')}")

    # Measure LUFS
    lufs = json.loads(await mcp_opendaw_measure_lufs())
    if lufs.get("success") or "lufs" in lufs:
        print(f"  LUFS: {lufs.get('lufs', 'N/A')} dB")

    # Export stems
    stems_export = json.loads(await mcp_opendaw_export_stems(filename="enhanced_stem", sample_rate=48000))
    if stems_export.get("success"):
        print(f"  Stems exported: {stems_export.get('stem_count', 0)} files")

    await bridge.stop()
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"Output: {args.output}/")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
