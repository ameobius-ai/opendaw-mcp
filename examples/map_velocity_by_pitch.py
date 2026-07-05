"""Map velocity based on pitch — expressive dynamics from note height.

This tool adjusts note velocity proportionally to pitch position, simulating
natural acoustic instrument behaviour where register affects perceived intensity.

Modes:
- higher_quieter: piano natural, orchestral, drums (kick loud, hi-hat soft)
- lower_quieter: lead synth, bells (highs cut through)
- bell_curve: vocal range, mid-range instruments
- inverse_bell: experimental (quiet middle, loud extremes)
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    mcp_opendaw_map_velocity_by_pitch,
)


async def main():
    # Step 1: Make drums natural — kick loud, hi-hat quiet
    print("=== Drums: higher_quieter (kick loud, hi-hat soft) ===")
    result = await mcp_opendaw_map_velocity_by_pitch(
        unit_index=0,
        track_index=0,  # drum track
        mode="higher_quieter",
        intensity=0.6,
        pitch_ref=48,  # C3 — drum kit center
    )
    print(result)

    # Step 2: Lead synth — highs cut through
    print("\n=== Lead synth: lower_quieter (highs cut through) ===")
    result2 = await mcp_opendaw_map_velocity_by_pitch(
        unit_index=0,
        track_index=3,  # lead track
        mode="lower_quieter",
        intensity=0.4,
        pitch_ref=72,  # C5 — lead synth center
    )
    print(result2)

    # Step 3: Piano — natural dynamics
    print("\n=== Piano: higher_quieter natural ===")
    result3 = await mcp_opendaw_map_velocity_by_pitch(
        unit_index=0,
        track_index=1,  # piano track
        mode="higher_quieter",
        intensity=0.5,
        pitch_ref=60,  # C4 — middle C
    )
    print(result3)

    # Step 4: Vocal range emphasis
    print("\n=== Vocal: bell_curve (mid register loudest) ===")
    result4 = await mcp_opendaw_map_velocity_by_pitch(
        unit_index=0,
        track_index=2,  # vocal track
        mode="bell_curve",
        intensity=0.3,
        pitch_ref=64,  # E4 — vocal sweet spot
    )
    print(result4)


if __name__ == "__main__":
    asyncio.run(main())
