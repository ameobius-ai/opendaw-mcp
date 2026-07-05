#!/usr/bin/env python3
"""Example: Passacaglia via create_passacaglia orchestration tool.

A passacaglia is a Baroque form where a short bass pattern repeats
throughout while harmonies evolve above it. Bach's BWV 582 is the
canonical example. Modern uses: film scoring, metal, electronic.

3 variation styles: block (sustained chords), arpeggiated (broken),
melodic (stepwise counter-melody from chord tones).

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/create_passacaglia.py
"""
import asyncio, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.dirname(SCRIPT_DIR))


async def main():
    from server import (bridge, mcp_opendaw_create_synth_track,
                        mcp_opendaw_create_passacaglia)

    await bridge.start()

    r = await mcp_opendaw_create_synth_track(name="Passacaglia", synth_type="vaporisateur")
    print(f"Track: {r[:80]}")

    # Baroque block: descending bass, minor chords, block voicing
    r = await mcp_opendaw_create_passacaglia(
        bass_pattern="36 43 41 36",
        bass_rhythm="1 1 1 1",
        bass_repeats=4,
        chord_pattern="Cm,Ab,Eb,Bb",
        variation_style="block",
    )
    print(f"Baroque block: {r[:120]}")

    # Arpeggiated: pedal bass, arpeggiated upper voices
    r = await mcp_opendaw_create_passacaglia(
        bass_pattern="36 36 36 36",
        bass_rhythm="1 1 1 1",
        bass_repeats=4,
        chord_pattern="Dm,Am,Em,Am",
        variation_style="arpeggiated",
        start_beat=16,
    )
    print(f"Arpeggiated: {r[:120]}")

    # Melodic: syncopated bass, stepwise counter-melody
    r = await mcp_opendaw_create_passacaglia(
        bass_pattern="40 43 46 43",
        bass_rhythm="0.5 0.5 1 2",
        bass_repeats=3,
        chord_pattern="Dm,Am,Em",
        variation_style="melodic",
        start_beat=32,
    )
    print(f"Melodic: {r[:120]}")

    # 3/4 waltz passacaglia
    r = await mcp_opendaw_create_passacaglia(
        bass_pattern="36 41 43",
        bass_rhythm="1 1 1",
        bass_repeats=4,
        chord_pattern="Cm,Ab,Eb,Fm",
        beats_per_bar=3,
        variation_style="block",
        start_beat=48,
    )
    print(f"3/4 waltz: {r[:120]}")

    await bridge.stop()
    print("\nDone! Passacaglia created.")


if __name__ == "__main__":
    asyncio.run(main())
