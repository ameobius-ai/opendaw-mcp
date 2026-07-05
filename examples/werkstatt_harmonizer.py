#!/usr/bin/env python3
"""Example: Harmonizer via werkstatt_harmonizer.js DSP script.

A dual-voice harmonizer that creates two pitch-shifted copies of the input
with independent semitone/cent control and micro-detune modulation. Unlike
single-voice pitch_shift, the harmonizer creates choir/harmony effects.

Classic for vocal harmonies, guitar harmonizers (Eventide), synth thickening.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_harmonizer.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_harmonizer.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled harmonizer: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Up an octave + down a fifth: rich harmony stack
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift1_semi", value=12)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift2_semi", value=-7)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift1_gain", value=0.4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift2_gain", value=0.5)
    print("Octave up + fifth down: harmony stack")

    # Diatonic thirds: +3 and -3 semitones
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift1_semi", value=4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift2_semi", value=3)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="detune", value=0.3)
    print("Major third + minor third: diatonic harmony")

    # Subtle thickening: small shifts + heavy detune
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift1_semi", value=0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift1_cent", value=8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift2_semi", value=0)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="shift2_cent", value=-8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="detune", value=0.8)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.3)
    print("Subtle thickening: ±8 cent, heavy detune")

    await bridge.stop()
    print("\nDone! Harmonizer DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
