#!/usr/bin/env python3
"""Example: create_mordent — classical baroque ornament.

A mordent is a rapid ornament: main note → neighbor → main.
Upper mordent flicks up, lower mordent flicks down.
Bach two-part inventions, Mozart sonatas.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_mordent

async def main():
    await bridge.start()
    r = await mcp_opendaw_create_synth_track(name="Mordent Demo", synth_type="vaporisateur")
    print(f"Track: {r[:60]}")

    # Upper mordent on C4 (C → D → C)
    r = await mcp_opendaw_create_mordent(main_pitch=60, direction="upper", interval=2, unit_index=1)
    print(f"Upper mordent: {r}")

    # Lower mordent on E4 (E → Eb → E)
    r = await mcp_opendaw_create_mordent(main_pitch=64, direction="lower", interval=1, unit_index=1, start_beat=2)
    print(f"Lower mordent: {r}")

if __name__ == "__main__":
    asyncio.run(main())
