"""Example: create_taiko_ensemble — Japanese taiko drumming.

Kumi-daiko (group taiko) combines multiple drum types into an ensemble.
Dynamic contrast from near silence to thunderous power. Ma (silence)
is a structural element.

4 instruments: odaiko (bass), chu-daiko (mid), shime-daiko (high), atarigane (gong).
5 styles: miyake, yatai, edo, hachijo, omega.
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_taiko_ensemble
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_taiko_ensemble(
        bars=8,
        style="miyake",
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
