"""Harmonic quintet: pads + arp + bass + melody + counter-melody in ONE call.

This example shows the full 5-layer harmonic pipeline from a single
chord progression string "Am-F-C-G". All layers derive from the same
progression and are placed on separate tracks — all in one call.

Track layout (auto-routed by create_harmonic_arrangement):
  0 — drums (not created here, add with create_XXX_arrangement)
  1 — bass
  2 — pads
  3 — arp
  4 — melody
  5 — counter-melody (contrary motion)

The counter-melody uses 'contrary' motion — it moves opposite to the
chord root motion, creating classic species-1 counterpoint.
"""
import asyncio
from server import (
    mcp_opendaw_create_harmonic_arrangement,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_render_full_song,
)


async def main():
    progression = "Am-F-C-G"

    # 1. Full harmonic quintet in ONE call (5 layers)
    r1 = await mcp_opendaw_create_harmonic_arrangement(
        progression,
        pad_octave=3,
        arp_pattern="up",
        bass_pattern="root",
        melody_pattern="chord_tones",
        counter_melody_pattern="contrary",
        counter_melody_octave=4,
        bars_per_chord=4,
        velocity=0.7,
    )
    print("Harmonic quintet:", r1)

    # 2. Mix
    r2 = await mcp_opendaw_apply_genre_mix(
        genre="synthwave",
        unit_index=0,
    )
    print("Mix:", r2)

    # 3. Render
    r3 = await mcp_opendaw_render_full_song()
    print("Render:", r3)


if __name__ == "__main__":
    asyncio.run(main())
