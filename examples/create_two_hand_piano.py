"""Example: create_two_hand_piano — two-hand piano arrangement.

    python3 examples/create_two_hand_piano.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import mcp_opendaw_create_synth_track, mcp_opendaw_create_note_track, mcp_opendaw_create_two_hand_piano

    # Setup
    await mcp_opendaw_create_synth_track("Piano", "vaporisateur")
    await mcp_opendaw_create_note_track(0)

    # ii-V-I in C major with Alberti bass + chord tones
    r = await mcp_opendaw_create_two_hand_piano(
        chords='[["D","min7"],["G","dom7"],["C","maj7"]]',
        left_hand="alberti",
        right_hand="chord_tones",
        chord_duration=4,
        arpeggio_rate=0.5,
    )
    print(f"ii-V-I Alberti: {r}")

    # Lofi progression with arpeggio up + arpeggio right hand
    r2 = await mcp_opendaw_create_two_hand_piano(
        chords='[["F","min7"],["Ab","maj7"],["Db","maj7"],["Eb","min7"]]',
        left_hand="arpeggio_up",
        right_hand="arpeggio",
        arpeggio_rate=0.25,
        bass_octave=2,
        chord_octave=3,
        melody_octave=5,
    )
    print(f"Lofi arpeggio: {r2}")

    # Custom melody over I-vi-IV-V with bass+chord left hand
    r3 = await mcp_opendaw_create_two_hand_piano(
        chords='[["C","maj"],["A","min"],["F","maj"],["G","maj"]]',
        left_hand="bass_chord",
        right_hand="melody",
        melody_pitches="72,76,79,76,72,74,76,72",
        chord_duration=4,
    )
    print(f"I-vi-IV-V melody: {r3}")


if __name__ == "__main__":
    asyncio.run(main())
