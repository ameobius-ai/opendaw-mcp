"""Example: set_note_cents — deterministic microtonal pitch control.

Set specific cent offsets on notes for honky-tonk piano, quarter-tone
scales, just intonation, synth drift, and MIDI chorus effects.
"""

import asyncio

from server import mcp_opendaw_set_note_cents


async def main():
    # Honky-tonk piano: alternate +8/-8 cents on all notes
    result = await mcp_opendaw_set_note_cents(
        cents=8,
        mode="alternating",
        direction="up",
    )
    print("Honky-tonk:", result)

    # Quarter-tone: +50 cents on specific pitch class (e.g. F)
    result = await mcp_opendaw_set_note_cents(
        cents=50,
        mode="pitch",
        target_pitch="65",  # F4 = MIDI 65, pc 5
        direction="up",
    )
    print("Quarter-tone on F:", result)

    # Synth drift: gradual +0 to +20 cents across all notes
    result = await mcp_opendaw_set_note_cents(
        cents=20,
        mode="gradient",
        direction="up",
    )
    print("Synth drift:", result)

    # Just intonation: -2 cents on major 3rd degree (scale_degree mode)
    result = await mcp_opendaw_set_note_cents(
        cents=-2,
        mode="scale_degree",
        target_pitch="3",  # degree 3
        scale="major",
        root_note="C",
    )
    print("Just intonation -2 on 3rd:", result)


if __name__ == "__main__":
    asyncio.run(main())
