"""Example: Cadenzas — unmeasured virtuosic solo passages.

This example demonstrates create_cadenza — the only tool that generates
rubato, unmeasured music with irregular rhythm, accelerandos, and fermatas.
"""

import asyncio

from opendaw_mcp.server import mcp_opendaw_create_cadenza


async def main():
    # 1. Classical cadenza — balanced phrases with trills
    print("=== Classical Cadenza ===")
    result = await mcp_opendaw_create_cadenza(
        root="C",
        scale="major",
        duration_beats=8,
        octave=4,
        style="classical",
        virtuosic=False,
        velocity=0.7,
    )
    print(result)

    # 2. Romantic cadenza — dramatic, wide leaps, cascading runs
    print("\n=== Romantic Cadenza (virtuosic) ===")
    result = await mcp_opendaw_create_cadenza(
        root="A",
        scale="minor",
        duration_beats=16,
        octave=4,
        style="romantic",
        virtuosic=True,
        velocity=0.75,
    )
    print(result)

    # 3. Jazz cadenza — bebop lines, chromatic turns
    print("\n=== Jazz Cadenza ===")
    result = await mcp_opendaw_create_cadenza(
        root="F",
        scale="dorian",
        duration_beats=8,
        octave=4,
        style="jazz",
        virtuosic=True,
        velocity=0.65,
    )
    print(result)

    # 4. Modern cadenza — extreme registers, clusters, fermatas
    print("\n=== Modern Cadenza ===")
    result = await mcp_opendaw_create_cadenza(
        root="E",
        scale="harmonic_minor",
        duration_beats=12,
        octave=3,
        style="modern",
        virtuosic=True,
        velocity=0.6,
    )
    print(result)

    # 5. Classical with breath marks — pauses at specific beats
    print("\n=== Classical Cadenza with Breath Marks ===")
    result = await mcp_opendaw_create_cadenza(
        root="D",
        scale="major",
        duration_beats=12,
        octave=4,
        style="classical",
        virtuosic=False,
        breath_marks="3.0,6.0,9.0",
        velocity=0.7,
    )
    print(result)

    # 6. Long romantic cadenza — 24 beats, virtuosic
    print("\n=== Long Romantic Cadenza (24 beats) ===")
    result = await mcp_opendaw_create_cadenza(
        root="G",
        scale="minor",
        duration_beats=24,
        octave=4,
        style="romantic",
        virtuosic=True,
        velocity=0.8,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
