"""Example: reverse DSP effect.

Real-time reverse playback with chunked circular buffer.
Variable speed, trigger modes, stereo modes, feedback.

Usage:
    python3 examples/werkstatt_reverse.py
"""
import asyncio
import os
from server import (
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_list_script_params,
)

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_reverse.js")


async def main():
    with open(SCRIPT_PATH) as f:
        code = f.read()

    r = await mcp_opendaw_set_script_device_code(
        device_type="werkstatt", unit_index=0, device_index=0, code=code
    )
    print(r)

    # 2-second chunks, double speed reverse, ping-pong stereo
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "chunk_size", 2.0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "speed", 2.0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "stereo_mode", 1)  # ping-pong
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "smooth", 0.02)   # 20ms crossfade
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "feedback", 0.3)  # layered reverse
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mix", 0.8)

    params = await mcp_opendaw_list_script_params("werkstatt", 0, 0)
    print(f"\nReverse params: {params}")


if __name__ == "__main__":
    asyncio.run(main())
