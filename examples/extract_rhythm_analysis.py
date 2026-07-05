"""Example: Extract rhythmic pattern from notes.

extract_rhythm analyzes the timing of notes — onset positions,
syncopation, swing, inter-onset intervals. Companion to analyze_melody
(which analyzes pitch contour).
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_extract_rhythm,
)


async def main():
    # 1. Create a syncopated rhythm
    print("Creating syncopated rhythm...")
    await mcp_opendaw_create_synth_track("Drums", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 4, "Loop", -1)

    # Boom-bap pattern: kick on 1 and 3, snare on 2 and 4
    # with some 16th hat syncopation
    notes = [
        {"pitch": 36, "position": 0, "duration": 0.5, "velocity": 0.9},   # kick beat 1
        {"pitch": 42, "position": 0.5, "duration": 0.25, "velocity": 0.4}, # hat
        {"pitch": 42, "position": 1, "duration": 0.25, "velocity": 0.5},   # hat
        {"pitch": 38, "position": 1, "duration": 0.5, "velocity": 0.85},   # snare beat 2
        {"pitch": 42, "position": 1.5, "duration": 0.25, "velocity": 0.4}, # hat
        {"pitch": 36, "position": 2, "duration": 0.5, "velocity": 0.9},   # kick beat 3
        {"pitch": 42, "position": 2.5, "duration": 0.25, "velocity": 0.5}, # hat
        {"pitch": 38, "position": 3, "duration": 0.5, "velocity": 0.85},   # snare beat 4
        {"pitch": 42, "position": 3.5, "duration": 0.25, "velocity": 0.6}, # hat
    ]
    await mcp_opendaw_create_notes_batch(notes, unit_index=0, track_index=0, region_index=0)

    # 2. Extract rhythm at 16th resolution
    print("\nRhythm analysis (16th grid):")
    result = await mcp_opendaw_extract_rhythm(0, 0, grid="16th")
    print(result)
    # Expected: rhythm_string like "x.x.x.x.x.x.x.x.", moderate syncopation


if __name__ == "__main__":
    asyncio.run(main())
