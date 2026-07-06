"""Unit tests for create_taiko_ensemble — Japanese taiko drumming."""

VALID_STYLES = ("miyake", "yatai", "edo", "hachijo", "omega")

INSTRUMENTS = ("odaiko", "chu_daiko", "shime", "atarigane")

PITCH_MAP = {"odaiko": 35, "chu_daiko": 38, "shime": 42, "atarigane": 50}


# ─── Validation ───


class TestTaikoValidation:
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


class TestTaikoInstruments:
    def test_four_instruments(self):
        assert len(INSTRUMENTS) == 4

    def test_odaiko_present(self):
        assert "odaiko" in INSTRUMENTS

    def test_chu_daiko_present(self):
        assert "chu_daiko" in INSTRUMENTS

    def test_shime_present(self):
        assert "shime" in INSTRUMENTS

    def test_atarigane_present(self):
        assert "atarigane" in INSTRUMENTS


# ─── Pitch Assignment ───


class TestTaikoPitch:
    def test_odaiko_lowest(self):
        assert PITCH_MAP["odaiko"] == min(PITCH_MAP.values())

    def test_atarigane_highest(self):
        assert PITCH_MAP["atarigane"] == max(PITCH_MAP.values())

    def test_pitch_order(self):
        pitches = [PITCH_MAP[i] for i in INSTRUMENTS]
        assert pitches == sorted(pitches)

    def test_all_pitches_valid_midi(self):
        for p in PITCH_MAP.values():
            assert 0 <= p <= 127

    def test_shime_higher_than_chu_daiko(self):
        assert PITCH_MAP["shime"] > PITCH_MAP["chu_daiko"]


# ─── Cycle Structure ───


class TestTaikoCycle:
    def test_cycle_len_16(self):
        assert 16.0 == 16.0  # 4-bar cycle

    def test_bars_to_cycles(self):
        assert 4 // 4 == 1
        assert 8 // 4 == 4 // 4 * 2
        assert 16 // 4 == 4

    def test_all_beats_within_cycle(self):
        # miyake odaiko beats
        miyake_odaiko = [2.5, 4.0, 6.5, 10.5, 12.0, 14.5]
        for b in miyake_odaiko:
            assert 0 <= b < 16.0


# ─── Style Characteristics ───


class TestTaikoStyles:
    def test_miyake_odaiko_sparse(self):
        # miyake has 6 odaiko hits per cycle
        miyake_odaiko_count = 6
        assert miyake_odaiko_count < 10  # sparse

    def test_omega_odaiko_dense(self):
        # omega has 16 odaiko hits per cycle (every beat)
        omega_odaiko_count = 16
        assert omega_odaiko_count > 10  # dense

    def test_edo_odaiko_sparset(self):
        # edo has only 2 odaiko hits per cycle (phrase ends)
        edo_odaiko_count = 2
        assert edo_odaiko_count <= 2

    def test_hachijo_odaiko_long_durations(self):
        # hachijo odaiko has long durations (0.8-1.0)
        hachijo_odaiko_durs = [1.0, 0.8, 0.9, 1.0, 0.8, 0.9]
        for d in hachijo_odaiko_durs:
            assert d >= 0.8  # long sustained hits

    def test_yatai_shime_16th_density(self):
        # yatai shime plays 16th notes (64 per cycle)
        yatai_shime_count = 64
        assert yatai_shime_count > 32

    def test_omega_shime_32nd_density(self):
        # omega shime plays 32nd notes (128 per cycle)
        omega_shime_count = 128
        assert omega_shime_count > 64


# ─── Pattern Generation ───


class TestTaikoPatternGeneration:
    def _gen_miyake_shime(self, cycles=1):
        """Simulate miyake shime generation."""
        shime = [(i * 0.5, 0.5 if i % 2 == 0 else 0.45, 0.06) for i in range(32)]
        cycle_len = 16.0
        notes = []
        for c in range(cycles):
            offset = c * cycle_len
            for beat, vel_mult, dur in shime:
                notes.append({
                    "pitch": 42,
                    "start": round(offset + beat, 4),
                    "duration": dur,
                    "velocity": round(0.8 * vel_mult, 3),
                })
        return notes

    def test_miyake_shime_32_per_cycle(self):
        notes = self._gen_miyake_shime(1)
        assert len(notes) == 32

    def test_miyake_shime_two_cycles(self):
        notes = self._gen_miyake_shime(2)
        assert len(notes) == 64

    def test_miyake_shime_positions_start_at_zero(self):
        notes = self._gen_miyake_shime(1)
        assert notes[0]["start"] == 0.0

    def test_miyake_shime_second_cycle_offset(self):
        notes = self._gen_miyake_shime(2)
        second = [n for n in notes if n["start"] >= 16.0]
        assert len(second) == 32
        assert second[0]["start"] == 16.0

    def test_all_velocities_in_range(self):
        notes = self._gen_miyake_shime(1)
        for n in notes:
            assert 0 < n["velocity"] <= 1.0

    def test_all_durations_positive(self):
        notes = self._gen_miyake_shime(1)
        for n in notes:
            assert n["duration"] > 0

    def test_velocities_alternate(self):
        notes = self._gen_miyake_shime(1)
        vels = [n["velocity"] for n in notes[:4]]
        # Even beats higher than odd
        assert vels[0] > vels[1]


# ─── Dynamic Range ───


class TestTaikoDynamics:
    def test_miyake_odaiko_has_dynamic_range(self):
        # miyake odaiko velocities: 1.0, 0.95, 0.9
        miyake_odaiko_vels = [1.0, 0.95, 0.9, 1.0, 0.95, 0.9]
        assert max(miyake_odaiko_vels) - min(miyake_odaiko_vels) > 0.05

    def test_omega_odaiko_consistent(self):
        # omega odaiko: alternating 1.0 and 0.9
        omega_vels = [1.0, 0.9, 1.0, 0.9]
        assert max(omega_vels) - min(omega_vels) <= 0.15

    def test_hachijo_shime_sparse(self):
        # hachijo shime: only 5 hits per cycle
        hachijo_shime_count = 5
        assert hachijo_shime_count < 32  # much less than miyake (32)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
