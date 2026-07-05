"""Example: create_trill — rapid two-note alternation ornaments.

Demonstrates trills across genres:
  1. Baroque trill (16th, upper accented)
  2. Fast 32nd trill
  3. Slow 8th trill
  4. Triplet 16th jazz shake
  5. Whole-tone trill (3 semitone interval)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DAW_URL", "http://localhost:5174")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_trill,
)


async def main():
    await bridge.start()
    print("bridge ready")

    r = await mcp_opendaw_create_synth_track("TrillDemo", "vaporisateur")
    print(f"synth: {r[:80]}")

    # 1. Baroque trill — C-D, 16th notes, upper accented, 1 bar
    r = await mcp_opendaw_create_trill(
        lower_pitch=60, upper_pitch=62, rate="16th",
        duration_beats=4, accent_upper=True, start_beat=0,
    )
    print(f"\n1. Baroque trill (C-D 16th): {r}")

    # 2. Fast 32nd trill — 2 bars
    r = await mcp_opendaw_create_trill(
        lower_pitch=64, upper_pitch=65, rate="32nd",
        duration_beats=8, start_beat=4,
    )
    print(f"2. Fast 32nd trill (C#-D): {r}")

    # 3. Slow 8th trill — like a measured tremolo
    r = await mcp_opendaw_create_trill(
        lower_pitch=55, upper_pitch=59, rate="8th",
        duration_beats=4, accent_upper=False, start_beat=12,
    )
    print(f"3. Slow 8th trill (G-B): {r}")

    # 4. Triplet 16th — jazz shake feel
    r = await mcp_opendaw_create_trill(
        lower_pitch=72, upper_pitch=74, rate="16t",
        duration_beats=4, start_beat=16,
    )
    print(f"4. Triplet 16th shake (C5-D5): {r}")

    # 5. Whole-tone trill — minor 3rd interval
    r = await mcp_opendaw_create_trill(
        lower_pitch=48, upper_pitch=51, rate="16th",
        duration_beats=2, accent_upper=False, start_beat=20,
    )
    print(f"5. Minor 3rd trill (C3-D#3): {r}")

    await bridge.stop()
    print("\ndone — 5 trills created")


if __name__ == "__main__":
    asyncio.run(main())
