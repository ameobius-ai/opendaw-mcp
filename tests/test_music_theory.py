"""Unit tests for opendaw_mcp.music_theory module."""

import pytest
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


class TestNoteToPitch:
    def test_natural_notes(self):
        assert NOTE_TO_PITCH["C"] == 0
        assert NOTE_TO_PITCH["D"] == 2
        assert NOTE_TO_PITCH["E"] == 4
        assert NOTE_TO_PITCH["F"] == 5
        assert NOTE_TO_PITCH["G"] == 7
        assert NOTE_TO_PITCH["A"] == 9
        assert NOTE_TO_PITCH["B"] == 11

    def test_sharps(self):
        assert NOTE_TO_PITCH["C#"] == 1
        assert NOTE_TO_PITCH["D#"] == 3
        assert NOTE_TO_PITCH["F#"] == 6
        assert NOTE_TO_PITCH["G#"] == 8
        assert NOTE_TO_PITCH["A#"] == 10

    def test_flats(self):
        assert NOTE_TO_PITCH["Db"] == 1
        assert NOTE_TO_PITCH["Eb"] == 3
        assert NOTE_TO_PITCH["Gb"] == 6
        assert NOTE_TO_PITCH["Ab"] == 8
        assert NOTE_TO_PITCH["Bb"] == 10

    def test_enharmonic_equality(self):
        assert NOTE_TO_PITCH["C#"] == NOTE_TO_PITCH["Db"]
        assert NOTE_TO_PITCH["D#"] == NOTE_TO_PITCH["Eb"]
        assert NOTE_TO_PITCH["F#"] == NOTE_TO_PITCH["Gb"]


class TestChordIntervals:
    def test_major_triad(self):
        assert CHORD_INTERVALS["maj"] == [0, 4, 7]

    def test_minor_triad(self):
        assert CHORD_INTERVALS["min"] == [0, 3, 7]

    def test_dominant_seventh(self):
        assert CHORD_INTERVALS["dom7"] == [0, 4, 7, 10]

    def test_major_seventh(self):
        assert CHORD_INTERVALS["maj7"] == [0, 4, 7, 11]

    def test_diminished(self):
        assert CHORD_INTERVALS["dim"] == [0, 3, 6]

    def test_augmented(self):
        assert CHORD_INTERVALS["aug"] == [0, 4, 8]


class TestScaleIntervals:
    def test_major_scale(self):
        assert SCALE_INTERVALS["major"] == [0, 2, 4, 5, 7, 9, 11]

    def test_natural_minor(self):
        assert SCALE_INTERVALS["minor"] == [0, 2, 3, 5, 7, 8, 10]
        assert SCALE_INTERVALS["natural_minor"] == SCALE_INTERVALS["minor"]

    def test_blues_scale(self):
        assert SCALE_INTERVALS["blues"] == [0, 3, 5, 6, 7, 10]

    def test_pentatonic(self):
        assert len(SCALE_INTERVALS["pentatonic_major"]) == 5
        assert len(SCALE_INTERVALS["pentatonic_minor"]) == 5

    def test_chromatic(self):
        assert len(SCALE_INTERVALS["chromatic"]) == 12


class TestGenrePresets:
    def test_house_bpm(self):
        assert GENRE_PRESETS["house"]["bpm"] == 128

    def test_techno_bpm(self):
        assert GENRE_PRESETS["techno"]["bpm"] == 130

    def test_dnb_bpm(self):
        assert GENRE_PRESETS["dnb"]["bpm"] == 174

    def test_all_genres_have_bpm(self):
        for name, preset in GENRE_PRESETS.items():
            assert "bpm" in preset, f"{name} missing bpm"

    def test_all_genres_have_drums(self):
        for name, preset in GENRE_PRESETS.items():
            assert "drums" in preset, f"{name} missing drums"

    def test_all_genres_have_bass(self):
        for name, preset in GENRE_PRESETS.items():
            assert "bass" in preset, f"{name} missing bass"

    def test_all_genres_have_chords(self):
        for name, preset in GENRE_PRESETS.items():
            assert "chords" in preset, f"{name} missing chords"

    def test_ambient_has_no_drums(self):
        assert GENRE_PRESETS["ambient"]["drums"] == {}

    def test_coldwave_exists(self):
        assert "coldwave" in GENRE_PRESETS
        assert GENRE_PRESETS["coldwave"]["bpm"] == 110

    def test_hiphop_exists(self):
        assert "hiphop" in GENRE_PRESETS
        assert GENRE_PRESETS["hiphop"]["bpm"] == 90

    def test_valid_genres_matches_presets(self):
        assert set(VALID_GENRES) == set(GENRE_PRESETS.keys())

    def test_drum_patterns_use_valid_chars(self):
        valid_chars = set("xo.")
        for name, preset in GENRE_PRESETS.items():
            for drum_name, pattern in preset["drums"].items():
                for char in pattern:
                    assert char in valid_chars, f"{name}.{drum_name} has invalid char '{char}'"


class TestChordToPitches:
    def test_c_major(self):
        # C4 = 60, major = [0, 4, 7] → [60, 64, 67]
        assert chord_to_pitches("C", "maj") == [60, 64, 67]

    def test_a_minor(self):
        # A4 = 69, minor = [0, 3, 7] → [69, 72, 76]
        assert chord_to_pitches("A", "min") == [69, 72, 76]

    def test_f_sharp_minor7(self):
        # F#4 = 66, min7 = [0, 3, 7, 10] → [66, 69, 73, 76]
        assert chord_to_pitches("F#", "min7") == [66, 69, 73, 76]

    def test_octave_shift(self):
        # C3 = 48
        assert chord_to_pitches("C", "maj", octave=3) == [48, 52, 55]

    def test_invalid_root(self):
        with pytest.raises(KeyError):
            chord_to_pitches("H", "maj")

    def test_invalid_chord_type(self):
        with pytest.raises(KeyError):
            chord_to_pitches("C", "foo")


class TestScaleToPitches:
    def test_c_major_one_octave(self):
        # C4 = 60, major = [0, 2, 4, 5, 7, 9, 11]
        result = scale_to_pitches("C", "major", length=7)
        assert result == [60, 62, 64, 65, 67, 69, 71]

    def test_a_minor_one_octave(self):
        # A4 = 69, minor = [0, 2, 3, 5, 7, 8, 10]
        result = scale_to_pitches("A", "minor", length=7)
        assert result == [69, 71, 72, 74, 76, 77, 79]

    def test_wraps_to_next_octave(self):
        # 8 notes in a 7-note scale → wraps
        result = scale_to_pitches("C", "major", length=8)
        assert result[7] == 72  # C5

    def test_pentatonic_length(self):
        result = scale_to_pitches("C", "pentatonic_major", length=5)
        assert len(result) == 5

    def test_blues_scale(self):
        result = scale_to_pitches("A", "blues", length=6)
        # A4=69, blues=[0, 3, 5, 6, 7, 10] → [69, 72, 74, 75, 76, 79]
        assert result == [69, 72, 74, 75, 76, 79]
