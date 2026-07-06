"""Example: Neurofunk DnB arrangement.

The 500th MCP tool — create_neurofunk_arrangement generates a complete
neurofunk drum & bass section with 4 tracks:
- Complex chopped breakbeat (extra kicks, ghost note clusters, snare rolls)
- Deep sustained sub-bass with syncopated gaps
- Reese bass (detuned saw with chromatic slides, rhythmic stabs)
- Dark minor chord stabs (root + b3 + tritone + b7)

Default: 174 BPM, F minor (classic neurofunk key).
Inspired by: Noisia, Spor, Phace, Ed Rush & Optical.
"""
import asyncio
from server import mcp_opendaw_create_neurofunk_arrangement


async def main():
    # Classic neurofunk — 174 BPM, F minor, 8 bars
    result = await mcp_opendaw_create_neurofunk_arrangement(
        bpm=174,
        root="F",
        bars=8,
        velocity=0.9,
    )
    print(result)

    # Darker variant — 180 BPM, E minor, 16 bars
    result2 = await mcp_opendaw_create_neurofunk_arrangement(
        bpm=180,
        root="E",
        bars=16,
        velocity=0.95,
        drum_track=0,
        bass_track=1,
        reese_track=2,
        stabs_track=3,
    )
    print(result2)


if __name__ == "__main__":
    asyncio.run(main())
