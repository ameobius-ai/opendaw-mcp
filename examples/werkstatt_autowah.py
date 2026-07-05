"""Example: werkstatt_autowah — envelope-followed filter (Mu-Tron III style).

    python3 examples/werkstatt_autowah.py
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
        "scripts", "werkstatt_autowah.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Funk", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"autowah loaded: {r[:80]}")

    # Classic funk autowah — bandpass mode, fast attack
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mode", 0)      # bandpass
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "base_freq", 300)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "sweep_range", 2000)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "sensitivity", 0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "attack", 0.003)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "release", 0.06)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "resonance", 6)
    print("funk autowah: bandpass, fast attack, wide sweep")


if __name__ == "__main__":
    asyncio.run(main())
