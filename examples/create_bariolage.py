"""Example: Bariolage — Baroque string crossing technique.

This example demonstrates create_bariolage — rapid alternation between a
fixed pedal pitch and moving notes, creating a two-voice illusion.
"""

import asyncio

from opendaw_mcp.server import mcp_opendaw_create_bariolage


async def main():
    # 1. Classic ascending bariolage — G pedal with ascending scale above
    print("=== Ascending Bariolage (G major) ===")
    result = await mcp_opendaw_create_bariolage(
        root="G",
        scale="major",
        bars=2,
        octave=4,
        moving_pattern="scale_asc",
        subdivision="16th",
        velocity=0.6,
        pedal_velocity=0.7,
        accent_pedal=True,
    )
    print(result)

    # 2. Descending bariolage — notes below the pedal
    print("\n=== Descending Bariolage ===")
    result = await mcp_opendaw_create_bariolage(
        root="D",
        scale="major",
        bars=2,
        octave=4,
        moving_pattern="scale_desc",
        subdivision="16th",
        velocity=0.55,
        pedal_velocity=0.65,
    )
    print(result)

    # 3. Wave pattern — alternating ascending and descending
    print("\n=== Wave Bariolage ===")
    result = await mcp_opendaw_create_bariolage(
        root="A",
        scale="minor",
        bars=4,
        octave=4,
        moving_pattern="scale_wave",
        subdivision="8th",
        velocity=0.6,
        pedal_velocity=0.7,
    )
    print(result)

    # 4. Arpeggio bariolage — chord tones rotating around pedal
    print("\n=== Arpeggio Bariolage ===")
    result = await mcp_opendaw_create_bariolage(
        root="C",
        scale="major",
        bars=2,
        octave=4,
        moving_pattern="arpeggio",
        subdivision="16th",
        velocity=0.6,
        pedal_velocity=0.72,
    )
    print(result)

    # 5. Chromatic bariolage — chromatic approach notes
    print("\n=== Chromatic Bariolage ===")
    result = await mcp_opendaw_create_bariolage(
        root="E",
        scale="minor",
        bars=2,
        octave=4,
        moving_pattern="chromatic",
        subdivision="32nd",
        velocity=0.55,
        pedal_velocity=0.68,
    )
    print(result)

    # 6. Fast 32nd-note bariolage — virtuosic Baroque style
    print("\n=== Virtuosic 32nd Bariolage ===")
    result = await mcp_opendaw_create_bariolage(
        root="G",
        scale="major",
        bars=1,
        octave=4,
        moving_pattern="scale_asc",
        subdivision="32nd",
        velocity=0.5,
        pedal_velocity=0.65,
        accent_pedal=True,
    )
    print(result)

    # 7. Custom pedal pitch — use low G as pedal, notes above
    print("\n=== Custom Pedal Pitch ===")
    result = await mcp_opendaw_create_bariolage(
        root="G",
        scale="major",
        bars=2,
        octave=4,
        pedal_pitch=55,  # G3 as pedal
        moving_pattern="arpeggio",
        subdivision="16th",
        velocity=0.6,
        pedal_velocity=0.7,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
