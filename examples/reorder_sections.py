"""reorder_sections — full song structure rearrangement.

This example demonstrates how to completely rearrange song sections.
While swap_sections exchanges two sections, reorder_sections can
rearrange any number of sections into a new order in one call.

Pipeline:
1. Create a song with multiple sections (verse, chorus, bridge)
2. Reorder sections: move chorus to front
3. Verify the new arrangement
"""

import asyncio
from opendaw_mcp.server import (
    mcp_opendaw_reorder_sections,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_notes_batch,
    mcp_opendaw_analyze_song_structure,
)


async def main():
    # 1. Create a synth track
    print("Creating synth track...")
    await mcp_opendaw_create_synth_track("Lead", "vaporisateur")

    # 2. Create notes in different sections
    #    Verse: beats 0-8, Chorus: beats 8-16, Bridge: beats 16-24
    print("\nCreating verse notes (beats 0-8)...")
    verse_notes = [
        {"pitch": 60, "start_beat": 0, "duration": 1, "velocity": 0.6},
        {"pitch": 62, "start_beat": 1, "duration": 1, "velocity": 0.6},
        {"pitch": 64, "start_beat": 2, "duration": 1, "velocity": 0.6},
    ]
    await mcp_opendaw_create_notes_batch(
        track_index=0, notes_json=str(verse_notes).replace("'", '"'),
        unit_index=0
    )

    # 3. Reorder: Chorus first, then Verse, then Bridge
    print("\nReordering sections: chorus → verse → bridge...")
    result = await mcp_opendaw_reorder_sections(
        section_order='[{"start":8,"end":16},{"start":0,"end":8},{"start":16,"end":24}]'
    )
    print(result)

    # 4. Analyze new structure
    print("\nAnalyzing new song structure...")
    result = await mcp_opendaw_analyze_song_structure()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
