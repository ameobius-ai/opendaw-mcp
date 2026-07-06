"""Example: Future bass arrangement.

create_future_bass_arrangement generates a complete future bass section with 4 tracks:
- Drums with pitching snare roll (ascending velocity crescendo before drops)
- Sub-bass following I-V-vi-IV chord roots
- Big supersaw chords (maj7/add9/min7 wide voicings)
- Vocal-chop style lead (starts bar 5)

Default: 150 BPM, C major.
Inspired by: Flume, San Holo, Illenium, ODESZA.
"""
import asyncio
from server import mcp_opendaw_create_future_bass_arrangement


async def main():
    # Classic future bass — 150 BPM, C major, 8 bars
    result = await mcp_opendaw_create_future_bass_arrangement(
        bpm=150,
        root="C",
        bars=8,
    )
    print(result)

    # Emotional variant — 140 BPM, G major, 16 bars
    result2 = await mcp_opendaw_create_future_bass_arrangement(
        bpm=140,
        root="G",
        bars=16,
        velocity=0.9,
    )
    print(result2)


if __name__ == "__main__":
    asyncio.run(main())
