"""Example: create_djembe_ensemble — West African djembe/dunun ensemble.

West African drumming is built on layered cyclical patterns. Three dununs
play interlocking ostinato, a bell plays the timeline, and two djembes
play lead (improvisation) and accompaniment parts.

6 instruments: kenkeni, sangban, dundunba, bell, djembe2, djembe1.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_djembe_ensemble
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_djembe_ensemble(
        bars=4,
        style="danza",
        velocity=0.75,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Style: {data.get('style')}")
    print(f"Bars: {data.get('bars')}")
    print(f"Instruments: {data.get('instruments')}")
    print(f"Instrument counts: {data.get('instrument_counts')}")
    print(f"Total notes: {data.get('total_notes')}")


if __name__ == "__main__":
    asyncio.run(main())
