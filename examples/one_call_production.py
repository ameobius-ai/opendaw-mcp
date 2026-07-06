"""
Example: One-Call Production Pipeline — produce_full_track + arrange_full_song

Demonstrates the two most powerful meta-tools:
  arrange_full_song  — Build a complete MIDI skeleton from a structure string
  produce_full_track — Full production: BPM + arrangement + drums + bass + mix + render

These tools replace 15-20 individual MCP calls with a single call each.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.bridge import HeadlessDawBridge

DAW_URL = "http://localhost:5174"


async def demo_arrange_full_song():
    """Build a complete song skeleton in one call."""
    print("=" * 60)
    print("DEMO 1: arrange_full_song — MIDI skeleton in one call")
    print("=" * 60)

    # Standard pop song structure
    structure = "intro:4,verse:8,prechorus:2,chorus:8,verse:8,prechorus:2,chorus:8,bridge:4,chorus:8,outro:4"

    bridge = HeadlessDawBridge(DAW_URL)
    await bridge.start()

    # Import the tool function directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("server", os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py"))
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)

    result = await server.mcp_opendaw_arrange_full_song(
        structure=structure,
        key_root="C",
        scale_type="minor",
        octave=4,
        velocity=0.65,
        intro_type="melodic",
        prechorus_type="build",
        bridge_type="breakdown",
        outro_type="fade",
    )

    data = json.loads(result)
    print(f"Sections created: {data.get('total_sections', 0)}")
    print(f"Total bars: {data.get('total_bars', 0)}")
    print(f"Total notes: {data.get('total_notes', 0)}")
    print(f"Key: {data.get('key_root', '?')} {data.get('scale_type', '?')}")

    for sec in data.get("sections", []):
        print(f"  {sec['section']:12s}  {sec['bars']:2d} bars  [{sec['start_beat']:.0f}-{sec['end_beat']:.0f}]  {sec['notes_generated']} notes")

    await bridge.stop()


async def demo_produce_full_track():
    """Produce a complete track in one call — BPM + arrangement + drums + bass + mix."""
    print()
    print("=" * 60)
    print("DEMO 2: produce_full_track — full production in one call")
    print("=" * 60)

    bridge = HeadlessDawBridge(DAW_URL)
    await bridge.start()

    import importlib.util
    spec = importlib.util.spec_from_file_location("server", os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py"))
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)

    # House track at 124 BPM
    result = await server.mcp_opendaw_produce_full_track(
        structure="intro:4,verse:8,prechorus:2,chorus:8,bridge:4,chorus:8,outro:4",
        key_root="A",
        scale_type="minor",
        octave=4,
        velocity=0.65,
        genre="house",
        bpm=124,
        render=False,
        seed=42,
    )

    data = json.loads(result)
    print(f"Produced: {data.get('produced', False)}")
    print(f"Genre: {data.get('genre', '?')}  BPM: {data.get('bpm', '?')}")
    print(f"Key: {data.get('key_root', '?')} {data.get('scale_type', '?')}")
    print(f"Total notes: {data.get('total_notes', 0)}")

    for key in ["arrangement", "drums", "bass", "mix", "render"]:
        if key in data:
            print(f"  {key}: {data[key]}")

    if data.get("rendered"):
        print(f"  WAV rendered: {data.get('render', {}).get('duration', 0):.1f}s")

    await bridge.stop()


async def demo_custom_structure():
    """Custom structure with all section types."""
    print()
    print("=" * 60)
    print("DEMO 3: Custom structure with all 9 section types")
    print("=" * 60)

    structure = "intro:8,prechorus:2,chorus:4,interlude:2,verse:8,prechorus:2,chorus:4,transition:2,chorus:4,bridge:4,chorus:8,coda:2"

    bridge = HeadlessDawBridge(DAW_URL)
    await bridge.start()

    import importlib.util
    spec = importlib.util.spec_from_file_location("server", os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py"))
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)

    result = await server.mcp_opendaw_arrange_full_song(
        structure=structure,
        key_root="D",
        scale_type="major",
        octave=4,
        velocity=0.7,
        intro_type="cinematic",
        prechorus_type="suspending",
        bridge_type="modulation",
        outro_type="ritardando",
        interlude_type="contrapuntal",
        transition_type="texture_build",
        coda_type="fanfare",
        seed=99,
    )

    data = json.loads(result)
    print(f"Sections: {data.get('total_sections', 0)}")
    print(f"Total bars: {data.get('total_bars', 0)}")
    print(f"Total notes: {data.get('total_notes', 0)}")

    for sec in data.get("sections", []):
        print(f"  {sec['section']:12s}  {sec['bars']:2d} bars  [{sec['start_beat']:.0f}-{sec['end_beat']:.0f}]")

    await bridge.stop()


async def main():
    print("openDAW MCP — One-Call Production Pipeline Examples")
    print("Requires: Vite dev server running on http://localhost:5174")
    print()

    try:
        await demo_arrange_full_song()
    except Exception as e:
        print(f"  (skipped: {e})")

    try:
        await demo_produce_full_track()
    except Exception as e:
        print(f"  (skipped: {e})")

    try:
        await demo_custom_structure()
    except Exception as e:
        print(f"  (skipped: {e})")


if __name__ == "__main__":
    asyncio.run(main())
