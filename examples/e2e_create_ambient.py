"""Example: create_ambient_arrangement — atmospheric soundscape."""
import asyncio
from server import mcp_opendaw_create_ambient_arrangement


async def main():
    result = await mcp_opendaw_create_ambient_arrangement(
        key_root="C", bpm=70, bars=32, velocity=0.5,
        track_index=0, start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
