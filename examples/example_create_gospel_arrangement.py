"""Example: create_gospel_arrangement — 4-track gospel.

Gospel music — the foundation of soul, R&B, and modern pop.
4 tracks: gospel shuffle drums, walking bass, Hammond B3 organ, SATB choir.
I-IV-V-I progression in Ab major (traditional gospel key).
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_gospel_arrangement


async def main():
    result = await mcp_opendaw_create_gospel_arrangement(
        bpm=75,
        bars=8,
        root="Ab",
        octave=3,
        unit_index=0,
        drum_track=0,
        bass_track=1,
        organ_track=2,
        choir_track=3,
        velocity=0.7,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
