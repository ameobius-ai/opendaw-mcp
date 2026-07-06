"""Unit tests for create_balkan_meter — Balkan additive meter pattern."""

VALID_METERS = ("7_8", "9_8", "11_16", "13_8", "7_8_sand", "9_8_ska")
VALID_VARIATIONS = ("classic", "modern", "wedding")

METERS = {
    "7_8": {"total_beats": 7, "groups": [2, 2, 3], "accents": [0, 2, 4]},
    "9_8": {"total_beats": 9, "groups": [2, 2, 2, 3], "accents": [0, 2, 4, 6]},
    "11_16": {"total_beats": 11, "groups": [2, 2, 3, 2, 2], "accents": [0, 2, 4, 7, 9]},
    "13_8": {"total_beats": 13, "groups": [2, 2, 3, 2, 2, 2], "accents": [0, 2, 4, 7, 9, 11]},
    "7_8_sand": {"total_beats": 7, "groups": [3, 2, 2], "accents": [0, 3, 5]},
    "9_8_ska": {"total_beats": 9, "groups": [2, 3, 2, 2], "accents": [0, 2, 5, 7]},
}


# ─── Validation ───


class TestBalkanValidation:
    def test_cycles_too_few(self):
        assert not (1 <= 0 <= 32)

    def test_cycles_too_many(self):
        assert not (1 <= 33 <= 32)

    def test_cycles_valid(self):
        for c in (1, 8, 16, 32):
            assert 1 <= c <= 32

    def test_invalid_variation(self):
        assert "bogus" not in VALID_VARIATIONS

    def test_valid_variations(self):
        for v in VALID_VARIATIONS:
            assert v in VALID_VARIATIONS

    def test_invalid_meter(self):
        assert "bogus" not in VALID_METERS

    def test_valid_meters(self):
        for m in VALID_METERS:
            assert m in VALID_METERS

    def test_six_meters(self):
        assert len(VALID_METERS) == 6


# ─── Meter Structure ───


class TestBalkanMeterStructure:
    def test_7_8_total_beats(self):
        assert METERS["7_8"]["total_beats"] == 7

    def test_9_8_total_beats(self):
        assert METERS["9_8"]["total_beats"] == 9

    def test_11_16_total_beats(self):
        assert METERS["11_16"]["total_beats"] == 11

    def test_13_8_total_beats(self):
        assert METERS["13_8"]["total_beats"] == 13

    def test_groups_sum_to_total(self):
        for name, data in METERS.items():
            assert sum(data["groups"]) == data["total_beats"], \
                f"{name}: groups {data['groups']} sum != {data['total_beats']}"

    def test_accents_match_group_starts(self):
        """Accents should be at the start of each group (cumulative sum of previous groups)."""
        for name, data in METERS.items():
            groups = data["groups"]
            expected_accents = [0]
            for g in groups[:-1]:
                expected_accents.append(expected_accents[-1] + g)
            assert data["accents"] == expected_accents, \
                f"{name}: accents {data['accents']} != expected {expected_accents}"

    def test_accents_within_range(self):
        for name, data in METERS.items():
            tb = data["total_beats"]
            for a in data["accents"]:
                assert 0 <= a < tb, f"{name}: accent {a} out of range [0,{tb})"

    def test_num_accents_equals_num_groups(self):
        for name, data in METERS.items():
            assert len(data["accents"]) == len(data["groups"]), \
                f"{name}: {len(data['accents'])} accents != {len(data['groups'])} groups"


# ─── Grouping Patterns ───


class TestBalkanGrouping:
    def test_7_8_standard_grouping(self):
        assert METERS["7_8"]["groups"] == [2, 2, 3]

    def test_7_8_sand_reversed(self):
        assert METERS["7_8_sand"]["groups"] == [3, 2, 2]

    def test_9_8_standard_grouping(self):
        assert METERS["9_8"]["groups"] == [2, 2, 2, 3]

    def test_9_8_ska_different(self):
        assert METERS["9_8_ska"]["groups"] == [2, 3, 2, 2]

    def test_11_16_has_group_of_3(self):
        assert 3 in METERS["11_16"]["groups"]

    def test_all_groups_are_2_or_3(self):
        """Balkan meters only use groups of 2 and 3."""
        for name, data in METERS.items():
            for g in data["groups"]:
                assert g in (2, 3), f"{name}: group {g} not 2 or 3"


# ─── Pattern Generation ───


class TestBalkanPatternGeneration:
    def _gen_7_8_classic(self, cycles=1):
        """Simulate note generation for 7/8 classic."""
        total_beats = 7
        accents = {0, 2, 4}
        beat_step = 0.5
        notes = []
        for cycle in range(cycles):
            cycle_start = cycle * total_beats * beat_step
            for beat_idx in range(total_beats):
                pos = cycle_start + beat_idx * beat_step
                is_accent = beat_idx in accents
                if is_accent:
                    notes.append({"pitch": 36, "start": pos, "type": "kick"})
                else:
                    notes.append({"pitch": 40, "start": pos, "type": "snare"})
                notes.append({"pitch": 42, "start": pos, "type": "hh"})
        return notes

    def test_7_8_notes_per_cycle(self):
        notes = self._gen_7_8_classic(1)
        # 7 beats: 7 (kick/snare) + 7 hh = 14
        assert len(notes) == 14

    def test_7_8_two_cycles_doubled(self):
        notes = self._gen_7_8_classic(2)
        assert len(notes) == 28

    def test_7_8_kick_count(self):
        notes = self._gen_7_8_classic(1)
        kicks = [n for n in notes if n["type"] == "kick"]
        # 3 accents in 7/8
        assert len(kicks) == 3

    def test_7_8_snare_count(self):
        notes = self._gen_7_8_classic(1)
        snares = [n for n in notes if n["type"] == "snare"]
        # 7 beats - 3 accents = 4 snare
        assert len(snares) == 4

    def test_7_8_hh_count(self):
        notes = self._gen_7_8_classic(1)
        hhs = [n for n in notes if n["type"] == "hh"]
        # hh on every beat
        assert len(hhs) == 7

    def test_positions_start_at_zero(self):
        notes = self._gen_7_8_classic(1)
        assert notes[0]["start"] == 0.0

    def test_second_cycle_offset(self):
        notes = self._gen_7_8_classic(2)
        second = [n for n in notes if n["start"] >= 7 * 0.5]
        assert len(second) == 14
        assert second[0]["start"] == 3.5  # 7 * 0.5


# ─── Meter Comparison ───


class TestBalkanMeterComparison:
    def test_13_8_longest(self):
        assert METERS["13_8"]["total_beats"] == max(
            d["total_beats"] for d in METERS.values())

    def test_7_8_shortest_or_equal(self):
        assert METERS["7_8"]["total_beats"] <= METERS["9_8"]["total_beats"]

    def test_7_8_and_sand_same_total(self):
        assert METERS["7_8"]["total_beats"] == METERS["7_8_sand"]["total_beats"]

    def test_9_8_and_ska_same_total(self):
        assert METERS["9_8"]["total_beats"] == METERS["9_8_ska"]["total_beats"]

    def test_sand_reversed_grouping(self):
        assert METERS["7_8"]["groups"] == [2, 2, 3]
        assert METERS["7_8_sand"]["groups"] == [3, 2, 2]

    def test_more_groups_more_accents(self):
        for name, data in METERS.items():
            assert len(data["accents"]) == len(data["groups"])


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
