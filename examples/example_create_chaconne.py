"""Example: create_chaconne — baroque variation form.

A chaconne repeats a bass line and chord progression, building
variations on top. This example creates a 4-cycle chaconne in C minor
with baroque-style variations (descending stepwise, grace notes accumulating).
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_chaconne


async def main():
    result = await mcp_opendaw_create_chaconne(
        bass_pattern="C2 G2 A2 E2",
        bass_rhythm="1 1 1 1",
        chord_pattern="Cm,G,Am,Em",
        variation_style="baroque",
        repeats=4,
        velocity=0.65,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
