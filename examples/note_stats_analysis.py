"""Example: Get comprehensive note statistics for a region.

note_stats returns a full statistical profile — pitch range, velocity
distribution, density, pitch class histogram. Useful for analysis
before processing and for detecting programming issues.
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_note_stats,
)


async def main():
    # 1. Create track with varied notes
    print("Creating track...")
    await mcp_opendaw_create_synth_track("Piano", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 8, "Phrase", -1)

    notes = [
        {"pitch": 60, "position": 0, "duration": 0.5, "velocity": 0.8},
        {"pitch": 62, "position": 1, "duration": 0.5, "velocity": 0.6},
        {"pitch": 64, "position": 2, "duration": 1.0, "velocity": 0.9},
        {"pitch": 67, "position": 3, "duration": 0.5, "velocity": 0.7},
        {"pitch": 72, "position": 4, "duration": 2.0, "velocity": 1.0},
        {"pitch": 60, "position": 6, "duration": 0.5, "velocity": 0.5},
        {"pitch": 64, "position": 7, "duration": 0.5, "velocity": 0.85},
    ]
    await mcp_opendaw_create_notes_batch(notes, unit_index=0, track_index=0, region_index=0)

    # 2. Get statistics
    print("\nNote statistics:")
    result = await mcp_opendaw_note_stats(0, 0)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
