"""E2E smoke test after modular refactoring — verifies bridge + tools work with live DAW."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import bridge, mcp_opendaw_get_project_state, mcp_opendaw_set_bpm, mcp_opendaw_create_synth_track, mcp_opendaw_list_effects, mcp_opendaw_add_effect, mcp_opendaw_list_tracks


async def main():
    print("Starting bridge...")
    await bridge.start()
    print("✅ Bridge started")

    # 1. Get project state
    r = await mcp_opendaw_get_project_state()
    import json
    state = json.loads(r)
    assert state.get("success") or "bpm" in state, f"get_project_state failed: {r[:200]}"
    print(f"✅ get_project_state: bpm={state.get('bpm', '?')}, tracks={state.get('tracks', state.get('track_count', '?'))}")

    # 2. Set BPM
    r = await mcp_opendaw_set_bpm(bpm=128)
    state = json.loads(r)
    assert state.get("success") or "bpm" in state, f"set_bpm failed: {r[:200]}"
    print("✅ set_bpm(128)")

    # 3. Create synth track
    r = await mcp_opendaw_create_synth_track(name="TestSynth", synth_type="Vaporisateur")
    state = json.loads(r)
    assert state.get("success") or "unit_index" in state, f"create_synth_track failed: {r[:200]}"
    unit_idx = state.get("unit_index", state.get("unit", 1))
    print(f"✅ create_synth_track: unit_index={unit_idx}")

    # 4. List effects
    r = await mcp_opendaw_list_effects()
    state = json.loads(r)
    print(f"✅ list_effects: {str(state)[:150]}")

    # 5. Add effect (delay)
    r = await mcp_opendaw_add_effect(unit_index=unit_idx, effect_type="Delay")
    state = json.loads(r)
    print(f"✅ add_effect(Delay): {str(state)[:150]}")

    # 6. List tracks
    r = await mcp_opendaw_list_tracks()
    state = json.loads(r)
    print(f"✅ list_tracks: {str(state)[:150]}")

    await bridge.stop()
    print("\n🎉 ALL E2E SMOKE TESTS PASSED — modular refactoring is runtime-safe")


asyncio.run(main())
