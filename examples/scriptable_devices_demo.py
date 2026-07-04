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
"""
import asyncio
import json
import os
import server

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
    synth_result = await server.mcp_opendaw_create_synth_track("Apparat Bass", "Apparat")
    synth_data = json.loads(synth_result)
    uid = synth_data["unit_index"]  # output bus = 0, instrument AU = 1+
    print(f"Apparat AU created: unit_index={uid}")

    # Load and compile the dark bass synth script
    darkbass_code = load_script("apparat_darkbass.js")
    compile_result = await server.mcp_opendaw_set_script_device_code(
        device_type="Apparat", unit_index=uid, device_index=0, code=darkbass_code
    )
    compile_data = json.loads(compile_result)
    print(f"Apparat: compiled darkbass — {compile_data.get('params_created', 0)} params, "
          f"worklet={'✅' if compile_data.get('worklet_registered') else '⚠'}")

    # List compiled parameters
    params_result = await server.mcp_opendaw_list_script_params(
        device_type="Apparat", unit_index=uid, device_index=0
    )
    params_data = json.loads(params_result)
    param_labels = [p["label"] for p in params_data.get("params", [])]
    print(f"  Parameters: {param_labels}")

    # Tweak synth params — darker, punchier
    await server.mcp_opendaw_set_script_param("Apparat", uid, 0, "cutoff", 350)
    await server.mcp_opendaw_set_script_param("Apparat", uid, 0, "resonance", 4.0)
    await server.mcp_opendaw_set_script_param("Apparat", uid, 0, "attack", 0.002)
    await server.mcp_opendaw_set_script_param("Apparat", uid, 0, "decay", 0.15)
    await server.mcp_opendaw_set_script_param("Apparat", uid, 0, "subOsc", 0.7)
    await server.mcp_opendaw_set_script_param("Apparat", uid, 0, "volume", 0.55)
    print("  Tuned: cutoff=350Hz, res=4.0, fast attack, sub boost")

    # ─── 3. Bassline ────────────────────────────────────────────
    print("\n--- Bassline ---")
    # create_note_track takes only unit_index
    await server.mcp_opendaw_create_note_track(uid)

    # create_track_region(unit_index, track_index, start_beat, duration_beats, name, hue)
    # 4 bars = 16 beats
    await server.mcp_opendaw_create_track_region(uid, 0, 0, 16, "Bassline", 220)

    # Bassline pattern: A minor, root notes + octave jumps
    # create_note(track_index, pitch, start_beat, duration_beats, velocity, unit_index)
    bassline = [
        (33, 0,    1.0,  0.85),    # A1, beat 1
        (33, 1.5,  0.5,  0.7),     # A1, 8th
        (33, 2,    1.0,  0.85),    # A1, beat 2
        (45, 3.5,  0.5,  0.9),     # A2, octave jump
        (36, 4,    1.0,  0.85),    # C2, bar 2
        (36, 5.5,  0.5,  0.7),     # C2, 8th
        (40, 6,    1.0,  0.85),    # E2, beat 3
        (36, 7.5,  0.5,  0.7),     # C2, 8th
        (31, 8,    1.0,  0.85),    # G1, bar 3
        (31, 9.5,  0.5,  0.7),     # G1, 8th
        (43, 10,   1.0,  0.9),     # G2, octave
        (31, 11.5, 0.5,  0.7),     # G1, 8th
        (33, 12,   1.0,  0.85),    # A1, bar 4
        (33, 13.5, 0.5,  0.7),     # A1, 8th
        (45, 14,   1.0,  0.9),     # A2, octave
        (33, 15.5, 0.5,  0.7),     # A1, 8th
    ]

    for pitch, start, dur, vel in bassline:
        await server.mcp_opendaw_create_note(
            track_index=0, pitch=pitch, start_beat=start,
            duration_beats=dur, velocity=vel, unit_index=uid
        )
    print(f"  {len(bassline)} notes — A minor bassline with octave jumps")

    # ─── 4. Werkstatt — custom audio effect (tape saturation) ───
    print("\n--- Werkstatt (custom audio effect) ---")
    await server.mcp_opendaw_add_effect(uid, "Werkstatt")
    print("  Werkstatt added to Apparat AU")

    # Load and compile the tape saturation DSP
    darksat_code = load_script("werkstatt_darksat.js")
    ws_result = await server.mcp_opendaw_set_script_device_code(
        device_type="Werkstatt", unit_index=uid, device_index=0, code=darksat_code
    )
    ws_data = json.loads(ws_result)
    print(f"  Werkstatt: compiled darksat — {ws_data.get('params_created', 0)} params")

    # Set warm tape settings
    await server.mcp_opendaw_set_script_param("Werkstatt", uid, 0, "drive", 0.55)
    await server.mcp_opendaw_set_script_param("Werkstatt", uid, 0, "bias", 0.05)
    await server.mcp_opendaw_set_script_param("Werkstatt", uid, 0, "tone", 0.4)
    await server.mcp_opendaw_set_script_param("Werkstatt", uid, 0, "mix", 0.8)
    await server.mcp_opendaw_set_script_param("Werkstatt", uid, 0, "output", -3)
    print("  Tuned: drive=0.55, bias=0.05, tone=0.4, mix=80%, output=-3dB")

    # ─── 5. Spielwerk — custom MIDI effect (arpeggiator) ───────
    print("\n--- Spielwerk (custom MIDI effect) ---")
    await server.mcp_opendaw_add_midi_effect(uid, "Spielwerk")
    print("  Spielwerk added as MIDI effect")

    # Load and compile the arpeggiator script
    arpeggiator_code = load_script("spielwerk_arpeggiator.js")
    sp_result = await server.mcp_opendaw_set_script_device_code(
        device_type="Spielwerk", unit_index=uid, device_index=0, code=arpeggiator_code
    )
    sp_data = json.loads(sp_result)
    print(f"  Spielwerk: compiled arpeggiator — {sp_data.get('params_created', 0)} params")

    # Configure: 16th notes, up pattern, 2 octaves
    await server.mcp_opendaw_set_script_param("Spielwerk", uid, 0, "rate", 240)
    await server.mcp_opendaw_set_script_param("Spielwerk", uid, 0, "mode", 0)
    await server.mcp_opendaw_set_script_param("Spielwerk", uid, 0, "octaves", 2)
    await server.mcp_opendaw_set_script_param("Spielwerk", uid, 0, "gate", 0.7)
    print("  Tuned: 16th notes, up pattern, 2 octaves, gate=70%")

    # ─── 6. Mix ─────────────────────────────────────────────────
    print("\n--- Mix ---")
    await server.mcp_opendaw_set_track_volume(uid, "-4")
    print(f"  Track volume: -4dB (unit {uid})")

    # Add a marker
    await server.mcp_opendaw_add_marker(0, "Drop")
    print("  Marker: Drop @ bar 1")

    # ─── Summary ────────────────────────────────────────────────
    print("\n=== Pipeline Complete ===")
    print("1 Apparat (custom dark bass synth, JS-compiled)")
    print("1 Werkstatt (custom tape saturation, JS-compiled)")
    print("1 Spielwerk (custom arpeggiator, JS-compiled)")
    print(f"{len(bassline)} bass notes → arpeggiated → tape saturated")
    print("\nThis is the only DAW where an agent writes DSP code and compiles it in.")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
