#!/usr/bin/env python3
"""E2E test for openDAW MCP server — 25 steps, full pipeline.
Copy to /tmp/e2e_test.py and run:
  cd /home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp
  source venv/bin/activate
  PYTHONPATH=. python3 /tmp/e2e_test.py
"""
import asyncio, logging, json
logging.basicConfig(level=logging.INFO)
import server

async def e2e():
    await server.bridge.start()
    p = []
    def c(name, r):
        ok = isinstance(r, dict) and not r.get("error") if isinstance(r, dict) else True
        p.append((name, ok, str(r)[:80]))

    # Setup: synth + effects
    c("create_synth", json.loads(await server.mcp_opendaw_create_synth_track(name="Lead", synth_type="vaporisateur")))
    c("add_delay", json.loads(await server.mcp_opendaw_add_effect(unit_index=1, effect_type="Delay")))
    c("add_reverb", json.loads(await server.mcp_opendaw_add_effect(unit_index=1, effect_type="Reverb")))

    # Notes (C major chord: C4=60, E4=64, G4=67)
    c("create_note_C", json.loads(await server.mcp_opendaw_create_note(track_index=0, pitch=60, start_beat=0, duration_beats=1, velocity=100, unit_index=1)))
    c("create_note_E", json.loads(await server.mcp_opendaw_create_note(track_index=0, pitch=64, start_beat=1, duration_beats=1, velocity=90, unit_index=1)))
    c("create_note_G", json.loads(await server.mcp_opendaw_create_note(track_index=0, pitch=67, start_beat=2, duration_beats=2, velocity=80, unit_index=1)))

    # Note operations
    c("list_notes", json.loads(await server.mcp_opendaw_list_notes(unit_index=1, track_index=0, region_index=0)))
    c("transpose", json.loads(await server.mcp_opendaw_transpose_notes(unit_index=1, track_index=0, semitones="12")))
    c("quantize", json.loads(await server.mcp_opendaw_quantize_notes(division="0.25", unit_index=1, track_index=0, strength="1.0")))

    # Effects
    c("list_params", json.loads(await server.mcp_opendaw_list_effect_parameters(unit_index=1, effect_index=0)))
    c("set_param", json.loads(await server.mcp_opendaw_set_effect_parameter(unit_index=1, effect_index=0, parameter_name="feedback", value=0.5)))
    c("move_effect", json.loads(await server.mcp_opendaw_move_effect(unit_index=1, from_index="0", to_index="1")))
    c("set_effect_enabled", json.loads(await server.mcp_opendaw_set_effect_enabled(unit_index=1, effect_index=0, enabled=False)))

    # Transport
    c("set_bpm", json.loads(await server.mcp_opendaw_set_bpm(bpm=128)))
    c("transport_play", json.loads(await server.mcp_opendaw_transport(action="play")))
    c("transport_stop", json.loads(await server.mcp_opendaw_transport(action="stop")))

    # Mix
    c("set_vol", json.loads(await server.mcp_opendaw_set_track_volume(unit_index=1, volume_db="-3.0")))
    c("set_pan", json.loads(await server.mcp_opendaw_set_track_panning(unit_index=1, panning="0.3")))
    c("rename", json.loads(await server.mcp_opendaw_rename_unit(unit_index=1, name="MyLead", icon="Piano")))

    # Markers & groove
    c("add_marker", json.loads(await server.mcp_opendaw_add_marker(position_beats=0, label="Verse")))
    c("groove", json.loads(await server.mcp_opendaw_set_groove_shuffle(amount=20)))

    # Undo/redo
    c("undo", json.loads(await server.mcp_opendaw_undo()))
    c("redo", json.loads(await server.mcp_opendaw_redo()))

    # Save
    c("save", json.loads(await server.mcp_opendaw_save_project(filename="e2e_test")))
    c("project_info", json.loads(await server.mcp_opendaw_get_project_info()))

    await server.bridge.stop()
    passed = sum(1 for _, ok, _ in p if ok)
    for name, ok, detail in p:
        status = "PASS" if ok else "FAIL"
        print(f"{status} {name}: {detail}")
    print(f"\n{passed}/{len(p)} passed")
    print("=== DONE ===")

asyncio.run(e2e())
