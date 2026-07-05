"""Example: werkstatt_dynamic_eq — surgical de-essing and resonance control.

    python3 examples/werkstatt_dynamic_eq.py
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
        "scripts", "werkstatt_dynamic_eq.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Vocal", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"dynamic eq loaded: {r[:80]}")

    # De-essing: band 3 at 7kHz, threshold 0.05, range 10 dB
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band3_freq", 7000)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band3_threshold", 0.05)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band3_range", 10)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band3_q", 3)
    print("De-essing: 7kHz, threshold=0.05, range=10dB")

    # Resonance control: band 1 at 200Hz, gentle
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_freq", 200)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_threshold", 0.08)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "band1_range", 6)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "attack", 0.01)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "release", 0.15)
    print("Resonance control: 200Hz, threshold=0.08, range=6dB")


if __name__ == "__main__":
    asyncio.run(main())
