"""Example: create_metric_modulation — metric modulation.

Elliott Carter-style metric modulation: change tempo while preserving
a specific note-value equivalence. A dotted eighth at the new tempo
has the same duration as a quarter at the old tempo.

Formula: new_bpm = old_bpm × (new_note_value / old_note_value)
"""

import asyncio

from server import mcp_opendaw_create_metric_modulation


async def main():
    # Classic Carter modulation: quarter@120 → dotted_eighth@90
    result = await mcp_opendaw_create_metric_modulation(
        position_beats=32,
        old_note="quarter",
        new_note="dotted_eighth",
        old_bpm=120,
    )
    print("Carter modulation:", result)

    # Direct ratio: 3:2 (three notes in new = two in old)
    result = await mcp_opendaw_create_metric_modulation(
        position_beats=64,
        ratio="3:2",
        old_bpm=100,
        add_time_signature="6/8",
    )
    print("3:2 with 6/8:", result)

    # Doubling: eighth@140 → quarter@280
    result = await mcp_opendaw_create_metric_modulation(
        position_beats=48,
        old_note="eighth",
        new_note="quarter",
        old_bpm=140,
    )
    print("Doubling:", result)


if __name__ == "__main__":
    asyncio.run(main())
