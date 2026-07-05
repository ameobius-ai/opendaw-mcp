#!/usr/bin/env python3
"""Example: Pitch vibrato via werkstatt_vibrato.js DSP script.

Vibrato adds pitch modulation to any audio — classic for vocals, guitars,
and synths. Uses a modulated delay line with an LFO.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_vibrato.py
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

    # Load vibrato script
    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_vibrato.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled vibrato: {r[:80]}")

    # List params
    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Set gentle vibrato: 5 Hz, 3ms depth, sine shape
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=5.0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="depth", value=0.003)
    print("Gentle vibrato: 5 Hz, 3ms depth")

    # Now aggressive vibrato: 12 Hz, 15ms depth, triangle shape
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=12.0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="depth", value=0.015)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shape", value=0.8)
    print("Aggressive vibrato: 12 Hz, 15ms depth, triangle shape")

    # Wide stereo spread
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="stereo", value=0.9)
    print("Stereo spread: 0.9 (wide)")

    await bridge.stop()
    print("\nDone! Vibrato DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
