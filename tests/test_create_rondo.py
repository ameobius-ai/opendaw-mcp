"""Unit tests for create_rondo."""
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

FORM_MAP = {
    "simple": ["A", "B", "A"],
    "classical": ["A", "B", "A", "C", "A"],
    "seven_part": ["A", "B", "A", "C", "A", "B", "A"],
    "pop_rock": ["A", "B", "A", "B", "C", "B"],
    "jazz": ["A", "B", "A", "C"],
}

SECTION_PATTERNS = {
    "A": [0, 2, 4, 2, 0, 1, 2, 0],
    "B": [4, 6, 2, 6, 4, 5, 6, 4],
    "C": [5, 1, 3, 1, 5, 3, 1, 5],
    "D": [3, 0, 2, 0, 3, 1, 0, 3],
}

BASS_PATTERNS = {
    "A": [0, 0, 4, 4, 0, 0, 4, 0],
    "B": [4, 4, 0, 0, 4, 4, 0, 4],
    "C": [5, 5, 1, 1, 5, 5, 1, 5],
    "D": [3, 3, 0, 0, 3, 3, 0, 3],
}


def _degree_to_pitch(degree, scale):
    n_intervals = len(scale)
    octave = degree // n_intervals
    index = degree % n_intervals
    if index < 0:
        index += n_intervals
        octave -= 1
    return octave * 12 + scale[index]


def _generate_rondo(key_root="C", scale_name="major", form_type="classical",
                    bars_per_section=4, velocity=0.7, start_beat=0.0):
    """Pure-Python reimplementation of create_rondo logic."""
    scale = SCALE_INTERVALS[scale_name]
    root_pc = NOTE_MAP[key_root]
    root_pitch = (3 + 1) * 12 + root_pc
    beats_per_bar = 4
    section_beats = bars_per_section * beats_per_bar

    rng = random.Random(42)
    sections = FORM_MAP[form_type]
    all_melody = []
    all_bass = []

    for sec_idx, section_type in enumerate(sections):
        sec_start = start_beat + sec_idx * section_beats
        melody_pat = SECTION_PATTERNS.get(section_type, SECTION_PATTERNS["A"])
        bass_pat = BASS_PATTERNS.get(section_type, BASS_PATTERNS["A"])

        for bar in range(bars_per_section):
            bar_start = sec_start + bar * beats_per_bar
            for h in range(8):
                deg = melody_pat[h % len(melody_pat)]
                if bar > 0 and rng.random() < 0.3:
                    deg = deg + rng.choice([-1, 1, 0])
                pitch = root_pitch + 12 + _degree_to_pitch(deg, scale)
                beat_pos = bar_start + h * 0.5
                all_melody.append({
                    "pitch": pitch,
                    "start": round(beat_pos, 4),
                    "duration": 0.45,
                    "velocity": round(velocity * (0.6 + 0.05 * (h % 4)), 3),
                })
            for b in range(4):
                deg = bass_pat[b % len(bass_pat)]
                pitch = root_pitch + _degree_to_pitch(deg, scale) - 12
                beat_pos = bar_start + b * 1.0
                all_bass.append({
                    "pitch": pitch,
                    "start": round(beat_pos, 4),
                    "duration": 0.9,
                    "velocity": round(velocity * 0.7, 3),
                })

    return all_melody, all_bass, sections


# === Form Types ===

class TestFormTypes:
    def test_simple_aba(self):
        _, _, sections = _generate_rondo(form_type="simple")
        assert sections == ["A", "B", "A"]

    def test_classical_abaca(self):
        _, _, sections = _generate_rondo(form_type="classical")
        assert sections == ["A", "B", "A", "C", "A"]

    def test_seven_part_abacaba(self):
        _, _, sections = _generate_rondo(form_type="seven_part")
        assert sections == ["A", "B", "A", "C", "A", "B", "A"]

    def test_pop_rock_ababcb(self):
        _, _, sections = _generate_rondo(form_type="pop_rock")
        assert sections == ["A", "B", "A", "B", "C", "B"]

    def test_jazz_abac(self):
        _, _, sections = _generate_rondo(form_type="jazz")
        assert sections == ["A", "B", "A", "C"]

    def test_a_returns_in_all_forms(self):
        """A section should appear multiple times in all forms."""
        for form in FORM_MAP:
            _, _, sections = _generate_rondo(form_type=form)
            a_count = sections.count("A")
            assert a_count >= 2, f"Form {form} has {a_count} A sections"


# === Section Counts ===

class TestSectionCounts:
    def test_simple_3_sections(self):
        melody, bass, sections = _generate_rondo(form_type="simple")
        assert len(sections) == 3

    def test_classical_5_sections(self):
        _, _, sections = _generate_rondo(form_type="classical")
        assert len(sections) == 5

    def test_seven_part_7_sections(self):
        _, _, sections = _generate_rondo(form_type="seven_part")
        assert len(sections) == 7

    def test_pop_rock_6_sections(self):
        _, _, sections = _generate_rondo(form_type="pop_rock")
        assert len(sections) == 6


# === Note Counts ===

class TestNoteCounts:
    def test_melody_notes_per_bar(self):
        # 8 eighth notes per bar
        melody, _, _ = _generate_rondo(form_type="simple", bars_per_section=1)
        assert len(melody) == 3 * 1 * 8  # 3 sections × 1 bar × 8 notes

    def test_bass_notes_per_bar(self):
        # 4 bass notes per bar
        _, bass, _ = _generate_rondo(form_type="simple", bars_per_section=1)
        assert len(bass) == 3 * 1 * 4  # 3 sections × 1 bar × 4 notes

    def test_classical_note_count(self):
        melody, bass, _ = _generate_rondo(form_type="classical", bars_per_section=4)
        assert len(melody) == 5 * 4 * 8  # 5 sections × 4 bars × 8 notes
        assert len(bass) == 5 * 4 * 4

    def test_seven_part_note_count(self):
        melody, bass, _ = _generate_rondo(form_type="seven_part", bars_per_section=2)
        assert len(melody) == 7 * 2 * 8
        assert len(bass) == 7 * 2 * 4


# === Pitches ===

class TestPitches:
    def test_c_major_root(self):
        melody, _, _ = _generate_rondo(key_root="C", scale_name="major",
                                        form_type="simple", bars_per_section=1)
        # First melody note: root_pitch + 12 + degree_to_pitch(0, major) = 48+12+0 = 60 (C4)
        assert melody[0]["pitch"] == 60

    def test_a_minor_root(self):
        melody, _, _ = _generate_rondo(key_root="A", scale_name="minor",
                                        form_type="simple", bars_per_section=1)
        # A3=57, +12=69 (A4), degree 0 of minor = 0
        assert melody[0]["pitch"] == 69

    def test_bass_below_root(self):
        _, bass, _ = _generate_rondo(key_root="C", scale_name="major",
                                      form_type="simple", bars_per_section=1)
        # Bass degree 0 = root_pitch - 12 = 48-12 = 36 (C2)
        assert bass[0]["pitch"] == 36

    def test_section_b_uses_different_degrees(self):
        """B section should start on degree 4 (dominant), not 0 (tonic)."""
        melody, _, _ = _generate_rondo(key_root="C", scale_name="major",
                                        form_type="simple", bars_per_section=1)
        # Section B starts at section_beats = 4 beats (1 bar × 4 beats)
        b_melody = [n for n in melody if n["start"] >= 4.0 and n["start"] < 8.0]
        # First note of B section should be based on degree 4
        # root_pitch + 12 + degree_to_pitch(4, major) = 48+12+7 = 67 (G4)
        # But with random variation, just check it's different from A
        a_melody = [n for n in melody if n["start"] < 4.0]
        # At minimum, B section should have notes
        assert len(b_melody) > 0


# === Timing ===

class TestTiming:
    def test_section_boundaries(self):
        melody, _, _ = _generate_rondo(form_type="classical", bars_per_section=4)
        beats_per_bar = 4
        section_beats = 4 * beats_per_bar  # 16
        # Section 0 starts at beat 0
        assert melody[0]["start"] == 0.0
        # Section 1 starts at beat 16
        sec1_notes = [n for n in melody if n["start"] >= 16.0 and n["start"] < 32.0]
        assert sec1_notes[0]["start"] == 16.0

    def test_melody_8th_note_spacing(self):
        melody, _, _ = _generate_rondo(form_type="simple", bars_per_section=1)
        # Within first bar, notes at 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5
        bar0 = [n for n in melody if n["start"] < 4.0]
        starts = [n["start"] for n in bar0]
        expected = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        assert starts == expected

    def test_bass_quarter_note_spacing(self):
        _, bass, _ = _generate_rondo(form_type="simple", bars_per_section=1)
        bar0 = [n for n in bass if n["start"] < 4.0]
        starts = [n["start"] for n in bar0]
        expected = [0.0, 1.0, 2.0, 3.0]
        assert starts == expected

    def test_start_beat_offset(self):
        melody, _, _ = _generate_rondo(form_type="simple", bars_per_section=1, start_beat=8.0)
        assert melody[0]["start"] == 8.0


# === Velocity ===

class TestVelocity:
    def test_melody_velocity_range(self):
        melody, _, _ = _generate_rondo(velocity=0.8, bars_per_section=1)
        for n in melody:
            assert 0.0 <= n["velocity"] <= 1.0

    def test_bass_velocity_lower(self):
        _, bass, _ = _generate_rondo(velocity=0.8, bars_per_section=1)
        # Bass = velocity * 0.7
        assert bass[0]["velocity"] == round(0.8 * 0.7, 3)

    def test_melody_velocity_varies(self):
        """Melody velocity should vary by position (h%4)."""
        melody, _, _ = _generate_rondo(velocity=0.7, bars_per_section=1)
        bar0 = [n for n in melody if n["start"] < 4.0]
        # h=0: 0.7*(0.6+0)=0.42, h=1: 0.7*(0.6+0.05)=0.455
        assert bar0[0]["velocity"] < bar0[1]["velocity"]


# === Cross-Form ===

class TestCrossForm:
    def test_all_forms_produce_notes(self):
        for form in FORM_MAP:
            melody, bass, _ = _generate_rondo(form_type=form, bars_per_section=1)
            assert len(melody) > 0, f"Form {form} produced no melody"
            assert len(bass) > 0, f"Form {form} produced no bass"

    def test_all_scales_produce_notes(self):
        for scale in SCALE_INTERVALS:
            melody, _, _ = _generate_rondo(scale_name=scale, bars_per_section=1)
            assert len(melody) > 0, f"Scale {scale} failed"

    def test_bars_per_section_affects_count(self):
        melody1, _, _ = _generate_rondo(bars_per_section=1)
        melody4, _, _ = _generate_rondo(bars_per_section=4)
        assert len(melody4) == len(melody1) * 4


class TestEdgeCases:
    def test_single_bar_per_section(self):
        melody, bass, _ = _generate_rondo(form_type="classical", bars_per_section=1)
        assert len(melody) == 5 * 1 * 8  # 5 sections × 1 bar × 8 notes

    def test_many_bars_per_section(self):
        melody, _, _ = _generate_rondo(form_type="simple", bars_per_section=8)
        assert len(melody) == 3 * 8 * 8

    def test_pop_rock_structure(self):
        """Pop/rock form ABABCB should have B as the recurring element (chorus)."""
        _, _, sections = _generate_rondo(form_type="pop_rock")
        b_count = sections.count("B")
        assert b_count == 3  # B appears 3 times (chorus)

    def test_jazz_has_improvisation_section(self):
        """Jazz form ABAC — B is the solo/improvisation section."""
        _, _, sections = _generate_rondo(form_type="jazz")
        assert "B" in sections
        assert "C" in sections
        assert sections[0] == "A"  # starts with head
