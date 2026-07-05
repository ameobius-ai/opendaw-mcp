"""spread_voicing — chord voicing spread/compact techniques.

Demonstrates 4 classic voicing transformations:
- open: widen spacing between chord tones
- close: collapse to one octave
- drop2: jazz piano comping voicing
- drop3: wider jazz voicing

Pipeline:
1. Create a chord progression with close voicings
2. Apply spread_voicing with different modes
"""

import asyncio
from opendaw_mcp.server import (
    mcp_opendaw_spread_voicing,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_chord_progression,
)


async def main():
    # 1. Create synth track
    print("Creating synth track...")
    await mcp_opendaw_create_synth_track("Keys", "vaporisateur")

    # 2. Create a chord progression (close voicings by default)
    print("\nCreating C major triad progression...")
    await mcp_opendaw_create_chord_progression(
        chords='[["C","maj"],["F","maj"],["G","maj"]]',
        unit_index=0, track_index=0, start_beat=0,
    )

    # 3. Open up the first chord for wider sound
    print("\nOpening voicing on beat 0...")
    result = await mcp_opendaw_spread_voicing(
        unit_index=0, track_index=0, region_index=0,
        chord_position=0.0, mode="open", spread_octaves=1,
    )
    print(result)

    # 4. Drop-2 voicing on second chord (jazz comping)
    print("\nDrop-2 voicing on beat 4...")
    result = await mcp_opendaw_spread_voicing(
        unit_index=0, track_index=0, region_index=0,
        chord_position=4.0, mode="drop2",
    )
    print(result)

    # 5. Drop-3 voicing on third chord
    print("\nDrop-3 voicing on beat 8...")
    result = await mcp_opendaw_spread_voicing(
        unit_index=0, track_index=0, region_index=0,
        chord_position=8.0, mode="drop3",
    )
    print(result)

    print("\n--- Voicing modes summary ---")
    print("open: every other note up an octave → airy, wide")
    print("close: collapse to one octave → tight, focused")
    print("drop2: 2nd highest down octave → jazz comping")
    print("drop3: 3rd highest down octave → wider jazz")


if __name__ == "__main__":
    asyncio.run(main())
