"""Example: create_garage_arrangement — UK garage 2-step."""
import asyncio
from server import mcp_opendaw_create_garage_arrangement


async def main():
    result = await mcp_opendaw_create_garage_arrangement(
        key_root="G", bpm=130, bars=16, velocity=0.7,
        track_index=0, start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
