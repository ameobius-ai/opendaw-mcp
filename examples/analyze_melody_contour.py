"""Example: Analyze melodic contour — direction, intervals, climax.

analyze_melody gives a full profile of a melody's shape — useful
before creating variations, comparing melodies, or evaluating
AI-generated content for contour interest.
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_analyze_melody,
)


async def main():
    # 1. Create a melody with an arch contour (rise then fall)
    print("Creating arch-shaped melody...")
    await mcp_opendaw_create_synth_track("Lead", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 8, "Phrase", -1)

    notes = [
        {"pitch": 60, "position": 0, "duration": 0.5, "velocity": 0.7},  # C4 — start low
        {"pitch": 62, "position": 1, "duration": 0.5, "velocity": 0.75},
        {"pitch": 65, "position": 2, "duration": 0.5, "velocity": 0.8},
        {"pitch": 69, "position": 3, "duration": 0.5, "velocity": 0.9},
        {"pitch": 72, "position": 4, "duration": 1.0, "velocity": 1.0},  # C5 — climax (middle)
        {"pitch": 69, "position": 5, "duration": 0.5, "velocity": 0.85},
        {"pitch": 65, "position": 6, "duration": 0.5, "velocity": 0.75},
        {"pitch": 62, "position": 7, "duration": 0.5, "velocity": 0.65},
    ]
    await mcp_opendaw_create_notes_batch(notes, unit_index=0, track_index=0, region_index=0)

    # 2. Analyze
    print("\nMelodic analysis:")
    result = await mcp_opendaw_analyze_melody(0, 0)
    print(result)
    # Expected: contour_shape="arch", climax at beat 4 (position ~0.57),
    # step_ratio high (mostly 2-3 semitone steps), range=12 (one octave)


if __name__ == "__main__":
    asyncio.run(main())
