"""Voice-led chord progression — smooth voice movement vs root position.

This example shows the difference between create_chord_pads (root position,
large jumps between chords) and create_voice_led_progression (re-voiced
for minimal voice movement — strings/pads that glide).

Usage:
    python voice_leading.py
"""

import asyncio
from opendaw_mcp.server import mcp_opendaw_create_voice_led_progression, mcp_opendaw_create_chord_pads


async def main():
    # Same progression, two approaches
    progression = "C-Am-F-G"  # I-vi-IV-V in C major (pop)

    # 1. Root position — standard chord pads
    # C: [48,52,55] → Am: [45,48,52] → F: [41,45,48] → G: [43,47,50]
    # Large jumps between chords (each voice moves 3-7 semitones)
    result_root = await mcp_opendaw_create_chord_pads(
        progression=progression,
        bars_per_chord=4,
        octave=3,
        track_index=2,
        velocity=0.65,
    )
    print("Root position pads created")
    print(result_root)

    # 2. Voice led — same chords, minimal movement
    # Each voice moves as little as possible. Common tones stay stationary.
    # Reports per-chord movement, total movement, and average.
    result_vl = await mcp_opendaw_create_voice_led_progression(
        progression=progression,
        bars_per_chord=4,
        octave=3,
        track_index=3,  # separate track
        velocity=0.65,
        voice_range=12,  # ±1 octave from center
    )
    print("\nVoice-led pads created")
    print(result_vl)

    # The voice-led version will show:
    # - Per-chord voicings (re-voiced, not root position)
    # - Movement per voice (much smaller than root position)
    # - total_movement and avg_movement_per_chord
    #
    # Compare: root position C→Am = 3+4+3 = 10 semitones total
    #          voice led C→Am might be 2+1+2 = 5 semitones total


if __name__ == "__main__":
    asyncio.run(main())
