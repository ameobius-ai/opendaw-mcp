"""Apply a rhythmic pattern to existing notes.

This demonstrates the rhythm analysis → modification loop:
1. extract_rhythm analyzes the rhythmic pattern of a drum track
2. apply_rhythm_pattern stamps a new groove onto a bass track

The rhythm_string format uses x=onset, .=rest. The pattern cycles to fill
the region. velocity_mode and duration_mode control how notes are adjusted.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import mcp_opendaw_extract_rhythm, mcp_opendaw_apply_rhythm_pattern


async def main():
    # Step 1: Analyze the drum groove
    print("=== Step 1: Extract rhythm from drums ===")
    rhythm = await mcp_opendaw_extract_rhythm(
        unit_index=0, track_index=0, grid="16th"
    )
    print(rhythm)

    # Step 2: Apply a new rhythmic pattern to bass
    # "x...x...x...x..." = quarter-note pulses (four on the floor)
    print("\n=== Step 2: Apply four-on-the-floor to bass ===")
    result = await mcp_opendaw_apply_rhythm_pattern(
        unit_index=0,
        track_index=1,  # bass track
        rhythm_string="x...x...x...x...",
        grid="16th",
        velocity_mode="accent",  # strong beats louder
        duration_mode="legato",  # notes connect
    )
    print(result)

    # Step 3: Apply a syncopated pattern
    # "x.x.x.x." = 8th-note off-beats (reggae skank feel)
    print("\n=== Step 3: Apply syncopated pattern ===")
    result2 = await mcp_opendaw_apply_rhythm_pattern(
        unit_index=0,
        track_index=1,
        rhythm_string="x.x.x.x.",
        grid="16th",
        velocity_mode="preserve",
        duration_mode="staccato",  # short hits
    )
    print(result2)

    # Step 4: Use onset_grid with velocity values
    # "0.9,0,0.6,0,0.8,0,0,0.5" = onsets with custom velocities
    print("\n=== Step 4: Pattern with velocity values ===")
    result3 = await mcp_opendaw_apply_rhythm_pattern(
        unit_index=0,
        track_index=1,
        onset_grid="0.9,0,0.6,0,0.8,0,0,0.5",
        grid="16th",
        velocity_mode="pattern",  # use the velocity values from onset_grid
        duration_mode="preserve",
    )
    print(result3)


if __name__ == "__main__":
    asyncio.run(main())
