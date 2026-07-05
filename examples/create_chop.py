"""Example: create_chop — slice and rearrange pitches.

Demonstrates 5 chop modes on the same source material:
  1. Reverse — classic Dilla flip
  2. Stutter — glitch-hop repeat
  3. Shuffle — Madlib-style random rearrangement
  4. Ping-pong — forward then backward
  5. Gate — chopped break feel (every other segment)

Also shows octave shift for bass chops.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DAW_URL", "http://localhost:5174")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_chop,
)


async def main():
    await bridge.start()
    print("bridge ready")

    # Create a synth track
    r = await mcp_opendaw_create_synth_track("ChopDemo", "vaporisateur")
    print(f"synth: {r[:80]}")

    # 1. Classic Dilla reverse flip
    r = await mcp_opendaw_create_chop(
        pitches="60,62,64,67,69,71",
        chop_mode="reverse",
        segment_beats=0.5,
        start_beat=0,
    )
    print(f"\n1. Reverse (Dilla flip): {r}")

    # 2. Glitch stutter — repeat each segment 3x
    r = await mcp_opendaw_create_chop(
        pitches="60,64,67,72",
        chop_mode="stutter",
        stutter_count=3,
        segment_beats=0.25,
        start_beat=8,
    )
    print(f"2. Stutter (glitch): {r}")

    # 3. Madlib shuffle — random order, seeded
    r = await mcp_opendaw_create_chop(
        pitches="60,62,64,67,69,71,72,74",
        chop_mode="shuffle",
        segment_beats=0.375,
        seed=1337,
        start_beat=16,
    )
    print(f"3. Shuffle (Madlib): {r}")

    # 4. Ping-pong — forward then backward
    r = await mcp_opendaw_create_chop(
        pitches="60,62,64,67",
        chop_mode="ping-pong",
        segment_beats=0.5,
        start_beat=24,
    )
    print(f"4. Ping-pong: {r}")

    # 5. Gate — chopped break, every other segment
    r = await mcp_opendaw_create_chop(
        pitches="60,62,64,67,69,71,72,74",
        chop_mode="gate",
        segment_beats=0.25,
        start_beat=32,
    )
    print(f"5. Gate (chopped break): {r}")

    # 6. Bass chop — octave down
    r = await mcp_opendaw_create_chop(
        pitches="48,50,52,55,48,52,50,48",
        chop_mode="shuffle",
        octave_shift=-1,
        segment_beats=0.5,
        velocity=0.85,
        velocity_variation=0.15,
        seed=777,
        start_beat=40,
    )
    print(f"6. Bass chop (octave -1): {r}")

    await bridge.stop()
    print("\ndone — 6 chops created across 48 beats")


if __name__ == "__main__":
    asyncio.run(main())
