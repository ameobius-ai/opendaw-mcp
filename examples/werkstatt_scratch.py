"""Example: scratch DSP effect.

DJ vinyl scratch with turntable physics — triangle LFO back-and-forth,
friction-based inertia, pullback yank, wow/flutter, crackle.

Usage:
    python3 examples/werkstatt_scratch.py
"""
import asyncio
import os
from server import (
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_list_script_params,
)

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_scratch.js")


async def main():
    with open(SCRIPT_PATH) as f:
        code = f.read()

    r = await mcp_opendaw_set_script_device_code(
        device_type="werkstatt", unit_index=0, device_index=0, code=code
    )
    print(r)

    # Aggressive scratch: deep, fast, high friction
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "depth", 0.8)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "rate", 5)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "pullback", 0.5)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "friction", 0.9)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "wow", 0.03)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "flutter", 0.08)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "crackle", 0.3)

    params = await mcp_opendaw_list_script_params("werkstatt", 0, 0)
    print(f"\nScratch params: {params}")


if __name__ == "__main__":
    asyncio.run(main())
