"""Example: create_tala — Indian classical tala.

Generates a teental (16-beat) tala cycle with tabla bols mapped to MIDI
pitches. Tali (clap) beats are emphasized, khali (wave) beats are soft.

The theka (stroke pattern) for teental:
  Dha Dhin Dhin Dha | Dha Dhin Dhin Dha | Dha Tin Tin Ta | Ta Dhin Dhin Dha
  ─── tali ──────── | ─── normal ────── | ─── khali ──── | ─── tali ──────
"""

import asyncio
import json

from opendaw_mcp.server import mcp_opendaw_create_tala
from opendaw_mcp.server import mcp_opendaw_create_note_track


async def main():
    # Create a note track for tabla
    print(await mcp_opendaw_create_note_track(unit_index=0))

    # Generate 4 cycles of teental at madhya (medium) laya
    result = await mcp_opendaw_create_tala(
        tala_name="teental",
        cycles=4,
        laya="madhya",
        velocity=0.75,
        unit_index=0,
        track_index=0,
        start_beat=0,
    )
    data = json.loads(result[result.index("{"):result.rindex("}") + 1])
    print(f"Tala: {data['tala']}")
    print(f"Laya: {data['laya']}")
    print(f"Vibhags: {data['vibhags']}")
    print(f"Tali beats: {data['tali']}")
    print(f"Khali beats: {data['khali']}")
    print(f"Notes created: {data['notes_created']}")
    print(f"Bols (one cycle): {data['bols']}")


if __name__ == "__main__":
    asyncio.run(main())
