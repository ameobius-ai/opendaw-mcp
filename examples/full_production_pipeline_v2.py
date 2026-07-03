"""Full production pipeline — agent creates a complete track from scratch.

Demonstrates the full openDAW MCP workflow:
1. Create a bass synth (Apparat SubCrusher) with notes
2. Create a lead synth (Vaporisateur) with notes
3. Add a MIDI arpeggiator (Spielwerk) on the lead
4. Add tape saturation (Werkstatt DarkSat) on the bass
5. Add delay on the lead
6. Set up send/return routing for reverb
7. Render to WAV

Usage:
    source venv/bin/activate
    python examples/full_production_pipeline_v2.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    bridge,
    mcp_opendaw_get_project_state,
    mcp_opendaw_create_synth_track,
    mcp_opendaw_create_note_track,
    mcp_opendaw_create_track_region,
    mcp_opendaw_create_note,
    mcp_opendaw_list_notes,
    mcp_opendaw_add_effect,
    mcp_opendaw_add_midi_effect,
    mcp_opendaw_set_effect_parameter,
    mcp_opendaw_set_script_device_code,
    mcp_opendaw_set_script_param,
    mcp_opendaw_list_script_params,
    mcp_opendaw_set_bpm,
    mcp_opendaw_render_full,
)

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")


def load_script(name: str) -> str:
    with open(os.path.join(SCRIPTS_DIR, name)) as f:
        return f.read()


async def main():
    print("=" * 60)
    print("Full Production Pipeline v2")
    print("=" * 60)

    await bridge.start()
    print("\nBridge ready\n")

    # ─── 1. Project setup ────────────────────────────────────
    state = json.loads(await mcp_opendaw_get_project_state())
    print(f"Initial: {state.get('track_count', 0)} tracks, BPM={state.get('bpm', 120)}")

    await mcp_opendaw_set_bpm(128)
    print("BPM set to 128")

    # ─── 2. Bass — Apparat SubCrusher ────────────────────────
    print("\n── Bass: Apparat SubCrusher ──")
    r = await mcp_opendaw_create_synth_track("SubBass", "apparat")
    bass_au = json.loads(r)["unit_index"]
    print(f"  Created AU {bass_au} (Apparat)")

    code = load_script("apparat_subcrusher.js")
    r = await mcp_opendaw_set_script_device_code("apparat", bass_au, 0, code)
    d = json.loads(r)
    print(f"  Code loaded: {d['code_length']} bytes, {d['params_created']} params")

    # Tune for 128 BPM techno bass
    await mcp_opendaw_set_script_param("apparat", bass_au, 0, "cutoff", 600)
    await mcp_opendaw_set_script_param("apparat", bass_au, 0, "resonance", 0.8)
    await mcp_opendaw_set_script_param("apparat", bass_au, 0, "drive", 0.5)
    await mcp_opendaw_set_script_param("apparat", bass_au, 0, "sub", 0.7)
    await mcp_opendaw_set_script_param("apparat", bass_au, 0, "release", 0.08)
    print("  Params: cutoff=600, reso=0.8, drive=0.5, sub=0.7, rel=0.08")

    # Note track + bassline
    await mcp_opendaw_create_note_track(bass_au)
    await mcp_opendaw_create_track_region(bass_au, 0, 0, 16, "bassline", -1)

    bass_pattern = [
        # A1(33) eighth notes with gaps
        (0, 33, 0.5), (0.5, 33, 0.5), (1, 33, 0.5), (1.5, 33, 0.5),
        (2, 33, 0.5), (2.5, 33, 0.5), (3, 36, 0.5), (3.5, 33, 0.5),
        (4, 33, 0.5), (4.5, 33, 0.5), (5, 33, 0.5), (5.5, 33, 0.5),
        (6, 38, 0.5), (6.5, 36, 0.5), (7, 33, 0.5), (7.5, 33, 0.5),
        # repeat
        (8, 33, 0.5), (8.5, 33, 0.5), (9, 33, 0.5), (9.5, 33, 0.5),
        (10, 33, 0.5), (10.5, 33, 0.5), (11, 36, 0.5), (11.5, 33, 0.5),
        (12, 33, 0.5), (12.5, 33, 0.5), (13, 33, 0.5), (13.5, 33, 0.5),
        (14, 38, 0.5), (14.5, 36, 0.5), (15, 33, 0.5), (15.5, 33, 0.5),
    ]
    for pos, pitch, dur in bass_pattern:
        await mcp_opendaw_create_note(0, pitch, pos, dur, 0.9, bass_au)
    print(f"  Bassline: {len(bass_pattern)} notes (A1/C2/D2 pattern)")

    # Add Werkstatt DarkSat saturation on bass
    r = await mcp_opendaw_add_effect(bass_au, "Werkstatt")
    werk_idx = json.loads(r).get("effect_index", 0)
    print(f"  Added Werkstatt effect at index {werk_idx}")

    sat_code = load_script("werkstatt_darksat.js")
    await mcp_opendaw_set_script_device_code("werkstatt", bass_au, werk_idx, sat_code)
    await mcp_opendaw_set_script_param("werkstatt", bass_au, werk_idx, "drive", 0.6)
    await mcp_opendaw_set_script_param("werkstatt", bass_au, werk_idx, "tone", 0.4)
    await mcp_opendaw_set_script_param("werkstatt", bass_au, werk_idx, "output", -2)
    print("  Saturation: drive=0.6, tone=0.4, output=-2dB")

    # ─── 3. Lead — Vaporisateur + Spielwerk Arpeggiator ──────
    print("\n── Lead: Vaporisateur + Spielwerk Arp ──")
    r = await mcp_opendaw_create_synth_track("LeadArp", "vaporisateur")
    lead_au = json.loads(r)["unit_index"]
    print(f"  Created AU {lead_au} (Vaporisateur)")

    # Add Spielwerk arpeggiator as MIDI effect
    r = await mcp_opendaw_add_midi_effect(lead_au, "Spielwerk")
    print(f"  Added Spielwerk MIDI effect")

    arp_code = load_script("spielwerk_arpeggiator.js")
    await mcp_opendaw_set_script_device_code("spielwerk", lead_au, 0, arp_code)
    await mcp_opendaw_set_script_param("spielwerk", lead_au, 0, "rate", 0.125)
    await mcp_opendaw_set_script_param("spielwerk", lead_au, 0, "octaves", 2)
    await mcp_opendaw_set_script_param("spielwerk", lead_au, 0, "direction", 0)
    await mcp_opendaw_set_script_param("spielwerk", lead_au, 0, "swing", 0.15)
    print("  Arp: rate=1/8, octaves=2, up, swing=0.15")

    # Note track + chord stabs (held notes feed the arpeggiator)
    await mcp_opendaw_create_note_track(lead_au)
    await mcp_opendaw_create_track_region(lead_au, 0, 0, 16, "chords", -1)

    # A minor chord stabs: A2(45), C3(48), E3(52)
    chords = [
        # bar 1-2: Am held
        (0, 45, 3.5), (0, 48, 3.5), (0, 52, 3.5),
        # bar 3-4: F major
        (4, 41, 3.5), (4, 45, 3.5), (4, 48, 3.5),
        # bar 5-6: C major
        (8, 48, 3.5), (8, 52, 3.5), (8, 55, 3.5),
        # bar 7-8: G major
        (12, 43, 3.5), (12, 47, 3.5), (12, 50, 3.5),
    ]
    for pos, pitch, dur in chords:
        await mcp_opendaw_create_note(0, pitch, pos, dur, 0.7, lead_au)
    print(f"  Chords: {len(chords)} notes (Am-F-C-G progression)")

    # Add delay on lead
    r = await mcp_opendaw_add_effect(lead_au, "Delay")
    delay_idx = json.loads(r).get("effect_index", 0)
    await mcp_opendaw_set_effect_parameter(lead_au, delay_idx, "time", 0.375)
    await mcp_opendaw_set_effect_parameter(lead_au, delay_idx, "feedback", 0.35)
    await mcp_opendaw_set_effect_parameter(lead_au, delay_idx, "mix", 0.3)
    print(f"  Delay: time=3/8, feedback=0.35, mix=0.3")

    # ─── 4. Project state summary ────────────────────────────
    print("\n── Project Summary ──")
    state = json.loads(await mcp_opendaw_get_project_state())
    print(f"  Tracks: {state.get('track_count', 0)}")
    print(f"  BPM: {state.get('bpm', 120)}")
    units = state.get("audio_units", [])
    for u in units:
        name = u.get("name", "?")
        idx = u.get("index", "?")
        instr = u.get("instrument_type", "none")
        effects = u.get("effects", [])
        midi_fx = u.get("midi_effects", [])
        print(f"  AU {idx}: {name} [{instr}] fx={len(effects)} midi_fx={len(midi_fx)}")

    # ─── 5. Render ───────────────────────────────────────────
    print("\n── Render ──")
    r = await mcp_opendaw_render_full("production_v2", 48000)
    d = json.loads(r)
    print(f"  File: {d.get('filepath', '?')}")
    print(f"  Size: {d.get('file_size_mb', 0):.1f} MB")
    print(f"  Has audio: {d.get('has_audio', False)}")
    print(f"  Max sample: {d.get('max_sample', 0)}")

    print("\n" + "=" * 60)
    print("Production pipeline complete ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
