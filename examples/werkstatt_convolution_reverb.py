"""Example: werkstatt_convolution_reverb — realistic room ambience via convolution.

    python3 examples/werkstatt_convolution_reverb.py
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
        "scripts", "werkstatt_convolution_reverb.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Keys", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"convolution reverb loaded: {r[:80]}")

    # Large hall — long decay, dark damping
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "room_size", 0.85)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "decay", 0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "damping", 0.35)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "predelay", 0.04)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "early_late", 0.4)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "width", 0.8)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mix", 0.4)
    print("Large hall: room=0.85, decay=0.7, mix=0.4")

    # Tight drum room — short decay, more early reflections
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "room_size", 0.3)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "decay", 0.2)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "early_late", 0.8)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "mix", 0.25)
    print("Drum room: room=0.3, decay=0.2, early_late=0.8")


if __name__ == "__main__":
    asyncio.run(main())
