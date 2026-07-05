"""Example: looper DSP effect.

Live looper with overdub — record, playback, layer new audio on top.
Variable speed, reverse mode, crossfade at loop boundaries.

Usage:
    python3 examples/werkstatt_looper.py
"""
import asyncio
import os
from server import (
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_list_script_params,
)

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_looper.js")


async def main():
    with open(SCRIPT_PATH) as f:
        code = f.read()

    r = await mcp_opendaw_set_script_device_code(
        device_type="werkstatt", unit_index=0, device_index=0, code=code
    )
    print(r)

    # 4-second loop, high feedback for layering, auto mode
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "loop_length", 4)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "feedback", 0.9)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "overdub", 1)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "play_mode", 0)  # auto
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "monitor", 0.3)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "fade_edges", 0.02)

    params = await mcp_opendaw_list_script_params("werkstatt", 0, 0)
    print(f"\nLooper params: {params}")


if __name__ == "__main__":
    asyncio.run(main())
