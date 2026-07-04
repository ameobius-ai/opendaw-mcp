"""Shared music theory constants and genre presets for openDAW MCP tools.

This module centralizes note-to-pitch mappings, chord interval definitions,
and genre preset data so that multiple MCP tools (create_genre_track,
create_chord_progression, etc.) can import from a single source of truth
instead of duplicating data inline.
"""

# Note name → semitone offset from C
NOTE_TO_PITCH: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

# Chord type → interval offsets from root
CHORD_INTERVALS: dict[str, list[int]] = {
    "maj":   [0, 4, 7],
    "min":   [0, 3, 7],
    "dom7":  [0, 4, 7, 10],
    "maj7":  [0, 4, 7, 11],
    "min7":  [0, 3, 7, 10],
    "sus2":  [0, 2, 7],
    "sus4":  [0, 5, 7],
    "add9":  [0, 4, 7, 14],
    "dim":   [0, 3, 6],
    "aug":   [0, 4, 8],
}

# Scale type → interval offsets from root
SCALE_INTERVALS: dict[str, list[int]] = {
    "major":           [0, 2, 4, 5, 7, 9, 11],
    "minor":           [0, 2, 3, 5, 7, 8, 10],
    "natural_minor":   [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":  [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor":   [0, 2, 3, 5, 7, 9, 11],
    "dorian":          [0, 2, 3, 5, 7, 9, 10],
    "phrygian":        [0, 1, 3, 5, 7, 8, 10],
    "lydian":          [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":      [0, 2, 4, 5, 7, 9, 10],
    "locrian":         [0, 1, 3, 5, 6, 8, 10],
    "pentatonic_major":[0, 2, 4, 7, 9],
    "pentatonic_minor":[0, 3, 5, 7, 10],
    "blues":           [0, 3, 5, 6, 7, 10],
    "chromatic":       [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
}

# Drum pattern notation: x = hit, o = soft hit, . = rest
# 16 steps per bar unless noted
GENRE_PRESETS: dict[str, dict] = {
    "house": {
        "bpm": 128,
        "drums": {
            "kick":  "x...x...x...x...",
            "hihat": "....o...o...o...",
        },
        "bass": [
            {"pitch": 36, "start": 0,   "duration": 0.5},
            {"pitch": 36, "start": 2,   "duration": 0.5},
            {"pitch": 43, "start": 4,   "duration": 0.5},
            {"pitch": 36, "start": 6,   "duration": 0.5},
        ],
        "chords": [["F", "min7"], ["Ab", "maj7"], ["Db", "maj7"], ["Eb", "min7"]],
    },
    "techno": {
        "bpm": 130,
        "drums": {
            "kick":  "x...x...x...x...",
            "hihat": "x.x.x.x.x.x.x.x.",
        },
        "bass": [
            {"pitch": 31, "start": 0,   "duration": 0.25},
            {"pitch": 31, "start": 0.5, "duration": 0.25},
            {"pitch": 31, "start": 1,   "duration": 0.25},
            {"pitch": 31, "start": 1.5, "duration": 0.25},
        ],
        "chords": [],
    },
    "lofi": {
        "bpm": 80,
        "drums": {
            "kick":  "x.......x.......",
            "snare": "....x.......x...",
            "hihat": "x.x.x.x.x.x.x.x.",
        },
        "bass": [],
        "chords": [["D", "min7"], ["G", "dom7"], ["C", "maj7"], ["A", "min7"]],
    },
    "dnb": {
        "bpm": 174,
        "drums": {
            "kick":  "x.......x...",
            "snare": "....x.......x..",
        },
        "bass": [
            {"pitch": 28, "start": 0, "duration": 2},
            {"pitch": 28, "start": 4, "duration": 2},
        ],
        "chords": [],
    },
    "trap": {
        "bpm": 140,
        "drums": {
            "kick":  "x.....x.x.....",
            "hihat": "x.x.x.xxx.x.x.x.",
        },
        "bass": [
            {"pitch": 36, "start": 0, "duration": 1},
            {"pitch": 36, "start": 3, "duration": 0.5},
        ],
        "chords": [["F", "min"], ["Ab", "maj"], ["Eb", "min"]],
    },
    "ambient": {
        "bpm": 70,
        "drums": {},
        "bass": [],
        "chords": [["C", "maj7"], ["F", "maj7"], ["A", "min7"], ["G", "maj7"]],
    },
    "coldwave": {
        "bpm": 110,
        "drums": {
            "kick":  "x...x...x...x...",
            "snare": "....x.......x...",
            "hihat": "..x...x...x...x.",
        },
        "bass": [
            {"pitch": 31, "start": 0, "duration": 0.5},
            {"pitch": 31, "start": 2, "duration": 0.5},
            {"pitch": 31, "start": 4, "duration": 0.5},
            {"pitch": 31, "start": 6, "duration": 0.5},
        ],
        "chords": [["D", "min"], ["F", "maj"], ["G", "min"], ["A", "min"]],
    },
    "hiphop": {
        "bpm": 90,
        "drums": {
            "kick":  "x.....x...x.....",
            "snare": "....x.......x...",
            "hihat": "x.x.x.x.x.x.x.x.",
        },
        "bass": [
            {"pitch": 36, "start": 0, "duration": 1},
            {"pitch": 36, "start": 3, "duration": 0.5},
            {"pitch": 36, "start": 6, "duration": 1},
        ],
        "chords": [["C", "min7"], ["Eb", "maj7"], ["G", "min7"], ["Bb", "maj7"]],
    },
}

# Valid genre names for validation / error messages
VALID_GENRES: list[str] = list(GENRE_PRESETS.keys())

# Valid chord types for validation
VALID_CHORD_TYPES: list[str] = list(CHORD_INTERVALS.keys())

# Valid scale types for validation
VALID_SCALE_TYPES: list[str] = list(SCALE_INTERVALS.keys())


def chord_to_pitches(root: str, chord_type: str, octave: int = 4) -> list[int]:
    """Convert chord name to MIDI pitch numbers.

    Args:
        root: Note name, e.g. "C", "F#", "Bb".
        chord_type: Chord type, e.g. "min7", "maj", "dom7".
        octave: MIDI octave (4 = C4=60, the middle C).

    Returns:
        List of MIDI pitch numbers.

    Raises:
        KeyError: If root or chord_type is unknown.
    """
    root_pc = NOTE_TO_PITCH[root]
    intervals = CHORD_INTERVALS[chord_type]
    base = (octave + 1) * 12  # C4 = 60
    return [base + root_pc + iv for iv in intervals]


def scale_to_pitches(root: str, scale_type: str, octave: int = 4, length: int = 7) -> list[int]:
    """Convert scale name to MIDI pitch numbers.

    Args:
        root: Note name, e.g. "C", "F#", "Bb".
        scale_type: Scale type, e.g. "minor", "dorian", "blues".
        octave: MIDI octave (4 = C4=60).
        length: How many notes to generate (wraps around the scale).

    Returns:
        List of MIDI pitch numbers.
    """
    root_pc = NOTE_TO_PITCH[root]
    intervals = SCALE_INTERVALS[scale_type]
    base = (octave + 1) * 12
    pitches = []
    for i in range(length):
        octave_offset = i // len(intervals)
        scale_idx = i % len(intervals)
        pitches.append(base + root_pc + intervals[scale_idx] + 12 * octave_offset)
    return pitches


def parse_melody_pattern(
    pattern: str,
    root: str,
    scale_type: str,
    octave: int = 4,
    velocity: float = 0.75,
    step_duration: float = 0.25,
    start_beat: float = 0,
) -> list[dict]:
    """Parse a melody pattern string into a list of note dicts.

    Pattern syntax (space-separated, each step = one 16th note):
        1-7   — scale degree (1 = root)
        0     — rest
        -     — sustain (extend previous note by one step)
        +     — octave up (applies to next note only)

    Args:
        pattern: Space-separated pattern string.
        root: Root note name (C, D#, Bb, etc.).
        scale_type: Scale type (major, minor, blues, etc.).
        octave: MIDI octave (4 = C4=60).
        velocity: Note velocity 0-1.
        step_duration: Duration of each step in beats (0.25 = 16th).
        start_beat: Starting beat position.

    Returns:
        List of dicts: {"pitch": int, "start": float, "duration": float, "velocity": float}

    Raises:
        KeyError: If root or scale_type is unknown.
        ValueError: If pattern contains invalid steps or produces no notes.
    """
    root_pc = NOTE_TO_PITCH[root]
    intervals = SCALE_INTERVALS[scale_type]
    base_pitch = (octave + 1) * 12 + root_pc

    steps = pattern.split()
    note_list: list[dict] = []
    current_octave_shift = 0

    for i, step in enumerate(steps):
        if step == "0":
            continue
        elif step == "-":
            if note_list:
                note_list[-1]["duration"] += step_duration
            continue
        elif step == "+":
            current_octave_shift = 12
            continue
        else:
            try:
                degree = int(step)
            except ValueError:
                raise ValueError(f"Invalid pattern step '{step}' at position {i}")

            if degree < 1 or degree > len(intervals):
                raise ValueError(
                    f"Scale degree {degree} out of range for {scale_type} (1-{len(intervals)})"
                )

            idx = degree - 1
            octave_wrap = idx // len(intervals)
            scale_idx = idx % len(intervals)
            pitch = base_pitch + intervals[scale_idx] + 12 * octave_wrap + current_octave_shift

            note_list.append({
                "pitch": pitch,
                "start": start_beat + i * step_duration,
                "duration": step_duration,
                "velocity": velocity,
            })
            current_octave_shift = 0

    if not note_list:
        raise ValueError("Pattern produced no notes (all rests?)")

    return note_list
