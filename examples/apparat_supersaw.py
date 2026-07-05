"""Example: apparat_supersaw — JP-8000 style supersaw lead.

    python3 examples/apparat_supersaw.py
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
        "scripts", "apparat_supersaw.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Supersaw Lead", "apparat")
    r = await mcp_opendaw_set_script_device_code("apparat", 1, 0, code)
    print(f"supersaw loaded: {r[:80]}")

    # Wide trance lead — high detune, wide spread
    await mcp_opendaw_set_script_param("apparat", 1, 0, "detune", 0.25)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "spread", 0.8)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "cutoff", 0.85)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "resonance", 0.3)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "attack", 0.01)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "release", 0.5)
    print("Trance lead: detune=0.25, spread=0.8, cutoff=0.85")

    # Tight hardstyle — less detune, darker
    await mcp_opendaw_set_script_param("apparat", 1, 0, "detune", 0.1)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "spread", 0.5)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "cutoff", 0.5)
    await mcp_opendaw_set_script_param("apparat", 1, 0, "resonance", 0.6)
    print("Hardstyle: detune=0.1, cutoff=0.5, resonance=0.6")


if __name__ == "__main__":
    asyncio.run(main())
