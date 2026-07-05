"""Example: werkstatt_rotary_speaker — Leslie rotary speaker.

    python3 examples/werkstatt_rotary_speaker.py
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
        "scripts", "werkstatt_rotary_speaker.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Organ", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"rotary loaded: {r[:80]}")

    # Fast speed — classic Leslie fast mode
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "speed", 1.0)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "depth", 0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "acceleration", 0.5)
    print("Fast: speed=1.0, depth=0.7, accel=0.5")

    # Slow speed — chorale mode
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "speed", 0.0)
    print("Slow: speed=0.0 (chorale)")


if __name__ == "__main__":
    asyncio.run(main())
