"""
Example: Create a chord progression with Vaporisateur synth.

Creates a I-V-vi-IV progression in C major:
- C major (C-E-G)
- G major (G-B-D)
- A minor (A-C-E)
- F major (F-A-C)

Each chord lasts 1 bar (4 beats).
"""

import asyncio
import json
import server

# Chord notes (MIDI pitches)
CHORDS = [
    [60, 64, 67],  # C major: C4, E4, G4
    [67, 71, 74],  # G major: G4, B4, D5
    [69, 72, 76],  # A minor: A4, C5, E5
    [65, 69, 72],  # F major: F4, A4, C5
]


async def main():
    await server.bridge.start()
    print("Bridge started")

    # 1. Create Vaporisateur synth
    result = await server.mcp_opendaw_create_synth_track("Synth", "Vaporisateur")
    data = json.loads(result)
    uid = data["unit_index"]
    print(f"Vaporisateur: unit_index={uid}")

    # 2. Set oscillator 1 to sawtooth for warmer sound
    # set_vaporisateur_osc_param(osc_index, param_name, value, unit_index)
    await server.mcp_opendaw_set_vaporisateur_osc_param("0", "waveform", 2, uid)
    print("Osc1 waveform → saw")

    # 3. Create note track + 4-bar region
    await server.mcp_opendaw_create_note_track(uid)
    await server.mcp_opendaw_create_track_region(uid, 0, 0, 16, "Chords", 200)

    # 4. Add chord notes — one chord per bar (4 beats each)
    # create_note(track_index, pitch, start_beat, duration_beats, velocity, unit_index)
    for bar, chord in enumerate(CHORDS):
        start = bar * 4
        for pitch in chord:
            result = await server.mcp_opendaw_create_note(
                0, pitch, start, 4, 0.7, uid
            )
            print(f"  Bar {bar+1} note {pitch}: {json.loads(result).get('success', '')}")

    # 5. Add a delay effect for atmosphere
    await server.mcp_opendaw_add_effect(uid, "Delay")
    print("Delay added")

    # 6. Set delay to dotted eighth (0.75 of a beat)
    # set_effect_parameter(unit_index, effect_index, parameter_name, value)
    await server.mcp_opendaw_set_effect_parameter(uid, 0, "time", 0.75)
    await server.mcp_opendaw_set_effect_parameter(uid, 0, "feedback", 0.3)
    print("Delay: time=0.75, feedback=0.3")

    # 7. Add reverb
    await server.mcp_opendaw_add_effect(uid, "Reverb")
    print("Reverb added")

    print("\nChord progression created!")
    print("I-V-vi-IV in C major | Saw wave | Delay + Reverb")

    await server.bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
