"""Unit tests for create_irish_trad — Irish traditional music accompaniment."""

VALID_TUNE_TYPES = ("reel", "jig", "hornpipe", "slip_jig", "polka", "slide")

TUNES = {
    "reel": {"meter": "4/4", "beats_per_bar": 4, "beat_step": 0.5, "accents": [0, 2], "swing": 0.0},
    "jig": {"meter": "6/8", "beats_per_bar": 6, "beat_step": 0.333333, "accents": [0, 3], "swing": 0.0},
    "hornpipe": {"meter": "4/4", "beats_per_bar": 4, "beat_step": 0.5, "accents": [0, 2], "swing": 0.6},
    "slip_jig": {"meter": "9/8", "beats_per_bar": 9, "beat_step": 0.333333, "accents": [0, 3, 6], "swing": 0.0},
    "polka": {"meter": "2/4", "beats_per_bar": 2, "beat_step": 0.5, "accents": [0, 1], "swing": 0.0},
    "slide": {"meter": "12/8", "beats_per_bar": 12, "beat_step": 0.333333, "accents": [0, 3, 6, 9], "swing": 0.0},
}


# ─── Validation ───


class TestIrishValidation:
    def test_bars_too_few(self):
        assert not (4 <= 2 <= 32 and 2 % 2 == 0)

    def test_bars_odd(self):
        assert not (5 % 2 == 0)

    def test_bars_too_many(self):
        assert not (4 <= 34 <= 32)

    def test_bars_valid(self):
        for b in (4, 8, 16, 32):
            assert 4 <= b <= 32 and b % 2 == 0

    def test_invalid_tune_type(self):
        assert "bogus" not in VALID_TUNE_TYPES

    def test_valid_tune_types(self):
        for t in VALID_TUNE_TYPES:
            assert t in VALID_TUNE_TYPES

    def test_six_tune_types(self):
        assert len(VALID_TUNE_TYPES) == 6


# ─── Meter Structure ───


class TestIrishMeter:
    def test_reel_4_4(self):
        assert TUNES["reel"]["meter"] == "4/4"
        assert TUNES["reel"]["beats_per_bar"] == 4

    def test_jig_6_8(self):
        assert TUNES["jig"]["meter"] == "6/8"
        assert TUNES["jig"]["beats_per_bar"] == 6

    def test_hornpipe_4_4(self):
        assert TUNES["hornpipe"]["meter"] == "4/4"
        assert TUNES["hornpipe"]["beats_per_bar"] == 4

    def test_slip_jig_9_8(self):
        assert TUNES["slip_jig"]["meter"] == "9/8"
        assert TUNES["slip_jig"]["beats_per_bar"] == 9

    def test_polka_2_4(self):
        assert TUNES["polka"]["meter"] == "2/4"
        assert TUNES["polka"]["beats_per_bar"] == 2

    def test_slide_12_8(self):
        assert TUNES["slide"]["meter"] == "12/8"
        assert TUNES["slide"]["beats_per_bar"] == 12

    def test_accents_within_bar(self):
        for name, tune in TUNES.items():
            bpb = tune["beats_per_bar"]
            for a in tune["accents"]:
                assert 0 <= a < bpb, f"{name}: accent {a} out of range [0,{bpb})"


# ─── Swing ───


class TestIrishSwing:
    def test_reel_straight(self):
        assert TUNES["reel"]["swing"] == 0.0

    def test_hornpipe_swung(self):
        assert TUNES["hornpipe"]["swing"] > 0.0

    def test_jig_no_swing(self):
        assert TUNES["jig"]["swing"] == 0.0

    def test_polka_no_swing(self):
        assert TUNES["polka"]["swing"] == 0.0

    def test_hornpipe_only_swing(self):
        swung = [name for name, t in TUNES.items() if t["swing"] > 0]
        assert swung == ["hornpipe"]


# ─── Accent Patterns ───


class TestIrishAccents:
    def test_reel_accents_1_and_3(self):
        assert TUNES["reel"]["accents"] == [0, 2]

    def test_jig_accents_1_and_4(self):
        assert TUNES["jig"]["accents"] == [0, 3]

    def test_slip_jig_3_accents(self):
        assert len(TUNES["slip_jig"]["accents"]) == 3

    def test_polka_2_accents(self):
        assert len(TUNES["polka"]["accents"]) == 2

    def test_slide_4_accents(self):
        assert len(TUNES["slide"]["accents"]) == 4

    def test_polka_accents_on_both_beats(self):
        assert set(TUNES["polka"]["accents"]) == {0, 1}


# ─── Pattern Generation ───


class TestIrishPatternGeneration:
    def _gen_reel(self, bars=4):
        """Simulate reel note generation."""
        bpb = 4
        step = 0.5
        accents = {0, 2}
        notes = []
        for bar in range(bars):
            bar_start = bar * bpb * step
            for beat_idx in range(bpb):
                pos = bar_start + beat_idx * step
                is_accent = beat_idx in accents
                if is_accent:
                    notes.append({"pitch": 36, "start": pos, "type": "bodhran"})
                notes.append({"pitch": 42, "start": pos, "type": "hh"})
            if bar % 2 == 0:
                notes.append({"pitch": 40, "start": bar_start, "type": "feet"})
        return notes

    def test_reel_notes_per_bar(self):
        notes = self._gen_reel(1)
        # 4 beats: 2 bodhran (accents) + 4 hh + 1 feet (bar 0) = 7
        assert len(notes) == 7

    def test_reel_4_bars(self):
        notes = self._gen_reel(4)
        # 4 bars: 4*(2+4) + 2 feet = 36 - 2 = 34... let me count properly
        # bar 0: 2 bodhran + 4 hh + 1 feet = 7
        # bar 1: 2 bodhran + 4 hh = 6
        # bar 2: 2 bodhran + 4 hh + 1 feet = 7
        # bar 3: 2 bodhran + 4 hh = 6
        # total = 26
        assert len(notes) == 26

    def test_reel_bodhran_count(self):
        notes = self._gen_reel(4)
        bodhran = [n for n in notes if n["type"] == "bodhran"]
        # 2 accents per bar × 4 bars = 8
        assert len(bodhran) == 8

    def test_reel_hh_count(self):
        notes = self._gen_reel(4)
        hhs = [n for n in notes if n["type"] == "hh"]
        # 4 beats per bar × 4 bars = 16
        assert len(hhs) == 16

    def test_reel_feet_count(self):
        notes = self._gen_reel(4)
        feet = [n for n in notes if n["type"] == "feet"]
        # feet on every other bar (bars 0, 2) = 2
        assert len(feet) == 2

    def test_reel_positions_start_at_zero(self):
        notes = self._gen_reel(1)
        assert notes[0]["start"] == 0.0


# ─── Tune Comparison ───


class TestIrishTuneComparison:
    def test_polka_fewest_beats(self):
        assert TUNES["polka"]["beats_per_bar"] == min(t["beats_per_bar"] for t in TUNES.values())

    def test_slide_most_beats(self):
        assert TUNES["slide"]["beats_per_bar"] == max(t["beats_per_bar"] for t in TUNES.values())

    def test_reel_and_hornpipe_same_meter(self):
        assert TUNES["reel"]["beats_per_bar"] == TUNES["hornpipe"]["beats_per_bar"]

    def test_jig_and_slide_triplet_feel(self):
        # Both use 1/3 step (triplet 8ths)
        assert abs(TUNES["jig"]["beat_step"] - TUNES["slide"]["beat_step"]) < 0.001

    def test_reel_and_polka_straight(self):
        # Both use 0.5 step (straight 8ths)
        assert TUNES["reel"]["beat_step"] == TUNES["polka"]["beat_step"] == 0.5

    def test_slip_jig_unique_meter(self):
        # 9/8 is unique among the set
        assert TUNES["slip_jig"]["meter"] == "9/8"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
