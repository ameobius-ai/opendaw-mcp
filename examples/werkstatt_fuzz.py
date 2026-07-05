"""Example: werkstatt_fuzz — hard clipping fuzz (Big Muff Pi style).

    python3 examples/werkstatt_fuzz.py
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
        "scripts", "werkstatt_fuzz.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Fuzz", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"fuzz loaded: {r[:80]}")

    # Big Muff Pi — thick sustain, smooth tone
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "sustain", 0.8)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tone", 0.4)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "octave", 0.0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "level", 0.5)
    print("big muff: thick sustain, warm tone")

    # Octave fuzz — Fuzz Face + octave-up
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "sustain", 0.6)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "octave", 0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tone", 0.6)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bias", 0.1)
    print("octave fuzz: rectified octave-up, slight asymmetry")


if __name__ == "__main__":
    asyncio.run(main())
