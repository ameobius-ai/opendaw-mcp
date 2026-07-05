"""Analyze harmonic rhythm — how fast chords change and where.

This tool identifies chords from MIDI notes (same as identify_chords) and
then analyses the temporal pattern of chord changes: how long each chord
lasts, where stable vs active sections are, and whether modulation is likely.

Use with analyze_song_structure for a complete form picture, and with
reharmonize_progression to know which chords to change.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    mcp_opendaw_analyze_harmonic_rhythm,
    mcp_opendaw_analyze_song_structure,
)


async def main():
    # Step 1: Analyze harmonic rhythm
    print("=== Harmonic rhythm analysis ===")
    result = await mcp_opendaw_analyze_harmonic_rhythm(
        unit_index=0,
        track_index=0,
        region_index=-2,  # all regions
    )
    print(result)

    # The result includes:
    # - chord_timeline: [{position, chord, duration_beats, duration_bars}]
    # - harmonic_rhythm_rate: fast / medium / slow
    # - avg_chord_duration: in beats and bars
    # - chords_per_bar: density
    # - stable_sections: chords lasting 4+ bars
    # - active_sections: chords changing every beat or faster
    # - modulation_likely: True if 6+ distinct roots

    # Step 2: Compare with song structure
    print("\n=== Song structure analysis ===")
    structure = await mcp_opendaw_analyze_song_structure(
        unit_index=0,
        bars_per_segment=4,
    )
    print(structure)

    # Together: harmonic rhythm + song structure = full form understanding


if __name__ == "__main__":
    asyncio.run(main())
