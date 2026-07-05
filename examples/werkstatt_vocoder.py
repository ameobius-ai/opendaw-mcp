"""Example: vocoder DSP effect.

Channel vocoder — maps the spectral envelope of a modulator signal
(vocals, drums, any audio) onto a carrier oscillator (saw/square/noise).

Classic robotic voice, synth vocal texture, Daft Punk-style sounds.

Usage:
    python3 examples/werkstatt_vocoder.py
"""
import asyncio
import os
from server import (
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_list_script_params,
)

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_vocoder.js")


async def main():
    with open(SCRIPT_PATH) as f:
        code = f.read()

    # Load vocoder onto first effect slot of track 0
    r = await mcp_opendaw_set_script_device_code(
        device_type="werkstatt", unit_index=0, device_index=0, code=code
    )
    print(r)

    # 24-band vocoder with square wave carrier at A2 (110 Hz)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "bands", 24)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "carrier_wave", 1)    # square
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "carrier_freq", 110)  # A2
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "emphasis", 1.0)      # boost highs
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mod_response", 0.15) # fast response
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "output", 3)          # +3 dB

    params = await mcp_opendaw_list_script_params("werkstatt", 0, 0)
    print(f"\nVocoder params: {params}")


if __name__ == "__main__":
    asyncio.run(main())
