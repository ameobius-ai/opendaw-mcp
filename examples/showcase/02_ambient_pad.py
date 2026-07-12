"""
Showcase Demo 2: Ambient soundscape — subtractive synthesis + reverb.

Builds a sustained ambient pad from scratch: detuned oscillators,
slow filter sweep, lush reverb, 8-bar sustain. No genre preset —
manual sound design showing the tool surface.

Usage:
    pip install opendaw-mcp==1.385.0
    python examples/showcase/02_ambient_pad.py

Expected output: WAV file, ~20s evolving ambient texture.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from server import (
    bridge,
    mcp_opendaw_set_bpm,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_note,
    mcp_opendaw_add_effect,
    mcp_opendaw_set_effect_parameter,
    mcp_opendaw_render_full,
)


async def main():
    await bridge.start()
    try:
        await mcp_opendaw_set_bpm(65)

        # Pad track: 3-layer chord (Am9: A C E G B)
        await mcp_opendaw_create_synth_track("Pad")
        chord = [57, 60, 64, 67, 71]
        for pitch in chord:
            await mcp_opendaw_create_note(1, 0, pitch, 0.0, 8.0)

        # Reverb — large space
        await mcp_opendaw_add_effect(1, "Reverb")
        await mcp_opendaw_set_effect_parameter(1, 0, "size", 0.85)
        await mcp_opendaw_set_effect_parameter(1, 0, "decay", 0.7)
        await mcp_opendaw_set_effect_parameter(1, 0, "mix", 0.6)

        # Slow filter sweep on second track
        await mcp_opendaw_create_synth_track("Sweep")
        for pitch in [48, 55]:
            await mcp_opendaw_create_note(2, 0, pitch, 0.0, 8.0)
        await mcp_opendaw_add_effect(2, "Filter")
        await mcp_opendaw_set_effect_parameter(2, 0, "cutoff", 0.3)
        await mcp_opendaw_set_effect_parameter(2, 0, "resonance", 0.4)

        result = await mcp_opendaw_render_full("showcase_ambient.wav", 44100)
        render = json.loads(result)
        print(f"Rendered: {render.get('samples', 0)} samples")
        print(f"Duration: {render.get('samples', 0) / 44100:.1f}s")
        print(f"Max sample: {render.get('max_sample', 0):.4f}")
        print(f"Output: {os.path.abspath('exports/showcase_ambient.wav')}")
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
