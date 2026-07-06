"""Example: create_comparsa — Cuban carnival procession percussion.

Comparsa is the percussion ensemble for Cuban carnival street processions.
7 instruments: conga low/high/open, claves, cowbell, maracas, guiro.
This example creates a 2-bar habanera pattern at 100 BPM.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_comparsa


async def main():
    result = await mcp_opendaw_create_comparsa(
        style="habanera",
        bars=2,
        tempo_bpm=100.0,
        velocity=0.7,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
