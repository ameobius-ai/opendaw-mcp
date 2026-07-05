"""Example: spielwerk_prob_gate — subtractive probability gate.

    python3 examples/spielwerk_prob_gate.py
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
        "scripts", "spielwerk_prob_gate.js"
    )
    with open(script_path) as f:
        code = f.read()

    await mcp_opendaw_create_synth_track("ProbGate", "vaporisateur")
    await mcp_opendaw_add_effect(0, "spielwerk")
    r = await mcp_opendaw_set_script_device_code("spielwerk", 0, 0, code)
    print(f"prob_gate loaded: {r[:80]}")

    # Generative ambient — 50% chance, position-based (downbeats more likely)
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "chance", 0.5)
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "mode", 1)       # position-based
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "variation", 0.3)
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "hold", 0.4)     # momentum
    await mcp_opendaw_set_script_param("spielwerk", 0, 0, "seed", 123)
    print("generative ambient: 50% chance, downbeat-weighted, momentum")


if __name__ == "__main__":
    asyncio.run(main())
