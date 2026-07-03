"""
Example: Filter cutoff automation sweep on a synth.

Creates a synthesizer with a delay effect, then automates the feedback
parameter to create a sweeping effect over 4 bars.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create Vaporisateur
    result = await server.mcp_opendaw_create_synth_track("Synth", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Vaporisateur: unit_index={uid}")

    # 2. List instrument params
    result = await server.mcp_opendaw_list_instrument_params(uid)
    params = json.loads(result)
    print(f"Instrument params: {len(params.get('params', params.get('parameters', [])))} found")

    # 3. Create a note track + region with a sustained chord
    await server.mcp_opendaw_create_note_track(uid)
    await server.mcp_opendaw_create_track_region(uid, 0, 0, 16, "Pad", 200)
    for pitch in [60, 64, 67]:
        await server.mcp_opendaw_create_note(0, pitch, 0, 16, 0.5, uid)
    print("Sustained C major chord across 4 bars")

    # 4. Add a delay effect (effect_index 0)
    await server.mcp_opendaw_add_effect(uid, "Delay")
    print("Delay added")

    # 5. Add automation on delay feedback
    # add_automation(unit_index, effect_index, parameter_name, points)
    # points: JSON array of [position_beats, value_0_to_1] pairs
    # Format: "[[0, 0.1], [4, 0.9], [8, 0.3], [16, 0.1]]"
    points = "[[0, 0.1], [4, 0.9], [8, 0.3], [16, 0.1]]"
    result = await server.mcp_opendaw_add_automation(uid, 0, "feedback", points)
    auto_data = json.loads(result)
    print(f"Automation: {auto_data}")

    print("\nFilter sweep automation created!")
    print("4-bar feedback sweep: 0.1→0.9→0.3→0.1")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
