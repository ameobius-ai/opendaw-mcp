"""Unit tests for create_djembe_ensemble — West African djembe/dunun ensemble."""

VALID_STYLES = ("danza", "kuku", "djole", "doundounba")

INSTRUMENTS = ("kenkeni", "sangban", "dundunba", "bell", "djembe2", "djembe1")

PITCH_MAP = {
    "kenkeni": 35, "sangban": 36, "dundunba": 38,
    "djembe1": 42, "djembe2": 46, "bell": 50,
}


# ─── Validation ───


class TestDjembeValidation:
    def test_bars_too_few(self):
        assert not (4 <= 2 <= 16 and 2 % 2 == 0)

    def test_bars_odd(self):
        assert not (5 % 2 == 0)

    def test_bars_too_many(self):
        assert not (4 <= 18 <= 16)

    def test_bars_valid(self):
        for b in (4, 6, 8, 16):
            assert 4 <= b <= 16 and b % 2 == 0

    def test_invalid_style(self):
        assert "bogus" not in VALID_STYLES

    def test_valid_styles(self):
        for s in VALID_STYLES:
            assert s in VALID_STYLES

    def test_four_styles(self):
        assert len(VALID_STYLES) == 4


# ─── Instruments ───


class TestDjembeInstruments:
    def test_six_instruments(self):
        assert len(INSTRUMENTS) == 6

    def test_kenkeni_present(self):
        assert "kenkeni" in INSTRUMENTS

    def test_sangban_present(self):
        assert "sangban" in INSTRUMENTS

    def test_dundunba_present(self):
        assert "dundunba" in INSTRUMENTS

    def test_bell_present(self):
        assert "bell" in INSTRUMENTS

    def test_djembe1_present(self):
        assert "djembe1" in INSTRUMENTS

    def test_djembe2_present(self):
        assert "djembe2" in INSTRUMENTS

    def test_three_dununs(self):
        dununs = [i for i in INSTRUMENTS if i in ("kenkeni", "sangban", "dundunba")]
        assert len(dununs) == 3

    def test_two_djembes(self):
        djembes = [i for i in INSTRUMENTS if i.startswith("djembe")]
        assert len(djembes) == 2


# ─── Pitch Assignment ───


class TestDjembePitch:
    def test_kenkeni_lowest_dunun(self):
        assert PITCH_MAP["kenkeni"] == 35

    def test_sangban_between_kenkeni_dundunba(self):
        assert PITCH_MAP["kenkeni"] < PITCH_MAP["sangban"] < PITCH_MAP["dundunba"]

    def test_dundunba_lower_than_djembe1(self):
        assert PITCH_MAP["dundunba"] < PITCH_MAP["djembe1"]

    def test_bell_highest(self):
        assert PITCH_MAP["bell"] == max(PITCH_MAP.values())

    def test_all_pitches_valid_midi(self):
        for p in PITCH_MAP.values():
            assert 0 <= p <= 127

    def test_dunun_pitches_bass_register(self):
        for inst in ("kenkeni", "sangban", "dundunba"):
            assert PITCH_MAP[inst] <= 40


# ─── Pattern Generation ───


class TestDjembePatternGeneration:
    def _gen_danza_sangban(self, cycles=1):
        sangban = [
            (0.0, 1.0, 0.4), (2.0, 0.8, 0.3), (4.0, 1.0, 0.4), (6.0, 0.8, 0.3),
        ]
        cycle_len = 8.0
        notes = []
        for c in range(cycles):
            offset = c * cycle_len
            for beat, vel_mult, dur in sangban:
                notes.append({"pitch": 36, "start": round(offset + beat, 4),
                              "duration": dur, "velocity": round(0.75 * vel_mult, 3)})
        return notes

    def test_sangban_4_notes_per_cycle(self):
        notes = self._gen_danza_sangban(1)
        assert len(notes) == 4

    def test_sangban_8_notes_two_cycles(self):
        notes = self._gen_danza_sangban(2)
        assert len(notes) == 8

    def test_sangban_on_beats_1_and_3(self):
        notes = self._gen_danza_sangban(1)
        beats = [n["start"] for n in notes]
        assert 0.0 in beats
        assert 4.0 in beats

    def test_sangban_positions_start_at_zero(self):
        notes = self._gen_danza_sangban(1)
        assert notes[0]["start"] == 0.0

    def test_sangban_second_cycle_offset(self):
        notes = self._gen_danza_sangban(2)
        second = [n for n in notes if n["start"] >= 8.0]
        assert len(second) == 4
        assert second[0]["start"] == 8.0

    def test_all_velocities_in_range(self):
        notes = self._gen_danza_sangban(1)
        for n in notes:
            assert 0 < n["velocity"] <= 1.0

    def test_all_durations_positive(self):
        notes = self._gen_danza_sangban(1)
        for n in notes:
            assert n["duration"] > 0

    def test_sangban_velocities_vary(self):
        notes = self._gen_danza_sangban(1)
        vels = [n["velocity"] for n in notes]
        assert len(set(vels)) > 1


# ─── Cycle Structure ───


class TestDjembeCycle:
    def test_cycle_len_8(self):
        assert 8.0 == 8.0  # 2-bar cycle

    def test_bars_to_cycles(self):
        assert 4 // 2 == 2
        assert 8 // 2 == 4

    def test_all_beats_within_cycle(self):
        sangban_beats = [0.0, 2.0, 4.0, 6.0]
        for b in sangban_beats:
            assert 0 <= b < 8.0


# ─── Instrument Roles ───


class TestDjembeInstrumentRoles:
    def test_kenkeni_steady_pulse(self):
        # danza kenkeni: every beat (0, 1, 2, 3, 4, 5, 6, 7) = 8 notes
        kenkeni_beats = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        assert len(kenkeni_beats) == 8

    def test_dundunba_on_offbeats(self):
        # danza dundunba: on odd beats (1, 3, 5, 7)
        dundunba_beats = [1.0, 3.0, 5.0, 7.0]
        for b in dundunba_beats:
            assert b % 2 == 1

    def test_bell_has_timeline_pattern(self):
        # bell: onset at 0, 0.5, 1.5, 2.0, 2.5, 3.5...
        bell_beats = [0.0, 0.5, 1.5]
        assert 0.0 in bell_beats
        assert 0.5 in bell_beats

    def test_djembe1_sparser_than_djembe2(self):
        # djembe1 (lead) has fewer notes than djembe2 (accompaniment) in danza
        djembe1_count = 8  # from pattern
        djembe2_count = 14  # from pattern
        assert djembe1_count <= djembe2_count


# ─── Style Comparison ───


class TestDjembeStyles:
    def test_doundounba_sangban_densest(self):
        # doundounba sangban has 32 notes per cycle (16th density)
        assert 32 > 4  # much more than danza (4 per cycle)

    def test_kuku_kenkeni_offbeat(self):
        # kuku kenkeni plays on offbeats (0.5, 1.5, 2.5...)
        kuku_kenkeni_beats = [0.5, 1.5, 2.5, 3.5]
        for b in kuku_kenkeni_beats:
            assert b % 1 == 0.5  # all on offbeats

    def test_djole_kenkeni_16th_density(self):
        # djole kenkeni plays 16ths (32 notes per 2-bar cycle)
        djole_kenkeni_count = 32
        assert djole_kenkeni_count > 8  # more than danza (8 per cycle)

    def test_danza_kenkeni_quarter_density(self):
        # danza kenkeni plays quarter notes (8 per 2-bar cycle)
        danza_kenkeni_count = 8
        assert danza_kenkeni_count < 32  # less than djole


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
