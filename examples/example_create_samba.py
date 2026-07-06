"""Example: create_samba_pattern — Brazilian samba percussion ensemble.

Samba is a multi-instrument percussion ensemble where each drum has its own
pattern and the layers interlock. Unlike songo (drum kit), samba is a bateria.

5 instruments: surdo (bass), caixa (snare), tamborim (small drum),
chocalho (shaker), repique (lead drum).
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_samba_pattern
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_samba_pattern(
        bars=4,
        style="batucada",
        velocity=0.8,
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
