"""
Example: Rhythmic stabs for house/disco/funk using create_stab.

Demonstrates three styles:
1. House off-beat Cm7 stabs (the classic "uh-uh-uh-uh")
2. Funky syncopated stabs with ghost notes, cycling F7→Cm7
3. Disco stabs with 16th-note busy pattern

Run: python examples/create_stab.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_stab,
    mcp_opendaw_save_project,
)


async def main():
    await bridge.start()

    # Create a synth track for stabs
    r = await mcp_opendaw_create_synth_track("stab_synth", "vaporisateur")
    print(f"Synth track: {r}")

    # 1. House off-beat stabs — Cm7 on every off-beat
    #    Beat:  1 e & a 2 e & a 3 e & a 4 e & a
    #    Stab:  - - X - - - X - - - X - - - X -
    #    Actually with 8th grid: x-x-x-x- = off-beat 8ths
    r1 = await mcp_opendaw_create_stab(
        chords='[["C","min7"]]',
        rhythm="x-x-x-x-",
        unit_index=-1,
        octave=4,
        velocity=0.85,
        length_beats=4,
        stab_duration=0.5,
    )
    print(f"\n1. House off-beat Cm7: {r1}")

    # 2. Funky syncopated stabs with ghost notes — cycling F7 and Cm7
    #    Ghost notes (.) add subtle texture between the hard stabs
    r2 = await mcp_opendaw_create_stab(
        chords='[["F","dom7"],["C","min7"]]',
        rhythm="x..x.xx-",
        unit_index=-1,
        octave=4,
        velocity=0.9,
        length_beats=4,
        stab_duration=0.375,
        start_beat=4,
    )
    print(f"2. Funky F7/Cm7 with ghosts: {r2}")

    # 3. Disco 16th-note busy pattern — F#m7 throughout
    #    Nearly every 16th gets a stab for that relentless disco feel
    r3 = await mcp_opendaw_create_stab(
        chords='[["F#","min7"]]',
        rhythm="xx-xx-xx-x-x-xx-",
        unit_index=-1,
        octave=5,
        velocity=0.75,
        length_beats=4,
        stab_duration=0.25,
        start_beat=8,
    )
    print(f"3. Disco F#m7 16th pattern: {r3}")

    # Save the project
    r4 = await mcp_opendaw_save_project("stab_demo")
    print(f"\nSaved: {r4}")

    await bridge.stop()
    print("\n✅ Stab demo complete — 3 styles across 12 bars")


if __name__ == "__main__":
    asyncio.run(main())
