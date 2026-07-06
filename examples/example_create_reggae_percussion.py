"""Example: create_reggae_percussion — Jamaican drum patterns.

6 styles covering the evolution of Jamaican popular music.
This example creates a 2-bar one-drop pattern at 75 BPM.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_reggae_percussion


async def main():
    result = await mcp_opendaw_create_reggae_percussion(
        style="one_drop",
        bars=2,
        tempo_bpm=75.0,
        velocity=0.7,
        swing=0.0,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
