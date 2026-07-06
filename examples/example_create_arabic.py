"""Example: create_arabic_percussion — Arabic/Middle Eastern percussion ensemble.

Darbuka (dum/tek/ka), daf (frame drum), zills (finger cymbals).
Maqsum is the "mother of all Arabic rhythms" — D-T-K-D-T-K-T pattern.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_arabic_percussion
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_arabic_percussion(
        bars=4,
        rhythm="maqsum",
        velocity=0.75,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Rhythm: {data.get('rhythm')}")
    print(f"Instruments: {data.get('instruments')}")
    print(f"Instrument counts: {data.get('instrument_counts')}")
    print(f"Stroke counts: {data.get('stroke_counts')}")
    print(f"Total notes: {data.get('total_notes')}")


if __name__ == "__main__":
    asyncio.run(main())
