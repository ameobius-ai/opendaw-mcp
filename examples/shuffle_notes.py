"""shuffle_notes — generative melodic/rhythmic variation via random permutation.

Takes an existing note region and shuffles its notes to create variations.
4 modes offer different creative directions:
- pitches: keep rhythm, shuffle melody (most musical)
- rhythm: keep pitches, shuffle timing
- full: shuffle everything
- within_groups: shuffle within beat groups for localized variation

Seeded for reproducibility — same seed = same shuffle result.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_shuffle_notes


async def main():
    # Mode 1: shuffle pitches only — keeps the rhythm, changes the melody
    result = await mcp_opendaw_shuffle_notes(
        unit_index=0,
        track_index=0,
        region_index=0,
        mode="pitches",
        seed=42,
        shuffle_amount=1.0,
        preserve_first=True,
        preserve_last=True,
    )
    print("Mode: pitches (keep rhythm, shuffle melody)")
    print(result)
    print()

    # Mode 2: shuffle rhythm — keeps pitches, reassigns onset times
    result = await mcp_opendaw_shuffle_notes(
        unit_index=0,
        track_index=0,
        region_index=0,
        mode="rhythm",
        seed=99,
        shuffle_amount=0.7,
        preserve_first=True,
    )
    print("Mode: rhythm (keep pitches, shuffle timing)")
    print(result)
    print()

    # Mode 3: shuffle within groups — localized variation per bar
    result = await mcp_opendaw_shuffle_notes(
        unit_index=0,
        track_index=0,
        region_index=0,
        mode="within_groups",
        seed=123,
        shuffle_amount=0.8,
        group_beats=4.0,
    )
    print("Mode: within_groups (shuffle within each bar)")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
