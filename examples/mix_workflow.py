"""
Example: Full mixing workflow.

Demonstrates:
- Setting track volumes
- Adding effects (Compressor, Maximizer)
- Creating send/return routing with parallel FX bus
- Setting effect parameters for a cohesive mix

Assumes project already has 2 AUs (synth + drums), e.g. after running
create_chord_progression.py + create_beat.py in sequence.
"""

import asyncio
import json
import server


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Get full project state to identify AUs
    result = await server.mcp_opendaw_get_full_project_state()
    state = json.loads(result)
    aus = state.get("audio_units", [])
    print(f"Found {len(aus)} audio units")

    # Identify synth and drum AUs by label
    synth_uid = None
    drum_uid = None
    for au in aus:
        label = au.get("label", "").lower()
        idx = au.get("index")
        if au.get("type") == "instrument":
            if "drum" in label or "play" in label:
                drum_uid = idx
            else:
                synth_uid = idx

    if synth_uid is None:
        synth_uid = 1
    if drum_uid is None:
        drum_uid = 2 if len(aus) > 2 else 1

    print(f"Synth AU={synth_uid}, Drum AU={drum_uid}")

    # 2. Set volumes — volume_db as string
    await server.mcp_opendaw_set_track_volume(synth_uid, "-6")
    print("Synth vol -6dB")

    await server.mcp_opendaw_set_track_volume(drum_uid, "-3")
    print("Drums vol -3dB")

    # 3. Add compressor on drums for punch
    # add_effect(unit_index, effect_type)
    await server.mcp_opendaw_add_effect(drum_uid, "Compressor")
    print("Compressor on drums")

    # set_effect_parameter(unit_index, effect_index, parameter_name, value)
    await server.mcp_opendaw_set_effect_parameter(drum_uid, 0, "ratio", 4.0)
    await server.mcp_opendaw_set_effect_parameter(drum_uid, 0, "attack", 0.01)
    await server.mcp_opendaw_set_effect_parameter(drum_uid, 0, "release", 0.1)
    await server.mcp_opendaw_set_effect_parameter(drum_uid, 0, "threshold", -18.0)
    print("Compressor: 4:1, -18dB threshold, 10ms attack")

    # 4. Add Maximizer on synth
    await server.mcp_opendaw_add_effect(synth_uid, "Maximizer")
    print("Maximizer on synth")

    # 5. Create a parallel reverb send from synth
    # create_send(src_unit, name, send_level_db, routing)
    # Creates a NEW FX bus + AudioUnit, returns fx_unit_index
    result = await server.mcp_opendaw_create_send(str(synth_uid), "Reverb Bus", "-6", "post")
    send_data = json.loads(result)
    print(f"Reverb send from synth: {send_data}")
    fx_unit = send_data.get("fx_unit_index")

    # Add reverb on the FX bus unit
    if fx_unit is not None:
        await server.mcp_opendaw_add_effect(fx_unit, "Reverb")
        print(f"Reverb added on FX bus unit {fx_unit}")

    # 6. Create a parallel delay send from drums
    result = await server.mcp_opendaw_create_send(str(drum_uid), "Delay Bus", "-9", "post")
    delay_send = json.loads(result)
    print(f"Delay send from drums: {delay_send}")
    delay_fx = delay_send.get("fx_unit_index")

    if delay_fx is not None:
        await server.mcp_opendaw_add_effect(delay_fx, "Delay")
        await server.mcp_opendaw_set_effect_parameter(delay_fx, 0, "time", 0.75)
        await server.mcp_opendaw_set_effect_parameter(delay_fx, 0, "feedback", 0.3)
        print(f"Delay added on FX bus unit {delay_fx}: time=0.75, feedback=0.3")

    print("\nMix workflow complete!")
    print("Synth -6dB + Maximizer | Drums -3dB + Compressor")
    print("Parallel sends: synth→reverb, drums→delay")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
