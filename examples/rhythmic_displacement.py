"""Rhythmic displacement — laid-back, pushed, and circular rotation feels.

Shows how displace_rhythm transforms the feel of existing MIDI patterns
without changing pitch or note duration.

Usage:
    python rhythmic_displacement.py
"""

import asyncio
from opendaw_mcp.server import (
    mcp_opendaw_create_drum_pattern,
    mcp_opendaw_displace_rhythm,
)


async def main():
    # 1. Create a basic four-on-the-floor drum pattern
    await mcp_opendaw_create_drum_pattern("four_on_the_floor", unit_index=0)
    print("Drums created: four-on-the-floor")

    # 2. J Dilla laid-back feel — drums 1/16 note behind the beat
    result_laidback = await mcp_opendaw_displace_rhythm(
        unit_index=0, track_index=0, offset=0.0625, mode="shift"
    )
    print("Laid-back drums (1/16 late):", result_laidback)

    # 3. Pushed feel — drums 1/32 note ahead of the beat (urgent energy)
    result_pushed = await mcp_opendaw_displace_rhythm(
        unit_index=0, track_index=0, offset=-0.03125, mode="shift"
    )
    print("Pushed drums (1/32 early):", result_pushed)

    # 4. Circular rotation — rotate the drum pattern by 1/8 note
    # This creates an entirely new rhythm from the same notes
    result_circular = await mcp_opendaw_displace_rhythm(
        unit_index=0, track_index=0, offset=0.125, mode="circular"
    )
    print("Circular rotation (1/8):", result_circular)


if __name__ == "__main__":
    asyncio.run(main())
