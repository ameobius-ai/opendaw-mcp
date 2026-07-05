"""Example: create_chorale — 4-voice SATB chorale with voice leading.

Generates soprano, alto, tenor, and bass voices from a chord progression
with proper voice leading (Bach chorale style).

Usage:
    python3 examples/create_chorale.py
"""
import asyncio
from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_chorale


async def main():
    # Create a synth track for the chorale
    await mcp_opendaw_create_synth_track("ChoraleSynth", "vaporisateur")

    # Classic I-vi-IV-V progression in C major
    # 4 voices × 4 chords = 16 notes
    r = await mcp_opendaw_create_chorale(
        chord_pattern="C,Am,F,G",
        beats_per_chord=4,
        soprano_velocity=0.7,
        alto_velocity=0.6,
        tenor_velocity=0.6,
        bass_velocity=0.65,
    )
    print(f"Chorale: {r}")

    # Jazz progression with 7th chords
    r2 = await mcp_opendaw_create_chorale(
        chord_pattern="Cmaj7,Am7,Dm7,G7",
        beats_per_chord=2,
        voice_spread=3,
    )
    print(f"Jazz chorale: {r2}")


if __name__ == "__main__":
    asyncio.run(main())
