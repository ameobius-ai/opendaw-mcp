"""Example: create_binary_form — AB form with dominant modulation.

Binary form: two contrasting sections with optional repeats (AABB).
A section in G major, B section modulates to D major (dominant).
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_create_binary_form


async def main():
    result = await mcp_opendaw_create_binary_form(
        key_root="G",
        scale_name="major",
        bars_per_section=8,
        repeat=True,
        modulation="dominant",
        unit_index=0,
        track_index=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
