"""Music theory module example — use shared note/chord/scale data directly.

This example shows how to use opendaw_mcp.music_theory to compute pitches,
chords, and scales in Python, then feed them into openDAW MCP tools.
"""

from opendaw_mcp.music_theory import (
    NOTE_TO_PITCH,
    VALID_GENRES,
    chord_to_pitches,
    scale_to_pitches,
)
from server import OpendawServer


def main():
    # 1. Look up note pitches
    print("Note pitches:")
    for name in ["C", "F#", "Bb", "Db"]:
        print(f"  {name} → semitone offset {NOTE_TO_PITCH[name]}")

    # 2. Build chord voicings
    print("\nChord voicings (MIDI pitches):")
    for root, ctype in [("C", "maj7"), ("A", "min7"), ("F#", "min7"), ("Eb", "dom7")]:
        pitches = chord_to_pitches(root, ctype, octave=4)
        print(f"  {root}{ctype} → {pitches}")

    # 3. Generate scale notes
    print("\nA minor scale (one octave):")
    pitches = scale_to_pitches("A", "minor", length=7)
    print(f"  {pitches}")

    print("\nC blues scale (6 notes):")
    pitches = scale_to_pitches("C", "blues", length=6)
    print(f"  {pitches}")

    print("\nA minor pentatonic (5 notes):")
    pitches = scale_to_pitches("A", "pentatonic_minor", length=5)
    print(f"  {pitches}")

    # 4. Show available genres
    print(f"\nAvailable genres: {VALID_GENRES}")

    # 5. Build a chord progression for create_chord_progression
    import json
    progression = [["D", "min7"], ["G", "dom7"], ["C", "maj7"], ["A", "min7"]]
    print(f"\nii-V-I-vi progression: {json.dumps(progression)}")

    # 6. Use create_chord_progression to play it in openDAW
    server = OpendawServer()
    server.bridge.start()

    # Create a synth track first
    r = server.mcp_opendaw_create_synth_track(
        synth="Vaporisateur",
        name="Chord Synth"
    )
    print(f"\nCreated synth: {r[:100]}")

    # Play the progression
    r = server.mcp_opendaw_create_chord_progression(
        chords=json.dumps(progression),
        unit_index=1,
        track_index=0,
        start_beat=0,
        chord_duration=4
    )
    print(f"Chord progression: {r[:200]}")

    server.bridge.stop()
    print("\nDone!")


if __name__ == "__main__":
    main()
