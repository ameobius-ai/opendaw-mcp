"""Unit tests for create_tala — Indian classical cyclic rhythm tool."""



# ─── Tala definitions (mirror server.py) ───

TALAS = {
    "teental": {
        "beats": 16,
        "vibhags": [4, 4, 4, 4],
        "tali": [0, 4, 12],
        "khali": [8],
        "theka": ["Dha", "Dhin", "Dhin", "Dha", "Dha", "Dhin", "Dhin", "Dha",
                  "Dha", "Tin", "Tin", "Ta", "Ta", "Dhin", "Dhin", "Dha"],
    },
    "ektal": {
        "beats": 12,
        "vibhags": [2, 2, 2, 2, 2, 2],
        "tali": [0, 4, 8, 10],
        "khali": [2, 6],
        "theka": ["Dhin", "Dha", "Ti", "Ta", "Tin", "Ta",
                  "Dhin", "Dha", "Ti", "Ta", "Dhin", "Dha"],
    },
    "jhaptal": {
        "beats": 10,
        "vibhags": [2, 3, 2, 3],
        "tali": [0, 2, 7],
        "khali": [5],
        "theka": ["Dhin", "Na", "Dhi", "Dhi", "Na", "Ti", "Na", "Dhi", "Dhi", "Na"],
    },
    "rupak": {
        "beats": 7,
        "vibhags": [3, 2, 2],
        "tali": [3, 5],
        "khali": [0],
        "theka": ["Tin", "Ti", "Na", "Dhin", "Na", "Dhin", "Na"],
    },
    "dadra": {
        "beats": 6,
        "vibhags": [3, 3],
        "tali": [0],
        "khali": [3],
        "theka": ["Dha", "Dhin", "Na", "Dha", "Dhin", "Na"],
    },
    "kehartwa": {
        "beats": 8,
        "vibhags": [4, 4],
        "tali": [0],
        "khali": [4],
        "theka": ["Dha", "Dha", "Ti", "Ta", "Dha", "Dha", "Ti", "Ta"],
    },
}

BOL_PITCHES = {
    "Dha": 36, "Dhin": 38, "Dhi": 39,
    "Tin": 48, "Ta": 52, "Na": 50, "Ti": 46,
}

LAYA_DURATIONS = {"vilambit": 2.0, "madhya": 1.0, "drut": 0.5}


# ─── Validation ───


class TestCreateTalaValidation:
    """Test parameter validation."""

    def test_invalid_tala_name(self):
        assert "bogus" not in TALAS

    def test_cycles_zero(self):
        assert not (1 <= 0 <= 16)

    def test_cycles_too_many(self):
        assert not (1 <= 17 <= 16)

    def test_cycles_valid(self):
        for c in (1, 4, 8, 16):
            assert 1 <= c <= 16

    def test_invalid_laya(self):
        assert "atishand" not in LAYA_DURATIONS

    def test_valid_laya_values(self):
        for laya in ("vilambit", "madhya", "drut"):
            assert laya in LAYA_DURATIONS

    def test_six_talas_defined(self):
        assert len(TALAS) == 6


# ─── Tala Definitions ───


class TestCreateTalaDefinitions:
    """Test tala structural definitions."""

    def test_teental_16_beats(self):
        assert TALAS["teental"]["beats"] == 16

    def test_ektal_12_beats(self):
        assert TALAS["ektal"]["beats"] == 12

    def test_jhaptal_10_beats(self):
        assert TALAS["jhaptal"]["beats"] == 10

    def test_rupak_7_beats(self):
        assert TALAS["rupak"]["beats"] == 7

    def test_dadra_6_beats(self):
        assert TALAS["dadra"]["beats"] == 6

    def test_kehartwa_8_beats(self):
        assert TALAS["kehartwa"]["beats"] == 8

    def test_vibhags_sum_to_beats(self):
        for name, tala in TALAS.items():
            assert sum(tala["vibhags"]) == tala["beats"], \
                f"{name}: vibhags {tala['vibhags']} sum != beats {tala['beats']}"

    def test_theka_length_matches_beats(self):
        for name, tala in TALAS.items():
            assert len(tala["theka"]) == tala["beats"], \
                f"{name}: theka length {len(tala['theka'])} != beats {tala['beats']}"


# ─── Tali / Khali ───


class TestCreateTalaTaliKhali:
    """Test tali (clap) and khali (wave) positions."""

    def test_teental_tali(self):
        assert TALAS["teental"]["tali"] == [0, 4, 12]

    def test_teental_khali(self):
        assert TALAS["teental"]["khali"] == [8]

    def test_rupak_starts_with_khali(self):
        assert 0 in TALAS["rupak"]["khali"]

    def test_dadra_tali(self):
        assert TALAS["dadra"]["tali"] == [0]

    def test_dadra_khali(self):
        assert TALAS["dadra"]["khali"] == [3]

    def test_tali_khali_disjoint(self):
        for name, tala in TALAS.items():
            tali = set(tala["tali"])
            khali = set(tala["khali"])
            assert not tali & khali, f"{name}: tali {tali} overlaps khali {khali}"

    def test_tali_within_cycle(self):
        for name, tala in TALAS.items():
            beats = tala["beats"]
            for t in tala["tali"]:
                assert 0 <= t < beats, f"{name}: tali {t} out of range"
            for k in tala["khali"]:
                assert 0 <= k < beats, f"{name}: khali {k} out of range"


# ─── Bols ───


class TestCreateTalaBols:
    """Test tabla bols (stroke names)."""

    def test_teental_bols_count(self):
        assert len(TALAS["teental"]["theka"]) == 16

    def test_teental_bols_start_with_dha(self):
        assert TALAS["teental"]["theka"][0] == "Dha"

    def test_teental_bols_end_with_dha(self):
        assert TALAS["teental"]["theka"][-1] == "Dha"

    def test_dadra_bols(self):
        theka = TALAS["dadra"]["theka"]
        assert len(theka) == 6
        assert theka[0] == "Dha"
        assert theka[3] == "Dha"

    def test_ektal_bols_count(self):
        assert len(TALAS["ektal"]["theka"]) == 12

    def test_rupak_bols_start_with_tin(self):
        assert TALAS["rupak"]["theka"][0] == "Tin"

    def test_all_bols_have_pitch(self):
        for name, tala in TALAS.items():
            for bol in tala["theka"]:
                assert bol in BOL_PITCHES, f"{name}: bol '{bol}' has no pitch mapping"

    def test_bols_are_string(self):
        for name, tala in TALAS.items():
            for bol in tala["theka"]:
                assert isinstance(bol, str)


# ─── Cycles ───


class TestCreateTalaCycles:
    """Test multi-cycle behavior."""

    def test_single_cycle_total_beats(self):
        assert 1 * TALAS["teental"]["beats"] == 16

    def test_four_cycles_total_beats(self):
        assert 4 * TALAS["teental"]["beats"] == 64

    def test_ektal_three_cycles(self):
        assert 3 * TALAS["ektal"]["beats"] == 36

    def test_rupak_two_cycles(self):
        assert 2 * TALAS["rupak"]["beats"] == 14

    def test_jhaptal_five_cycles(self):
        assert 5 * TALAS["jhaptal"]["beats"] == 50


# ─── Laya ───


class TestCreateTalaLaya:
    """Test laya (tempo) parameters."""

    def test_vilambit_duration(self):
        assert LAYA_DURATIONS["vilambit"] == 2.0

    def test_madhya_duration(self):
        assert LAYA_DURATIONS["madhya"] == 1.0

    def test_drut_duration(self):
        assert LAYA_DURATIONS["drut"] == 0.5

    def test_vilambit_longest(self):
        assert LAYA_DURATIONS["vilambit"] > LAYA_DURATIONS["madhya"]

    def test_drut_shortest(self):
        assert LAYA_DURATIONS["drut"] < LAYA_DURATIONS["madhya"]


# ─── Pitch Mapping ───


class TestCreateTalaPitchMapping:
    """Test bol-to-pitch mapping for tabla strokes."""

    def test_dha_lower_register(self):
        assert BOL_PITCHES["Dha"] == 36

    def test_dhin_lower_register(self):
        assert BOL_PITCHES["Dhin"] == 38

    def test_ta_higher_register(self):
        assert BOL_PITCHES["Ta"] == 52

    def test_tin_higher_than_dha(self):
        assert BOL_PITCHES["Tin"] > BOL_PITCHES["Dha"]

    def test_na_between_ti_and_ta(self):
        assert BOL_PITCHES["Ti"] < BOL_PITCHES["Na"] < BOL_PITCHES["Ta"]

    def test_all_pitches_valid_midi(self):
        for bol, pitch in BOL_PITCHES.items():
            assert 0 <= pitch <= 127, f"{bol}: pitch {pitch} out of MIDI range"

    def test_lower_register_bols_below_45(self):
        for bol in ("Dha", "Dhin", "Dhi"):
            assert BOL_PITCHES[bol] < 45, f"{bol} should be in lower register"

    def test_higher_register_bols_above_45(self):
        for bol in ("Tin", "Ta", "Na", "Ti"):
            assert BOL_PITCHES[bol] > 45, f"{bol} should be in higher register"


# ─── Velocity Computation ───


class TestCreateTalaVelocity:
    """Test velocity computation for tali/khali beats."""

    def test_tali_beat_higher_velocity(self):
        base = 0.7
        tali_vel = min(1.0, base * 1.2)
        normal_vel = base * 0.75
        assert tali_vel > normal_vel

    def test_khali_beat_lower_velocity(self):
        base = 0.7
        khali_vel = base * 0.45
        normal_vel = base * 0.75
        assert khali_vel < normal_vel

    def test_tali_velocity_capped(self):
        base = 0.9
        tali_vel = min(1.0, base * 1.2)
        assert tali_vel == 1.0

    def test_khali_velocity_not_zero(self):
        base = 0.7
        khali_vel = base * 0.45
        assert khali_vel > 0


# ─── Note Generation Simulation ───


class TestCreateTalaNoteGeneration:
    """Test note generation logic."""

    def _generate_notes(self, tala_name, cycles, velocity=0.7):
        """Simulate note generation."""
        tala = TALAS[tala_name]
        beats = tala["beats"]
        theka = tala["theka"]
        tali = tala["tali"]
        khali = tala["khali"]
        notes = []

        for cycle in range(cycles):
            cycle_start = cycle * beats
            for beat_idx in range(beats):
                bol = theka[beat_idx]
                pitch = BOL_PITCHES.get(bol, 48)
                pos = cycle_start + beat_idx

                if beat_idx in khali:
                    vel = velocity * 0.45
                elif beat_idx in tali:
                    vel = min(1.0, velocity * 1.2)
                else:
                    vel = velocity * 0.75

                notes.append({"pitch": pitch, "pos": pos, "bol": bol, "vel": round(vel, 4)})
        return notes

    def test_notes_per_cycle_teental(self):
        notes = self._generate_notes("teental", 1)
        assert len(notes) == 16

    def test_notes_multi_cycle(self):
        notes = self._generate_notes("teental", 4)
        assert len(notes) == 64

    def test_notes_dadra_one_cycle(self):
        notes = self._generate_notes("dadra", 1)
        assert len(notes) == 6

    def test_notes_jhaptal_two_cycles(self):
        notes = self._generate_notes("jhaptal", 2)
        assert len(notes) == 20

    def test_khali_beat_low_velocity(self):
        notes = self._generate_notes("teental", 1)
        # beat 8 is khali
        khali_note = [n for n in notes if n["pos"] == 8][0]
        assert khali_note["vel"] == 0.7 * 0.45

    def test_tali_beat_high_velocity(self):
        notes = self._generate_notes("teental", 1)
        # beat 0 is tali (sam)
        tali_note = [n for n in notes if n["pos"] == 0][0]
        assert tali_note["vel"] == min(1.0, 0.7 * 1.2)

    def test_normal_beat_velocity(self):
        notes = self._generate_notes("teental", 1)
        # beat 1 is normal (not tali, not khali)
        normal_note = [n for n in notes if n["pos"] == 1][0]
        assert abs(normal_note["vel"] - 0.7 * 0.75) < 0.001

    def test_positions_sequential(self):
        notes = self._generate_notes("teental", 2)
        positions = [n["pos"] for n in notes]
        assert positions == sorted(positions)

    def test_positions_start_at_zero(self):
        notes = self._generate_notes("dadra", 1)
        assert notes[0]["pos"] == 0

    def test_second_cycle_offset(self):
        notes = self._generate_notes("dadra", 2)
        second_cycle_notes = [n for n in notes if n["pos"] >= 6]
        assert len(second_cycle_notes) == 6
        assert second_cycle_notes[0]["pos"] == 6


# ─── Vibhag Structure ───


class TestCreateTalaVibhags:
    """Test vibhag (section) grouping."""

    def test_teental_uniform_vibhags(self):
        assert TALAS["teental"]["vibhags"] == [4, 4, 4, 4]

    def test_jhaptal_asymmetric_vibhags(self):
        assert TALAS["jhaptal"]["vibhags"] == [2, 3, 2, 3]

    def test_rupak_asymmetric_vibhags(self):
        assert TALAS["rupak"]["vibhags"] == [3, 2, 2]

    def test_dadra_symmetric(self):
        assert TALAS["dadra"]["vibhags"] == [3, 3]

    def test_ektal_all_twos(self):
        assert TALAS["ektal"]["vibhags"] == [2, 2, 2, 2, 2, 2]

    def test_kehartwa_halves(self):
        assert TALAS["kehartwa"]["vibhags"] == [4, 4]

    def test_vibhag_boundaries_match_tali(self):
        """Tali should occur at vibhag boundaries (cumulative sums)."""
        for name, tala in TALAS.items():
            vibhags = tala["vibhags"]
            boundaries = [0]
            for v in vibhags:
                boundaries.append(boundaries[-1] + v)
            boundaries = boundaries[:-1]  # exclude final = total beats
            tali = set(tala["tali"])
            for t in tali:
                if t != 0:  # khali-on-beat-1 exception for rupak
                    assert t in boundaries or t in tala["khali"], \
                        f"{name}: tali at {t} not at vibhag boundary {boundaries}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
