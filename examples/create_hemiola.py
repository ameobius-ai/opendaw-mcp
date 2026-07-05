#!/usr/bin/env python3
"""Example: Hemiola — 3:2 rhythmic displacement.

A hemiola creates a cross-rhythm by grouping notes in 3s against 2s
(or vice versa) over the same time span. Fundamental to Afro-Cuban music,
jazz, and minimalist composition.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/create_hemiola.py
"""
import asyncio, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(SCRIPT_DIR)))


async def main():
    from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_hemiola
    import json

    await bridge.start()

    # Create a synth track
    r = await mcp_opendaw_create_synth_track(name="Hemiola", synth_type="vaporisateur")
    print(f"Created track: {r[:80]}")

    # Classic 3:2 hemiola — 3 notes in time of 2
    r = await mcp_opendaw_create_hemiola(
        pattern="3:2",
        bars=2,
        unit_index=1,
        primary_pitch=60,
        secondary_pitch=67,
        primary_velocity=0.75,
        secondary_velocity=0.55,
        duration=0.25,
    )
    d = json.loads(r)
    print(f"3:2 hemiola: {d.get('total_notes')} notes, ratio={d.get('ratio')}")

    # Inverse 2:3 hemiola — 2 notes in time of 3
    r = await mcp_opendaw_create_hemiola(
        pattern="2:3",
        bars=2,
        unit_index=1,
        start_beat=10,
        primary_pitch=55,
        secondary_pitch=62,
        primary_velocity=0.7,
        secondary_velocity=0.5,
        duration=0.3,
    )
    d = json.loads(r)
    print(f"2:3 hemiola: {d.get('total_notes')} notes, ratio={d.get('ratio')}")

    await bridge.stop()
    print("\nDone! Hemiola patterns created.")


if __name__ == "__main__":
    asyncio.run(main())
