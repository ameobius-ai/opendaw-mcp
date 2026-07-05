"""Example: spielwerk_harmonizer — generate harmony voices from MIDI input.

    python3 examples/spielwerk_harmonizer.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_add_effect,
        mcp_opendaw_set_script_device_code,
        mcp_opendaw_set_script_param,
    )

    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", "spielwerk_harmonizer.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Lead", "vaporisateur")
    await mcp_opendaw_add_effect(0, "spielwerk")
    r = await mcp_opendaw_set_script_device_code("spielwerk", 0, 0, code)
    print(f"harmonizer loaded: {r[:80]}")

    # Classic 3-part harmony: +fifth, +octave, unison off
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "interval1", 7)   # fifth
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "interval2", 12)  # octave
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "interval3", 0)   # off
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "vel1", 0.8)
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "vel2", 0.6)
    print("fixed harmony: +5th @0.8 vel, +oct @0.6 vel")

    # Diatonic mode — intervals become scale degrees
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "mode", 1)
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "key_root", 0)   # C
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "scale", 0)      # major
    print("diatonic mode: C major, scale-aware harmonization")


if __name__ == "__main__":
    asyncio.run(main())
