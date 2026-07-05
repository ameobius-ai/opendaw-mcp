"""add_chord_tension — jazz chord extensions on existing chords.

Demonstrates adding tension notes (9, b9, #9, 11, #11, 13, b13) to
chords already on the timeline. This is how triads become jazz chords.

Pipeline:
1. Create a chord progression with basic triads
2. Add 9th to first chord (Cmaj → Cmaj9)
3. Add b13 to dominant (G7 → G7b13)
4. Add #11 for Lydian sound
"""

import asyncio
from opendaw_mcp.server import (
    mcp_opendaw_add_chord_tension,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_chord_progression,
)


async def main():
    # 1. Create synth track
    print("Creating keys track...")
    await mcp_opendaw_create_synth_track("Jazz Keys", "vaporisateur")

    # 2. Create a ii-V-I progression (Dm-G-C)
    print("\nCreating Dm-G-C progression...")
    await mcp_opendaw_create_chord_progression(
        chords='[["D","min"],["G","maj"],["C","maj"]]',
        unit_index=0, track_index=0, start_beat=0,
    )

    # 3. Add 9th to Dm → Dm9 (warmth)
    print("\nAdding 9th to Dm (beat 0) → Dm9...")
    result = await mcp_opendaw_add_chord_tension(
        unit_index=0, track_index=0, region_index=0,
        chord_position=0.0, extension="9",
    )
    print(result)

    # 4. Add b13 to G → G7b13 (dark dominant)
    print("\nAdding b13 to G (beat 4) → G7b13...")
    result = await mcp_opendaw_add_chord_tension(
        unit_index=0, track_index=0, region_index=0,
        chord_position=4.0, extension="b13",
    )
    print(result)

    # 5. Add #11 to C → Cmaj7#11 (Lydian)
    print("\nAdding #11 to C (beat 8) → Cmaj#11...")
    result = await mcp_opendaw_add_chord_tension(
        unit_index=0, track_index=0, region_index=0,
        chord_position=8.0, extension="#11",
    )
    print(result)

    print("\n--- Extension summary ---")
    print("9: warmth, color (Cmaj9)")
    print("b9: dark, tense (G7b9)")
    print("#9: Hendrix chord (E7#9)")
    print("11: suspended, open (Dm11)")
    print("#11: Lydian, dreamy (Cmaj7#11)")
    print("13: rich, complete (G13)")
    print("b13: dramatic, Spanish (G7b13)")


if __name__ == "__main__":
    asyncio.run(main())
