"""Suno → stem split → openDAW mixing pipeline (one-call import).

Demonstrates the full Suno integration workflow using import_audio_to_tracks:
1. Import a Suno-generated track with automatic stem separation (bs6 = 6 stems)
2. Each stem gets its own instrument track, loaded and placed automatically
3. Apply genre-specific mixing (compressor, EQ, saturation per stem)
4. Add mastering chain for final polish
5. Render the enhanced mix to WAV

This is the simplest Suno-to-DAW pipeline — one import call replaces 12+ manual
calls (split_stems + create_instrument_track × 6 + load_audio × 6 + place_audio_region × 6).

Usage:
    source venv/bin/activate
    python examples/suno_stems_pipeline.py /path/to/suno_track.wav

If no file is provided, prints usage and exits.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_import_audio_to_tracks,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_add_mastering_chain,
    mcp_opendaw_render_full,
    mcp_opendaw_measure_lufs,
    mcp_opendaw_set_bpm,
)


async def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not audio_path or not os.path.exists(audio_path):
        print("Usage: python examples/suno_stems_pipeline.py /path/to/suno_track.wav")
        print("\nDownload a track from Suno (or any audio file) and pass its path.")
        return

    print("=" * 60)
    print("Suno → Stem Split → openDAW Mix Pipeline")
    print("=" * 60)
    print(f"\nInput: {audio_path}")

    await bridge.start()

    # ─── 1. Set BPM ───────────────────────────────────────────
    print("\n[1/5] Setting BPM to 120...")
    await mcp_opendaw_set_bpm(bpm=120)

    # ─── 2. Import with stem splitting ────────────────────────
    print("\n[2/5] Importing with bs6 stem separation (6 stems)...")
    result = json.loads(await mcp_opendaw_import_audio_to_tracks(
        file_path=audio_path,
        mode="bs6",
        start_beat=0.0,
    ))

    if "error" in result:
        print(f"  Import failed: {result['error']}")
        if "detail" in result:
            print(f"  Detail: {json.dumps(result['detail'], indent=2)[:500]}")
        await bridge.stop()
        return

    tracks = result.get("tracks", [])
    print(f"  Stems imported: {len(tracks)}")
    for t in tracks:
        if "error" in t:
            print(f"    {t['stem']}: ERROR — {t['error']}")
        else:
            print(f"    {t['stem']}: unit {t['unit_index']}, "
                  f"track {t['track_index']}, {t['duration']:.1f}s")

    if not tracks or all("error" in t for t in tracks):
        print("\nNo stems loaded successfully. Exiting.")
        await bridge.stop()
        return

    # ─── 3. Apply genre mix ───────────────────────────────────
    # For stem-separated imports, apply a pop-style mix across stems
    # (drums → comp+EQ, bass → EQ+sat, vocals → reverb+delay, other → reverb)
    print("\n[3/5] Applying genre mix (pop style)...")
    num_tracks = len([t for t in tracks if "error" not in t])
    mix = json.loads(await mcp_opendaw_apply_genre_mix(
        genre="pop",
        unit_index=0,
        num_tracks=min(num_tracks, 4),
        sidechain=True,
    ))
    print(f"  Effects added: {mix.get('effect_count', 0)}")
    print(f"  Sidechain: {mix.get('sidechain', 'n/a')}")

    # ─── 4. Mastering chain ───────────────────────────────────
    print("\n[4/5] Adding mastering chain (-14 LUFS, Spotify target)...")
    master = json.loads(await mcp_opendaw_add_mastering_chain(
        unit_index=0,
        target_lufs=-14,
        style="transparent",
    ))
    if "error" not in master:
        print(f"  Mastering: {master.get('effects_added', 0)} effects")
    else:
        print(f"  Mastering: {master.get('error', 'skipped')}")

    # ─── 5. Render ────────────────────────────────────────────
    print("\n[5/5] Rendering final mix...")
    render = json.loads(await mcp_opendaw_render_full(
        filename="suno_stems_mixed",
        sample_rate=48000,
    ))
    if render.get("success"):
        print(f"  Rendered: {render.get('file_path', 'unknown')}")
    else:
        print(f"  Render: {render.get('error', 'check engine')}")

    # Measure LUFS
    lufs = json.loads(await mcp_opendaw_measure_lufs())
    if "lufs" in lufs:
        print(f"  LUFS: {lufs['lufs']} dB (Spotify: -14, Apple: -16)")

    await bridge.stop()
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)
    print(f"\n{len(tracks)} stems → genre mix → mastering → render")
    print("The Suno track has been split, mixed, mastered, and rendered.")


if __name__ == "__main__":
    asyncio.run(main())
