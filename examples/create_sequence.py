"""Example: create_sequence — transposed melodic repetition.

The most fundamental compositional technique in Western music.

  1. Ascending 4th sequence (baroque/classical)
  2. Descending 2nd sequence (jazz ii-V-I chain)
  3. Alternating 5th (film score tension)
  4. Fade-out sequence (EDM build decay)
  5. Rising quint build-up (cinematic escalation)
"""
import asyncio, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DAW_URL", "http://localhost:5174")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_sequence,
)

async def main():
    await bridge.start()
    print("bridge ready")

    r = await mcp_opendaw_create_synth_track("SeqDemo", "vaporisateur")
    print(f"synth: {r[:80]}")

    # 1. Ascending 4th — Pachelbel-style
    r = await mcp_opendaw_create_sequence(pattern="60,64,67,64", transposition=5, repeats=4, direction="up", segment_beats=2, start_beat=0)
    print(f"\n1. Ascending 4th: {r}")

    # 2. Descending 2nd — jazz chain
    r = await mcp_opendaw_create_sequence(pattern="74,72,71,69", transposition=2, repeats=4, direction="down", segment_beats=2, start_beat=8)
    print(f"2. Descending 2nd: {r}")

    # 3. Alternating 5th — film score tension
    r = await mcp_opendaw_create_sequence(pattern="60,62,64", transposition=7, repeats=4, direction="alternating", segment_beats=1.5, start_beat=16)
    print(f"3. Alternating 5th: {r}")

    # 4. Fade-out — EDM build decay
    r = await mcp_opendaw_create_sequence(pattern="60,64,67,72", repeats=5, velocity_decay=-0.12, velocity=0.9, segment_beats=2, start_beat=22)
    print(f"4. Fade-out: {r}")

    # 5. Rising quint build-up — cinematic escalation
    r = await mcp_opendaw_create_sequence(pattern="48,52,55,60", transposition=7, repeats=5, direction="up", velocity_decay=0.08, segment_beats=2, start_beat=32)
    print(f"5. Rising quint: {r}")

    await bridge.stop()
    print("\ndone — 5 sequences created")

if __name__ == "__main__":
    asyncio.run(main())
