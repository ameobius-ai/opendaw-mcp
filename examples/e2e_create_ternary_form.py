"""Example: create_ternary_form — ABA form with trio contrast.

Minuet & Trio style: A section in C major, B section in F major (subdominant trio),
A' return with ornamentation.
"""
import asyncio
from server import mcp_opendaw_create_ternary_form


async def main():
    result = await mcp_opendaw_create_ternary_form(
        key_root="C",
        scale_name="major",
        a_bars=8,
        b_bars=8,
        a_prime_ornamented=True,
        b_contrast="trio",
        velocity=0.7,
        track_index=0,
        start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
