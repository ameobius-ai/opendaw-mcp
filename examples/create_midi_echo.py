"""Create MIDI echo — repeat notes with decaying velocity and pitch shift.

This creative effect repeats existing notes with configurable delay, velocity
decay, and pitch shift per repeat. Think guitar delay throws, synth echo
fills, or cascading octave echoes.

4 feedback modes control how velocity changes per repeat:
- linear: geometric decay (0.6 → 0.6, 0.36, 0.216)
- exponential: faster decay
- constant: same velocity (stutter feel)
- reverse: decreasing velocity (build-up from loud to quiet)
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import mcp_opendaw_create_midi_echo


async def main():
    # Guitar-style echo: 3 repeats, 8th note delay, decaying
    print("=== Guitar echo: linear decay ===")
    result = await mcp_opendaw_create_midi_echo(
        unit_index=0,
        track_index=0,
        repeats=3,
        delay_beats=0.5,  # 8th note
        velocity_decay=0.5,
        feedback_mode="linear",
    )
    print(result)

    # Cascading octave echoes on separate track
    print("\n=== Cascading octave echoes ===")
    result2 = await mcp_opendaw_create_midi_echo(
        unit_index=0,
        track_index=0,
        repeats=4,
        delay_beats=0.25,  # 16th note
        pitch_shift=12,  # octave up each repeat
        dest_track=2,  # separate track
        velocity_decay=0.7,
    )
    print(result2)

    # Stutter feel: constant velocity
    print("\n=== Stutter echo: constant velocity ===")
    result3 = await mcp_opendaw_create_midi_echo(
        unit_index=0,
        track_index=0,
        repeats=4,
        delay_beats=0.25,
        feedback_mode="constant",
        velocity_decay=0.8,  # ignored in constant mode
    )
    print(result3)


if __name__ == "__main__":
    asyncio.run(main())
