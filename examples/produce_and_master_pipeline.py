"""
Example: One-Call Produce & Master — produce_and_master pipeline

The ultimate demo: one call produces AND masters a complete track.
Replaces 30-40 individual tool calls with a single call.

Shows 5 genre examples:
  1. House — A minor, 124 BPM, Spotify
  2. DnB — A minor, 174 BPM, Spotify
  3. Metal — D minor, 160 BPM, Club (loud)
  4. Ambient — C major, 70 BPM, Apple (quiet)
  5. Industrial — D minor, 135 BPM, YouTube

Usage:
  # Start Vite dev server first:
  cd headless-daw && npx vite --port 5174

  # Then run:
  python examples/produce_and_master_pipeline.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.bridge import HeadlessDawBridge

DAW_URL = "http://localhost:5174"


async def demo_genre(genre, key_root, scale_type, bpm, platform, master_style, structure):
    """Run produce_and_master for a single genre."""
    print(f"\n{'='*60}")
    print(f"  {genre.upper()} — {key_root} {scale_type}, {bpm} BPM, {platform}, {master_style}")
    print(f"{'='*60}")

    bridge = HeadlessDawBridge(DAW_URL)
    await bridge.start()

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "server",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py")
        )
        server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)

        result = await server.mcp_opendaw_produce_and_master(
            structure=structure,
            key_root=key_root,
            scale_type=scale_type,
            genre=genre,
            bpm=bpm,
            platform=platform,
            master_style=master_style,
            render=False,  # skip render for speed
            seed=42,
        )

        data = json.loads(result)
        print(f"  Steps: {data.get('steps_completed', 0)}/{data.get('steps_total', 7)}")
        print(f"  Notes: {data.get('total_notes', 0)}")

        if "arrangement" in data:
            arr = data["arrangement"]
            print(f"  Arrangement: {arr.get('sections', 0)} sections, {arr.get('bars', 0)} bars")
        if "drums" in data:
            print(f"  Drums: {data['drums']} notes")
        if "bass" in data:
            print(f"  Bass: {data['bass']} notes")
        if "genre_effects" in data:
            fx = data["genre_effects"]
            print(f"  Genre FX: {fx.get('added', 0)}/{fx.get('planned', 0)} effects")
        if "mastering" in data:
            print(f"  Mastering: {platform} / {master_style}")

        errors = [k for k in data if k.endswith("_error")]
        if errors:
            print(f"  Warnings: {', '.join(errors)}")

    finally:
        await bridge.stop()


async def main():
    print("=" * 60)
    print("  opendaw-mcp — One-Call Produce & Master Pipeline")
    print("  5 genre demos, each = 1 tool call = full track + mastering")
    print("=" * 60)

    genres = [
        ("house", "A", "minor", 124, "spotify", "balanced",
         "intro:4,verse:8,prechorus:2,chorus:8,bridge:4,chorus:8,outro:4"),
        ("dnb", "A", "minor", 174, "spotify", "balanced",
         "intro:8,verse:8,chorus:8,bridge:4,chorus:8,outro:4"),
        ("metal", "D", "minor", 160, "club", "loud",
         "intro:4,verse:8,chorus:8,bridge:4,chorus:8,outro:4"),
        ("ambient", "C", "major", 70, "apple", "transparent",
         "intro:8,verse:8,chorus:8,outro:8"),
        ("industrial", "D", "minor", 135, "youtube", "warm",
         "intro:4,verse:8,chorus:8,bridge:4,chorus:8,outro:4"),
    ]

    for genre, key, scale, bpm, platform, style, structure in genres:
        try:
            await demo_genre(genre, key, scale, bpm, platform, style, structure)
        except Exception as e:
            print(f"  (skipped: {e})")

    print(f"\n{'='*60}")
    print("  Done — 5 genres, 5 calls, 5 produced tracks")
    print("  Each call replaced ~30-40 individual tool calls")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
