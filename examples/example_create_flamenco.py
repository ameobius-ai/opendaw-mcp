"""Example: create_flamenco_compas — Flamenco rhythmic cycle.

The compás is the cyclical rhythmic foundation of Flamenco. 12-beat cycles
with accents on specific beats create the characteristic Flamenco feel.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_flamenco_compas
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_flamenco_compas(
        palo="bulerias",
        cycles=4,
        velocity=0.75,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Palo: {data.get('palo')}")
    print(f"Cycle beats: {data.get('cycle_beats')}")
    print(f"Accents: {data.get('accents')}")
    print(f"Instrument counts: {data.get('instrument_counts')}")
    print(f"Total notes: {data.get('total_notes')}")


if __name__ == "__main__":
    asyncio.run(main())
