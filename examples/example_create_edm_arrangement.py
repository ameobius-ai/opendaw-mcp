"""Example: create_edm_arrangement — festival/mainstage EDM.

4 tracks: 4-on-floor drums + offbeat bass + supersaw synth + arpeggiated lead.
i-VI-III-VII progression in F minor. 128 BPM.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_edm_arrangement


async def main():
    result = await mcp_opendaw_create_edm_arrangement(
        bpm=128,
        bars=16,
        root="F",
        octave=3,
        unit_index=0,
        drum_track=0,
        bass_track=1,
        synth_track=2,
        lead_track=3,
        velocity=0.8,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
