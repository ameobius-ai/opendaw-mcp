"""Combined pipeline example — genre arrangement + harmonic layers.

Pattern: create genre arrangement (drums + bass) then add harmonic
layers (pads + arp + melody) from a chord progression. This combines
rhythm from genre presets with harmony from progression strings.
"""
import asyncio
from server import (
    mcp_opendaw_create_liquid_dnb_arrangement,
    mcp_opendaw_create_harmonic_arrangement,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_render_full_song,
)


async def main():
    # 1. Genre arrangement: drums + melodic sub-bass + lush pads + soulful melody
    await mcp_opendaw_create_liquid_dnb_arrangement(
        bpm=174, root="F", bars=8, velocity=0.75,
    )

    # 2. Add harmonic layers from same key progression
    # Skip pads (arrangement already has lush pads) and bass (arrangement has melodic sub-bass)
    # Just add arp and melody from F minor progression
    await mcp_opendaw_create_harmonic_arrangement(
        "Fm-Db-Ab-Eb",
        pad_octave=-1,       # skip pads (arrangement has them)
        bass_pattern="",     # skip bass (arrangement has it)
        arp_pattern="up",
        arp_octave=4,
        arp_step=0.25,
        melody_pattern="chord_tones",
        melody_octave=5,
        bars_per_chord=2,
        velocity=0.7,
    )

    # 3. Mix with liquid DnB genre settings
    await mcp_opendaw_apply_genre_mix("liquid_dnb", num_tracks=4)

    # 4. Render
    await mcp_opendaw_render_full_song(filename="liquid_dnb_harmonic")

    print("✓ Liquid DnB with harmonic layers rendered")


asyncio.run(main())
