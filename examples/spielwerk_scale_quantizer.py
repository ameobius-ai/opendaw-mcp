"""Example: spielwerk_scale_quantizer — force notes into scale.

    python3 examples/spielwerk_scale_quantizer.py
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
        "scripts", "spielwerk_scale_quantizer.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("Lead", "vaporisateur")
    # Spielwerk is a MIDI effect — add to midiEffects chain
    await mcp_opendaw_add_effect(0, "spielwerk")
    r = await mcp_opendaw_set_script_device_code("spielwerk", 0, 0, code)
    print(f"scale quantizer loaded: {r[:80]}")

    # C minor — snap all incoming notes to natural minor
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "scale", 1)  # minor
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "root", 0)   # C
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "direction", 0)  # nearest
    print("C minor: scale=1 (minor), root=0 (C), direction=nearest")

    # D dorian — classic jazz/modal mode
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "scale", 2)  # dorian
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "root", 2)   # D
    print("D dorian: scale=2 (dorian), root=2 (D)")


if __name__ == "__main__":
    asyncio.run(main())
