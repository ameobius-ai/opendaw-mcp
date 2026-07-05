#!/usr/bin/env python3
"""Example: Multiband compressor via werkstatt_multiband_comp.js DSP script.

A 3-band multiband compressor with Linkwitz-Riley 4th order crossovers
(24dB/oct). Each band (low/mid/high) has independent threshold, ratio,
attack, release, and makeup gain. Classic mastering tool for controlling
dynamics separately across frequency ranges.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_multiband_comp.py
"""
import asyncio, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.dirname(SCRIPT_DIR))


async def main():
    from server import (bridge, mcp_opendaw_add_effect,
                        mcp_opendaw_set_script_device_code,
                        mcp_opendaw_set_script_param,
                        mcp_opendaw_list_script_params)

    await bridge.start()

    r = await mcp_opendaw_add_effect(unit_index=0, effect_type="Werkstatt")
    print(f"Added Werkstatt: {r[:80]}")

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_multiband_comp.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled multiband comp: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Mastering: tight lows, controlled mids, open highs
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="crossover1", value=120)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="crossover2", value=2500)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="low_threshold", value=0.6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="low_ratio", value=4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="low_attack", value=0.005)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mid_threshold", value=0.5)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mid_ratio", value=3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_threshold", value=0.45)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_ratio", value=2)
    print("Mastering: tight lows (4:1), controlled mids (3:1), gentle highs (2:1)")

    # Glue: gentle compression across all bands
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="low_ratio", value=2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mid_ratio", value=2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_ratio", value=2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="low_release", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mid_release", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_release", value=0.3)
    print("Glue: 2:1 all bands, slow release 0.3s")

    # De-ess: aggressive high band compression
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="crossover2", value=4000)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_threshold", value=0.3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_ratio", value=6)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_attack", value=0.001)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="high_release", value=0.05)
    print("De-ess: crossover 4kHz, high band 6:1, fast attack")

    await bridge.stop()
    print("\nDone! Multiband compressor loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
