#!/usr/bin/env python3
"""Example: Hocket — melodic line split between voices.

Hocket divides a single melody between two or more voices, creating
an interlocking texture. Each voice plays only part of the melody.
Found in medieval polyphony, African mbira, Balinese gamelan, and
Steve Reich minimalism.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/create_hocket.py
"""
import asyncio, os, sys

os.environ["DAW_URL"] = "http://localhost:5174"
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_create_note_track, mcp_opendaw_create_hocket


async def main():
    await bridge.start()

    # Create synth track with 2 note tracks (for 2 voices)
    r = await mcp_opendaw_create_synth_track("Hocket", "vaporisateur")
    print(f"Synth: {r[:80]}")
    r = await mcp_opendaw_create_note_track(unit_index=-1)
    print(f"Note track 2: {r[:60]}")

    # 1. Classic alternate hocket — C major scale split between 2 voices
    r = await mcp_opendaw_create_hocket(
        melody="60,62,64,65,67,69,71,72",
        voices=2,
        split_mode="alternate",
        note_duration=0.5,
        start_beat=0,
    )
    print(f"Alternate 2v: {r[:120]}")

    # 2. 3-voice hocket with pairs mode
    r = await mcp_opendaw_create_note_track(unit_index=-1)
    print(f"Note track 3: {r[:60]}")
    r = await mcp_opendaw_create_hocket(
        melody="60,62,64,65,67,65,64,62,60,62,64,65",
        voices=3,
        split_mode="pairs",
        note_duration=0.25,
        start_beat=8,
    )
    print(f"Pairs 3v: {r[:120]}")

    # 3. Phrase hocket — 4-note phrases alternating
    r = await mcp_opendaw_create_hocket(
        melody="60,62,64,65,67,69,71,72,71,69,67,65",
        voices=2,
        split_mode="phrase",
        note_duration=0.5,
        start_beat=20,
    )
    print(f"Phrase 2v: {r[:120]}")

    await bridge.stop()
    print("\nDone! Hocket patterns created.")


if __name__ == "__main__":
    asyncio.run(main())
