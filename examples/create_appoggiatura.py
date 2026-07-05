#!/usr/bin/env python3
"""Example: create_appoggiatura — expressive leaning grace note.

The appoggiatura plays a neighbor note FIRST (longer), then resolves
into the main note. Creates harmonic tension → release. The most
expressive of the four essential ornaments.

Bach cello suites, Mozart operas, Chopin nocturnes.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_appoggiatura

async def main():
    await bridge.start()
    r = await mcp_opendaw_create_synth_track(name="Appogg Demo", synth_type="vaporisateur")
    print(f"Track: {r[:60]}")

    # Appoggiatura above: D → C (approach from above, 2/3 tension)
    r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=62, unit_index=1)
    print(f"Appoggiatura above: {r}")

    # Appoggiatura below: B → C (approach from below, equal split)
    r = await mcp_opendaw_create_appoggiatura(main_pitch=60, approach_pitch=59, appoggiatura_ratio=0.5, unit_index=1, start_beat=4)
    print(f"Appoggiatura below: {r}")

if __name__ == "__main__":
    asyncio.run(main())
