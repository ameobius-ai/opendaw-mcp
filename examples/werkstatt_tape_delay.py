#!/usr/bin/env python3
"""Example: Tape delay via werkstatt_tape_delay.js DSP script.

Tape delay emulates the warm, wobbling character of magnetic tape echo —
wow (slow pitch drift) and flutter (fast pitch wobble) modulate the delay
time, while saturation in the feedback path degrades repeats gracefully.
Classic for dub, guitar, ambient, and lo-fi.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_tape_delay.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_tape_delay.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled tape delay: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Dub style: long time, high feedback, heavy wow, saturated repeats
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="time", value=0.4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="feedback", value=0.75)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="wow", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="flutter", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="saturation", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.4)
    print("Dub: time 0.4, feedback 0.75, wow 0.5, flutter 0.3, sat 0.5")

    # Guitar amp: short slapback, subtle wow, clean
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="time", value=0.1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="feedback", value=0.15)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="wow", value=0.1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="flutter", value=0.1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="saturation", value=0.2)
    print("Slapback: time 0.1, feedback 0.15, wow 0.1, flutter 0.1")

    # Ambient wash: long, max feedback, heavy wow+flutter
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="time", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="feedback", value=0.85)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="wow", value=0.7)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="flutter", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="saturation", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.5)
    print("Ambient wash: time 0.6, feedback 0.85, wow 0.7, flutter 0.6, sat 0.6, mix 0.5")

    await bridge.stop()
    print("\nDone! Tape delay DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
