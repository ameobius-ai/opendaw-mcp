"""Example: create_acid_arrangement — TB-303 acid house."""
import asyncio
from server import mcp_opendaw_create_acid_arrangement


async def main():
    result = await mcp_opendaw_create_acid_arrangement(
        key_root="A", bpm=125, bars=16, velocity=0.75,
        track_index=0, start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
