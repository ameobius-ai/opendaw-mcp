"""
Showcase Demo 1: Techno track in 30 seconds.

Zero to mastered techno loop with LUFS targeting.
Demonstrates: genre preset, humanize, auto-mix, auto-master, render.

Usage:
    pip install opendaw-mcp==1.385.0
    python examples/showcase/01_techno_30s.py

Expected output: WAV file at -14 LUFS (Spotify-ready).
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from server import (
    bridge,
    mcp_opendaw_create_song_with_variations,
    mcp_opendaw_render_full_song,
)


async def main():
    await bridge.start()
    try:
        # Build 16-bar techno track: drums + bass + lead, 3 varied sections
        song = await mcp_opendaw_create_song_with_variations(
            genre="techno",
            root="A",
            scale="minor",
            bars=16,
            variations=["full", "drums_bass", "full_busy"],
            humanize=True,
            mix=True,
            master=True,
        )
        data = json.loads(song)
        print(f"Song created: {data.get('bars', '?')} bars, tempo {data.get('bpm', '?')} BPM")

        # Render to WAV at 44.1kHz
        result = await mcp_opendaw_render_full_song("showcase_techno.wav", 44100)
        render = json.loads(result)
        print(f"Rendered: {render.get('samples', 0)} samples")
        print(f"Max sample: {render.get('max_sample', 0):.4f}")
        if render.get("lufs_integrated"):
            print(f"LUFS: {render['lufs_integrated']} dB")
        print(f"Output: {os.path.abspath('exports/showcase_techno.wav')}")
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
