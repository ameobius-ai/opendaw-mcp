#!/usr/bin/env python3
"""Example: Spring reverb via werkstatt_spring_reverb.js DSP script.

Spring reverb emulates the physical characteristics of a spring tank —
dispersive wave propagation, metallic character, and the characteristic
"boing" transient response. Classic for surf rock, dub, guitar amps.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_spring_reverb.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_spring_reverb.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled spring reverb: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Surf rock: long decay, bright, boingy
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="decay", value=0.7)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="tension", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="boing", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.4)
    print("Surf rock: decay 0.7, tension 0.6, boing 0.5, mix 0.4")

    # Dub: dark, long, subtle boing
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="decay", value=0.85)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="damp", value=0.8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="tension", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="boing", value=0.2)
    print("Dub: decay 0.85, damp 0.8, tension 0.3, boing 0.2")

    # Tight amp: short, mid tension, minimal boing
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="decay", value=0.2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="damp", value=0.4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="tension", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="boing", value=0.1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.25)
    print("Tight amp: decay 0.2, damp 0.4, tension 0.5, boing 0.1, mix 0.25")

    await bridge.stop()
    print("\nDone! Spring reverb DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
