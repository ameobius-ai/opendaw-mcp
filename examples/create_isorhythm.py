#!/usr/bin/env python3
"""Example: Isorhythm — repeating rhythm (talea) × repeating pitch (color).

Isorhythm separates rhythm and pitch into independent cycles. The talea
(rhythmic pattern) and color (pitch series) repeat at their own rates,
creating constantly shifting relationships. When they have different
lengths, the full pattern only realigns at the LCM of both lengths.

Found in medieval motets (Machaut), influenced Messiaen, Boulez.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/create_isorhythm.py
"""
import asyncio, os, sys

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_isorhythm


async def main():
    await bridge.start()

    r = await mcp_opendaw_create_synth_track("Isorhythm", "vaporisateur")
    print(f"Synth: {r[:80]}")

    # 1. Classic isorhythm: 8-note talea × 8-note color, 3 cycles
    r = await mcp_opendaw_create_isorhythm(
        talea="1,1,0.5,0.5,1,0.5,0.5,1",
        color="60,62,64,65,67,65,64,62",
        repeats=3,
    )
    print(f"Classic 8×8: {r[:140]}")

    # 2. Phase shift: talea=4, color=5 → LCM=20, pattern shifts
    r = await mcp_opendaw_create_isorhythm(
        talea="1,1,0.5,0.5",
        color="60,64,67,72,67",
        repeats=4,
        start_beat=24,
    )
    print(f"Phase 4×5: {r[:140]}")

    # 3. Minimalist: simple talea, rich color
    r = await mcp_opendaw_create_isorhythm(
        talea="0.25,0.25,0.5,0.5",
        color="60,62,64,65,67,69,71,72",
        repeats=4,
        start_beat=48,
    )
    print(f"Minimalist 4×8: {r[:140]}")

    await bridge.stop()
    print("\nDone! Isorhythm patterns created.")


if __name__ == "__main__":
    asyncio.run(main())
