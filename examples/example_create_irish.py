"""Example: create_irish_trad — Irish traditional music accompaniment.

Irish trad is defined by tune types, each with a characteristic meter.
Bodhrán (frame drum) + feet stomp provide the rhythmic foundation.

6 tune types: reel (4/4), jig (6/8), hornpipe (4/4 swung), slip jig (9/8),
polka (2/4), slide (12/8).
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_irish_trad
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    print(await mcp_opendaw_create_note_track(unit_index=0))

    result = await mcp_opendaw_create_irish_trad(
        tune_type="reel",
        bars=8,
        velocity=0.7,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Tune type: {data.get('tune_type')}")
    print(f"Meter: {data.get('meter')}")
    print(f"Beats per bar: {data.get('beats_per_bar')}")
    print(f"Accents: {data.get('accents')}")
    print(f"Swing: {data.get('swing')}")
    print(f"Instrument counts: {data.get('instrument_counts')}")
    print(f"Total notes: {data.get('total_notes')}")


if __name__ == "__main__":
    asyncio.run(main())
