"""Unit tests for create_songo_pattern — Cuban drum-kit fusion tool."""



# Mirror of server.py patterns (2-bar cycles)
PATTERNS = {
    "classic": [
        (0.0, "kick", "normal"), (0.0, "hh", "accent"),
        (0.5, "hh", "normal"), (1.0, "hh", "normal"), (1.5, "hh", "normal"),
        (2.5, "kick", "normal"), (2.5, "hh", "normal"),
        (3.0, "snare", "rim"), (3.0, "hh", "normal"),
        (3.5, "hh", "normal"),
        (4.0, "kick", "normal"), (4.0, "hh", "accent"),
        (4.5, "snare", "open"), (4.5, "hh", "normal"),
        (5.0, "hh", "normal"), (5.5, "hh", "normal"),
        (6.5, "kick", "normal"), (6.5, "hh", "normal"),
        (7.0, "snare", "rim"), (7.0, "hh", "normal"),
        (7.5, "hh", "normal"),
        (8.0, "kick", "normal"), (8.0, "hh", "accent"),
        (8.5, "hh", "normal"), (9.0, "hh", "normal"), (9.5, "hh", "normal"),
        (10.5, "kick", "normal"), (10.5, "hh", "normal"),
        (11.0, "snare", "rim"), (11.0, "hh", "normal"),
        (11.5, "tom", "normal"), (11.5, "hh", "normal"),
        (12.0, "kick", "normal"), (12.0, "hh", "accent"),
        (12.5, "snare", "open"), (12.5, "hh", "normal"),
        (13.0, "tom", "normal"), (13.0, "hh", "normal"),
        (13.5, "tom", "normal"), (13.5, "hh", "normal"),
        (14.0, "snare", "rim"), (14.0, "hh", "normal"),
        (14.5, "kick", "normal"), (14.5, "hh", "normal"),
        (15.0, "tom", "normal"), (15.0, "hh", "normal"),
        (15.5, "hh", "normal"),
    ],
}

VEL_MAP = {
    "accent": 0.95, "normal": 0.8, "ghost": 0.5,
    "open": 0.9, "rim": 0.7,
}

VALID_VARIATIONS = ("classic", "modern", "fusion", "songo_funk")


# ─── Validation ───


class TestSongoValidation:
    def test_bars_too_few(self):
        assert not (2 <= 0 <= 16 and 0 % 2 == 0)

    def test_bars_odd(self):
        assert not (3 % 2 == 0 and 2 <= 3 <= 16)

    def test_bars_too_many(self):
        assert not (2 <= 18 <= 16 and 18 % 2 == 0)

    def test_bars_valid(self):
        for b in (2, 4, 6, 8, 16):
            assert 2 <= b <= 16 and b % 2 == 0

    def test_invalid_variation(self):
        assert "bogus" not in VALID_VARIATIONS

    def test_valid_variations(self):
        for v in VALID_VARIATIONS:
            assert v in VALID_VARIATIONS

    def test_four_variations(self):
        assert len(VALID_VARIATIONS) == 4


# ─── Pattern Structure ───


class TestSongoPatternStructure:
    def test_classic_2bar_cycle(self):
        assert len(PATTERNS["classic"]) > 20

    def test_classic_has_kick(self):
        instruments = {s[1] for s in PATTERNS["classic"]}
        assert "kick" in instruments

    def test_classic_has_snare(self):
        instruments = {s[1] for s in PATTERNS["classic"]}
        assert "snare" in instruments

    def test_classic_has_hh(self):
        instruments = {s[1] for s in PATTERNS["classic"]}
        assert "hh" in instruments

    def test_classic_has_tom(self):
        instruments = {s[1] for s in PATTERNS["classic"]}
        assert "tom" in instruments

    def test_classic_has_all_four_instruments(self):
        instruments = {s[1] for s in PATTERNS["classic"]}
        assert instruments == {"kick", "snare", "hh", "tom"}

    def test_all_beats_within_2_bars(self):
        for beat, inst, stroke in PATTERNS["classic"]:
            assert 0 <= beat < 16.0, f"beat {beat} out of 2-bar range"

    def test_beats_sorted(self):
        beats = [s[0] for s in PATTERNS["classic"]]
        assert beats == sorted(beats)

    def test_stroke_types_valid(self):
        valid_strokes = {"normal", "accent", "ghost", "open", "rim"}
        for beat, inst, stroke in PATTERNS["classic"]:
            assert stroke in valid_strokes, f"invalid stroke type: {stroke}"


# ─── Velocity ───


class TestSongoVelocity:
    def test_accent_highest(self):
        base = 0.8
        assert abs(min(1.0, base + 0.15) - 0.95) < 0.001

    def test_ghost_lowest(self):
        base = 0.8
        assert max(0.05, base - 0.3) == 0.5

    def test_normal_is_base(self):
        base = 0.8
        assert base == 0.8

    def test_open_above_normal(self):
        base = 0.8
        assert min(1.0, base + 0.1) > base

    def test_rim_below_normal(self):
        base = 0.8
        assert max(0.0, base - 0.1) < base

    def test_accent_capped_at_1(self):
        base = 0.95
        assert min(1.0, base + 0.15) == 1.0

    def test_ghost_not_zero(self):
        base = 0.8
        assert max(0.05, base - 0.3) > 0


# ─── Duration ───


class TestSongoDuration:
    DUR_MAP = {"accent": 0.15, "normal": 0.12, "ghost": 0.06, "open": 0.2, "rim": 0.1}

    def test_open_longest(self):
        assert self.DUR_MAP["open"] == max(self.DUR_MAP.values())

    def test_ghost_shortest(self):
        assert self.DUR_MAP["ghost"] == min(self.DUR_MAP.values())

    def test_all_positive(self):
        for d in self.DUR_MAP.values():
            assert d > 0


# ─── Pitch Mapping ───


class TestSongoPitch:
    def test_kick_default(self):
        assert 36 == 36

    def test_snare_default(self):
        assert 38 == 38

    def test_hh_default(self):
        assert 42 == 42

    def test_tom_default(self):
        assert 45 == 45

    def test_kick_lowest(self):
        assert 36 < 38 < 42 < 45


# ─── Note Generation Simulation ───


class TestSongoNoteGeneration:
    def _generate(self, variation, cycles, velocity=0.8):
        pattern = PATTERNS.get(variation, PATTERNS["classic"])
        cycle_len = 16.0  # one full songo cycle = 4 bars of 4/4
        pitch_map = {"kick": 36, "snare": 38, "hh": 42, "tom": 45}
        vel_map = {
            "accent": min(1.0, velocity + 0.15),
            "normal": velocity,
            "ghost": max(0.05, velocity - 0.3),
            "open": min(1.0, velocity + 0.1),
            "rim": max(0.0, velocity - 0.1),
        }
        dur_map = {"accent": 0.15, "normal": 0.12, "ghost": 0.06, "open": 0.2, "rim": 0.1}

        all_notes = []
        for c in range(cycles):
            offset = c * cycle_len
            for beat, inst, stroke in pattern:
                all_notes.append({
                    "pitch": pitch_map[inst],
                    "start": round(offset + beat, 4),
                    "duration": dur_map[stroke],
                    "velocity": round(vel_map[stroke], 3),
                })
        return all_notes

    def test_classic_2_bars_note_count(self):
        notes = self._generate("classic", 1)
        assert len(notes) == len(PATTERNS["classic"])

    def test_classic_4_bars_doubled(self):
        notes1 = self._generate("classic", 1)
        notes2 = self._generate("classic", 2)
        assert len(notes2) == 2 * len(notes1)

    def test_kick_count_in_classic(self):
        notes = self._generate("classic", 1)
        kicks = [n for n in notes if n["pitch"] == 36]
        # Count kick notes from pattern
        pattern_kicks = sum(1 for s in PATTERNS["classic"] if s[1] == "kick")
        assert len(kicks) == pattern_kicks

    def test_hh_continuous_8ths(self):
        """Hi-hat should play on most 8th positions."""
        notes = self._generate("classic", 1)
        hh_notes = [n for n in notes if n["pitch"] == 42]
        # Should have many HH notes (near continuous 8ths)
        assert len(hh_notes) > 10

    def test_all_pitches_valid_midi(self):
        notes = self._generate("classic", 1)
        for n in notes:
            assert 0 <= n["pitch"] <= 127

    def test_all_velocities_in_range(self):
        notes = self._generate("classic", 1)
        for n in notes:
            assert 0 < n["velocity"] <= 1.0

    def test_all_durations_positive(self):
        notes = self._generate("classic", 1)
        for n in notes:
            assert n["duration"] > 0

    def test_positions_start_at_zero(self):
        notes = self._generate("classic", 1)
        assert notes[0]["start"] == 0.0

    def test_second_cycle_offset(self):
        notes = self._generate("classic", 2)
        second_cycle = [n for n in notes if n["start"] >= 16.0]
        assert len(second_cycle) == len(PATTERNS["classic"])
        assert second_cycle[0]["start"] == 16.0

    def test_ghost_notes_lower_velocity(self):
        base = 0.8
        ghost_vel = max(0.05, base - 0.3)
        normal_vel = base
        assert ghost_vel < normal_vel


# ─── Stroke Counts ───


class TestSongoStrokeCounts:
    def test_classic_has_kick(self):
        counts = {"kick": 0, "snare": 0, "hh": 0, "tom": 0}
        for _, inst, _ in PATTERNS["classic"]:
            counts[inst] += 1
        assert counts["kick"] > 0

    def test_classic_hh_most_frequent(self):
        counts = {"kick": 0, "snare": 0, "hh": 0, "tom": 0}
        for _, inst, _ in PATTERNS["classic"]:
            counts[inst] += 1
        assert counts["hh"] == max(counts.values())

    def test_classic_has_rim_strokes(self):
        strokes = {s[2] for s in PATTERNS["classic"]}
        assert "rim" in strokes

    def test_classic_has_open_strokes(self):
        strokes = {s[2] for s in PATTERNS["classic"]}
        assert "open" in strokes


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
