"""explode_chords — chord track to individual voice tracks.

Takes a chord progression and splits each chord into separate voices,
distributing to different tracks. Fundamental orchestration technique:
piano chords → bass + cello + viola + violin.
"""
import asyncio
import sys
sys.path.insert(0, ".")
from server import mcp_opendaw_explode_chords


async def main():
    # 4 voices, down direction, natural velocity balance
    result = await mcp_opendaw_explode_chords(
        unit_index=0,
        track_index=0,
        region_index=0,
        num_voices=4,
        direction="down",
        velocity_balance="natural",
    )
    print("4 voices, down, natural velocity:")
    print(result)
    print()

    # 3 voices, up direction, top_heavy
    result = await mcp_opendaw_explode_chords(
        unit_index=0,
        track_index=0,
        region_index=0,
        num_voices=3,
        direction="up",
        velocity_balance="top_heavy",
        target_units="0,1,2",
    )
    print("3 voices, up, top_heavy, target AUs 0,1,2:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
