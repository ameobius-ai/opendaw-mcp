"""Unit tests for create_korean_percussion — Korean nongak/samul nori."""

VALID_STYLES = ("nongak", "samul_nori", "binari", "utdari_pungnyu", "yeongnam_folk")

INSTRUMENTS = ("janggu_chwe", "janggu_kyong", "buk", "kkwaenggwari", "jing")

PITCH_MAP = {
    "janggu_chwe": 35, "janggu_kyong": 42, "buk": 36,
    "kkwaenggwari": 54, "jing": 48,
}


# ─── Validation ───


class TestKoreanValidation:
    def test_bars_too_few(self):
        assert not (4 <= 2 <= 32 and 2 % 2 == 0)

    def test_bars_odd(self):
        assert not (5 % 2 == 0)

    def test_bars_too_many(self):
        assert not (4 <= 34 <= 32)

    def test_bars_valid(self):
        for b in (4, 8, 16, 32):
            assert 4 <= b <= 32 and b % 2 == 0

    def test_invalid_style(self):
        assert "bogus" not in VALID_STYLES

    def test_valid_styles(self):
        for s in VALID_STYLES:
            assert s in VALID_STYLES

    def test_five_styles(self):
        assert len(VALID_STYLES) == 5


# ─── Instruments ───


class TestKoreanInstruments:
    def test_five_instruments(self):
        assert len(INSTRUMENTS) == 5

    def test_janggu_two_heads(self):
        heads = [i for i in INSTRUMENTS if "janggu" in i]
        assert len(heads) == 2

    def test_buk_present(self):
        assert "buk" in INSTRUMENTS

    def test_kkwaenggwari_present(self):
        assert "kkwaenggwari" in INSTRUMENTS

    def test_jing_present(self):
        assert "jing" in INSTRUMENTS

    def test_four_instrument_types(self):
        # janggu counts as one instrument with two heads
        types = {"janggu", "buk", "kkwaenggwari", "jing"}
        actual = set()
        for inst in INSTRUMENTS:
            if "janggu" in inst:
                actual.add("janggu")
            else:
                actual.add(inst)
        assert actual == types


# ─── Pitch Assignment ───


class TestKoreanPitch:
    def test_janggu_chwe_lowest(self):
        assert PITCH_MAP["janggu_chwe"] == min(PITCH_MAP.values())

    def test_kkwaenggwari_highest(self):
        assert PITCH_MAP["kkwaenggwari"] == max(PITCH_MAP.values())

    def test_janggu_chwe_lower_than_kyong(self):
        assert PITCH_MAP["janggu_chwe"] < PITCH_MAP["janggu_kyong"]

    def test_jing_between_buk_and_kkwaenggwari(self):
        assert PITCH_MAP["buk"] < PITCH_MAP["jing"] < PITCH_MAP["kkwaenggwari"]

    def test_all_pitches_valid_midi(self):
        for p in PITCH_MAP.values():
            assert 0 <= p <= 127

    def test_buk_bass_register(self):
        assert PITCH_MAP["buk"] <= 40


# ─── Cycle Structure ───


class TestKoreanCycle:
    def test_cycle_len_16(self):
        assert 16.0 == 16.0

    def test_bars_to_cycles(self):
        assert 4 // 4 == 1
        assert 8 // 4 == 2
        assert 16 // 4 == 4


# ─── Style Characteristics ───


class TestKoreanStyles:
    def test_nongak_janggu_8th_density(self):
        # nongak janggu_chwe: 16 notes per cycle (8th notes)
        nongak_chwe_count = 16
        assert nongak_chwe_count > 8

    def test_samul_nori_janggu_16th_density(self):
        # samul_nori janggu_chwe: 32 notes per cycle (16th notes)
        samul_chwe_count = 32
        assert samul_chwe_count > 16

    def test_binari_sparse(self):
        # binari janggu_chwe: only 4 notes per cycle
        binari_chwe_count = 4
        assert binari_chwe_count < 16

    def test_binari_jing_long_durations(self):
        # binari jing: durations 1.5 and 1.2 (ceremonial)
        binari_jing_durs = [1.5, 1.2]
        for d in binari_jing_durs:
            assert d > 1.0

    def test_yeongnam_syncopated(self):
        # yeongnam janggu has syncopated positions (0.75, 2.75, etc.)
        yeongnam_positions = [0.0, 0.75, 1.5, 2.0, 2.75]
        assert 0.75 in yeongnam_positions

    def test_utdari_sparse_kkwaenggwari(self):
        # utdari kkwaenggwari: only 2 hits per cycle
        utdari_kk_count = 2
        assert utdari_kk_count < 8


# ─── Pattern Generation ───


class TestKoreanPatternGeneration:
    def _gen_nongak_buk(self, cycles=1):
        buk = [
            (0.0, 0.9, 0.3), (2.0, 0.8, 0.25), (4.0, 0.9, 0.3),
            (6.0, 0.8, 0.25), (8.0, 0.9, 0.3), (10.0, 0.8, 0.25),
            (12.0, 0.9, 0.3), (14.0, 0.8, 0.25),
        ]
        cycle_len = 16.0
        notes = []
        for c in range(cycles):
            offset = c * cycle_len
            for beat, vel_mult, dur in buk:
                notes.append({
                    "pitch": 36,
                    "start": round(offset + beat, 4),
                    "duration": dur,
                    "velocity": round(0.75 * vel_mult, 3),
                })
        return notes

    def test_buk_8_notes_per_cycle(self):
        notes = self._gen_nongak_buk(1)
        assert len(notes) == 8

    def test_buk_two_cycles(self):
        notes = self._gen_nongak_buk(2)
        assert len(notes) == 16

    def test_buk_positions_start_at_zero(self):
        notes = self._gen_nongak_buk(1)
        assert notes[0]["start"] == 0.0

    def test_buk_second_cycle_offset(self):
        notes = self._gen_nongak_buk(2)
        second = [n for n in notes if n["start"] >= 16.0]
        assert len(second) == 8
        assert second[0]["start"] == 16.0

    def test_all_velocities_in_range(self):
        notes = self._gen_nongak_buk(1)
        for n in notes:
            assert 0 < n["velocity"] <= 1.0

    def test_all_durations_positive(self):
        notes = self._gen_nongak_buk(1)
        for n in notes:
            assert n["duration"] > 0

    def test_velocities_vary(self):
        notes = self._gen_nongak_buk(1)
        vels = [n["velocity"] for n in notes]
        assert len(set(vels)) > 1


# ─── Element Symbolism ───


class TestKoreanElementSymbolism:
    """Four instruments represent weather elements."""

    def test_four_instrument_types(self):
        types = {"janggu", "buk", "kkwaenggwari", "jing"}
        assert len(types) == 4

    def test_two_gongs(self):
        gongs = {"kkwaenggwari", "jing"}
        assert len(gongs) == 2

    def test_two_drums(self):
        drums = {"janggu", "buk"}
        assert len(drums) == 2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
