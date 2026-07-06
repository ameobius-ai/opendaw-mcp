"""Example: Genre-specific drum solos.

create_drum_solo generates a complete drum solo with rudimental vocabulary.
5 styles, seeded PRNG.

Examples:
- Rock 4-bar solo (double kick, tom fills, crash climax)
- Jazz 8-bar solo (swing ride, comping, press rolls)
- Funk 4-bar solo (ghost-note 16ths, hi-hat splashes)
- Latin 4-bar solo (cascara, mambo bell, timbale fills)
- Marching 4-bar solo (paradiddles, flams, drags, open rolls)
"""
import asyncio
from server import mcp_opendaw_create_drum_solo


async def main():
    # Rock — 4 bars
    print("=== Rock drum solo (4 bars) ===")
    r = await mcp_opendaw_create_drum_solo(solo_type="rock", bars=4)
    print(r)

    # Jazz — 8 bars
    print("\n=== Jazz drum solo (8 bars) ===")
    r = await mcp_opendaw_create_drum_solo(solo_type="jazz", bars=8)
    print(r)

    # Marching — 4 bars
    print("\n=== Marching drum solo (4 bars) ===")
    r = await mcp_opendaw_create_drum_solo(solo_type="marching", bars=4, seed=100)
    print(r)


if __name__ == "__main__":
    asyncio.run(main())
