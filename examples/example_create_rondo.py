"""Example: create_rondo — classical rondo form ABACA.

A rondo alternates a recurring theme (A) with contrasting episodes (B, C).
This example creates a classical 5-section rondo in C major.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_rondo


async def main():
    result = await mcp_opendaw_create_rondo(
        key_root="C",
        scale_name="major",
        form_type="classical",
        bars_per_section=4,
        tempo_bpm=120.0,
        velocity=0.7,
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
