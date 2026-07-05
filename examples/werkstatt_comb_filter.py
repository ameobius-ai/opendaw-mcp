#!/usr/bin/env python3
"""Example: Comb filter via werkstatt_comb_filter.js DSP script.

A standalone comb filter using a delay line with feedback. The delay time
is determined by 1/freq, creating characteristic spectral combing (notches
or peaks at harmonic intervals). Positive polarity creates peaks at harmonics,
negative polarity creates notches.

Damping LP in the feedback path controls how quickly high frequencies decay
in the resonant tail. Classic building block of flangers and chorus, but
standalone gives a distinctive filtered/resonant character.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/werkstatt_comb_filter.py
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

    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "werkstatt_comb_filter.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="werkstatt", unit_index=0, device_index=0, code=code)
    print(f"Compiled comb filter: {r[:80]}")

    r = await mcp_opendaw_list_script_params(device_type="werkstatt", unit_index=0, device_index=0)
    print(f"Params: {r[:120]}")

    # Resonant body: low freq, high feedback, moderate damping
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="freq", value=200)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="feedback", value=0.85)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="damping", value=0.4)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.6)
    print("Resonant body: freq 200Hz, feedback 0.85, damping 0.4")

    # Bright combing: high freq, negative feedback (notches)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="freq", value=3000)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="feedback", value=-0.7)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="damping", value=0.2)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="polarity", value=1)
    print("Negative comb: freq 3kHz, feedback -0.7, polarity inverted")

    # Karplus-Strong-ish: plucked string resonance
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="freq", value=110)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="feedback", value=0.95)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="damping", value=0.7)
    await mcp_opendaw_set_script_param(device_type="werkstatt", unit_index=0, device_index=0, param_name="mix", value=0.8)
    print("String resonance: freq 110Hz, feedback 0.95, damping 0.7")

    await bridge.stop()
    print("\nDone! Comb filter DSP loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
