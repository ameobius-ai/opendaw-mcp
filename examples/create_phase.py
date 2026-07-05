"""Example: create_phase — Steve Reich phase shifting pattern.

    python3 examples/create_phase.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_create_phase,
    )

    await mcp_opendaw_create_synth_track("Phase", "vaporisateur")

    # Steve Reich "Piano Phase" style — 2 voices, gradual drift
    r = await mcp_opendaw_create_phase(
        pattern="60 66 72 67 64 60",
        voices=2,
        phase_rate=0.1,
        phase_direction="forward",
        repeats=12,
        step_duration=0.25,
    )
    print(f"piano phase: {r[:120]}")

    # 3-voice diverge — ambient texture
    r = await mcp_opendaw_create_phase(
        pattern="60 64 67 71",
        voices=3,
        phase_rate=0.08,
        phase_direction="diverge",
        repeats=16,
        velocity_decay=0.12,
    )
    print(f"ambient diverge: {r[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
