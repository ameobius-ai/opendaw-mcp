"""Example: werkstatt_moog_ladder — Moog ladder filter.

    python3 examples/werkstatt_moog_ladder.py
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
        "scripts", "werkstatt_moog_ladder.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Acid", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"moog loaded: {r[:80]}")

    # Acid bass — high resonance, low cutoff
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "cutoff", 400)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "resonance", 0.85)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "drive", 0.3)
    print("Acid: cutoff=400, res=0.85, drive=0.3")

    # Warm LP — moderate resonance with warmth
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "cutoff", 1200)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "resonance", 0.4)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "warmth", 0.5)
    print("Warm: cutoff=1200, res=0.4, warmth=0.5")


if __name__ == "__main__":
    asyncio.run(main())
