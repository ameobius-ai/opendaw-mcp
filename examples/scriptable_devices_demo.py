"""
Scriptable Devices Demo

Showcases openDAW's unique scriptable device system — the only DAW where
an agent can write custom DSP/MIDI code and compile it directly into the project.

Three device types, all user-scriptable via JavaScript:
1. Apparat — custom instrument synth (generates audio from MIDI notes)
2. Werkstatt — custom audio effect (processes audio in real-time)
3. Spielwerk — custom MIDI effect (transforms MIDI events)

Each script uses @param / @sample declarations that openDAW parses into
automated parameters and sample slots. The MCP server compiles the code,
validates it, and registers it as an AudioWorklet processor.

This example:
- Creates an Apparat instrument with a custom dark bass synth
- Programs a bassline
- Adds a Werkstatt tape saturation effect on the bass
- Inserts a Spielwerk arpeggiator as a MIDI effect
- Tweak parameters on all three devices
- Renders stems
"""
import asyncio
import json
import os
import server

PPQN = 960  # 1 quarter note = 960 PPQN
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def load_script(name):
    """Load a DSP script from the scripts/ directory."""
    path = os.path.join(SCRIPTS_DIR, name)
    with open(path) as f:
        return f.read()


async def main():
    await server.bridge.start()
    print("=== Scriptable Devices Demo ===\n")

    # ─── 1. Project setup ───────────────────────────────────────
    await server.mcp_opendaw_set_bpm(128)
    await server.mcp_opendaw_set_time_signature(4, 4)
    print("Project: 128 BPM, 4/4\n")

    # ─── 2. Apparat — custom instrument synth ───────────────────
    print("--- Apparat (custom instrument) ---")
    # Apparat is a scriptable instrument — we write the synth engine in JS
    synth_result = await server.mcp_opendaw_create_synth_track("Apparat")
    synth_data = json.loads(synth_result)
    print(f"Apparat AU created: {synth_data}")

    # Load and compile the dark bass synth script
    darkbass_code = load_script("apparat_darkbass.js")
    await server.mcp_opendaw_set_script_device_code(
        device_type="Apparat", unit_index=0, device_index=0, code=darkbass_code
    )
    print("Apparat: compiled darkbass synth (saw + sub osc + resonant LPF + ADSR)")

    # Read back to confirm compilation
    code_back = await server.mcp_opendaw_get_script_device_code(
        device_type="Apparat", unit_index=0, device_index=0
    )
    code_data = json.loads(code_back)
    print(f"  Code verified: {len(code_data.get('code', ''))} chars, header={code_data.get('header', '?')}")

    # List compiled parameters
    params = await server.mcp_opendaw_list_script_params(
        device_type="Apparat", unit_index=0, device_index=0
    )
    params_data = json.loads(params)
    print(f"  Parameters: {[p['label'] for p in params_data['params']]}")

    # Tweak synth params — darker, punchier
    await server.mcp_opendaw_set_script_param("Apparat", 0, 0, "cutoff", 350)
    await server.mcp_opendaw_set_script_param("Apparat", 0, 0, "resonance", 4.0)
    await server.mcp_opendaw_set_script_param("Apparat", 0, 0, "attack", 0.002)
    await server.mcp_opendaw_set_script_param("Apparat", 0, 0, "decay", 0.15)
    await server.mcp_opendaw_set_script_param("Apparat", 0, 0, "subOsc", 0.7)
    await server.mcp_opendaw_set_script_param("Apparat", 0, 0, "volume", 0.55)
    print("  Tuned: cutoff=350Hz, res=4.0, fast attack, sub boost")

    # ─── 3. Bassline ────────────────────────────────────────────
    print("\n--- Bassline ---")
    note_track = await server.mcp_opendaw_create_note_track(0, "note")
    region = await server.mcp_opendaw_create_track_region(0, 0, 0, 4 * 4 * PPQN)

    # Bassline pattern: root notes + octave jumps (A minor)
    # A1=33, C2=36, E2=40, G1=31, A1=33
    bassline = [
        (33, 0,        PPQN),         # A1, beat 1
        (33, PPQN,     PPQN // 2),    # A1, beat 1.5 (8th)
        (33, PPQN * 2, PPQN),         # A1, beat 2
        (45, PPQN * 3, PPQN // 2),    # A2, beat 3.5 (octave jump)
        (36, PPQN * 4, PPQN),         # C2, bar 2
        (36, PPQN * 5, PPQN // 2),    # C2, 8th
        (40, PPQN * 6, PPQN),         # E2, beat 3
        (36, PPQN * 7, PPQN // 2),    # C2, 8th
        (31, PPQN * 8, PPQN),         # G1, bar 3
        (31, PPQN * 9, PPQN // 2),    # G1, 8th
        (43, PPQN * 10, PPQN),        # G2, octave
        (31, PPQN * 11, PPQN // 2),   # G1, 8th
        (33, PPQN * 12, PPQN),        # A1, bar 4
        (33, PPQN * 13, PPQN // 2),   # A1, 8th
        (45, PPQN * 14, PPQN),        # A2, octave
        (33, PPQN * 15, PPQN // 2),   # A1, 8th
    ]

    for pitch, pos, dur in bassline:
        await server.mcp_opendaw_create_note(
            unit_index=0, track_index=0, region_index=0,
            pitch=pitch, position=pos, duration=dur, velocity=0.85
        )
    print(f"  {len(bassline)} notes — A minor bassline with octave jumps")

    # ─── 4. Werkstatt — custom audio effect (tape saturation) ───
    print("\n--- Werkstatt (custom audio effect) ---")
    werk_result = await server.mcp_opendaw_add_effect(0, "Werkstatt")
    print(f"  Werkstatt added to Apparat AU")

    # Load and compile the tape saturation DSP
    darksat_code = load_script("werkstatt_darksat.js")
    await server.mcp_opendaw_set_script_device_code(
        device_type="Werkstatt", unit_index=0, device_index=0, code=darksat_code
    )
    print("  Werkstatt: compiled darksat tape saturation")

    # Set warm tape settings
    await server.mcp_opendaw_set_script_param("Werkstatt", 0, 0, "drive", 0.55)
    await server.mcp_opendaw_set_script_param("Werkstatt", 0, 0, "bias", 0.05)
    await server.mcp_opendaw_set_script_param("Werkstatt", 0, 0, "tone", 0.4)
    await server.mcp_opendaw_set_script_param("Werkstatt", 0, 0, "mix", 0.8)
    await server.mcp_opendaw_set_script_param("Werkstatt", 0, 0, "output", -3)
    print("  Tuned: drive=0.55, bias=0.05, tone=0.4, mix=80%, output=-3dB")

    # ─── 5. Spielwerk — custom MIDI effect (arpeggiator) ───────
    print("\n--- Spielwerk (custom MIDI effect) ---")
    # Spielwerk is a MIDI effect — transforms notes before they hit the instrument
    # We use the MCP tool for inserting MIDI effects
    spiel_result = await server.mcp_opendaw_add_midi_effect(0, "Spielwerk")
    print(f"  Spielwerk added as MIDI effect")

    # Load and compile the arpeggiator script
    arpeggiator_code = load_script("spielwerk_arpeggiator.js")
    await server.mcp_opendaw_set_script_device_code(
        device_type="Spielwerk", unit_index=0, device_index=0, code=arpeggiator_code
    )
    print("  Spielwerk: compiled arpeggiator")

    # Configure: 16th notes, up pattern, 2 octaves
    await server.mcp_opendaw_set_script_param("Spielwerk", 0, 0, "rate", 240)   # 16th notes (960/4)
    await server.mcp_opendaw_set_script_param("Spielwerk", 0, 0, "mode", 0)     # up
    await server.mcp_opendaw_set_script_param("Spielwerk", 0, 0, "octaves", 2)
    await server.mcp_opendaw_set_script_param("Spielwerk", 0, 0, "gate", 0.7)
    print("  Tuned: 16th notes, up pattern, 2 octaves, gate=70%")

    # ─── 6. Mix ─────────────────────────────────────────────────
    print("\n--- Mix ---")
    await server.mcp_opendaw_set_track_volume(0, -4)
    print("  Track volume: -4dB")

    # Add a marker
    await server.mcp_opendaw_add_marker(0, "Drop")
    print("  Marker: Drop @ bar 1")

    # ─── 7. Render ──────────────────────────────────────────────
    print("\n--- Render ---")
    await server.mcp_opendaw_start_engine()

    stems = await server.mcp_opendaw_export_stems()
    stems_data = json.loads(stems)
    print(f"  Stems: {stems_data}")

    lufs = await server.mcp_opendaw_measure_lufs()
    lufs_data = json.loads(lufs)
    print(f"  LUFS: {lufs_data}")

    # ─── Summary ────────────────────────────────────────────────
    print("\n=== Pipeline Complete ===")
    print("1 Apparat (custom dark bass synth, JS-compiled)")
    print("1 Werkstatt (custom tape saturation, JS-compiled)")
    print("1 Spielwerk (custom arpeggiator, JS-compiled)")
    print(f"{len(bassline)} bass notes → arpeggiated → tape saturated → rendered")
    print("\nThis is the only DAW where an agent writes DSP code and compiles it in.")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
