"""Example: Parallel interval doubling — octave, diatonic thirds, power chords.

double_melody creates a parallel copy of a melody at a named musical interval.
This example shows three common doubling scenarios:
1. Octave doubling (thickens melody in place)
2. Diatonic thirds (classic harmony on separate track)
3. Power chord fifth (rock/metal doubling)
"""
import asyncio
from server import mcp_opendaw_generate_melody, mcp_opendaw_double_melody


async def main():
    # 1. Generate a melody in C major
    print("Generating melody in C major...")
    result = await mcp_opendaw_generate_melody(
        root="C", scale="major", contour="arch",
        rhythm="eighth", bars=4, octave=4,
        unit_index=0, track_index=0,
    )
    print(f"Melody: {result}")

    # 2. Octave doubling — thickens in place (same region)
    print("\nOctave doubling (in-place thickening)...")
    result = await mcp_opendaw_double_melody(
        unit_index=0, track_index=0,
        interval="octave",
        velocity_scale=0.7,  # quieter double
    )
    print(f"Octave doubled: {result}")

    # 3. Diatonic thirds on a separate track — stays in key
    # C→E (major third), D→F (minor third) — correct quality automatically
    print("\nDiatonic thirds (cross-track harmony)...")
    result = await mcp_opendaw_double_melody(
        unit_index=0, track_index=0,
        interval="third",
        diatonic=True, root="C", scale="major",
        dest_track_index=1,  # separate track
        velocity_scale=0.8,
    )
    print(f"Diatonic thirds: {result}")

    # 4. Power chord doubling — root + fifth
    print("\nPower chord doubling (fifth)...")
    result = await mcp_opendaw_double_melody(
        unit_index=0, track_index=0,
        interval="fifth",
        velocity_scale=0.9,
    )
    print(f"Power chord: {result}")


if __name__ == "__main__":
    asyncio.run(main())
