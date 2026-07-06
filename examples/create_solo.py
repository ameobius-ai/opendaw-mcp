"""Example: Genre-specific melodic solos.

create_solo generates a complete solo line using vocabulary appropriate
to the chosen style. 5 solo types, 6 scales, seeded PRNG.

Examples:
- Bebop over F major (ii-V-I-vi)
- Blues over A (12-bar, pentatonic + blue notes)
- Rock over E minor pentatonic (register climaxes)
- Jazz swing over C (swung 8ths, guide tones)
- Fusion over D dorian (wide intervals, rhythmic displacement)
"""
import asyncio
from server import mcp_opendaw_create_solo


async def main():
    # Bebop — F major, 8 bars
    print("=== Bebop solo (F major) ===")
    r = await mcp_opendaw_create_solo(solo_type="bebop", key_root="F", bars=8)
    print(r)

    # Blues — A, 12 bars
    print("\n=== Blues solo (A, 12-bar) ===")
    r = await mcp_opendaw_create_solo(solo_type="blues", key_root="A", scale_type="blues", bars=12)
    print(r)

    # Rock — E minor pentatonic, 16 bars
    print("\n=== Rock solo (E minor pentatonic) ===")
    r = await mcp_opendaw_create_solo(solo_type="rock", key_root="E", scale_type="pentatonic_minor", bars=16)
    print(r)

    # Fusion — D dorian, 8 bars
    print("\n=== Fusion solo (D dorian) ===")
    r = await mcp_opendaw_create_solo(solo_type="fusion", key_root="D", scale_type="dorian", bars=8)
    print(r)


if __name__ == "__main__":
    asyncio.run(main())
