"""Example: create_songo_pattern — Cuban songo drum-kit pattern.

Songo is the Cuban drum-kit fusion that revolutionized Latin music in the 1970s
with Los Van Van (drummer Changuito). It fuses son montuno, rumba, jazz, and
rock drumming into a single drum-kit groove — kick + snare + hi-hat + toms.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_songo_pattern
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    # Create a note track for the drum kit
    print(await mcp_opendaw_create_note_track(unit_index=0))

    # Generate classic songo pattern
    result = await mcp_opendaw_create_songo_pattern(
        bars=4,
        variation="classic",
        velocity=0.8,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Variation: {data.get('variation')}")
    print(f"Bars: {data.get('bars')}")
    print(f"Total notes: {data.get('total_notes')}")
    print(f"Stroke counts: {data.get('stroke_counts')}")


if __name__ == "__main__":
    asyncio.run(main())
