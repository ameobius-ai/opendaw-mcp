"""Example: create_korean_percussion — Korean nongak/samul nori.

Korean percussion uses 4 instrument types representing weather elements:
janggu (rain), buk (clouds), kkwaenggwari (thunder), jing (wind).

5 styles: nongak, samul_nori, binari, utdari_pungnyu, yeongnam_folk.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_korean_percussion
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_korean_percussion(
        bars=8,
        style="nongak",
        velocity=0.75,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Style: {data.get('style')}")
    print(f"Instruments: {data.get('instruments')}")
    print(f"Instrument counts: {data.get('instrument_counts')}")
    print(f"Total notes: {data.get('total_notes')}")


if __name__ == "__main__":
    asyncio.run(main())
