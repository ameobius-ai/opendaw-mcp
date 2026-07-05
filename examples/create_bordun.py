#!/usr/bin/env python3
"""Example: Bordun — continuously sustained drone chord.

A bordun provides a harmonic foundation beneath changing melody.
Unlike pedal_point (single anchored note), the bordun is a sustained
textural layer — open fifths, octaves, or drone chords. Found in
bagpipes, tanpura, hurdy-gurdy, ambient drone, folk.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/create_bordun.py
"""
import asyncio, os, sys

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_bordun


async def main():
    await bridge.start()

    # Create a synth track for the bordun
    r = await mcp_opendaw_create_synth_track("Bordun", "vaporisateur")
    print(f"Synth track: {r[:80]}")

    # 1. Open fifth drone — C3+G3, 4 bars sustained
    r = await mcp_opendaw_create_bordun(root="C", octave=3, intervals="0,7", bars=4)
    print(f"Open fifth: {r[:120]}")

    # 2. Octave+fifth — D2+A2+D3, 2 bars, deep and rich
    r = await mcp_opendaw_create_bordun(root="D", octave=2, intervals="0,7,12", bars=2, start_beat=16)
    print(f"Octave+fifth: {r[:120]}")

    # 3. Minor triad drone — A3+C4+E4, retrigger every 2 bars
    r = await mcp_opendaw_create_bordun(root="A", octave=3, intervals="0,3,7", bars=4, retrigger_bars=2, start_beat=24)
    print(f"Minor triad retrigger: {r[:120]}")

    # 4. Single low drone — G2, 8 bars, very soft
    r = await mcp_opendaw_create_bordun(root="G", octave=2, intervals="0", bars=8, velocity=0.4, start_beat=40)
    print(f"Single low drone: {r[:120]}")

    await bridge.stop()
    print("\nDone! Bordun drones created.")


if __name__ == "__main__":
    asyncio.run(main())
