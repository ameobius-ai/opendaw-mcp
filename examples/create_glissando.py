"""Example: create_glissando — smooth scale runs between two pitches.

Demonstrates glissando across scales and directions:
  1. Chromatic ascending (C→C, every semitone)
  2. Major scale ascending
  3. Pentatonic minor (fewer notes, bluesy)
  4. Descending chromatic
  5. Whole tone (Debussy dream)
"""
import asyncio, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DAW_URL", "http://localhost:5174")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_glissando,
)

async def main():
    await bridge.start()
    print("bridge ready")

    r = await mcp_opendaw_create_synth_track("GlissDemo", "vaporisateur")
    print(f"synth: {r[:80]}")

    r = await mcp_opendaw_create_glissando(60, 72, "chromatic", rate="16th", duration_beats=4, start_beat=0)
    print(f"\n1. Chromatic asc: {r}")

    r = await mcp_opendaw_create_glissando(60, 72, "major", rate="8th", duration_beats=4, start_beat=4)
    print(f"2. Major asc: {r}")

    r = await mcp_opendaw_create_glissando(60, 72, "pentatonic_minor", rate="8th", velocity_curve="ramp_up", start_beat=8)
    print(f"3. Pentatonic minor: {r}")

    r = await mcp_opendaw_create_glissando(72, 60, "chromatic", rate="16th", velocity_curve="ramp_down", start_beat=12)
    print(f"4. Chromatic desc: {r}")

    r = await mcp_opendaw_create_glissando(60, 72, "whole_tone", rate="16t", velocity_curve="arc", start_beat=16)
    print(f"5. Whole tone: {r}")

    await bridge.stop()
    print("\ndone — 5 glissandi created")

if __name__ == "__main__":
    asyncio.run(main())
