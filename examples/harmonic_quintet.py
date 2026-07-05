"""Harmonic quintet: pads + arp + bass + melody + counter-melody.

This example shows the full 5-layer harmonic pipeline from a single
chord progression string "Am-F-C-G". All layers derive from the same
progression and are placed on separate tracks.

Track layout:
  0 — drums (not created here, add with create_XXX_arrangement)
  1 — bass (create_bass_from_progression)
  2 — pads (create_chord_pads)
  3 — melody (create_melody_from_progression)
  4 — counter-melody (create_counter_melody_from_progression)

The counter-melody uses 'contrary' motion — it moves opposite to the
chord root motion, creating classic species-1 counterpoint.
"""
import asyncio
from server import (
    mcp_opendaw_create_harmonic_arrangement,
    mcp_opendaw_create_counter_melody_from_progression,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_render_full_song,
)


async def main():
    progression = "Am-F-C-G"

    # 1. Harmonic arrangement: pads + arp + bass + melody (4 layers, one call)
    r1 = await mcp_opendaw_create_harmonic_arrangement(
        progression,
        pad_octave=3,
        arp_pattern="up",
        bass_pattern="root",
        melody_pattern="chord_tones",
        bars_per_chord=4,
        velocity=0.7,
    )
    print("Harmonic arrangement:", r1)

    # 2. Counter-melody: contrary motion on track 4
    r2 = await mcp_opendaw_create_counter_melody_from_progression(
        progression,
        pattern="contrary",
        bars_per_chord=4,
        octave=4,
        velocity=0.6,
        track_index=4,
    )
    print("Counter-melody:", r2)

    # 3. Mix
    r3 = await mcp_opendaw_apply_genre_mix(
        genre="synthwave",
        unit_index=0,
    )
    print("Mix:", r3)

    # 4. Render
    r4 = await mcp_opendaw_render_full_song()
    print("Render:", r4)


if __name__ == "__main__":
    asyncio.run(main())
