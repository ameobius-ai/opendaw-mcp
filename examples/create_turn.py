#!/usr/bin/env python3
"""Example: create_turn — circular baroque ornament (gruppetto).

A turn circles around the main note: main → upper → main → lower → main.
Upper turn goes up first, lower turn goes down first.
Mozart piano concertos, Beethoven sonatas, Bach partitas.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_turn

async def main():
    await bridge.start()
    r = await mcp_opendaw_create_synth_track(name="Turn Demo", synth_type="vaporisateur")
    print(f"Track: {r[:60]}")

    # Upper turn on C4: C → D → C → Bb → C
    r = await mcp_opendaw_create_turn(main_pitch=60, direction="upper", interval=2, unit_index=1)
    print(f"Upper turn: {r}")

    # Lower turn on E4: E → Eb → E → F → E
    r = await mcp_opendaw_create_turn(main_pitch=64, direction="lower", interval=1, unit_index=1, start_beat=4)
    print(f"Lower turn: {r}")

if __name__ == "__main__":
    asyncio.run(main())
