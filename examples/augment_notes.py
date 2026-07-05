#!/usr/bin/env python3
"""Example: augment_notes — the fourth classical motivic transformation.

Augmentation (slowing down) and diminution (speeding up) complete the set of
four fundamental transformations used by Bach, Beethoven, and every composition
teacher: transpose, reverse, invert, and now augment/diminish.

This example creates a melody, then applies augmentation (x2) and diminution (x0.5)
to demonstrate how the same motif sounds at different time scales.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

from server import (
    bridge,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_melody,
    mcp_opendaw_augment_notes,
)


async def main():
    await bridge.start()

    # Create a synth track
    r = await mcp_opendaw_create_synth_track(name="Augment Demo", synth_type="vaporisateur")
    print(f"Track: {r[:80]}")

    # Create a melody
    r = await mcp_opendaw_create_melody(
        scale="major", root="C", pattern="1 2 3 4 5 4 3 2 1",
        unit_index=1, track_index=0,
    )
    print(f"Melody: {r[:80]}")

    # Augment x2 (twice as slow — Beethoven 5th recapitulation style)
    r = await mcp_opendaw_augment_notes(
        factor=2.0, unit_index=1, track_index=0, region_index=0, mode="scale",
    )
    print(f"Augmented x2: {r}")

    # Diminish x0.5 (twice as fast — Bach fugue finale style)
    r = await mcp_opendaw_augment_notes(
        factor=0.5, unit_index=1, track_index=0, region_index=0, mode="scale",
    )
    print(f"Diminished x0.5: {r}")


if __name__ == "__main__":
    asyncio.run(main())
