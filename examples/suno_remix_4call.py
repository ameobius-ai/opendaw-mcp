"""Suno → openDAW remix pipeline — 4 calls from generation to render.

Uses remix_track for the entire remix process:
  1. chirp_generate (Suno)
  2. download_audio (URL → local file)
  3. remix_track (analyze + set_bpm + import + progression + harmony + mix + master)
  4. render_full (export WAV)

remix_track does 7 steps internally:
  - analyze_track: BPM + key + mode + LUFS + duration + dynamic range
  - set_bpm: match project tempo to source
  - import_audio_to_tracks: stem separation (bs6 = 6 stems) + load + place
  - create_progression_from_key: diatonic auto-progression from detected key
  - create_harmonic_arrangement: arp + melody on top of stems
  - apply_genre_mix: genre-specific processing (compressor, EQ, saturation)
  - add_mastering_chain: LUFS-targeted mastering

Requirements:
  - Vite dev server running on localhost:5174 (headless-daw)
  - Suno chirp_generate available (Hermes tool)
  - opendaw-mcp venv activated

Usage:
  source venv/bin/activate
  python examples/suno_remix_4call.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    bridge,
    mcp_opendaw_download_audio,
    mcp_opendaw_remix_track,
    mcp_opendaw_render_full,
)


async def suno_remix_pipeline(
    suno_audio_url: str,
    genre: str = "synthwave",
    style: str = "synthwave",
    stem_mode: str = "bs6",
    master_lufs: float = -14,
    add_counter_melody: bool = True,
    output_filename: str = "remix_final",
):
    """Full Suno remix pipeline — 4 calls from URL to rendered WAV.

    Args:
        suno_audio_url: Direct audio URL from chirp_generate result.
        genre: Genre for mix processing (synthwave, house, techno, dnb, etc).
        style: Progression style (pop, jazz, rock, synthwave, folk, lofi).
        stem_mode: Stem separation mode (bs2, bs4, bs6) or "" for simple import.
        master_lufs: Mastering target (-14 Spotify, -10 loud, -16 Apple).
        add_counter_melody: Add counter-melody harmonic layer.
        output_filename: Output WAV filename (without extension).

    Returns:
        dict with remix results and render path.
    """
    await bridge.start()

    print("=== Suno → openDAW Remix Pipeline (4 calls) ===\n")

    # Call 1: Download Suno track
    print("1. Downloading Suno track...")
    dl = await mcp_opendaw_download_audio(url=suno_audio_url, filename="suno_track.wav")
    dl_data = __import__("json").loads(dl)
    path = dl_data.get("file_path", "/tmp/suno_track.wav")
    print(f"   Downloaded: {path}")

    # Call 2: Full remix (7 steps in 1 call)
    print("2. Remixing (analyze + import + harmony + mix + master)...")
    remix = await mcp_opendaw_remix_track(
        filename=path,
        genre=genre,
        style=style,
        stem_mode=stem_mode,
        add_counter_melody=add_counter_melody,
        master_lufs=master_lufs,
    )
    remix_data = __import__("json").loads(remix)
    print(f"   BPM: {remix_data.get('detected_bpm')}")
    print(f"   Key: {remix_data.get('detected_key')} {remix_data.get('detected_mode')}")
    print(f"   Progression: {remix_data.get('progression')}")
    print(f"   Ready: {remix_data.get('ready_for_export')}")

    # Call 3: Render
    print("3. Rendering final mix...")
    render = await mcp_opendaw_render_full(filename=output_filename, sample_rate=48000)
    print(f"   Rendered: {output_filename}.wav")

    await bridge.stop()

    print(f"\n=== Done: {output_filename}.wav ===")
    return {
        "remix": remix_data,
        "render": render,
    }


if __name__ == "__main__":
    # Example: replace with actual Suno audio URL from chirp_generate
    # result = chirp_generate(prompt="dark synthwave 80s retro", style="synthwave, dark, 110 BPM")
    # suno_url = result[0]["audio_url"]

    demo_url = sys.argv[1] if len(sys.argv) > 1 else "https://cdn.suno.ai/example.wav"

    asyncio.run(suno_remix_pipeline(
        suno_audio_url=demo_url,
        genre="synthwave",
        style="synthwave",
        stem_mode="bs6",
        master_lufs=-14,
        add_counter_melody=True,
        output_filename="remix_final",
    ))
