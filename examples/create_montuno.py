"""Example: Montuno patterns for Latin/jazz piano.

This example demonstrates create_montuno — a repeating Latin piano ostinato
with syncopated chord stabs and melodic passages locked to the clave.
"""

import asyncio

from opendaw_mcp.server import mcp_opendaw_create_montuno


async def main():
    # 1. Classic 2-3 clave montuno in C major
    # 2-bar cycle, eighth-note based, I-vi-IV-V auto progression
    print("=== 2-3 Clave Montuno ===")
    result = await mcp_opendaw_create_montuno(
        root="C",
        scale="major",
        bars=2,
        octave=4,
        pattern="2-3",
        rhythm="8th",
        velocity=0.65,
        accent_beats="1,3",
    )
    print(result)

    # 2. 3-2 clave (reversed) in A minor
    print("\n=== 3-2 Clave Montuno (Am) ===")
    result = await mcp_opendaw_create_montuno(
        root="A",
        scale="minor",
        bars=2,
        octave=4,
        pattern="3-2",
        rhythm="8th",
        velocity=0.6,
        accent_beats="1,3",
    )
    print(result)

    # 3. Guajira style — dotted rhythm feel in D
    print("\n=== Guajira Montuno ===")
    result = await mcp_opendaw_create_montuno(
        root="D",
        scale="major",
        bars=2,
        octave=4,
        pattern="guajira",
        rhythm="8th",
        velocity=0.55,
        accent_beats="1,3",
    )
    print(result)

    # 4. Charanga — flowing, melodic passages in G
    print("\n=== Charanga Montuno ===")
    result = await mcp_opendaw_create_montuno(
        root="G",
        scale="major",
        bars=4,
        octave=4,
        pattern="charanga",
        rhythm="16th",
        velocity=0.6,
        accent_beats="1,3",
    )
    print(result)

    # 5. Custom chord progression: Dm-G-C-Am (ii-V-I-vi)
    print("\n=== Custom Progression Montuno ===")
    result = await mcp_opendaw_create_montuno(
        root="C",
        scale="major",
        bars=4,
        octave=4,
        chord_prog="Dm,G,C,Am",
        pattern="2-3",
        rhythm="8th",
        velocity=0.65,
        accent_beats="1,3",
    )
    print(result)

    # 6. Quarter-note mambo style — simpler, punchier
    print("\n=== Mambo Style (quarter notes) ===")
    result = await mcp_opendaw_create_montuno(
        root="F",
        scale="major",
        bars=2,
        octave=3,
        pattern="2-3",
        rhythm="quarter",
        velocity=0.75,
        accent_beats="1,3",
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
