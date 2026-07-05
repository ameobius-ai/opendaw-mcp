"""Example: spectral_gate DSP effect.

Multiband spectral gate — per-band envelope gating for noise reduction
and creative frequency manipulation.

Usage:
    python3 examples/werkstatt_spectral_gate.py
"""
import asyncio
import os
from server import (
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_list_script_params,
)

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_spectral_gate.js")


async def main():
    with open(SCRIPT_PATH) as f:
        code = f.read()

    r = await mcp_opendaw_set_script_device_code(
        device_type="werkstatt", unit_index=0, device_index=0, code=code
    )
    print(r)

    # 12-band spectral gate for noise reduction
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bands", 12)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "threshold", 0.08)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "reduction", 0.9)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tilt", 0.3)  # brighten
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "attack", 0.003)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "release", 0.15)

    params = await mcp_opendaw_list_script_params("werkstatt", 0, 0)
    print(f"\nSpectral gate params: {params}")


if __name__ == "__main__":
    asyncio.run(main())
