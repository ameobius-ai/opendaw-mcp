"""Example: Apply beat-aware velocity accents to notes.

accent_beats determines accent strength from each note's beat position,
not its index. This is how real musicians play — downbeats stronger,
off-beats lighter.
"""
import asyncio
from server import (
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_drum_pattern,
    mcp_opendaw_accent_beats,
    mcp_opendaw_note_stats,
)


async def main():
    # 1. Create a drum track with a basic pattern
    print("Creating drum track...")
    await mcp_opendaw_create_synth_track("Drums", "vaporisateur")
    await mcp_opendaw_create_track_region(0, 0, 0, 4, "Drum Loop", -1)
    await mcp_opendaw_create_drum_pattern("kick_snare_kick_snare", unit_index=0)

    # 2. Check stats before — probably flat velocity
    print("\nBefore accent:")
    print(await mcp_opendaw_note_stats(0, 0))

    # 3. Apply backbeat — accent beats 2 and 4 (snare)
    print("\nApplying backbeat accents...")
    result = await mcp_opendaw_accent_beats(
        0, 0, "backbeat",
        strong_velocity=1.0,
        medium_velocity=0.6,
        weak_velocity=0.3,
    )
    print(result)

    # 4. Check stats after — velocity std should be higher
    print("\nAfter accent:")
    print(await mcp_opendaw_note_stats(0, 0))


if __name__ == "__main__":
    asyncio.run(main())
