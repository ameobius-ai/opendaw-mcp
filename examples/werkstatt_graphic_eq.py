#!/usr/bin/env python3
"""Example: Graphic EQ via werkstatt_graphic_eq.js DSP script.

A 10-band graphic EQ with ISO frequency centers (32, 64, 125, 250, 500,
1k, 2k, 4k, 8k, 16k Hz), each with ±12 dB gain. Classic rack-mount EQ
for tone shaping, mixing corrective EQ, and live sound.

Unlike parametric EQ (movable bands with Q control), graphic EQ uses
fixed frequency bands — simpler, faster, predictable.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_graphic_eq.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_graphic_eq.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled graphic EQ: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Mix bus: cut lows, slight presence boost, air on top
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_32", value=-4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_64", value=-2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_250", value=-1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_2k", value=2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_8k", value=3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_16k", value=4)
    print("Mix bus: cut 32/64 Hz, presence +2k, air +8k/+16k")

    # Old school: smile curve — boosted lows and highs, scooped mids
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_32", value=5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_125", value=3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_500", value=-3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_1k", value=-4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_4k", value=-2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_16k", value=6)
    print("Smile curve: lows +, mids −, highs +")

    # Vocal clarity: remove mud, add presence
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_250", value=-5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_500", value=-3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_4k", value=4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="band_8k", value=2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="master", value=-2)
    print("Vocal clarity: cut 250/500 Hz mud, +4k presence, master −2dB")

    await bridge.stop()
    print("\nDone! Graphic EQ loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
