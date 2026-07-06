"""Unit tests for create_soli."""
import json
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}

SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
}


def _degree_to_pitch(degree, scale):
    n_intervals = len(scale)
    octave = degree // n_intervals
    index = degree % n_intervals
    if index < 0:
        index += n_intervals
        octave -= 1
    return octave * 12 + scale[index]


def _generate_soli(melody_pattern, rhythm_pattern, key_root="C", scale_name="major",
                   voices=3, octave_spread=2, velocity=0.7, start_beat=0.0):
    """Pure-Python reimplementation of create_soli logic."""
    scale = SCALE_INTERVALS[scale_name]
    root_pc = NOTE_MAP[key_root]
    root_pitch = (3 + 1) * 12 + root_pc

    degrees = [int(d) for d in melody_pattern.split()]
    durations = [float(d) for d in rhythm_pattern.split()]
    if len(durations) < len(degrees):
        durations.extend([0.5] * (len(degrees) - len(durations)))
    n_notes = len(degrees)

    if voices == 2:
        octave_offsets = [0, 12 * octave_spread]
    elif voices == 3:
        octave_offsets = [0, 12 * (octave_spread // 2), 12 * octave_spread]
    elif voices == 4:
        octave_offsets = [0, 12 * (octave_spread // 3), 12 * (2 * octave_spread // 3), 12 * octave_spread]
    else:  # 5
        octave_offsets = [0, 12 * (octave_spread // 4), 12 * (octave_spread // 2), 12 * (3 * octave_spread // 4), 12 * octave_spread]

    all_voice_notes = []
    for v in range(voices):
        voice_notes = []
        beat = start_beat
        octave_offset = octave_offsets[v]
        voice_vel = velocity * (1.0 if v == 0 or v == voices - 1 else 0.85)
        for i in range(n_notes):
            pitch = root_pitch + _degree_to_pitch(degrees[i], scale) + octave_offset
            dur = durations[i] if i < len(durations) else 0.5
            voice_notes.append({
                "pitch": pitch,
                "start": round(beat, 4),
                "duration": round(dur * 0.95, 4),
                "velocity": round(max(0.0, min(1.0, voice_vel)), 3),
            })
            beat += dur
        all_voice_notes.append(voice_notes)

    return all_voice_notes, octave_offsets


# === Degree to Pitch ===

class TestDegreeToPitch:
    def test_root(self):
        assert _degree_to_pitch(0, SCALE_INTERVALS["major"]) == 0

    def test_third(self):
        assert _degree_to_pitch(2, SCALE_INTERVALS["major"]) == 4

    def test_fifth(self):
        assert _degree_to_pitch(4, SCALE_INTERVALS["major"]) == 7

    def test_octave_up(self):
        assert _degree_to_pitch(7, SCALE_INTERVALS["major"]) == 12

    def test_below_root(self):
        # -1 in major = 7th below = -1 octave + index 6 = -12 + 11 = -1
        assert _degree_to_pitch(-1, SCALE_INTERVALS["major"]) == -1

    def test_pentatonic(self):
        # Pentatonic has 5 intervals
        assert _degree_to_pitch(0, SCALE_INTERVALS["pentatonic_major"]) == 0
        assert _degree_to_pitch(1, SCALE_INTERVALS["pentatonic_major"]) == 2
        assert _degree_to_pitch(5, SCALE_INTERVALS["pentatonic_major"]) == 12  # octave


# === Voice Generation ===

class TestVoiceGeneration:
    def test_two_voices(self):
        voices, offsets = _generate_soli("0 2 4", "1 1 1", voices=2, octave_spread=2)
        assert len(voices) == 2
        assert len(voices[0]) == 3
        assert len(voices[1]) == 3
        # Octave 2 = 24 semitones apart
        assert offsets == [0, 24]
        assert voices[1][0]["pitch"] - voices[0][0]["pitch"] == 24

    def test_three_voices(self):
        voices, offsets = _generate_soli("0 2", "1 1", voices=3, octave_spread=2)
        assert len(voices) == 3
        assert offsets == [0, 12, 24]
        # Each voice is an octave apart
        assert voices[1][0]["pitch"] - voices[0][0]["pitch"] == 12
        assert voices[2][0]["pitch"] - voices[1][0]["pitch"] == 12

    def test_four_voices(self):
        voices, offsets = _generate_soli("0", "4", voices=4, octave_spread=3)
        assert len(voices) == 4
        assert offsets == [0, 12, 24, 36]

    def test_five_voices(self):
        voices, offsets = _generate_soli("0", "4", voices=5, octave_spread=4)
        assert len(voices) == 5
        assert offsets == [0, 12, 24, 36, 48]

    def test_unison_rhythm(self):
        """All voices should have same rhythm (start + duration)."""
        voices, _ = _generate_soli("0 2 4 7", "0.5 0.5 0.5 0.5", voices=3)
        for i in range(len(voices[0])):
            assert voices[0][i]["start"] == voices[1][i]["start"] == voices[2][i]["start"]
            assert voices[0][i]["duration"] == voices[1][i]["duration"] == voices[2][i]["duration"]


# === Pitches ===

class TestPitches:
    def test_c_major_root(self):
        voices, _ = _generate_soli("0", "4", key_root="C", scale_name="major")
        # C3 = 48
        assert voices[0][0]["pitch"] == 48

    def test_a_minor_root(self):
        voices, _ = _generate_soli("0", "4", key_root="A", scale_name="minor")
        # A3 = 57
        assert voices[0][0]["pitch"] == 57

    def test_scale_degrees(self):
        voices, _ = _generate_soli("0 1 2 3 4 5 6 7", "0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5",
                                   key_root="C", scale_name="major", voices=1)
        # C major: C D E F G A B C
        expected = [48, 50, 52, 53, 55, 57, 59, 60]
        actual = [n["pitch"] for n in voices[0]]
        assert actual == expected

    def test_negative_degree(self):
        voices, _ = _generate_soli("-1 0", "1 1", key_root="C", scale_name="major", voices=1)
        # -1 = B below C3 = 47, 0 = C3 = 48
        assert voices[0][0]["pitch"] == 47
        assert voices[0][1]["pitch"] == 48

    def test_octave_doubling(self):
        voices, _ = _generate_soli("0", "4", voices=2, octave_spread=1)
        # 1 octave apart
        assert voices[1][0]["pitch"] - voices[0][0]["pitch"] == 12

    def test_dorian_scale(self):
        voices, _ = _generate_soli("0 1 2 3 4 5 6 7", "0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5",
                                   key_root="D", scale_name="dorian", voices=1)
        # D dorian: D E F G A B C D
        expected = [50, 52, 53, 55, 57, 59, 60, 62]
        actual = [n["pitch"] for n in voices[0]]
        assert actual == expected


# === Velocity ===

class TestVelocity:
    def test_outer_voices_full_velocity(self):
        voices, _ = _generate_soli("0", "4", voices=3, velocity=0.8)
        # Voice 0 and voice 2 (outer) = 0.8
        assert voices[0][0]["velocity"] == 0.8
        assert voices[2][0]["velocity"] == 0.8

    def test_inner_voice_reduced(self):
        voices, _ = _generate_soli("0", "4", voices=3, velocity=0.8)
        # Voice 1 (inner) = 0.8 * 0.85 = 0.68
        assert voices[1][0]["velocity"] == round(0.8 * 0.85, 3)

    def test_velocity_clamped(self):
        voices, _ = _generate_soli("0", "4", voices=2, velocity=1.5)
        assert voices[0][0]["velocity"] == 1.0
        voices_low, _ = _generate_soli("0", "4", voices=2, velocity=-0.5)
        assert voices_low[0][0]["velocity"] == 0.0


# === Rhythm ===

class TestRhythm:
    def test_rhythm_pattern_applied(self):
        voices, _ = _generate_soli("0 0 0 0", "0.5 0.25 0.25 1.0", voices=1)
        assert voices[0][0]["start"] == 0.0
        assert voices[0][1]["start"] == 0.5
        assert voices[0][2]["start"] == 0.75
        assert voices[0][3]["start"] == 1.0

    def test_duration_slightly_shorter(self):
        voices, _ = _generate_soli("0", "1.0", voices=1)
        # Duration = 1.0 * 0.95 = 0.95
        assert voices[0][0]["duration"] == 0.95

    def test_rhythm_pad(self):
        # More notes than rhythm values → padded with 0.5
        voices, _ = _generate_soli("0 0 0 0", "1 1", voices=1)
        assert voices[0][2]["duration"] == round(0.5 * 0.95, 4)
        assert voices[0][3]["duration"] == round(0.5 * 0.95, 4)

    def test_start_beat_offset(self):
        voices, _ = _generate_soli("0 0", "1 1", voices=1, start_beat=8.0)
        assert voices[0][0]["start"] == 8.0
        assert voices[0][1]["start"] == 9.0


# === Structure ===

class TestStructure:
    def test_total_notes(self):
        voices, _ = _generate_soli("0 2 4 7", "1 1 1 1", voices=4)
        total = sum(len(v) for v in voices)
        assert total == 16  # 4 notes × 4 voices

    def test_homorhythmic(self):
        """All voices play same number of notes."""
        voices, _ = _generate_soli("0 2 4", "1 1 1", voices=3)
        assert len(voices[0]) == len(voices[1]) == len(voices[2])

    def test_all_scales_produce_notes(self):
        for scale in SCALE_INTERVALS:
            voices, _ = _generate_soli("0 2 4", "1 1 1", scale_name=scale, voices=2)
            assert len(voices[0]) > 0, f"Scale {scale} failed"

    def test_octave_offsets_correct(self):
        for spread in [1, 2, 3, 4]:
            voices, offsets = _generate_soli("0", "4", voices=2, octave_spread=spread)
            assert offsets[1] == 12 * spread


class TestEdgeCases:
    def test_single_note(self):
        voices, _ = _generate_soli("0", "4", voices=2)
        assert len(voices[0]) == 1
        assert len(voices[1]) == 1

    def test_long_melody(self):
        voices, _ = _generate_soli("0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7",
                                    "0.25 " * 16, voices=3)
        assert len(voices[0]) == 16
        assert len(voices[2]) == 16

    def test_blues_scale(self):
        voices, _ = _generate_soli("0 1 2 3 4 5 6", "0.5 0.5 0.5 0.5 0.5 0.5 0.5",
                                   key_root="C", scale_name="blues", voices=1)
        # C blues: C Eb F F# G Bb C(+octave)
        # 6 intervals, degree 6 = octave = 12
        expected = [48, 51, 53, 54, 55, 58, 60]
        actual = [n["pitch"] for n in voices[0]]
        assert actual == expected

    def test_whole_tone(self):
        voices, _ = _generate_soli("0 1 2 3 4 5 6", "0.5 0.5 0.5 0.5 0.5 0.5 0.5",
                                   key_root="C", scale_name="whole_tone", voices=1)
        # C whole tone: C D E F# G# A# C(+octave)
        expected = [48, 50, 52, 54, 56, 58, 60]
        actual = [n["pitch"] for n in voices[0]]
        assert actual == expected
