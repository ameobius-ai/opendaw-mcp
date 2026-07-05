#!/usr/bin/env python3
"""Example: Bitcrusher via werkstatt_bitcrusher.js DSP script.

Bitcrusher reduces bit depth and sample rate for lo-fi, chiptune,
and industrial textures. Dedicated bitcrusher separate from coldfold's
combined wavefold+crush.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_bitcrusher.py
"""
import asyncio, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(SCRIPT_DIR)))


async def main():
    from server import bridge, mcp_opendaw_add_effect, mcp_opendaw_set_script_device_code, mcp_opendaw_set_script_param, mcp_opendaw_list_script_params

    await bridge.start()

    # Add Werkstatt effect on unit 0
    r = await mcp_opendaw_add_effect(unit_index=0, effect_type="Werkstatt")
    print(f"Added Werkstatt: {r[:80]}")

    # Load bitcrusher script
    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_bitcrusher.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled bitcrusher: {r[:80]}")

    # List params
    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Lo-fi: 8-bit, slight rate reduction
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bits", value=8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.7)
    print("Lo-fi: 8-bit, 30% rate reduction, 70% wet")

    # Chiptune: 4-bit, heavy rate reduction
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bits", value=4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="drive", value=1.2)
    print("Chiptune: 4-bit, 60% rate reduction, drive 1.2")

    # Extreme: 1-bit, max rate reduction
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bits", value=1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=0.9)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=1.0)
    print("Extreme: 1-bit, 90% rate reduction, 100% wet")

    await bridge.stop()
    print("\nDone! Bitcrusher DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
