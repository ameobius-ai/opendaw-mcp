"""Example: shift_mode — modal transformation.

Transform notes from one scale to another, preserving the tonic.
Only the degrees that differ between scales are shifted — the melodic
contour is preserved.
"""

import asyncio

from server import mcp_opendaw_shift_mode


async def main():
    # A minor -> A dorian (raise the 6th: F -> F#)
    result = await mcp_opendaw_shift_mode(
        root_note="A",
        from_scale="minor",
        to_scale="dorian",
    )
    print("A minor -> A dorian:", result)

    # E minor -> E phrygian (lower the 2nd: F# -> F)
    result = await mcp_opendaw_shift_mode(
        root_note="E",
        from_scale="minor",
        to_scale="phrygian",
        unit_index=0,
        track_index=0,
    )
    print("E minor -> E phrygian:", result)

    # D major -> D mixolydian (lower the 7th: C# -> C)
    result = await mcp_opendaw_shift_mode(
        root_note="D",
        from_scale="major",
        to_scale="mixolydian",
    )
    print("D major -> D mixolydian:", result)


if __name__ == "__main__":
    asyncio.run(main())
