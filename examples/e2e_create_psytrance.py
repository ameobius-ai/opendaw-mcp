"""Example: create_psytrance_arrangement — Goa/psychedelic trance."""
import asyncio
from server import mcp_opendaw_create_psytrance_arrangement


async def main():
    result = await mcp_opendaw_create_psytrance_arrangement(
        key_root="F", bpm=145, bars=16, velocity=0.75,
        track_index=0, start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
