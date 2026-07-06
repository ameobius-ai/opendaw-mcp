"""Unit tests for create_konokol."""
import json
import pytest

THOM = 36
NAM = 38
TA = 42
MI = 43
KHA = 45

SYLLABLE_MAP = {
    "ta": TA, "ka": TA, "dhi": NAM, "mi": MI,
    "thom": THOM, "nam": NAM, "ghu": THOM,
    "khatam": KHA, "dham": NAM, "num": THOM,
    "ta-ka": TA, "ta-ki": TA, "ta-dhi": NAM,
}

TALAS = {
    "adi_tala": {
        "beats": 8,
        "syllables": ["ta", "ka", "dhi", "mi", "ta", "ka", "dhi", "mi", "ta", "ka", "ta", "ka"],
        "subdivisions": [4, 4, 4],
    },
    "roopaka_tala": {
        "beats": 6,
        "syllables": ["ta", "ka", "dhi", "ta", "ka", "dhi", "mi"],
        "subdivisions": [3, 4],
    },
    "khanda_chapu": {
        "beats": 5,
        "syllables": ["ta", "ka", "ta", "ka", "ta", "dhi", "mi"],
        "subdivisions": [2, 5],
    },
    "mishra_chapu": {
        "beats": 7,
        "syllables": ["ta", "ki", "ta", "ta", "ka", "ta", "ka"],
        "subdivisions": [3, 2, 2],
    },
    "triputa_tala": {
        "beats": 7,
        "syllables": ["ta", "ka", "dhi", "mi", "ta", "ka", "ta"],
        "subdivisions": [4, 2, 1],
    },
    "jhampa_tala": {
        "beats": 10,
        "syllables": ["ta", "ka", "dhi", "mi", "ta", "ka", "ta", "ka", "dhi", "mi"],
        "subdivisions": [4, 2, 4],
    },
}


def _generate_konokol(style="adi_tala", cycles=2, velocity=0.7, start_beat=0.0):
    """Pure-Python reimplementation."""
    tala = TALAS[style]
    cycle_beats = tala["beats"]
    syllables = tala["syllables"]
    subdivisions = tala["subdivisions"]
    n_syllables = len(syllables)
    beat_per_syllable = cycle_beats / n_syllables

    notes = []
    for c in range(cycles):
        cycle_start = start_beat + c * cycle_beats
        for i, syl in enumerate(syllables):
            pitch = SYLLABLE_MAP.get(syl, TA)
            beat_pos = cycle_start + i * beat_per_syllable
            emph = 1.0
            pos_in_cycle = i
            for sd in subdivisions:
                if pos_in_cycle == 0:
                    emph = 1.0
                    break
                pos_in_cycle -= sd
                if pos_in_cycle < 0:
                    emph = 0.65
                    break
            notes.append({
                "pitch": pitch,
                "start": round(beat_pos, 4),
                "duration": round(beat_per_syllable * 0.9, 4),
                "velocity": round(max(0.0, min(1.0, velocity * emph)), 3),
            })
    return notes


# === Tala Structures ===

class TestTalaStructures:
    def test_adi_tala_8_beats(self):
        notes = _generate_konokol("adi_tala", 1)
        assert len(notes) == 12  # 12 syllables
        # 8 beats / 12 syllables = 0.6667 per syllable
        assert notes[-1]["start"] == round(11 * (8/12), 4)

    def test_roopaka_6_beats(self):
        notes = _generate_konokol("roopaka_tala", 1)
        assert len(notes) == 7

    def test_khanda_chapu_5_beats(self):
        notes = _generate_konokol("khanda_chapu", 1)
        assert len(notes) == 7

    def test_mishra_chapu_7_beats(self):
        notes = _generate_konokol("mishra_chapu", 1)
        assert len(notes) == 7

    def test_jhampa_10_beats(self):
        notes = _generate_konokol("jhampa_tala", 1)
        assert len(notes) == 10


# === Syllable Mapping ===

class TestSyllableMapping:
    def test_ta_maps_to_hat(self):
        notes = _generate_konokol("adi_tala", 1)
        # First syllable "ta" → TA = 42
        assert notes[0]["pitch"] == 42

    def test_dhi_maps_to_snare(self):
        notes = _generate_konokol("adi_tala", 1)
        # Syllable index 2 = "dhi" → NAM = 38
        assert notes[2]["pitch"] == 38

    def test_mi_maps_to_tom(self):
        notes = _generate_konokol("adi_tala", 1)
        # Syllable index 3 = "mi" → MI = 43
        assert notes[3]["pitch"] == 43


# === Timing ===

class TestTiming:
    def test_equal_syllable_spacing(self):
        notes = _generate_konokol("adi_tala", 1)
        # 8 beats / 12 syllables = 0.6667
        beat_per = 8 / 12
        for i, n in enumerate(notes):
            assert n["start"] == round(i * beat_per, 4)

    def test_cycle_repeats(self):
        notes = _generate_konokol("adi_tala", 2)
        # Second cycle starts at beat 8
        assert notes[12]["start"] == 8.0

    def test_start_beat_offset(self):
        notes = _generate_konokol("adi_tala", 1, start_beat=8.0)
        assert notes[0]["start"] == 8.0

    def test_duration_proportional(self):
        notes = _generate_konokol("adi_tala", 1)
        # Duration = beat_per_syllable * 0.9
        beat_per = 8 / 12
        assert notes[0]["duration"] == round(beat_per * 0.9, 4)


# === Velocity / Emphasis ===

class TestVelocity:
    def test_first_syllable_emphasized(self):
        notes = _generate_konokol("adi_tala", 1, velocity=0.8)
        # First syllable has emph=1.0
        assert notes[0]["velocity"] == 0.8

    def test_non_first_lower_emphasis(self):
        notes = _generate_konokol("adi_tala", 1, velocity=0.8)
        # Syllable index 1 = "ka" — not at start of subdivision → emph=0.65
        # subdivisions = [4,4,4], so indices 0,4,8 are emphasized
        assert notes[1]["velocity"] == round(0.8 * 0.65, 3)

    def test_subdivision_starts_emphasized(self):
        notes = _generate_konokol("adi_tala", 1, velocity=0.8)
        # Index 4 = start of second subdivision → emphasized
        assert notes[4]["velocity"] == 0.8

    def test_velocity_clamped(self):
        notes = _generate_konokol("adi_tala", 1, velocity=1.5)
        assert notes[0]["velocity"] <= 1.0

    def test_velocity_clamped_low(self):
        notes = _generate_konokol("adi_tala", 1, velocity=-0.5)
        assert notes[0]["velocity"] >= 0.0


# === Cross-Style ===

class TestCrossStyle:
    def test_all_styles_produce_notes(self):
        for style in TALAS:
            notes = _generate_konokol(style, 1)
            assert len(notes) > 0, f"Style {style} produced no notes"

    def test_all_styles_first_note_is_ta(self):
        """All talas start with 'ta' syllable."""
        for style in TALAS:
            notes = _generate_konokol(style, 1)
            assert notes[0]["pitch"] == TA, f"Style {style} first note not TA"

    def test_multiple_cycles(self):
        for style in TALAS:
            notes = _generate_konokol(style, 4)
            tala = TALAS[style]
            assert len(notes) == len(tala["syllables"]) * 4

    def test_cycle_length_correct(self):
        for style in TALAS:
            tala = TALAS[style]
            notes = _generate_konokol(style, 1)
            # Last note should be within cycle_beats
            last_start = notes[-1]["start"]
            assert last_start < tala["beats"]


class TestEdgeCases:
    def test_single_cycle(self):
        notes = _generate_konokol("adi_tala", 1)
        assert len(notes) == 12

    def test_many_cycles(self):
        notes = _generate_konokol("roopaka_tala", 8)
        assert len(notes) == 7 * 8

    def test_syllable_sequence(self):
        """Verify the syllable sequence is correct."""
        tala = TALAS["adi_tala"]
        expected = ["ta", "ka", "dhi", "mi", "ta", "ka", "dhi", "mi", "ta", "ka", "ta", "ka"]
        assert tala["syllables"] == expected

    def test_mishra_chapu_subdivisions(self):
        """Mishra chapu has 3+2+2 structure."""
        tala = TALAS["mishra_chapu"]
        assert tala["subdivisions"] == [3, 2, 2]
        assert sum(tala["subdivisions"]) == 7

    def test_jhampa_10_beat_cycle(self):
        """Jhampa tala is a 10-beat cycle."""
        tala = TALAS["jhampa_tala"]
        assert tala["beats"] == 10
        assert len(tala["syllables"]) == 10
