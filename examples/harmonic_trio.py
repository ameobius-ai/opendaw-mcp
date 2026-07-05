"""Harmonic trio example — chord pads + arpeggiated progression + bass from same chords.

All three tools take the same "Am-F-C-G" progression string:
- create_chord_pads → sustained harmony (track 2)
- create_arpeggiated_progression → melodic movement (track 3)
- create_bass_from_progression → bass foundation (track 1)
"""
import asyncio
from server import (
    mcp_opendaw_create_song_with_variations,
    mcp_opendaw_create_chord_pads,
    mcp_opendaw_create_arpeggiated_progression,
    mcp_opendaw_create_bass_from_progression,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_render_full_song,
)


async def main():
    # 1. Base song (drums + bass + melody from synthwave arrangement)
    await mcp_opendaw_create_song_with_variations("synthwave")

    # 2. Harmonic trio — all from same "Am-F-C-G" progression
    progression = "Am-F-C-G"

    # Sustained pads (harmony track)
    await mcp_opendaw_create_chord_pads(
        progression, bars_per_chord=4, octave=3, track_index=2,
        velocity=0.6,
    )

    # Arpeggiated movement (melody track, 16th up pattern)
    await mcp_opendaw_create_arpeggiated_progression(
        progression, pattern="up", octave=4, step_duration=0.25,
        track_index=3, velocity=0.7,
    )

    # Bass foundation (bass track, root pattern)
    await mcp_opendaw_create_bass_from_progression(
        progression, pattern="root", octave=2, track_index=1,
        velocity=0.9,
    )

    # 3. Mix
    await mcp_opendaw_apply_genre_mix("synthwave")

    # 4. Render
    await mcp_opendaw_render_full_song(filename="harmonic_trio")

    print("✓ Harmonic trio rendered — pads + arp + bass from Am-F-C-G")


asyncio.run(main())
