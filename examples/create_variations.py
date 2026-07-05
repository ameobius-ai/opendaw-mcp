"""Example: create_variations — thematic variation generator.

    python3 examples/create_variations.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_create_note_track,
        mcp_opendaw_create_melody,
        mcp_opendaw_create_variations,
    )

    # Setup: synth + note track
    await mcp_opendaw_create_synth_track("Theme", "vaporisateur")
    await mcp_opendaw_create_note_track(0)

    # Create source theme (A minor scale)
    await mcp_opendaw_create_melody(
        scale="minor", root="A", pattern="1 2 3 5 4 3 2 1",
        unit_index=0, track_index=0,
    )

    # Generate 5 variations
    r = await mcp_opendaw_create_variations(
        source_unit=0, source_track=0, source_region=0,
        variations="transpose:5,invert,reverse,augment:2,octave_down",
        start_beat=8,
    )
    print(f"Variations: {r[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
