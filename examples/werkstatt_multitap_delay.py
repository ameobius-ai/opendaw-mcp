"""Example: werkstatt_multitap_delay — 4-tap delay with stereo spread.

    python3 examples/werkstatt_multitap_delay.py
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
        "scripts", "werkstatt_multitap_delay.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Delay", "vaporisateur")
    await mcp_opendaw_add_effect(0, "werkstatt")
    r = await mcp_opendaw_set_script_device_code("werkstatt", 0, 0, code)
    print(f"multitap delay loaded: {r[:80]}")

    # U2-style dotted-eighth + quarter layering
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap1_time", 0.375)  # dotted 8th
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap2_time", 0.5)    # quarter
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap3_time", 0.75)   # dotted quarter
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap4_time", 1.0)    # whole
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap1_pan", -0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap2_pan", 0.7)
    await mcp_opendaw_set_script_param("werkstatt", 0, 0, "tap1_fb", 0.4)
    print("U2-style: dotted-8th L, quarter R, dotted-quarter, whole")


if __name__ == "__main__":
    asyncio.run(main())
