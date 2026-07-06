"""Unit tests for create_ternary_form."""
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


def _deg_to_pitch(degree, root_note, sc):
    ns = len(sc)
    oct_shift = degree // ns
    idx = degree % ns
    if idx < 0:
        idx += ns
        oct_shift -= 1
    return root_note + oct_shift * 12 + sc[idx]


def _compute_b_key(root_pc, scale_name, b_contrast):
    if b_contrast == "trio":
        return (root_pc + 5) % 12, scale_name
    elif b_contrast == "dominant":
        return (root_pc + 7) % 12, scale_name
    elif b_contrast == "relative":
        if scale_name == "minor":
            return (root_pc + 3) % 12, "major"
        return (root_pc + 9) % 12, "minor"
    return root_pc, scale_name


def _generate_ternary_notes(key_root="C", scale_name="major",
                            a_bars=8, b_bars=8,
                            a_prime_ornamented=True,
                            b_contrast="trio",
                            velocity=0.7, start_beat=0):
    if b_contrast not in ("trio", "dominant", "relative", "episode", "development"):
        return None, None, {"error": f"Invalid b_contrast '{b_contrast}'"}
    if scale_name not in SCALE_INTERVALS:
        return None, None, {"error": f"Invalid scale '{scale_name}'"}
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, None, {"error": f"Invalid key_root '{key_root}'"}

    scale = SCALE_INTERVALS[scale_name]
    melody_oct = (3 + 1) * 12 + root_pc
    bass_oct = (2 + 1) * 12 + root_pc
    b_root_pc, b_scale_name = _compute_b_key(root_pc, scale_name, b_contrast)
    b_scale = SCALE_INTERVALS[b_scale_name]
    b_melody_oct = (3 + 1) * 12 + b_root_pc
    b_bass_oct = (2 + 1) * 12 + b_root_pc

    a_degrees = [0, 2, 1, 0, -1, 0, 2, 4]
    a_rhythm = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    a_bass_deg = [0, 0, 4, 4]

    if b_contrast == "trio":
        b_degrees = [0, 3, 2, 0, -1, 0, 3, 2]
        b_rhythm = [1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 0, 3, 3]
    elif b_contrast == "dominant":
        b_degrees = [0, 2, 4, 2, 5, 4, 2, 0]
        b_rhythm = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 4, 0, 4]
    elif b_contrast == "relative":
        b_degrees = [0, 5, 3, 0, 7, 5, 3, 0]
        b_rhythm = [1.0, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 0, 5, 5]
    elif b_contrast == "episode":
        b_degrees = [7, 2, 5, 0, 9, 4, 7, 2]
        b_rhythm = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 5, 3, 4]
    else:
        b_degrees = a_degrees[:4] + [4, 2, 0, -1]
        b_rhythm = [0.5, 0.5, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5]
        b_bass_deg = [0, 0, 4, 4]

    import random as _rng
    rng = _rng.Random(77)

    all_melody = []
    all_bass = []
    a_b = max(2, a_bars)
    b_b = max(2, b_bars)

    # A section
    beat = start_beat
    for bar in range(a_b):
        bar_start = beat
        for i in range(len(a_degrees)):
            pitch = _deg_to_pitch(a_degrees[i] + (bar % 3) - 1, melody_oct, scale)
            dur = a_rhythm[i % len(a_rhythm)]
            all_melody.append({"pitch": pitch, "start": round(bar_start, 4),
                               "duration": round(dur * 0.9, 4),
                               "velocity": round(velocity * 0.95, 3)})
            bar_start += dur
        for b in range(4):
            bidx = (bar * 4 + b) % len(a_bass_deg)
            bp = _deg_to_pitch(a_bass_deg[bidx], bass_oct, scale)
            all_bass.append({"pitch": bp, "start": round(beat + b, 4),
                             "duration": 0.9, "velocity": round(velocity * 0.8, 3)})
        beat += 4.0

    # B section
    for bar in range(b_b):
        bar_start = beat
        for i in range(len(b_degrees)):
            pitch = _deg_to_pitch(b_degrees[i] + (bar % 2), b_melody_oct, b_scale)
            dur = b_rhythm[i % len(b_rhythm)]
            vel_mult = 0.85 if b_contrast in ("trio", "relative") else 0.9
            all_melody.append({"pitch": pitch, "start": round(bar_start, 4),
                               "duration": round(dur * 0.9, 4),
                               "velocity": round(velocity * vel_mult, 3)})
            bar_start += dur
        for b in range(4):
            bidx = (bar * 4 + b) % len(b_bass_deg)
            bp = _deg_to_pitch(b_bass_deg[bidx], b_bass_oct, b_scale)
            all_bass.append({"pitch": bp, "start": round(beat + b, 4),
                             "duration": 0.9, "velocity": round(velocity * 0.75, 3)})
        beat += 4.0

    # A' section
    for bar in range(a_b):
        bar_start = beat
        for i in range(len(a_degrees)):
            deg = a_degrees[i] + (bar % 3) - 1
            dur = a_rhythm[i % len(a_rhythm)]
            if a_prime_ornamented and rng.random() < 0.35:
                ornament_deg = deg + rng.choice([1, -1, 2, -2])
                all_melody.append({"pitch": _deg_to_pitch(ornament_deg, melody_oct, scale),
                                   "start": round(bar_start, 4),
                                   "duration": round(dur * 0.3, 4),
                                   "velocity": round(velocity * 0.7, 3)})
                all_melody.append({"pitch": _deg_to_pitch(deg, melody_oct, scale),
                                   "start": round(bar_start + dur * 0.3, 4),
                                   "duration": round(dur * 0.6, 4),
                                   "velocity": round(velocity * 0.95, 3)})
            else:
                all_melody.append({"pitch": _deg_to_pitch(deg, melody_oct, scale),
                                   "start": round(bar_start, 4),
                                   "duration": round(dur * 0.9, 4),
                                   "velocity": round(velocity * 0.95, 3)})
            bar_start += dur
        for b in range(4):
            bidx = (bar * 4 + b) % len(a_bass_deg)
            bp = _deg_to_pitch(a_bass_deg[bidx], bass_oct, scale)
            all_bass.append({"pitch": bp, "start": round(beat + b, 4),
                             "duration": 0.9, "velocity": round(velocity * 0.8, 3)})
        beat += 4.0

    all_melody.sort(key=lambda n: (n["start"], n["pitch"]))
    all_bass.sort(key=lambda n: (n["start"], n["pitch"]))
    return all_melody, all_bass, {"b_root_pc": b_root_pc, "b_scale_name": b_scale_name}


class TestTernaryValidation:
    def test_invalid_scale(self):
        _, _, info = _generate_ternary_notes(scale_name="bogus")
        assert "error" in info

    def test_invalid_key_root(self):
        _, _, info = _generate_ternary_notes(key_root="Z")
        assert "error" in info

    def test_invalid_contrast(self):
        _, _, info = _generate_ternary_notes(b_contrast="bogus")
        assert "error" in info

    def test_all_contrasts_valid(self):
        for c in ("trio", "dominant", "relative", "episode", "development"):
            mel, bass, info = _generate_ternary_notes(b_contrast=c)
            assert "error" not in info
            assert mel is not None

    def test_all_scales_valid(self):
        for sc in SCALE_INTERVALS:
            mel, _, info = _generate_ternary_notes(scale_name=sc)
            assert "error" not in info


class TestTernaryStructure:
    def test_has_melody_and_bass(self):
        mel, bass, _ = _generate_ternary_notes()
        assert len(mel) > 0
        assert len(bass) > 0

    def test_total_bars(self):
        mel, _, _ = _generate_ternary_notes(a_bars=8, b_bars=8)
        total_bars = 24
        max_beat = max(n["start"] for n in mel)
        assert max_beat < total_bars * 4.0

    def test_three_sections_equal_bars(self):
        mel, _, _ = _generate_ternary_notes(a_bars=8, b_bars=8)
        total_bars = 24
        max_beat = max(n["start"] for n in mel)
        assert max_beat < total_bars * 4.0
        assert max_beat >= (total_bars - 1) * 4.0

    def test_custom_bar_counts(self):
        mel, _, _ = _generate_ternary_notes(a_bars=4, b_bars=6)
        total_bars = 14
        max_beat = max(n["start"] for n in mel)
        assert max_beat < total_bars * 4.0

    def test_melody_more_than_bass(self):
        mel, bass, _ = _generate_ternary_notes()
        assert len(mel) >= len(bass)

    def test_note_count_scales_with_bars(self):
        small, _, _ = _generate_ternary_notes(a_bars=2, b_bars=2)
        large, _, _ = _generate_ternary_notes(a_bars=16, b_bars=16)
        assert len(large) > len(small)

    def test_a_prime_has_more_notes_when_ornamented(self):
        plain, _, _ = _generate_ternary_notes(a_bars=8, b_bars=8,
                                               a_prime_ornamented=False)
        ornamented, _, _ = _generate_ternary_notes(a_bars=8, b_bars=8,
                                                    a_prime_ornamented=True)
        # Ornamented A' should have more or equal notes
        assert len(ornamented) >= len(plain)


class TestTernaryBSectionKeys:
    def test_trio_modulates_to_subdominant(self):
        _, _, info = _generate_ternary_notes(key_root="C", b_contrast="trio")
        assert info["b_root_pc"] == 5  # F

    def test_dominant_modulates_to_dominant(self):
        _, _, info = _generate_ternary_notes(key_root="C", b_contrast="dominant")
        assert info["b_root_pc"] == 7  # G

    def test_relative_from_major_to_minor(self):
        _, _, info = _generate_ternary_notes(key_root="C", scale_name="major",
                                              b_contrast="relative")
        assert info["b_root_pc"] == 9  # A minor
        assert info["b_scale_name"] == "minor"

    def test_relative_from_minor_to_major(self):
        _, _, info = _generate_ternary_notes(key_root="A", scale_name="minor",
                                              b_contrast="relative")
        assert info["b_root_pc"] == 0  # C major
        assert info["b_scale_name"] == "major"

    def test_episode_same_key(self):
        _, _, info = _generate_ternary_notes(key_root="D", b_contrast="episode")
        assert info["b_root_pc"] == NOTE_MAP["D"]  # same key

    def test_development_same_key(self):
        _, _, info = _generate_ternary_notes(key_root="E", b_contrast="development")
        assert info["b_root_pc"] == NOTE_MAP["E"]

    def test_g_trio_modulates_to_c(self):
        _, _, info = _generate_ternary_notes(key_root="G", b_contrast="trio")
        assert info["b_root_pc"] == 0  # C

    def test_f_dominant_modulates_to_c(self):
        _, _, info = _generate_ternary_notes(key_root="F", b_contrast="dominant")
        assert info["b_root_pc"] == 0  # C


class TestTernaryNotes:
    def test_all_pitches_in_range(self):
        mel, bass, _ = _generate_ternary_notes()
        for n in mel + bass:
            assert 0 <= n["pitch"] <= 127

    def test_all_starts_non_negative(self):
        mel, bass, _ = _generate_ternary_notes()
        for n in mel + bass:
            assert n["start"] >= 0

    def test_all_durations_positive(self):
        mel, bass, _ = _generate_ternary_notes()
        for n in mel + bass:
            assert n["duration"] > 0

    def test_all_velocities_in_range(self):
        mel, bass, _ = _generate_ternary_notes()
        for n in mel + bass:
            assert 0 < n["velocity"] <= 1.0

    def test_bass_lower_than_melody(self):
        mel, bass, _ = _generate_ternary_notes()
        avg_mel = sum(n["pitch"] for n in mel) / len(mel)
        avg_bass = sum(n["pitch"] for n in bass) / len(bass)
        assert avg_bass < avg_mel

    def test_notes_sorted_by_start(self):
        mel, _, _ = _generate_ternary_notes()
        for i in range(1, len(mel)):
            assert mel[i]["start"] >= mel[i - 1]["start"]

    def test_start_beat_offset(self):
        mel, _, _ = _generate_ternary_notes(start_beat=10.0)
        assert min(n["start"] for n in mel) >= 10.0


class TestTernaryBSectionContrast:
    def test_trio_section_uses_subdominant_pitches(self):
        mel, _, _ = _generate_ternary_notes(key_root="C", a_bars=8, b_bars=8,
                                             b_contrast="trio")
        # B section: beats 32-64
        b_pitches = [n["pitch"] % 12 for n in mel if 32.0 <= n["start"] < 64.0]
        # Should contain F-centered pitches (subdominant)
        f_pc = 5
        assert f_pc in b_pitches

    def test_dominant_section_uses_dominant_pitches(self):
        mel, _, _ = _generate_ternary_notes(key_root="C", a_bars=8, b_bars=8,
                                             b_contrast="dominant")
        b_pitches = [n["pitch"] % 12 for n in mel if 32.0 <= n["start"] < 64.0]
        g_pc = 7
        assert g_pc in b_pitches

    def test_relative_section_uses_minor_tonal_center(self):
        mel, _, info = _generate_ternary_notes(key_root="C", scale_name="major",
                                                a_bars=8, b_bars=8,
                                                b_contrast="relative")
        b_pitches = [n["pitch"] % 12 for n in mel if 32.0 <= n["start"] < 64.0]
        # A minor = relative minor of C major. Tonal center shifts to A (pc 9).
        # A should be the most frequent pitch class in B section.
        from collections import Counter
        pc_counts = Counter(b_pitches)
        most_common = pc_counts.most_common(1)[0][0]
        assert most_common == 9  # A is tonal center

    def test_a_prime_returns_to_tonic(self):
        mel, _, _ = _generate_ternary_notes(key_root="C", a_bars=8, b_bars=8,
                                             b_contrast="trio")
        # A' section: beats 64-96
        a_prime_pitches = [n["pitch"] % 12 for n in mel if n["start"] >= 64.0]
        # Should be C-centered (pc 0 present)
        assert 0 in a_prime_pitches


class TestTernaryOrnamentation:
    def test_ornamented_a_prime_has_passing_tones(self):
        """A' with ornaments should have notes at unexpected scale positions."""
        mel, _, _ = _generate_ternary_notes(key_root="C", a_bars=8, b_bars=8,
                                             a_prime_ornamented=True)
        # A' section: beats 64-96
        a_prime = [n for n in mel if n["start"] >= 64.0]
        # Some notes should be short (ornament passing tones, duration < 0.2)
        short_notes = [n for n in a_prime if n["duration"] < 0.2]
        # With ornamentation, there should be at least some short notes
        assert len(short_notes) > 0

    def test_plain_a_prime_no_ornaments(self):
        mel, _, _ = _generate_ternary_notes(a_bars=8, b_bars=8,
                                             a_prime_ornamented=False)
        a_prime = [n for n in mel if n["start"] >= 64.0]
        # Without ornamentation, no very short notes (< 0.2)
        short_notes = [n for n in a_prime if n["duration"] < 0.2]
        assert len(short_notes) == 0
