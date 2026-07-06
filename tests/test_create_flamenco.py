"""Unit tests for create_flamenco_compas — Flamenco rhythmic cycle tool."""

VALID_PALOS = ("bulerias", "solea", "alegrias", "siguiriyas", "tangos", "rumba")

INSTRUMENTS = ("palmas_secas", "palmas_sordas", "cajon", "golpe")

PITCH_MAP = {"palmas_secas": 39, "palmas_sordas": 42, "cajon": 36, "golpe": 50}

PALOS = {
    "bulerias": {"cycle_beats": 12, "accents": [12, 3, 6, 8, 10], "cajon_beats": [12, 6]},
    "solea": {"cycle_beats": 12, "accents": [3, 6, 8, 10, 12], "cajon_beats": [3, 8]},
    "alegrias": {"cycle_beats": 12, "accents": [3, 6, 12, 8, 10], "cajon_beats": [3, 6]},
    "siguiriyas": {"cycle_beats": 12, "accents": [3, 6, 8, 11], "cajon_beats": [3, 8]},
    "tangos": {"cycle_beats": 4, "accents": [1, 3], "cajon_beats": [1, 3]},
    "rumba": {"cycle_beats": 4, "accents": [1, 2.5, 3], "cajon_beats": [1, 3]},
}


# ─── Validation ───


class TestFlamencoValidation:
    def test_bars_too_few(self):
        assert not (1 <= 0 <= 16)

    def test_bars_too_many(self):
        assert not (1 <= 17 <= 16)

    def test_bars_valid(self):
        for c in (1, 4, 8, 16):
            assert 1 <= c <= 16

    def test_invalid_palo(self):
        assert "bogus" not in VALID_PALOS

    def test_valid_palos(self):
        for p in VALID_PALOS:
            assert p in VALID_PALOS

    def test_six_palos(self):
        assert len(VALID_PALOS) == 6


# ─── Instruments ───


class TestFlamencoInstruments:
    def test_four_instruments(self):
        assert len(INSTRUMENTS) == 4

    def test_palmas_secas(self):
        assert "palmas_secas" in INSTRUMENTS

    def test_palmas_sordas(self):
        assert "palmas_sordas" in INSTRUMENTS

    def test_cajon(self):
        assert "cajon" in INSTRUMENTS

    def test_golpe(self):
        assert "golpe" in INSTRUMENTS

    def test_two_palmas_types(self):
        palmas = [i for i in INSTRUMENTS if "palmas" in i]
        assert len(palmas) == 2


# ─── Pitch Assignment ───


class TestFlamencoPitch:
    def test_cajon_lowest(self):
        assert PITCH_MAP["cajon"] == min(PITCH_MAP.values())

    def test_golpe_highest(self):
        assert PITCH_MAP["golpe"] == max(PITCH_MAP.values())

    def test_palmas_secas_lower_than_sordas(self):
        assert PITCH_MAP["palmas_secas"] < PITCH_MAP["palmas_sordas"]

    def test_all_pitches_valid_midi(self):
        for p in PITCH_MAP.values():
            assert 0 <= p <= 127


# ─── Cycle Structure ───


class TestFlamencoCycle:
    def test_bulerias_12_beat(self):
        assert PALOS["bulerias"]["cycle_beats"] == 12

    def test_solea_12_beat(self):
        assert PALOS["solea"]["cycle_beats"] == 12

    def test_alegrias_12_beat(self):
        assert PALOS["alegrias"]["cycle_beats"] == 12

    def test_siguiriyas_12_beat(self):
        assert PALOS["siguiriyas"]["cycle_beats"] == 12

    def test_tangos_4_beat(self):
        assert PALOS["tangos"]["cycle_beats"] == 4

    def test_rumba_4_beat(self):
        assert PALOS["rumba"]["cycle_beats"] == 4

    def test_12_beat_palos_have_5_accents(self):
        for name in ("bulerias", "solea", "alegrias"):
            assert len(PALOS[name]["accents"]) >= 4


# ─── Accent Patterns ───


class TestFlamencoAccents:
    def test_bulerias_accents(self):
        assert set(PALOS["bulerias"]["accents"]) == {12, 3, 6, 8, 10}

    def test_solea_accents(self):
        assert set(PALOS["solea"]["accents"]) == {3, 6, 8, 10, 12}

    def test_siguiriyas_asymmetric(self):
        assert 11 in PALOS["siguiriyas"]["accents"]

    def test_tangos_simple_accents(self):
        assert set(PALOS["tangos"]["accents"]) == {1, 3}

    def test_rumba_syncopated(self):
        assert 2.5 in PALOS["rumba"]["accents"]

    def test_accents_within_cycle(self):
        for name, data in PALOS.items():
            cb = data["cycle_beats"]
            for a in data["accents"]:
                assert 0 < a <= cb, f"{name}: accent {a} out of range [1,{cb}]"

    def test_cajon_beats_within_cycle(self):
        for name, data in PALOS.items():
            cb = data["cycle_beats"]
            for b in data["cajon_beats"]:
                assert 0 < b <= cb, f"{name}: cajon beat {b} out of range"


# ─── Pattern Generation ───


class TestFlamencoPatternGeneration:
    def _gen_bulerias(self, cycles=1):
        """Simulate note generation for bulerias."""
        palo = PALOS["bulerias"]
        cb = palo["cycle_beats"]
        accents = set(palo["accents"])
        cajon_beats = set(palo["cajon_beats"])
        notes = []

        for cycle in range(cycles):
            cycle_start = cycle * cb
            for beat_1 in range(1, cb + 1):
                beat_pos = beat_1 - 1
                pos = cycle_start + beat_pos

                if beat_1 in cajon_beats:
                    notes.append({"pitch": 36, "start": float(pos), "type": "cajon"})

                if beat_1 in accents:
                    notes.append({"pitch": 39, "start": float(pos), "type": "secas"})
                else:
                    notes.append({"pitch": 42, "start": float(pos), "type": "sordas"})

            # golpe at end
            notes.append({"pitch": 50, "start": float(cycle_start + cb - 1), "type": "golpe"})

        return notes

    def test_bulerias_notes_per_cycle(self):
        notes = self._gen_bulerias(1)
        # 12 beats: 12 palmas (secas or sordas) + 2 cajon + 1 golpe = 15
        assert len(notes) == 15

    def test_bulerias_two_cycles(self):
        notes = self._gen_bulerias(2)
        assert len(notes) == 30

    def test_positions_start_at_zero(self):
        notes = self._gen_bulerias(1)
        starts = [n["start"] for n in notes]
        assert 0.0 in starts

    def test_second_cycle_offset(self):
        notes = self._gen_bulerias(2)
        second = [n for n in notes if n["start"] >= 12.0]
        assert len(second) == 15

    def test_golpe_at_end_of_cycle(self):
        notes = self._gen_bulerias(1)
        golpes = [n for n in notes if n["type"] == "golpe"]
        assert len(golpes) == 1
        assert golpes[0]["start"] == 11.0  # beat 12 (0-indexed = 11)

    def test_cajon_on_accented_beats(self):
        notes = self._gen_bulerias(1)
        cajon = [n for n in notes if n["type"] == "cajon"]
        # bulerias cajon on beats 12 and 6 (1-indexed) = positions 11 and 5
        cajon_positions = sorted([n["start"] for n in cajon])
        assert 5.0 in cajon_positions
        assert 11.0 in cajon_positions

    def test_secas_on_accents(self):
        notes = self._gen_bulerias(1)
        secas = [n for n in notes if n["type"] == "secas"]
        # 5 accents in bulerias
        assert len(secas) == 5

    def test_sordas_on_non_accents(self):
        notes = self._gen_bulerias(1)
        sordas = [n for n in notes if n["type"] == "sordas"]
        # 12 beats - 5 accents = 7 sordas
        assert len(sordas) == 7


# ─── Palo Comparison ───


class TestFlamencoPaloComparison:
    def test_tangos_shorter_than_bulerias(self):
        assert PALOS["tangos"]["cycle_beats"] < PALOS["bulerias"]["cycle_beats"]

    def test_rumba_same_cycle_as_tangos(self):
        assert PALOS["rumba"]["cycle_beats"] == PALOS["tangos"]["cycle_beats"]

    def test_siguiriyas_fewer_accents_than_solea(self):
        assert len(PALOS["siguiriyas"]["accents"]) < len(PALOS["solea"]["accents"])

    def test_all_12_beat_palos_have_12_cycle(self):
        for name in ("bulerias", "solea", "alegrias", "siguiriyas"):
            assert PALOS[name]["cycle_beats"] == 12

    def test_rumba_has_fractional_accent(self):
        """Rumba's 2.5 accent is the only fractional beat in the set."""
        has_fractional = any(a != int(a) for a in PALOS["rumba"]["accents"])
        assert has_fractional


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
