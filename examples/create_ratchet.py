"""create_ratchet — repeated notes with changing subdivision rate.

Demonstrates Bach-style ratchet (accelerando repeat) on a note track,
creating a sense of acceleration from 8th notes to 32nd notes.
"""
import asyncio
from server import (
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_ratchet,
    mcp_opendaw_list_tracks,
)


async def main():
    # 1. list tracks
    tracks = await mcp_opendaw_list_tracks()
    print("Tracks:", tracks[:200])

    # 2. create a note track
    result = await mcp_opendaw_create_note_track(unit_index=0, name="ratchet")
    print("Created track:", result[:200])

    # 3. accelerate ratchet: 2 beats, 8th→32nd notes
    r1 = await mcp_opendaw_create_ratchet(
        unit_index=0, track_index=0,
        pitch=60, start_beat=0, length_beats=2.0,
        subdivisions="accelerate", max_subdivisions=8,
        velocity=0.7, velocity_decay=0.01
    )
    print("Accelerate ratchet:", r1[:300])

    # 4. decelerate ratchet: fast→slow
    r2 = await mcp_opendaw_create_ratchet(
        unit_index=0, track_index=0,
        pitch=64, start_beat=3, length_beats=2.0,
        subdivisions="decelerate", max_subdivisions=16,
        velocity=0.6, pitch_drift=1  # ascending chromatic
    )
    print("Decelerate ratchet:", r2[:300])

    # 5. exponential acceleration for build-up
    r3 = await mcp_opendaw_create_ratchet(
        unit_index=0, track_index=0,
        pitch=67, start_beat=6, length_beats=4.0,
        subdivisions="exponential", max_subdivisions=32,
        velocity=0.5, velocity_decay=0.005,
        pitch_drift=12  # ascending octaves
    )
    print("Exponential ratchet:", r3[:300])


if __name__ == "__main__":
    asyncio.run(main())
