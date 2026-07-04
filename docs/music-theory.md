# Music Theory Module

The `opendaw_mcp.music_theory` module provides shared music theory constants and helper functions
that power the orchestration tools (`create_genre_track`, `create_chord_progression`, etc.).
You can import and use these directly in your Python code.

## Import

```python
from opendaw_mcp.music_theory import (
    NOTE_TO_PITCH,
    CHORD_INTERVALS,
    SCALE_INTERVALS,
    GENRE_PRESETS,
    VALID_GENRES,
    VALID_CHORD_TYPES,
    VALID_SCALE_TYPES,
    chord_to_pitches,
    scale_to_pitches,
)
```

## Note → Pitch

`NOTE_TO_PITCH` maps note names to semitone offsets from C:

```python
NOTE_TO_PITCH["C"]   # 0
NOTE_TO_PITCH["F#"]  # 6
NOTE_TO_PITCH["Bb"]  # 10
NOTE_TO_PITCH["Db"]  # 1  (enharmonic to C#)
```

Supports both sharps (`C#`, `D#`, `F#`, `G#`, `A#`) and flats (`Db`, `Eb`, `Gb`, `Ab`, `Bb`).

## Chord Intervals

`CHORD_INTERVALS` maps chord type names to interval offset arrays:

| Type | Intervals | Example |
|------|-----------|---------|
| `maj` | [0, 4, 7] | C major: C-E-G |
| `min` | [0, 3, 7] | C minor: C-Eb-G |
| `dom7` | [0, 4, 7, 10] | C7: C-E-G-Bb |
| `maj7` | [0, 4, 7, 11] | Cmaj7: C-E-G-B |
| `min7` | [0, 3, 7, 10] | Cm7: C-Eb-G-Bb |
| `sus2` | [0, 2, 7] | Csus2: C-D-G |
| `sus4` | [0, 5, 7] | Csus4: C-F-G |
| `add9` | [0, 4, 7, 14] | Cadd9: C-E-G-D |
| `dim` | [0, 3, 6] | Cdim: C-Eb-Gb |
| `aug` | [0, 4, 8] | Caug: C-E-G# |

## Scale Intervals

`SCALE_INTERVALS` maps scale names to interval arrays:

| Scale | Intervals |
|-------|-----------|
| `major` | [0, 2, 4, 5, 7, 9, 11] |
| `minor` / `natural_minor` | [0, 2, 3, 5, 7, 8, 10] |
| `harmonic_minor` | [0, 2, 3, 5, 7, 8, 11] |
| `melodic_minor` | [0, 2, 3, 5, 7, 9, 11] |
| `dorian` | [0, 2, 3, 5, 7, 9, 10] |
| `phrygian` | [0, 1, 3, 5, 7, 8, 10] |
| `lydian` | [0, 2, 4, 6, 7, 9, 11] |
| `mixolydian` | [0, 2, 4, 5, 7, 9, 10] |
| `locrian` | [0, 1, 3, 5, 6, 8, 10] |
| `pentatonic_major` | [0, 2, 4, 7, 9] |
| `pentatonic_minor` | [0, 3, 5, 7, 10] |
| `blues` | [0, 3, 5, 6, 7, 10] |
| `chromatic` | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] |

## Genre Presets

`GENRE_PRESETS` contains full genre templates used by `create_genre_track`:

```python
GENRE_PRESETS["house"]
# {
#   "bpm": 128,
#   "drums": {"kick": "x...x...x...x...", "hihat": "....o...o...o..."},
#   "bass": [{"pitch": 36, "start": 0, "duration": 0.5}, ...],
#   "chords": [["F", "min7"], ["Ab", "maj7"], ["Db", "maj7"], ["Eb", "min7"]]
# }
```

Available genres: `house`, `techno`, `lofi`, `dnb`, `trap`, `ambient`, `coldwave`, `hiphop`

Each preset contains:
- **`bpm`** — default tempo
- **`drums`** — step-sequencer patterns (`x` = hit, `o` = soft, `.` = rest)
- **`bass`** — list of `{pitch, start, duration}` notes
- **`chords`** — list of `[root, type]` chord specs

## Helper Functions

### `chord_to_pitches(root, chord_type, octave=4)`

Convert a chord name to MIDI pitch numbers:

```python
chord_to_pitches("C", "maj")       # [60, 64, 67]  — C4 major
chord_to_pitches("A", "min7")      # [69, 72, 76, 79]  — A4 minor 7
chord_to_pitches("F#", "min7", octave=3)  # [54, 57, 61, 64]  — F#3 minor 7
```

Octave 4 = MIDI 60 (middle C). Octave 3 = MIDI 48.

### `scale_to_pitches(root, scale_type, octave=4, length=7)`

Generate MIDI pitches for a scale:

```python
scale_to_pitches("C", "major")           # [60, 62, 64, 65, 67, 69, 71]
scale_to_pitches("A", "minor")           # [69, 71, 72, 74, 76, 77, 79]
scale_to_pitches("C", "blues", length=6) # [60, 63, 65, 66, 67, 70]
scale_to_pitches("A", "pentatonic_minor", length=5)  # [69, 72, 74, 76, 79]
```

When `length` exceeds the scale's interval count, the function wraps to the next octave.
