#!/usr/bin/env python3
"""Example: Tube saturator via werkstatt_tube_saturator.js DSP script.

Tube saturation emulates the warm, harmonically rich character of valve
electronics — even harmonic dominance from asymmetrical transfer, smooth
soft-clip, and post-saturation tone control. Distinct from tape (darksat)
and soft-clip (overdrive). Classic for warming up digital mixes, vocals,
bass, and guitars.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_tube_saturator.py
"""
import asyncio, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(SCRIPT_DIR)))


async def main():
    from server import bridge, mcp_opendaw_add_effect, mcp_opendaw_set_script_device_code, mcp_opendaw_set_script_param, mcp_opendaw_list_script_params

    await bridge.start()

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type="Werkstatt")
    print(f"Added Werkstatt: {r[:80]}")

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_tube_saturator.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled tube saturator: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Gentle warmth: low drive, high warmth, dark tone
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="drive", value=0.2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="warmth", value=0.7)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bias", value=0.2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="tone", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.6)
    print("Gentle warmth: drive 0.2, warmth 0.7, bias 0.2, tone 0.3")

    # Aggressive crunch: high drive, low warmth, bright
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="drive", value=0.8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="warmth", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bias", value=-0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="tone", value=0.7)
    print("Aggressive crunch: drive 0.8, warmth 0.3, bias -0.3, tone 0.7")

    # Vintage vocal: subtle, warm, full mix
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="drive", value=0.15)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="warmth", value=0.85)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bias", value=0.35)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="tone", value=0.4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.5)
    print("Vintage vocal: drive 0.15, warmth 0.85, bias 0.35, tone 0.4, mix 0.5")

    await bridge.stop()
    print("\nDone! Tube saturator DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
