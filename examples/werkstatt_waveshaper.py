"""Example: werkstatt_waveshaper — custom-curve distortion.

    python3 examples/werkstatt_waveshaper.py
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
        "scripts", "werkstatt_waveshaper.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Guitar", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"waveshaper loaded: {r[:80]}")

    # Chebyshev curve with high drive — harmonic injection
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "curve", 3)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 1.5)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "harmonics", 0.7)
    print("Chebyshev: drive=1.5, harmonics=0.7")

    # Switch to tanh — warm saturation
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "curve", 0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 0.8)
    print("Tanh: drive=0.8")


if __name__ == "__main__":
    asyncio.run(main())
