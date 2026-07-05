"""
Example: Create drum fills and transitions.

Generates rhythmic fills between song sections with 5 types:
build, break, roll, crash, tom. Adjustable density and bar length.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create a synth track (acts as drum machine via MIDI)
    result = await server.mcp_opendaw_create_synth_track("Drums", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Drum synth: unit_index={uid}")

    # 2. Build fill — density increases toward end (verse → chorus transition)
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="build", bars=1, start_beat=0, density="medium"
    )
    data = json.loads(result)
    print(f"Build fill (1 bar): {data['total_notes']} notes, lanes={data['lanes']}")

    # 3. Roll fill — sustained snare roll with accents (breakdown → drop)
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="roll", bars=2, start_beat=4, density="dense"
    )
    data = json.loads(result)
    print(f"Roll fill (2 bars): {data['total_notes']} notes, lanes={data['lanes']}")

    # 4. Tom fill — descending tom pattern
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="tom", bars=1, start_beat=12, density="sparse"
    )
    data = json.loads(result)
    print(f"Tom fill (1 bar): {data['total_notes']} notes, lanes={data['lanes']}")

    # 5. Crash fill — impact with sparse hits
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="crash", bars=1, start_beat=16, density="medium"
    )
    data = json.loads(result)
    print(f"Crash fill (1 bar): {data['total_notes']} notes, lanes={data['lanes']}")

    # 6. Break fill — density decreases (winding down after a section)
    result = await server.mcp_opendaw_create_drum_fill(
        unit_index=uid, fill_type="break", bars=2, start_beat=20, density="dense"
    )
    data = json.loads(result)
    print(f"Break fill (2 bars): {data['total_notes']} notes, lanes={data['lanes']}")

    await server.bridge.stop()
    print("\nDone — 5 drum fill types created across 26 beats")


if __name__ == "__main__":
    asyncio.run(main())
