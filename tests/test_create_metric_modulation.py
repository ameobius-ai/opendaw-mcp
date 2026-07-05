"""Unit tests for create_metric_modulation — metric modulation tool."""



NOTE_VALUES = {
    "whole": 1.0,
    "half": 0.5,
    "dotted_half": 0.75,
    "quarter": 0.25,
    "dotted_quarter": 0.375,
    "quarter_triplet": 1.0 / 6.0,
    "eighth": 0.125,
    "dotted_eighth": 3.0 / 16.0,
    "eighth_triplet": 1.0 / 12.0,
    "sixteenth": 0.0625,
    "dotted_sixteenth": 3.0 / 32.0,
    "thirty_second": 0.03125,
}


def compute_mod_ratio(old_note, new_note):
    """Compute modulation ratio: new_bpm = old_bpm * ratio."""
    old_v = NOTE_VALUES[old_note]
    new_v = NOTE_VALUES[new_note]
    return new_v / old_v


def compute_new_bpm(old_bpm, ratio):
    return old_bpm * ratio


def parse_ratio(ratio_str):
    parts = ratio_str.replace(" ", "").split(":")
    return float(parts[0]) / float(parts[1])


# --- Note value table tests ---

class TestNoteValueTable:
    def test_all_note_values_defined(self):
        expected = [
            "whole", "half", "dotted_half", "quarter", "dotted_quarter",
            "quarter_triplet", "eighth", "dotted_eighth", "eighth_triplet",
            "sixteenth", "dotted_sixteenth", "thirty_second",
        ]
        for nv in expected:
            assert nv in NOTE_VALUES

    def test_quarter_value(self):
        assert NOTE_VALUES["quarter"] == 0.25

    def test_eighth_value(self):
        assert NOTE_VALUES["eighth"] == 0.125

    def test_dotted_quarter_value(self):
        assert abs(NOTE_VALUES["dotted_quarter"] - 0.375) < 0.001

    def test_dotted_eighth_value(self):
        assert abs(NOTE_VALUES["dotted_eighth"] - 0.1875) < 0.001

    def test_quarter_triplet_value(self):
        assert abs(NOTE_VALUES["quarter_triplet"] - (1.0 / 6.0)) < 0.001

    def test_thirty_second_value(self):
        assert NOTE_VALUES["thirty_second"] == 0.03125

    def test_sixteenth_value(self):
        assert NOTE_VALUES["sixteenth"] == 0.0625

    def test_whole_value(self):
        assert NOTE_VALUES["whole"] == 1.0

    def test_half_value(self):
        assert NOTE_VALUES["half"] == 0.5

    def test_dotted_half_value(self):
        assert abs(NOTE_VALUES["dotted_half"] - 0.75) < 0.001

    def test_eighth_triplet_value(self):
        assert abs(NOTE_VALUES["eighth_triplet"] - (1.0 / 12.0)) < 0.001

    def test_dotted_sixteenth_value(self):
        assert abs(NOTE_VALUES["dotted_sixteenth"] - (3.0 / 32.0)) < 0.001


# --- Ratio computation tests ---

class TestRatioComputation:
    def test_quarter_to_dotted_eighth(self):
        # Classic Carter modulation: quarter at old = dotted_eighth at new
        ratio = compute_mod_ratio("quarter", "dotted_eighth")
        assert abs(ratio - 0.75) < 0.001

    def test_quarter_to_eighth(self):
        # Doubling: eighth at new = quarter at old
        ratio = compute_mod_ratio("quarter", "eighth")
        assert abs(ratio - 0.5) < 0.001

    def test_eighth_to_quarter(self):
        # Halving: quarter at new = eighth at old
        ratio = compute_mod_ratio("eighth", "quarter")
        assert abs(ratio - 2.0) < 0.001

    def test_quarter_to_quarter(self):
        # Identity: no change
        ratio = compute_mod_ratio("quarter", "quarter")
        assert abs(ratio - 1.0) < 0.001

    def test_half_to_quarter(self):
        ratio = compute_mod_ratio("half", "quarter")
        assert abs(ratio - 0.5) < 0.001

    def test_sixteenth_to_eighth(self):
        ratio = compute_mod_ratio("sixteenth", "eighth")
        assert abs(ratio - 2.0) < 0.001

    def test_dotted_eighth_to_quarter(self):
        # Inverse of Carter modulation
        ratio = compute_mod_ratio("dotted_eighth", "quarter")
        expected = 0.25 / (3.0 / 16.0)
        assert abs(ratio - expected) < 0.001

    def test_quarter_triplet_to_quarter(self):
        ratio = compute_mod_ratio("quarter_triplet", "quarter")
        expected = 0.25 / (1.0 / 6.0)
        assert abs(ratio - expected) < 0.001


# --- BPM computation tests ---

class TestBpmComputation:
    def test_carter_modulation_120(self):
        ratio = compute_mod_ratio("quarter", "dotted_eighth")
        new_bpm = compute_new_bpm(120, ratio)
        assert abs(new_bpm - 90.0) < 0.01

    def test_doubling_140(self):
        ratio = compute_mod_ratio("eighth", "quarter")
        new_bpm = compute_new_bpm(140, ratio)
        assert abs(new_bpm - 280.0) < 0.01

    def test_halving_100(self):
        ratio = compute_mod_ratio("quarter", "eighth")
        new_bpm = compute_new_bpm(100, ratio)
        assert abs(new_bpm - 50.0) < 0.01

    def test_identity_120(self):
        ratio = compute_mod_ratio("quarter", "quarter")
        new_bpm = compute_new_bpm(120, ratio)
        assert abs(new_bpm - 120.0) < 0.01

    def test_ratio_3_2(self):
        ratio = parse_ratio("3:2")
        new_bpm = compute_new_bpm(100, ratio)
        assert abs(new_bpm - 150.0) < 0.01

    def test_ratio_2_3(self):
        ratio = parse_ratio("2:3")
        new_bpm = compute_new_bpm(120, ratio)
        assert abs(new_bpm - 80.0) < 0.01

    def test_ratio_4_3(self):
        ratio = parse_ratio("4:3")
        new_bpm = compute_new_bpm(90, ratio)
        assert abs(new_bpm - 120.0) < 0.01

    def test_ratio_5_4(self):
        ratio = parse_ratio("5:4")
        new_bpm = compute_new_bpm(80, ratio)
        assert abs(new_bpm - 100.0) < 0.01

    def test_clamping_to_range(self):
        # If old_bpm=120 and ratio=3.0, new_bpm=360 — clamped to maxBpm
        new_bpm = compute_new_bpm(120, 3.0)
        assert new_bpm == 360.0  # raw, before clamping


# --- Ratio parsing tests ---

class TestRatioParsing:
    def test_simple_ratio(self):
        assert abs(parse_ratio("3:2") - 1.5) < 0.001

    def test_simple_ratio_reversed(self):
        assert abs(parse_ratio("2:3") - (2.0 / 3.0)) < 0.001

    def test_ratio_with_spaces(self):
        assert abs(parse_ratio("3 : 2") - 1.5) < 0.001

    def test_ratio_unity(self):
        assert abs(parse_ratio("1:1") - 1.0) < 0.001

    def test_ratio_fraction(self):
        assert abs(parse_ratio("7:4") - 1.75) < 0.001


# --- Equivalence verification tests ---

class TestEquivalenceVerification:
    def test_duration_preserved_quarter_to_dotted_eighth(self):
        """A quarter at old tempo should have the same duration as a
        dotted eighth at the new tempo."""
        old_bpm = 120
        ratio = compute_mod_ratio("quarter", "dotted_eighth")
        new_bpm = compute_new_bpm(old_bpm, ratio)

        old_dur = NOTE_VALUES["quarter"] * (60.0 / old_bpm)  # in seconds
        new_dur = NOTE_VALUES["dotted_eighth"] * (60.0 / new_bpm)
        assert abs(old_dur - new_dur) < 0.0001

    def test_duration_preserved_eighth_to_quarter(self):
        """An eighth at old tempo = a quarter at new tempo."""
        old_bpm = 140
        ratio = compute_mod_ratio("eighth", "quarter")
        new_bpm = compute_new_bpm(old_bpm, ratio)

        old_dur = NOTE_VALUES["eighth"] * (60.0 / old_bpm)
        new_dur = NOTE_VALUES["quarter"] * (60.0 / new_bpm)
        assert abs(old_dur - new_dur) < 0.0001

    def test_duration_preserved_ratio_3_2(self):
        """3 notes in new tempo = 2 notes in old tempo."""
        old_bpm = 100
        ratio = parse_ratio("3:2")
        new_bpm = compute_new_bpm(old_bpm, ratio)

        # 2 beats at old tempo = 3 beats at new tempo
        old_dur = 2 * (60.0 / old_bpm)
        new_dur = 3 * (60.0 / new_bpm)
        assert abs(old_dur - new_dur) < 0.0001

    def test_duration_preserved_half_to_quarter(self):
        old_bpm = 80
        ratio = compute_mod_ratio("half", "quarter")
        new_bpm = compute_new_bpm(old_bpm, ratio)

        old_dur = NOTE_VALUES["half"] * (60.0 / old_bpm)
        new_dur = NOTE_VALUES["quarter"] * (60.0 / new_bpm)
        assert abs(old_dur - new_dur) < 0.0001

    def test_duration_preserved_sixteenth_to_eighth(self):
        old_bpm = 60
        ratio = compute_mod_ratio("sixteenth", "eighth")
        new_bpm = compute_new_bpm(old_bpm, ratio)

        old_dur = NOTE_VALUES["sixteenth"] * (60.0 / old_bpm)
        new_dur = NOTE_VALUES["eighth"] * (60.0 / new_bpm)
        assert abs(old_dur - new_dur) < 0.0001


# --- Time signature parsing tests ---

class TestTimeSignatureParsing:
    def test_valid_signatures(self):
        valid = ["3/4", "6/8", "4/4", "7/8", "5/4", "2/4", "12/8"]
        for ts in valid:
            parts = ts.split("/")
            assert int(parts[0]) >= 1 and int(parts[0]) <= 32
            assert int(parts[1]) in [1, 2, 4, 8, 16, 32, 64]

    def test_compound_meter(self):
        parts = "6/8".split("/")
        assert int(parts[0]) == 6 and int(parts[1]) == 8

    def test_asymmetric_meter(self):
        parts = "7/8".split("/")
        assert int(parts[0]) == 7 and int(parts[1]) == 8

    def test_simple_quadruple(self):
        parts = "4/4".split("/")
        assert int(parts[0]) == 4 and int(parts[1]) == 4

    def test_waltz(self):
        parts = "3/4".split("/")
        assert int(parts[0]) == 3 and int(parts[1]) == 4
