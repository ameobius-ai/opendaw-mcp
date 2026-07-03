"""
Example: Full mixing workflow.

Demonstrates:
- Setting track volumes
- Adding effects (EQ, Compressor, Reverb)
- Creating send/return routing
- Setting effect parameters for a cohesive mix
"""

import asyncio
import json
import server

async def main():
    await server.bridge.start()
    print("Bridge started")

    # Assume project has 2 AUs: synth (0) and drums (1)
    # This example just sets up mixing on an existing project

    # 1. Get mixer state to see what we have
    result = await server.mcp_opendaw_get_mixer_state()
    state = json.loads(result)
    print(f"Mixer state: {state}")

    # 2. Set volumes
    # Synth at -6 dB, drums at -3 dB
    result = await server.mcp_opendaw_set_track_volume(0, -6.0)
    print(f"Synth vol -6dB: {json.loads(result).get('success', '')}")

    result = await server.mcp_opendaw_set_track_volume(1, -3.0)
    print(f"Drums vol -3dB: {json.loads(result).get('success', '')}")

    # 3. Add compressor on drums for punch
    result = await server.mcp_opendaw_add_effect(1, "Compressor")
    comp_data = json.loads(result)
    print(f"Compressor on drums: {comp_data}")
    comp_idx = comp_data.get("effect_index", 0)

    # Set compression: 4:1 ratio, medium attack, auto gain
    await server.mcp_opendaw_set_effect_parameter(1, comp_idx, "ratio", 4.0)
    await server.mcp_opendaw_set_effect_parameter(1, comp_idx, "attack", 0.01)
    await server.mcp_opendaw_set_effect_parameter(1, comp_idx, "release", 0.1)
    await server.mcp_opendaw_set_effect_parameter(1, comp_idx, "threshold", -18.0)
    print("Compressor: 4:1, -18dB threshold, 10ms attack")

    # 4. Add EQ on synth to cut lows
    result = await server.mcp_opendaw_add_effect(0, "Maximizer")
    print(f"Maximizer on synth: {json.loads(result)}")

    # 5. Create a reverb bus and send from both tracks
    result = await server.mcp_opendaw_create_audio_bus()
    bus_data = json.loads(result)
    print(f"Reverb bus: {bus_data}")

    # Add reverb on the bus
    bus_idx = bus_data.get("bus_index", 0)
    result = await server.mcp_opendaw_add_effect(bus_idx, "Reverb")
    print(f"Reverb on bus: {json.loads(result)}")

    # Create sends from synth and drums to reverb bus
    result = await server.mcp_opendaw_create_send(0, bus_idx, 0.2)
    print(f"Send synth→reverb: {json.loads(result)}")

    result = await server.mcp_opendaw_create_send(1, bus_idx, 0.15)
    print(f"Send drums→reverb: {json.loads(result)}")

    print("\nMix workflow complete!")
    print("Synth -6dB + Maximizer | Drums -3dB + Compressor | Shared reverb bus")

    await server.bridge.stop()

if __name__ == "__main__":
    asyncio.run(main())
