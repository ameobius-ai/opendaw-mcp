"""Example: create_downtempo_arrangement — Bristol trip-hop."""
import asyncio
from server import mcp_opendaw_create_downtempo_arrangement


async def main():
    result = await mcp_opendaw_create_downtempo_arrangement(
        key_root="D", bpm=85, bars=16, velocity=0.6,
        track_index=0, start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
