"""Example: create_pedal_point — sustained bass under changing chords.

The foundational technique in film scoring, organ preludes, and rock ballads.

  1. Retriggered pedal (Cm,Ab,Eb,Bb — vi-IV-I-V in Eb)
  2. Sustained pedal (one long drone)
  3. 7th chords with pedal (jazz)
  4. 2 bars per chord (slower harmonic rhythm)
  5. 3/4 waltz with pedal
"""
import asyncio, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DAW_URL", "http://localhost:5174")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_pedal_point,
)

async def main():
    await bridge.start()
    print("bridge ready")

    r = await mcp_opendaw_create_synth_track("PedalDemo", "vaporisateur")
    print(f"synth: {r[:80]}")

    # 1. Retriggered pedal — vi-IV-I-V in Eb
    r = await mcp_opendaw_create_pedal_point(pedal_pitch=28, chord_pattern="Cm,Ab,Eb,Bb", start_beat=0)
    print(f"\n1. Retriggered pedal (C2): {r}")

    # 2. Sustained drone — one long note
    r = await mcp_opendaw_create_pedal_point(pedal_pitch=36, chord_pattern="Fm,Db,Ab,Eb", retrigger_pedal=False, start_beat=16)
    print(f"2. Sustained drone: {r}")

    # 3. Jazz 7ths
    r = await mcp_opendaw_create_pedal_point(pedal_pitch=40, chord_pattern="Cm7,Fm7,Bb7,Ebmaj7", chord_velocity=0.55, start_beat=32)
    print(f"3. Jazz 7ths: {r}")

    # 4. Slow — 2 bars per chord
    r = await mcp_opendaw_create_pedal_point(pedal_pitch=33, chord_pattern="Am,F,C,G", bars_per_chord=2, start_beat=48)
    print(f"4. 2 bars per chord: {r}")

    # 5. 3/4 waltz
    r = await mcp_opendaw_create_pedal_point(pedal_pitch=41, chord_pattern="Dm,Gm,A", beats_per_bar=3, start_beat=64)
    print(f"5. 3/4 waltz: {r}")

    await bridge.stop()
    print("\ndone — 5 pedal points created")

if __name__ == "__main__":
    asyncio.run(main())
