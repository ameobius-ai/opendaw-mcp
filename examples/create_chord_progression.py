"""
Example: Create a chord progression with Vaporisateur synth.

Creates a I-V-vi-IV progression in C major:
- C major (C-E-G)
- G major (G-B-D)
- A minor (A-C-E)
- F major (F-A-C)

Each chord lasts 1 bar (4 beats = 3840 PPQN).
"""

import asyncio
import json
import server

PPQN = 960

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
    result = await server.mcp_opendaw_create_synth("Vaporisateur")
    data = json.loads(result)
    print(f"Vaporisateur: {data}")
    au_index = 0

    # 2. Set oscillator 1 to sawtooth for warmer sound
    result = await server.mcp_opendaw_set_osc_param(au_index, 0, "waveform", 2)
    print(f"Osc1 waveform → saw: {json.loads(result).get('success', '')}")

    # 3. Create note track + 4-bar region
    await server.mcp_opendaw_create_note_track(au_index)
    track_index = 0

    bar_length = 4 * PPQN  # 3840 PPQN per bar
    await server.mcp_opendaw_create_note_region(0, 0, 0, bar_length * 4)
    region_index = 0

    # 4. Add chord notes
    for bar, chord in enumerate(CHORDS):
        pos = bar * bar_length
        for pitch in chord:
            result = await server.mcp_opendaw_create_note_event(
                0, 0, region_index,
                position=pos, duration=bar_length, pitch=pitch, velocity=0.7
            )
            print(f"  Bar {bar+1} note {pitch}: {json.loads(result).get('success', '')}")

    # 5. Add a delay effect for atmosphere
    result = await server.mcp_opendaw_add_effect(0, "Delay")
    print(f"Delay: {json.loads(result)}")

    # 6. Set delay to dotted eighth (3/4 of a beat)
    result = await server.mcp_opendaw_set_effect_parameter(0, 0, "time", 0.75)
    print(f"Delay time: {json.loads(result).get('success', '')}")

    result = await server.mcp_opendaw_set_effect_parameter(0, 0, "feedback", 0.3)
    print(f"Delay feedback: {json.loads(result).get('success', '')}")

    # 7. Add reverb
    result = await server.mcp_opendaw_add_effect(0, "Reverb")
    print(f"Reverb: {json.loads(result)}")

    print("\nChord progression created!")
    print("I-V-vi-IV in C major | Saw wave | Delay + Reverb")

    await server.bridge.stop()

if __name__ == "__main__":
    asyncio.run(main())
