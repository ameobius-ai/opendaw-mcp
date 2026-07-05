"""Example: werkstatt_tape_stop — exponential tape stop effect.

    python3 examples/werkstatt_tape_stop.py
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
        "scripts", "werkstatt_tape_stop.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("TapeStop", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"tape_stop loaded: {r[:80]}")

    # Classic trap intro — slow stop over 1 second
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "stop_time", 1.0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "curve", 2)       # classic tape curve
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "trigger", 1)     # trigger the stop
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "wow", 0.01)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "flutter", 0.005)
    print("trap intro: 1s tape stop, classic curve")

    # DJ Screw — very slow stop, heavy wow
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "stop_time", 3.0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "curve", 1.5)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "wow", 0.03)
    print("DJ Screw: 3s slow stop, heavy wow")


if __name__ == "__main__":
    asyncio.run(main())
