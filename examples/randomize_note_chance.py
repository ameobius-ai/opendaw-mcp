"""randomize_note_chance — generative MIDI probability variation.

Demonstrates 5 distribution modes for note playback probability:
- uniform: even random between min and max
- decreasing: fade-out probability (high to low)
- increasing: emerge from silence (low to high)
- sparse: mostly silent with occasional hits
- binary: coin flip between min and max

Pipeline:
1. Create a drum pattern
2. Apply randomize_note_chance for generative variation
"""

import asyncio
from opendaw_mcp.server import (
    mcp_opendaw_randomize_note_chance,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_drum_pattern,
)


async def main():
    # 1. Create a drum track
    print("Creating drum pattern...")
    await mcp_opendaw_create_synth_track("Drums", "vaporisateur")
    await mcp_opendaw_create_drum_pattern(
        kick="x...x...x...x...",
        snare="....x.......x...",
        hat="x.x.x.x.x.x.x.x.",
        unit_index=0, track_index=0,
    )

    # 2. Ghost note variation — 30-80% chance
    print("\nGhost note variation (30-80% chance, uniform)...")
    result = await mcp_opendaw_randomize_note_chance(
        unit_index=0, track_index=0,
        min_chance=30, max_chance=80,
        mode="uniform", seed=7,
    )
    print(result)

    # 3. Dissolving pattern — high to low
    print("\nDissolving pattern (decreasing, 100→0%)...")
    result = await mcp_opendaw_randomize_note_chance(
        unit_index=0, track_index=0,
        min_chance=0, max_chance=100,
        mode="decreasing", seed=42,
    )
    print(result)

    # 4. Emerging pattern — low to high
    print("\nEmerging pattern (increasing, 0→100%)...")
    result = await mcp_opendaw_randomize_note_chance(
        unit_index=0, track_index=0,
        min_chance=0, max_chance=100,
        mode="increasing", seed=42,
    )
    print(result)

    print("\n--- Mode summary ---")
    print("uniform: each note gets independent random chance")
    print("decreasing: pattern dissolves — first notes likely, last silent")
    print("increasing: pattern emerges — first silent, last likely")
    print("sparse: 70% get min, 30% get max — ghost note texture")
    print("binary: coin flip — stark on/off patterns")


if __name__ == "__main__":
    asyncio.run(main())
