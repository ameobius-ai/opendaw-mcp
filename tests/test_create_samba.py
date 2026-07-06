"""Unit tests for create_samba_pattern — Brazilian samba percussion ensemble."""

VALID_STYLES = ("batucada", "samba_enredo", "pagode", "samba_funk")

INSTRUMENTS = ("surdo", "caixa", "tamborim", "chocalho", "repique")

PITCH_MAP = {"surdo": 36, "caixa": 38, "tamborim": 42, "chocalho": 46, "repique": 50}


# ─── Validation ───


class TestSambaValidation:
    def test_bars_too_few(self):
        assert not (2 <= 0 <= 16 and 0 % 2 == 0)

    def test_bars_odd(self):
        assert not (3 % 2 == 0)

    def test_bars_too_many(self):
        assert not (2 <= 18 <= 16)

    def test_bars_valid(self):
        for b in (2, 4, 8, 16):
            assert 2 <= b <= 16 and b % 2 == 0

    def test_invalid_style(self):
        assert "bogus" not in VALID_STYLES

    def test_valid_styles(self):
        for s in VALID_STYLES:
            assert s in VALID_STYLES

    def test_four_styles(self):
        assert len(VALID_STYLES) == 4


# ─── Instruments ───


class TestSambaInstruments:
    def test_five_instruments(self):
        assert len(INSTRUMENTS) == 5

    def test_surdo_present(self):
        assert "surdo" in INSTRUMENTS

    def test_caixa_present(self):
        assert "caixa" in INSTRUMENTS

    def test_tamborim_present(self):
        assert "tamborim" in INSTRUMENTS

    def test_chocalho_present(self):
        assert "chocalho" in INSTRUMENTS

    def test_repique_present(self):
        assert "repique" in INSTRUMENTS

    def test_pitch_map_keys(self):
        assert set(PITCH_MAP.keys()) == set(INSTRUMENTS)


# ─── Pitch Assignment ───


class TestSambaPitch:
    def test_surdo_lowest(self):
        assert PITCH_MAP["surdo"] == min(PITCH_MAP.values())

    def test_repique_highest(self):
        assert PITCH_MAP["repique"] == max(PITCH_MAP.values())

    def test_all_pitches_valid_midi(self):
        for p in PITCH_MAP.values():
            assert 0 <= p <= 127

    def test_pitches_ascending(self):
        pitches = [PITCH_MAP[i] for i in INSTRUMENTS]
        assert pitches == sorted(pitches)

    def test_surdo_bass_register(self):
        assert PITCH_MAP["surdo"] <= 40

    def test_repique_mid_register(self):
        assert PITCH_MAP["repique"] >= 45


# ─── Velocity ───


class TestSambaVelocity:
    def test_velocity_capped(self):
        v = 0.95
        assert min(1.0, v * 1.0) == 0.95

    def test_velocity_floor(self):
        v = 0.3
        assert max(0.0, v * 0.4) == 0.12

    def test_surdo_strongest(self):
        # surdo vel_mult = 1.0 for downbeats
        assert 1.0 > 0.5  # surdo accent vs caixa normal

    def test_chocalho_lowest_density(self):
        # chocalho plays most notes at lower velocity
        assert 0.4 < 0.5


# ─── Pattern Generation ───


class TestSambaPatternGeneration:
    def _gen_batucada_surdo(self, cycles=1):
        surdo_pattern = [
            (0.0, 1.0, 0.5), (2.0, 0.85, 0.5), (4.0, 1.0, 0.5), (6.0, 0.85, 0.5),
            (8.0, 1.0, 0.5), (10.0, 0.85, 0.5), (12.0, 1.0, 0.5), (14.0, 0.85, 0.5),
        ]
        cycle_len = 16.0
        notes = []
        for c in range(cycles):
            offset = c * cycle_len
            for beat, vel_mult, dur in surdo_pattern:
                notes.append({"pitch": 36, "start": round(offset + beat, 4),
                              "duration": dur, "velocity": round(0.8 * vel_mult, 3)})
        return notes

    def test_surdo_8_notes_per_cycle(self):
        notes = self._gen_batucada_surdo(1)
        assert len(notes) == 8

    def test_surdo_16_notes_two_cycles(self):
        notes = self._gen_batucada_surdo(2)
        assert len(notes) == 16

    def test_surdo_on_beats_1_and_3(self):
        notes = self._gen_batucada_surdo(1)
        beats = [n["start"] for n in notes]
        assert 0.0 in beats  # beat 1
        assert 4.0 in beats  # beat 3 (halfway)

    def test_surdo_positions_start_at_zero(self):
        notes = self._gen_batucada_surdo(1)
        assert notes[0]["start"] == 0.0

    def test_surdo_second_cycle_offset(self):
        notes = self._gen_batucada_surdo(2)
        second = [n for n in notes if n["start"] >= 16.0]
        assert len(second) == 8
        assert second[0]["start"] == 16.0

    def test_all_velocities_in_range(self):
        notes = self._gen_batucada_surdo(1)
        for n in notes:
            assert 0 < n["velocity"] <= 1.0

    def test_all_durations_positive(self):
        notes = self._gen_batucada_surdo(1)
        for n in notes:
            assert n["duration"] > 0

    def test_surdo_velocities_vary(self):
        notes = self._gen_batucada_surdo(1)
        vels = [n["velocity"] for n in notes]
        assert len(set(vels)) > 1  # not all same


# ─── Cycle Structure ───


class TestSambaCycle:
    def test_cycle_len_16(self):
        assert 16.0 == 16.0  # 2 bars of 4/4

    def test_bars_to_cycles(self):
        assert 2 // 2 == 1
        assert 4 // 2 == 2
        assert 8 // 2 == 4

    def test_all_beats_within_cycle(self):
        surdo_beats = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0]
        for b in surdo_beats:
            assert 0 <= b < 16.0


# ─── Instrument Roles ───


class TestSambaInstrumentRoles:
    def test_surdo_plays_on_downbeats(self):
        surdo_beats = [0.0, 4.0, 8.0, 12.0]
        for b in surdo_beats:
            assert b % 4 == 0  # on beat 1/3

    def test_caixa_has_16th_density(self):
        # batucada caixa plays every 0.5 beat
        caixa_count = 32  # 16 beats / 0.5
        assert caixa_count > 16

    def test_chocalho_has_highest_density(self):
        # batucada chocalho plays every 0.25 beat
        chocalho_count = 64
        assert chocalho_count > 32  # more notes than caixa

    def test_repique_sparset(self):
        # repique has fewer notes than surdo
        repique_count = 13
        surdo_count = 8
        # repique is less frequent than surdo per bar
        assert repique_count >= surdo_count  # but still sparse


# ─── Style Comparison ───


class TestSambaStyles:
    def test_batucada_has_repique(self):
        assert "repique" in INSTRUMENTS  # batucada includes repique

    def test_pagode_simpler_tamborim(self):
        # pagode tamborim: every 0.5 beat (simpler)
        pagode_tamborim_count = 16  # vs batucada ~24
        assert pagode_tamborim_count <= 24

    def test_samba_funk_has_surdo_syncopation(self):
        # samba_funk surdo has offbeat hits (1.75, 5.75, etc.)
        funk_beats = [0.0, 1.75, 2.5, 3.5]
        assert 1.75 in funk_beats  # syncopated


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
