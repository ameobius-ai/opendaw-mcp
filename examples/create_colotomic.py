"""Example: Colotomic structure — gamelan gong layers.

This example demonstrates create_colotomic — interlocking gong layers
marking cyclic time, the foundation of Indonesian gamelan music.
"""

import asyncio

from opendaw_mcp.server import mcp_opendaw_create_colotomic


async def main():
    # 1. Slendro structure — 8-beat cycle, sparse (gongs only)
    print("=== Slendro (sparse) ===")
    result = await mcp_opendaw_create_colotomic(
        root="C",
        scale="pentatonic_minor",
        cycles=4,
        octave=4,
        structure="slendro",
        tempo_density="sparse",
        velocity=0.65,
    )
    print(result)

    # 2. Slendro with medium density — gongs + saron balungan
    print("\n=== Slendro (medium) ===")
    result = await mcp_opendaw_create_colotomic(
        root="D",
        scale="pentatonic_minor",
        cycles=4,
        octave=4,
        structure="slendro",
        tempo_density="medium",
        velocity=0.65,
    )
    print(result)

    # 3. Pelog structure — 16-beat cycle, dense
    print("\n=== Pelog (dense) ===")
    result = await mcp_opendaw_create_colotomic(
        root="G",
        scale="pentatonic_major",
        cycles=2,
        octave=4,
        structure="pelog",
        tempo_density="dense",
        velocity=0.6,
    )
    print(result)

    # 4. Lancaran — 8-beat with doubled kethuk
    print("\n=== Lancaran (medium) ===")
    result = await mcp_opendaw_create_colotomic(
        root="A",
        scale="pentatonic_minor",
        cycles=4,
        octave=4,
        structure="lancaran",
        tempo_density="medium",
        velocity=0.65,
    )
    print(result)

    # 5. Ketawang — 16-beat with dense kethuk on every odd beat
    print("\n=== Ketawang (dense) ===")
    result = await mcp_opendaw_create_colotomic(
        root="E",
        scale="pentatonic_minor",
        cycles=2,
        octave=3,
        structure="ketawang",
        tempo_density="dense",
        velocity=0.6,
    )
    print(result)

    # 6. Long slendro — 8 cycles
    print("\n=== Long Slendro (8 cycles) ===")
    result = await mcp_opendaw_create_colotomic(
        root="C",
        scale="pentatonic_minor",
        cycles=8,
        octave=4,
        structure="slendro",
        tempo_density="dense",
        velocity=0.6,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
