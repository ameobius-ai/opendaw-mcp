"""Example: create_stutter — stutter edit for transitions and glitch fills.

    python3 examples/create_stutter.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_create_note_track,
        mcp_opendaw_create_stutter,
    )

    await mcp_opendaw_create_synth_track("Stutter", "vaporisateur")
    await mcp_opendaw_create_note_track(0)

    # Classic stutter build — accelerating 16ths, velocity ramps up
    r1 = await mcp_opendaw_create_stutter(
        pitches="60",
        pattern="accelerate",
        rate="16th",
        repeat_count=16,
        velocity_ramp="build",
        accent_pattern="downbeat",
        unit_index=0, track_index=0,
    )
    print(f"build: {r1[:120]}")

    # Glitch fill — 32nd notes with gate for choppy feel
    r2 = await mcp_opendaw_create_stutter(
        pitches="64,67,71",
        pattern="ping_pong",
        rate="32nd",
        gate=0.6,
        repeat_count=12,
        start_beat=8,
    )
    print(f"glitch: {r2[:120]}")

    # Reverse stutter — decelerating from fast to slow
    r3 = await mcp_opendaw_create_stutter(
        pitches="72",
        pattern="decelerate",
        rate="64th",
        velocity_ramp="fade_out",
        repeat_count=20,
        start_beat=16,
    )
    print(f"reverse: {r3[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
