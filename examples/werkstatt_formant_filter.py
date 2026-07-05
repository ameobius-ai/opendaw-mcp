#!/usr/bin/env python3
"""Example: Formant filter via werkstatt_formant_filter.js DSP script.

A 3-band parallel formant filter simulating vocal tract resonances.
5 vowel presets (/a/, /i/, /u/, /o/) with smooth interpolation, or
manual F1/F2/F3 frequency control. Biquad bandpass filters in parallel.

Classic for vocoder-like vocal coloring, talk-box effects, and making
any signal (sawtooth, noise, guitar) sound like it's saying vowels.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_formant_filter.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_formant_filter.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled formant filter: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Vowel /a/ (father): bright, open
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="vowel", value=1)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="resonance", value=0.9)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.8)
    print("Vowel /a/: F1=730, F2=1090, F3=2440, resonance 0.9")

    # Vowel /i/ (heed): bright, forward
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="vowel", value=2)
    print("Vowel /i/: F1=270, F2=2290, F3=3010")

    # Vowel /u/ (who): dark, rounded
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="vowel", value=3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="resonance", value=0.95)
    print("Vowel /u/: F1=530, F2=1840, F3=2480, resonance 0.95")

    # Manual formants: custom vocal tract
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="vowel", value=0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="formant_a", value=600)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="formant_b", value=1800)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="formant_c", value=3200)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="bandwidth_a", value=0.08)
    print("Manual: F1=600, F2=1800, F3=3200, BW=0.08")

    await bridge.stop()
    print("\nDone! Formant filter DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
