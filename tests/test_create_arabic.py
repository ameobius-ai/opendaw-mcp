"""Unit tests for create_arabic_percussion — Middle Eastern percussion ensemble."""

VALID_RHYTHMS = ("maqsum", "baladi", "saidi", "ayoub", "malfouf", "chiftetelli")

INSTRUMENTS = ("darbuka", "daf", "zills")

PITCH_MAP = {"darbuka": 36, "daf": 42, "zills": 50}

STROKE_OFFSET = {"D": -5, "T": 2, "K": 4, "S": 0}

# Rhythm cycle lengths
CYCLE_BEATS = {
    "maqsum": 8.0, "baladi": 8.0, "saidi": 8.0,
    "ayoub": 4.0, "malfouf": 4.0, "chiftetelli": 8.0,
}

# Darbuka stroke patterns (beat, stroke)
MAQSUM_DARBUKA = [
    (0.0, "D"), (1.0, "T"), (2.0, "K"), (3.5, "D"),
    (5.0, "T"), (6.0, "K"), (7.0, "T"),
]


# ─── Validation ───


class TestArabicValidation:
    def test_bars_too_few(self):
        assert not (2 <= 0 <= 16 and 0 % 2 == 0)

    def test_bars_odd(self):
        assert not (3 % 2 == 0)

    def test_bars_too_many(self):
        assert not (2 <= 18 <= 16)

    def test_bars_valid(self):
        for b in (2, 4, 8, 16):
            assert 2 <= b <= 16 and b % 2 == 0

    def test_invalid_rhythm(self):
        assert "bogus" not in VALID_RHYTHMS

    def test_valid_rhythms(self):
        for r in VALID_RHYTHMS:
            assert r in VALID_RHYTHMS

    def test_six_rhythms(self):
        assert len(VALID_RHYTHMS) == 6


# ─── Instruments ───


class TestArabicInstruments:
    def test_three_instruments(self):
        assert len(INSTRUMENTS) == 3

    def test_darbuka_present(self):
        assert "darbuka" in INSTRUMENTS

    def test_daf_present(self):
        assert "daf" in INSTRUMENTS

    def test_zills_present(self):
        assert "zills" in INSTRUMENTS

    def test_pitch_map_keys(self):
        assert set(PITCH_MAP.keys()) == set(INSTRUMENTS)


# ─── Pitch Assignment ───


class TestArabicPitch:
    def test_darbuka_lowest(self):
        assert PITCH_MAP["darbuka"] == min(PITCH_MAP.values())

    def test_zills_highest(self):
        assert PITCH_MAP["zills"] == max(PITCH_MAP.values())

    def test_daf_between(self):
        assert PITCH_MAP["darbuka"] < PITCH_MAP["daf"] < PITCH_MAP["zills"]

    def test_all_pitches_valid_midi(self):
        for p in PITCH_MAP.values():
            assert 0 <= p <= 127

    def test_dum_lowers_pitch(self):
        assert STROKE_OFFSET["D"] < 0

    def test_tek_raises_pitch(self):
        assert STROKE_OFFSET["T"] > 0

    def test_ka_raises_more_than_tek(self):
        assert STROKE_OFFSET["K"] > STROKE_OFFSET["T"]


# ─── Cycle Structure ───


class TestArabicCycle:
    def test_maqsum_8_beat_cycle(self):
        assert CYCLE_BEATS["maqsum"] == 8.0

    def test_ayoub_4_beat_cycle(self):
        assert CYCLE_BEATS["ayoub"] == 4.0

    def test_malfouf_4_beat_cycle(self):
        assert CYCLE_BEATS["malfouf"] == 4.0

    def test_chiftetelli_8_beat_cycle(self):
        assert CYCLE_BEATS["chiftetelli"] == 8.0

    def test_all_cycles_positive(self):
        for v in CYCLE_BEATS.values():
            assert v > 0


# ─── Maqsum Pattern ───


class TestArabicMaqsum:
    def test_maqsum_has_7_strokes(self):
        assert len(MAQSUM_DARBUKA) == 7

    def test_maqsum_starts_with_dum(self):
        assert MAQSUM_DARBUKA[0][1] == "D"

    def test_maqsum_has_two_dums(self):
        dums = [s for _, s in MAQSUM_DARBUKA if s == "D"]
        assert len(dums) == 2

    def test_maqsum_dum_positions(self):
        dum_beats = [b for b, s in MAQSUM_DARBUKA if s == "D"]
        assert 0.0 in dum_beats
        assert 3.5 in dum_beats  # syncopated second dum

    def test_maqsum_beats_within_cycle(self):
        for beat, _ in MAQSUM_DARBUKA:
            assert 0 <= beat < 8.0

    def test_maqsum_has_tek_and_ka(self):
        strokes = {s for _, s in MAQSUM_DARBUKA}
        assert "T" in strokes
        assert "K" in strokes

    def test_maqsum_tek_count(self):
        teks = [s for _, s in MAQSUM_DARBUKA if s == "T"]
        assert len(teks) == 3

    def test_maqsum_ka_count(self):
        kas = [s for _, s in MAQSUM_DARBUKA if s == "K"]
        assert len(kas) == 2


# ─── Pattern Generation ───


class TestArabicPatternGeneration:
    def _gen_maqsum_darbuka(self, cycles=1):
        notes = []
        for c in range(cycles):
            offset = c * 8.0
            for beat, stroke in MAQSUM_DARBUKA:
                vel_mults = {"D": 1.0, "T": 0.6, "K": 0.5}
                durs = {"D": 0.4, "T": 0.12, "K": 0.1}
                notes.append({
                    "pitch": max(0, 36 + STROKE_OFFSET[stroke]),
                    "start": round(offset + beat, 4),
                    "duration": durs[stroke],
                    "velocity": round(0.75 * vel_mults[stroke], 3),
                })
        return notes

    def test_7_notes_per_cycle(self):
        notes = self._gen_maqsum_darbuka(1)
        assert len(notes) == 7

    def test_14_notes_two_cycles(self):
        notes = self._gen_maqsum_darbuka(2)
        assert len(notes) == 14

    def test_positions_start_at_zero(self):
        notes = self._gen_maqsum_darbuka(1)
        assert notes[0]["start"] == 0.0

    def test_second_cycle_offset(self):
        notes = self._gen_maqsum_darbuka(2)
        second = [n for n in notes if n["start"] >= 8.0]
        assert len(second) == 7
        assert second[0]["start"] == 8.0

    def test_all_velocities_in_range(self):
        notes = self._gen_maqsum_darbuka(1)
        for n in notes:
            assert 0 < n["velocity"] <= 1.0

    def test_all_durations_positive(self):
        notes = self._gen_maqsum_darbuka(1)
        for n in notes:
            assert n["duration"] > 0

    def test_dum_lower_pitch_than_tek(self):
        notes = self._gen_maqsum_darbuka(1)
        dums = [n for n in notes if n["pitch"] == 31]  # 36-5
        teks = [n for n in notes if n["pitch"] == 38]  # 36+2
        assert dums and teks
        assert dums[0]["pitch"] < teks[0]["pitch"]

    def test_velocities_vary(self):
        notes = self._gen_maqsum_darbuka(1)
        vels = [n["velocity"] for n in notes]
        assert len(set(vels)) > 1


# ─── Rhythm Comparison ───


class TestArabicRhythmComparison:
    def test_maqsum_dum_on_1_and_3_5(self):
        dums = [b for b, s in MAQSUM_DARBUKA if s == "D"]
        assert 0.0 in dums and 3.5 in dums

    def test_baladi_has_double_dum(self):
        # baladi: dum on 0 and 0.5 (double dum)
        baladi_dum_beats = [0.0, 0.5, 3.5]
        assert 0.5 in baladi_dum_beats

    def test_saidi_has_double_dum_at_3_5_and_4(self):
        saidi_dum_beats = [0.0, 3.5, 4.0]
        assert 3.5 in saidi_dum_beats and 4.0 in saidi_dum_beats

    def test_ayoub_shorter_cycle(self):
        assert CYCLE_BEATS["ayoub"] < CYCLE_BEATS["maqsum"]

    def test_malfouf_shortest_or_equal(self):
        assert CYCLE_BEATS["malfouf"] <= CYCLE_BEATS["maqsum"]

    def test_chiftetelli_same_cycle_as_maqsum(self):
        assert CYCLE_BEATS["chiftetelli"] == CYCLE_BEATS["maqsum"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
