"""
Showcase Demo 3: Suno → DAW pipeline.

Import a Suno-generated track, separate into stems, rebuild the
project with individual tracks for each stem, add effects, re-render.

Demonstrates: audio import, stem separation, multi-track rebuild.

Usage:
    pip install opendaw-mcp==1.385.0
    # Requires a Suno export WAV file
    python examples/showcase/03_suno_to_daw.py /path/to/suno_track.wav

Expected output: Multi-track project with isolated drums, bass, vocals, other.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from server import (
    bridge,
    mcp_opendaw_import_audio_to_tracks,
    mcp_opendaw_set_bpm,
    mcp_opendaw_add_effect,
    mcp_opendaw_set_effect_parameter,
    mcp_opendaw_render_full,
    mcp_opendaw_get_full_project_state,
)


async def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not audio_path or not os.path.exists(audio_path):
        print("Usage: python 03_suno_to_daw.py /path/to/suno_track.wav")
        print("\nDownload any Suno track as WAV and pass its path.")
        sys.exit(1)

    await bridge.start()
    try:
        # Import Suno track → separate into stems (drums, bass, vocals, other)
        result = await mcp_opendaw_import_audio_to_tracks(audio_path, separate=True)
        data = json.loads(result)
        tracks_created = data.get("tracks_created", 0)
        print(f"Imported: {tracks_created} stem tracks from {os.path.basename(audio_path)}")

        # Add effects per stem
        # Drums: light compression
        await mcp_opendaw_add_effect(1, "Compressor")
        await mcp_opendaw_set_effect_parameter(1, 0, "ratio", 4)
        await mcp_opendaw_set_effect_parameter(1, 0, "threshold", 0.5)

        # Bass: sidechain-style ducking via volume automation
        if tracks_created >= 2:
            await mcp_opendaw_add_effect(2, "Compressor")
            await mcp_opendaw_set_effect_parameter(2, 0, "ratio", 6)
            await mcp_opendaw_set_effect_parameter(2, 0, "threshold", 0.4)

        # Vocals: reverb
        if tracks_created >= 3:
            await mcp_opendaw_add_effect(3, "Reverb")
            await mcp_opendaw_set_effect_parameter(3, 0, "mix", 0.35)
            await mcp_opendaw_set_effect_parameter(3, 0, "decay", 0.5)

        # Project state
        state = await mcp_opendaw_get_full_project_state()
        state_data = json.loads(state)
        print(f"Project: {len(state_data.get('tracks', []))} tracks, BPM {state_data.get('bpm', '?')}")

        # Render
        render = await mcp_opendaw_render_full("showcase_suno_remix.wav", 44100)
        render_data = json.loads(render)
        print(f"Rendered: {render_data.get('samples', 0)} samples")
        print(f"Max sample: {render_data.get('max_sample', 0):.4f}")
        print(f"Output: {os.path.abspath('exports/showcase_suno_remix.wav')}")
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
