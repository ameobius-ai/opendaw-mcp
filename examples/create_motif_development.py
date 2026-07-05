"""Example: create_motif_development — Beethoven-style melodic development.

    python3 examples/create_motif_development.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_create_note_track,
        mcp_opendaw_create_motif_development,
    )

    await mcp_opendaw_create_synth_track("Motif", "vaporisateur")
    await mcp_opendaw_create_note_track(0)

    # Beethoven 5th style: 4-note motif developed into full arc
    r = await mcp_opendaw_create_motif_development(
        motif="1,1,1,2",
        scale="minor", root="G",
        steps="statement,statement,sequence_up,fragment,invert,sequence_down,fragment,octave_up,compress,cadence",
        step_duration=0.25,
        unit_index=0, track_index=0,
    )
    print(f"Development: {r[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
