"""Example: create_balkan_meter — Balkan additive meter pattern.

Balkan music uses additive meters: 7/8 (2+2+3), 9/8 (2+2+2+3), 11/16, 13/8.
The unequal groupings create the characteristic "limping" feel.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_balkan_meter
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_balkan_meter(
        meter="7_8",
        cycles=8,
        variation="classic",
        velocity=0.75,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Meter: {data.get('meter')}")
    print(f"Total beats: {data.get('total_beats')}")
    print(f"Groups: {data.get('groups')}")
    print(f"Accents: {data.get('accents')}")
    print(f"Instrument counts: {data.get('instrument_counts')}")
    print(f"Total notes: {data.get('total_notes')}")


if __name__ == "__main__":
    asyncio.run(main())
