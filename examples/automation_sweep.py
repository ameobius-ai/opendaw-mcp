"""
Example: Filter cutoff automation sweep on a synth.

Creates a synthesizer with a filter, then automates the cutoff
frequency to create a sweeping effect over 4 bars.
"""

import asyncio
import json
import server

PPQN = 960

async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create Vaporisateur
    await server.mcp_opendaw_create_synth("Vaporisateur")
    print("Vaporisateur created")

    # 2. Create an automation track for the filter cutoff
    # First, find the parameter name we want to automate
    result = await server.mcp_opendaw_list_instrument_params(0)
    params = json.loads(result)
    print(f"Instrument params: {params}")

    # 3. Create automation track (targeting cutoff parameter)
    result = await server.mcp_opendaw_create_automation_track(0, "cutoff")
    data = json.loads(result)
    print(f"Automation track: {data}")
    auto_track = data.get("track_index", 0)

    # 4. Create a 4-bar automation region
    bar = 4 * PPQN
    result = await server.mcp_opendaw_create_value_region(0, auto_track, 0, 0, bar * 4)
    print(f"Automation region: {json.loads(result)}")

    # 5. Add automation events — low to high sweep
    # Start at 0.1 (low cutoff), sweep to 0.9 (high), then back to 0.3
    events = [
        (0, 0.1),           # bar 0: closed filter
        (bar * 2, 0.9),     # bar 2: open filter
        (bar * 3, 0.3),     # bar 3: partially closed
        (bar * 4, 0.1),     # bar 4: closed again
    ]

    for pos, value in events:
        result = await server.mcp_opendaw_create_automation_event(
            0, auto_track, 0,
            position=pos, value=value, interpolation="linear"
        )
        print(f"  Automation at {pos//PPQN} beats: {value} → {json.loads(result).get('success', '')}")

    print("\nFilter sweep automation created!")
    print("4-bar sweep: low → high → medium → low")

    await server.bridge.stop()

if __name__ == "__main__":
    asyncio.run(main())
