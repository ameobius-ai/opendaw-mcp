#!/usr/bin/env python3
"""Example: Wavetable synthesizer via apparat_wavetable.js DSP script.

Wavetable synthesis scans through 8 waveforms with optional LFO modulation.
Unison detune adds thickness. Classic for pads, leads, and bass.

Setup:
    cd headless-daw && npx vite --port 5174

Run:
    python examples/apparat_wavetable.py
"""
import asyncio, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("OPENDAW_URL", "http://localhost:5174")
os.environ.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/snap/bin/chromium")

sys.path.insert(0, os.path.join(os.path.dirname(SCRIPT_DIR)))


async def main():
    from server import bridge, mcp_opendaw_create_synth_track, mcp_opendaw_set_script_device_code, mcp_opendaw_set_script_param, mcp_opendaw_list_script_params

    await bridge.start()

    # Create Apparat synth track
    r = await mcp_opendaw_create_synth_track(name="Wavetable Pad", synth_type="apparat")
    print(f"Created Apparat track: {r[:80]}")

    # Load wavetable script
    code = open(os.path.join(os.path.dirname(SCRIPT_DIR), "scripts", "apparat_wavetable.js")).read()
    r = await mcp_opendaw_set_script_device_code(device_type="apparat", unit_index=1, device_index=0, code=code)
    print(f"Compiled wavetable: {r[:80]}")

    # List params
    r = await mcp_opendaw_list_script_params(device_type="apparat", unit_index=1, device_index=0)
    print(f"Params: {r[:120]}")

    # Preset 1: Sweeping pad — scan with slow LFO, 5-voice unison
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="pos", value=0.3)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="pos_lfo_rate", value=0.2)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="pos_lfo_depth", value=0.5)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="unison", value=5)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="detune", value=0.12)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="attack", value=0.5)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="release", value=1.5)
    print("Preset 1: Sweeping pad (0.2Hz LFO, 5-voice unison, slow attack)")

    # Preset 2: Aggressive lead — fixed position, square-ish wave, fast attack
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="pos", value=0.5)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="pos_lfo_depth", value=0.0)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="unison", value=3)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="detune", value=0.08)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="attack", value=0.005)
    await mcp_opendaw_set_script_param(device_type="apparat", unit_index=1, device_index=0, param_label="release", value=0.2)
    print("Preset 2: Aggressive lead (pos=0.5, 3-voice unison, fast attack)")

    await bridge.stop()
    print("\nDone! Wavetable synth loaded and configured.")


if __name__ == "__main__":
    asyncio.run(main())
