"""Example: create_konokol — Indian Carnatic vocal percussion.

Konokol (solkattu) is the South Indian art of vocal percussion.
Syllables represent rhythmic patterns. This example creates a 2-cycle
adi tala (8-beat cycle, the most common in Carnatic music).
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_konokol


async def main():
    result = await mcp_opendaw_create_konokol(
        style="adi_tala",
        cycles=2,
        tempo_bpm=100.0,
        velocity=0.7,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
