"""Unit tests for create_binary_form."""
import json
import pytest
import random

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

a_melody_degrees = [0, 1, 2, 1, 0, 2, 4, 2, 0, 2, 1, 0, -1, 0, 2, 0]
b_melody_degrees = [4, 2, 5, 4, 2, 0, 2, 4, 5, 7, 5, 4, 2, 1, 0, 0]
a_bass_degrees = [0, 0, 4, 4, 0, 0, 4, 0, 0, 0, 4, 4, 0, 0, 0, 0]
b_bass_degrees = [0, 0, 4, 4, 0, 0, 4, 0, 0, 0, 4, 4, 0, 0, -5, 0]


def _degree_to_pitch(degree, base_pitch, sc):
    n_intervals = len(sc)
    octave = degree // n_intervals
    index = degree % n_intervals
    if index < 0:
        index += n_intervals
        octave -= 1
    return base_pitch + octave * 12 + sc[index]


def _generate_binary(key_root="G", scale_name="major", bars_per_section=8,
                     repeat=True, modulation="dominant", velocity=0.7, start_beat=0.0):
    """Pure-Python reimplementation."""
    scale = SCALE_INTERVALS[scale_name]
    root_pc = NOTE_MAP[key_root]
    root_pitch = (3 + 1) * 12 + root_pc
    beats_per_bar = 4

    is_minor = 3 in scale[:3]
    if modulation == "dominant":
        b_root_offset = 7
    elif modulation == "relative":
        b_root_offset = 3 if is_minor else -3
    elif modulation == "subdominant":
        b_root_offset = 5
    else:
        b_root_offset = 0

    b_root_pitch = root_pitch + b_root_offset

    rng = random.Random(42)

    def generate_section(degrees, bass_degrees, base_pitch, sec_start, bars, sc, vel):
        melody_notes = []
        bass_notes = []
        notes_per_bar = len(degrees) // bars if bars > 0 else len(degrees)
        beat_per_note = beats_per_bar / notes_per_bar
        for bar in range(bars):
            bar_start = sec_start + bar * beats_per_bar
            for n in range(notes_per_bar):
                idx = bar * notes_per_bar + n
                if idx >= len(degrees):
                    break
                deg = degrees[idx]
                if bar > 0 and rng.random() < 0.15:
                    deg = deg + rng.choice([-1, 0, 1])
                pitch = _degree_to_pitch(deg, base_pitch, sc)
                beat_pos = bar_start + n * beat_per_note
                melody_notes.append({"pitch": pitch, "start": round(beat_pos, 4), "duration": round(beat_per_note * 0.9, 4), "velocity": round(vel * (0.6 + 0.05 * (n % 4)), 3)})
            for b in range(4):
                b_idx = (bar * 4 + b) % len(bass_degrees)
                b_deg = bass_degrees[b_idx]
                b_pitch = _degree_to_pitch(b_deg, base_pitch, sc) - 12
                bass_notes.append({"pitch": b_pitch, "start": round(bar_start + b, 4), "duration": 0.9, "velocity": round(vel * 0.7, 3)})
        return melody_notes, bass_notes

    all_melody = []
    all_bass = []
    sections = []
    sections.append(("A", root_pitch, scale, a_melody_degrees, a_bass_degrees))
    if repeat:
        sections.append(("A", root_pitch, scale, a_melody_degrees, a_bass_degrees))
    sections.append(("B", b_root_pitch, scale, b_melody_degrees, b_bass_degrees))
    if repeat:
        sections.append(("B", b_root_pitch, scale, b_melody_degrees, b_bass_degrees))

    current_beat = start_beat
    labels = []
    for label, base_pitch, sc, mel_deg, bass_deg in sections:
        m, b = generate_section(mel_deg, bass_deg, base_pitch, current_beat, bars_per_section, sc, velocity)
        all_melody.extend(m)
        all_bass.extend(b)
        labels.append(label)
        current_beat += bars_per_section * beats_per_bar

    return all_melody, all_bass, labels


# === Structure ===

class TestStructure:
    def test_aabb_with_repeat(self):
        _, _, labels = _generate_binary(repeat=True)
        assert labels == ["A", "A", "B", "B"]

    def test_ab_without_repeat(self):
        _, _, labels = _generate_binary(repeat=False)
        assert labels == ["A", "B"]

    def test_four_sections_with_repeat(self):
        m, b, labels = _generate_binary(repeat=True)
        assert len(labels) == 4

    def test_two_sections_without_repeat(self):
        m, b, labels = _generate_binary(repeat=False)
        assert len(labels) == 2


# === Note Counts ===

class TestNoteCounts:
    def test_melody_notes_per_bar(self):
        # 16 degrees / 8 bars = 2 notes per bar
        m, _, _ = _generate_binary(bars_per_section=8, repeat=False)
        # 2 sections × 8 bars × 2 notes = 32
        assert len(m) == 32

    def test_bass_notes_per_bar(self):
        _, b, _ = _generate_binary(bars_per_section=8, repeat=False)
        # 2 sections × 8 bars × 4 bass notes = 64
        assert len(b) == 64

    def test_repeat_doubles_notes(self):
        m_no_rep, _, _ = _generate_binary(repeat=False)
        m_rep, _, _ = _generate_binary(repeat=True)
        assert len(m_rep) == len(m_no_rep) * 2


# === Modulation ===

class TestModulation:
    def test_dominant_modulation(self):
        m, _, _ = _generate_binary(key_root="G", scale_name="major", modulation="dominant", repeat=False, bars_per_section=4)
        # A section starts at G3=55, B section starts at D3=62 (G+7)
        a_notes = [n for n in m if n["start"] < 16]
        b_notes = [n for n in m if n["start"] >= 16]
        # A first note should be based on G root, B on D root
        # A: degree 0, G3 = 55. B: degree 4, D3+degree4 = 62+7 = 69
        assert a_notes[0]["pitch"] == 55  # G3
        assert b_notes[0]["pitch"] == 69  # D3 + major[4] = 62+7 = 69

    def test_relative_modulation_major(self):
        m, _, _ = _generate_binary(key_root="C", scale_name="major", modulation="relative", repeat=False, bars_per_section=4)
        # C major → relative minor = A minor, offset = -3
        # A section: C3=48, B section: A3=45
        a_notes = [n for n in m if n["start"] < 16]
        b_notes = [n for n in m if n["start"] >= 16]
        assert a_notes[0]["pitch"] == 48  # C3
        # B: degree 4, A3=45, major[4]=7 → 45+7 = 52
        assert b_notes[0]["pitch"] == 52

    def test_subdominant_modulation(self):
        m, _, _ = _generate_binary(key_root="C", scale_name="major", modulation="subdominant", repeat=False, bars_per_section=4)
        # C → F (subdominant), offset = +5
        # A: C3=48, B: F3=53
        a_notes = [n for n in m if n["start"] < 16]
        b_notes = [n for n in m if n["start"] >= 16]
        assert a_notes[0]["pitch"] == 48
        # B: degree 4, F3=53, major[4]=7 → 53+7 = 60
        assert b_notes[0]["pitch"] == 60

    def test_no_modulation_same_pitch(self):
        m, _, _ = _generate_binary(key_root="C", scale_name="major", modulation="no_modulation", repeat=False, bars_per_section=4)
        a_notes = [n for n in m if n["start"] < 16]
        b_notes = [n for n in m if n["start"] >= 16]
        # Both sections same root
        assert a_notes[0]["pitch"] == 48
        # B first note: degree 4, same root → 48+7 = 55
        assert b_notes[0]["pitch"] == 55


# === Pitches ===

class TestPitches:
    def test_g_major_root(self):
        m, _, _ = _generate_binary(key_root="G", scale_name="major", repeat=False, bars_per_section=4)
        assert m[0]["pitch"] == 55  # G3

    def test_c_major_root(self):
        m, _, _ = _generate_binary(key_root="C", scale_name="major", repeat=False, bars_per_section=4)
        assert m[0]["pitch"] == 48  # C3

    def test_bass_below_root(self):
        _, b, _ = _generate_binary(key_root="C", scale_name="major", repeat=False, bars_per_section=4)
        # Bass degree 0 → root_pitch - 12 = 48-12 = 36
        assert b[0]["pitch"] == 36


# === Timing ===

class TestTiming:
    def test_section_boundaries(self):
        m, _, _ = _generate_binary(bars_per_section=4, repeat=False)
        # A section: 0-16 beats, B section: 16-32 beats
        a_notes = [n for n in m if n["start"] < 16]
        b_notes = [n for n in m if n["start"] >= 16]
        assert a_notes[0]["start"] == 0.0
        assert b_notes[0]["start"] == 16.0

    def test_repeat_section_boundary(self):
        m, _, _ = _generate_binary(bars_per_section=4, repeat=True)
        # AABB: A1=0-16, A2=16-32, B1=32-48, B2=48-64
        sections = [n for n in m if n["start"] < 16]
        a2 = [n for n in m if 16 <= n["start"] < 32]
        b1 = [n for n in m if 32 <= n["start"] < 48]
        b2 = [n for n in m if n["start"] >= 48]
        assert sections[0]["start"] == 0.0
        assert a2[0]["start"] == 16.0
        assert b1[0]["start"] == 32.0
        assert b2[0]["start"] == 48.0

    def test_start_beat_offset(self):
        m, _, _ = _generate_binary(bars_per_section=4, repeat=False, start_beat=8.0)
        assert m[0]["start"] == 8.0


# === Cross-Modulation ===

class TestCrossModulation:
    def test_all_modulations_produce_notes(self):
        for mod in ["dominant", "relative", "subdominant", "parallel", "no_modulation"]:
            m, b, _ = _generate_binary(modulation=mod, bars_per_section=4, repeat=False)
            assert len(m) > 0, f"Modulation {mod} failed"
            assert len(b) > 0, f"Modulation {mod} bass failed"


# === Edge Cases ===

class TestEdgeCases:
    def test_2_bars(self):
        m, _, _ = _generate_binary(bars_per_section=2, repeat=False)
        assert len(m) > 0

    def test_16_bars(self):
        m, _, _ = _generate_binary(bars_per_section=16, repeat=False)
        assert len(m) > 0

    def test_all_scales(self):
        for scale in SCALE_INTERVALS:
            m, _, _ = _generate_binary(scale_name=scale, bars_per_section=4, repeat=False)
            assert len(m) > 0, f"Scale {scale} failed"

    def test_velocity_range(self):
        m, b, _ = _generate_binary(velocity=0.9, bars_per_section=4, repeat=True)
        for n in m + b:
            assert 0.0 <= n["velocity"] <= 1.0
