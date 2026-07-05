#!/usr/bin/env python3
"""Example: create_comping — rhythmic chordal accompaniment.

Jazz piano comping: ii-V-I progression with off-beat eighth-note rhythm.
The most common accompaniment style in modern music — chords follow the groove.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")
from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_comping

async def main():
    await bridge.start()
    r = await mcp_opendaw_create_synth_track(name="Comping Demo", synth_type="vaporisateur")
    print(f"Track: {r[:60]}")

    # Jazz ii-V-I comping: Dmin7 → G7 → Cmaj7, off-beat eighths
    r = await mcp_opendaw_create_comping(
        chords='[["D","min7"],["G","dom7"],["C","maj7"],["C","maj7"]]',
        rhythm="x-x-x-x-",
        unit_index=1,
        track_index=0,
        velocity=0.65,
        syncopation=0.15,
    )
    print(f"Comping: {r}")

if __name__ == "__main__":
    asyncio.run(main())
