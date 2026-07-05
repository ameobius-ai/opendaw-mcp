"""Example: werkstatt_dimension_chorus — Roland Dimension D-style stereo widener.

    python3 examples/werkstatt_dimension_chorus.py
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
        "scripts", "werkstatt_dimension_chorus.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Pad", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"dimension chorus loaded: {r[:80]}")

    # Dimension D classic — slightly detuned L/R rates, triangle wave
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "rate_l", 0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "rate_r", 1.1)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "depth", 0.35)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "width", 0.8)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "brightness", 0.6)
    print("Dimension D: detuned L/R, triangle LFO, no feedback, wide stereo")


if __name__ == "__main__":
    asyncio.run(main())
