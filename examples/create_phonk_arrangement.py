"""Example: Drift phonk arrangement.

create_phonk_arrangement generates a complete drift phonk section with 3 tracks:
- Memphis drums (punchy kick 1&3, clap 2&4, 16th hats with rolls)
- Sliding 808 bass (chromatic slides, sustained resonance, octave drops)
- Cowbell lead (minor pentatonic repetitive riff, 1-bar cycle)

Default: 130 BPM, F minor.
Inspired by: Kordhell, MC Slvr, LXST CXNTURY.
"""
import asyncio
from server import mcp_opendaw_create_phonk_arrangement


async def main():
    # Classic drift phonk — 130 BPM, F minor, 8 bars
    result = await mcp_opendaw_create_phonk_arrangement(
        bpm=130,
        root="F",
        bars=8,
        velocity=0.85,
    )
    print(result)

    # Darker variant — 140 BPM, D# minor, 16 bars
    result2 = await mcp_opendaw_create_phonk_arrangement(
        bpm=140,
        root="D#",
        bars=16,
        velocity=0.9,
    )
    print(result2)


if __name__ == "__main__":
    asyncio.run(main())
