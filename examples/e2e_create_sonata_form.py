"""Example: create_sonata_form — classical sonata form in C major.

Generates a full sonata-form movement:
  Exposition (16 bars): Theme 1 in C → transition → Theme 2 in G
  Development (12 bars): fragmentation + modulations + dominant pedal
  Recapitulation (16 bars): Theme 1 in C → Theme 2 in C (no modulation)
"""
import asyncio
from server import mcp_opendaw_create_sonata_form


async def main():
    result = await mcp_opendaw_create_sonata_form(
        key_root="C",
        scale_name="major",
        exposition_bars=16,
        development_bars=12,
        recap_bars=16,
        velocity=0.7,
        track_index=0,
        start_beat=0,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
