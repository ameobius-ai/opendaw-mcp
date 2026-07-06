"""Example: create_hardstyle_arrangement — 150 BPM Dutch hardstyle."""
import asyncio
from server import mcp_opendaw_create_hardstyle_arrangement


async def main():
    result = await mcp_opendaw_create_hardstyle_arrangement(
        key_root="F", bpm=150, bars=16, velocity=0.8,
        track_index=0, start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
