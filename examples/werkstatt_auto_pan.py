#!/usr/bin/env python3
"""Example: Auto-pan via werkstatt_auto_pan.js DSP script.

Auto-pan modulates the stereo position of a signal with an LFO, moving it
between left and right channels. Unlike stereowidth (which expands existing
stereo content), auto-pan actively redistributes the signal.

Waveform morph: sine (smooth) → triangle (linear) → square (hard L/R switch).
Classic for guitars, synths, percussion — adds movement and width.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_auto_pan.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_auto_pan.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled auto-pan: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Gentle sine pan: slow, smooth, subtle
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="depth", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shape", value=0)
    print("Gentle sine: rate 0.5 Hz, depth 0.5, sine shape")

    # Fast tremolo pan: 8 Hz, triangle, deep
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="depth", value=0.9)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shape", value=0.5)
    print("Tremolo pan: rate 8 Hz, depth 0.9, triangle")

    # Hard switch: square, 4 Hz, full depth
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="depth", value=1.0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shape", value=1.0)
    print("Hard switch: rate 4 Hz, depth 1.0, square")

    # Offset pan: bias toward right
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="rate", value=1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="depth", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shape", value=0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="offset", value=0.3)
    print("Offset: rate 1 Hz, depth 0.6, sine, offset +0.3 (right-biased)")

    await bridge.stop()
    print("\nDone! Auto-pan DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
