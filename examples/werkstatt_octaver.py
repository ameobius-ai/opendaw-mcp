"""Example: werkstatt_octaver — sub-octave generator (Boss OC-2 style).

    python3 examples/werkstatt_octaver.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from server import (
        mcp_opendaw_create_synth_track,
        mcp_opendaw_add_effect,
        mcp_opendaw_set_script_device_code,
        mcp_opendaw_set_script_param,
    )

    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", "werkstatt_octaver.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Bass", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"octaver loaded: {r[:80]}")

    # Classic bass octaver — -1 octave with envelope tracking
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "oct1", 0.8)     # -1 octave level
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "oct2", 0.0)     # -2 octave off
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "direct", 0.3)   # some dry signal
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "smooth", 0.3)   # moderate edge smoothing
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "track", 0.6)    # medium envelope tracking
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "trigger", 0.01) # zero-crossing hysteresis
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "output", 0)     # 0 dB
    print("bass octaver: -1 octave, envelope tracked, smooth square waves")


if __name__ == "__main__":
    asyncio.run(main())
