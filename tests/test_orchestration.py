"""Unit tests for orchestration tool pattern generation logic.

Tests the Python-side pattern generation of drum_fill, ostinato, and crescendo tools
without requiring a running DAW bridge.
"""

import pytest


class TestDrumFillPatternGeneration:
    """Test the pattern generation logic of create_drum_fill."""

    def _generate_fill(self, fill_type: str, bars: int, density: str):
        """Replicate the pattern generation logic from create_drum_fill."""
        import random
        rng = random.Random(hash(fill_type + density) & 0xFFFFFFFF)
        total_steps = bars * 16
        kick, snare, hihat, perc = [], [], [], []
        density_factor = {"sparse": 0.15, "medium": 0.35, "dense": 0.6}[density]

        if fill_type == "build":
            for i in range(total_steps):
                progress = i / total_steps
                local_density = density_factor * (0.3 + 0.7 * progress)
                if rng.random() < local_density:
                    hihat.append(i)
                if progress > 0.6 and rng.random() < local_density * 0.6:
                    kick.append(i)
                if progress > 0.5 and rng.random() < local_density * 0.5:
                    snare.append(i)
                if i == total_steps - 1:
                    kick.append(i)
        elif fill_type == "roll":
            for i in range(total_steps):
                snare.append(i)
                if i % 4 == 0:
                    kick.append(i)
                if i % 8 == 0:
                    hihat.append(i)
            kick.append(total_steps - 1)
        elif fill_type == "break":
            for i in range(total_steps):
                progress = i / total_steps
                local_density = density_factor * (0.9 - 0.6 * progress)
                if rng.random() < local_density:
                    hihat.append(i)
                if progress < 0.4 and rng.random() < local_density * 0.5:
                    kick.append(i)
                if rng.random() < local_density * 0.3:
                    snare.append(i)
        elif fill_type == "crash":
            kick.append(0)
            kick.append(total_steps - 1)
            for i in range(total_steps):
                if rng.random() < density_factor * 0.2:
                    perc.append(i)
        elif fill_type == "tom":
            tom_spacing = max(2, int(8 / (bars + 1)))
            for i in range(0, total_steps, tom_spacing):
                perc.append(i)
                if i % (tom_spacing * 2) == 0:
                    kick.append(i)
            for i in range(total_steps):
                if rng.random() < density_factor * 0.3:
                    hihat.append(i)
        return kick, snare, hihat, perc

    def test_build_increasing_density(self):
        kick, snare, hihat, perc = self._generate_fill("build", 4, "dense")
        # With 4 bars, second half should have more hihat than first half
        first_half = sum(1 for h in hihat if h < 32)
        second_half = sum(1 for h in hihat if h >= 32)
        assert second_half >= first_half, f"Build fill should increase density (first={first_half}, second={second_half})"

    def test_roll_snare_on_every_step(self):
        kick, snare, hihat, perc = self._generate_fill("roll", 1, "medium")
        assert len(snare) == 16, "Roll should have snare on every step"

    def test_roll_kick_accents_every_4(self):
        kick, snare, hihat, perc = self._generate_fill("roll", 1, "medium")
        expected_kick = [0, 4, 8, 12, 15]  # 4 accents + final crash
        assert kick == expected_kick

    def test_crash_has_first_and_last(self):
        kick, snare, hihat, perc = self._generate_fill("crash", 1, "medium")
        assert 0 in kick, "Crash should hit at step 0"
        assert 15 in kick, "Crash should hit at last step"

    def test_tom_uses_perc_lane(self):
        kick, snare, hihat, perc = self._generate_fill("tom", 1, "medium")
        assert len(perc) > 0, "Tom fill should use perc lane"

    def test_all_types_produce_notes(self):
        for fill_type in ["build", "break", "roll", "crash", "tom"]:
            kick, snare, hihat, perc = self._generate_fill(fill_type, 1, "medium")
            total = len(kick) + len(snare) + len(hihat) + len(perc)
            assert total > 0, f"Fill type {fill_type} produced 0 notes"

    def test_reproducible_with_same_seed(self):
        r1 = self._generate_fill("build", 2, "dense")
        r2 = self._generate_fill("build", 2, "dense")
        assert r1 == r2, "Same fill_type+density should produce same pattern"

    def test_different_density_different_pattern(self):
        sparse = self._generate_fill("build", 2, "sparse")
        dense = self._generate_fill("build", 2, "dense")
        assert sparse != dense, "Different density should produce different patterns"

    def test_bars_affect_length(self):
        kick1, snare1, _, _ = self._generate_fill("roll", 1, "medium")
        kick2, snare2, _, _ = self._generate_fill("roll", 2, "medium")
        assert len(snare1) == 16, "1 bar = 16 snare steps"
        assert len(snare2) == 32, "2 bars = 32 snare steps"


class TestOstinatoPatternGeneration:
    """Test the pattern repetition logic of create_ostinato."""

    def _generate_ostinato(self, pattern: str, root: str, scale: str, repeats: int, octave: int = 4):
        """Replicate ostinato note generation using parse_melody_pattern."""
        from opendaw_mcp.music_theory import parse_melody_pattern
        base_notes = parse_melody_pattern(pattern, root, scale, octave, 0.7, 0.25, 0)
        pattern_beats = max(n["start"] + n["duration"] for n in base_notes)
        all_notes = []
        for rep in range(repeats):
            for note in base_notes:
                all_notes.append({
                    "pitch": note["pitch"],
                    "start": rep * pattern_beats + note["start"],
                    "duration": note["duration"],
                    "velocity": note["velocity"],
                })
        return all_notes

    def test_repeats_multiplier(self):
        notes = self._generate_ostinato("1 5 3 5", "C", "minor", 4)
        # 4 pattern notes × 4 repeats = 16 notes
        assert len(notes) == 16

    def test_pitch_consistent_across_repeats(self):
        notes = self._generate_ostinato("1 3 5", "C", "major", 3)
        # Each repeat should have the same pitches
        pitches_rep0 = [n["pitch"] for n in notes[:3]]
        pitches_rep1 = [n["pitch"] for n in notes[3:6]]
        pitches_rep2 = [n["pitch"] for n in notes[6:9]]
        assert pitches_rep0 == pitches_rep1 == pitches_rep2

    def test_start_positions_offset(self):
        notes = self._generate_ostinato("1 5 3 5", "C", "minor", 3)
        # First note of each repeat should be at 0, pattern_beats, 2*pattern_beats
        starts = [notes[i * 4]["start"] for i in range(3)]
        assert starts[0] == 0
        assert starts[1] > starts[0]
        assert starts[2] > starts[1]

    def test_single_repeat(self):
        notes = self._generate_ostinato("1 3 5", "D", "dorian", 1)
        assert len(notes) == 3

    def test_rests_excluded(self):
        notes = self._generate_ostinato("1 0 3 0 5", "C", "major", 2)
        # 3 actual notes (1,3,5) × 2 repeats = 6
        assert len(notes) == 6


class TestCrescendoCurveMath:
    """Test the velocity curve calculations of create_crescendo."""

    def _compute_velocities(self, n: int, start: float, end: float, curve: str) -> list[float]:
        """Replicate crescendo velocity computation."""
        velocities = []
        for i in range(n):
            t = i / (n - 1) if n > 1 else 0
            if curve == "exp":
                vel = start + (end - start) * (t * t)
            elif curve == "log":
                vel = start + (end - start) * (t**0.5)
            else:  # linear
                vel = start + (end - start) * t
            velocities.append(max(0, min(1, vel)))
        return velocities

    def test_linear_crescendo(self):
        vels = self._compute_velocities(5, 0.2, 0.8, "linear")
        assert vels[0] == pytest.approx(0.2)
        assert vels[-1] == pytest.approx(0.8)
        # Linear: middle should be exactly halfway
        assert vels[2] == pytest.approx(0.5)

    def test_exp_crescendo(self):
        vels = self._compute_velocities(5, 0.2, 0.8, "exp")
        assert vels[0] == pytest.approx(0.2)
        assert vels[-1] == pytest.approx(0.8)
        # Exponential: second note should be closer to start than linear
        linear_second = 0.2 + (0.8 - 0.2) * 0.25
        assert vels[1] < linear_second

    def test_log_crescendo(self):
        vels = self._compute_velocities(5, 0.2, 0.8, "log")
        assert vels[0] == pytest.approx(0.2)
        assert vels[-1] == pytest.approx(0.8)
        # Logarithmic: second note should be closer to end than linear
        linear_second = 0.2 + (0.8 - 0.2) * 0.25
        assert vels[1] > linear_second

    def test_decrescendo(self):
        vels = self._compute_velocities(5, 0.9, 0.15, "linear")
        assert vels[0] == pytest.approx(0.9)
        assert vels[-1] == pytest.approx(0.15)
        # Should be decreasing
        assert all(vels[i] >= vels[i + 1] for i in range(4))

    def test_single_note(self):
        vels = self._compute_velocities(1, 0.2, 0.8, "linear")
        assert len(vels) == 1
        # Single note: t=0, should get start velocity
        assert vels[0] == pytest.approx(0.2)

    def test_clamped_to_0_1(self):
        vels = self._compute_velocities(5, -0.5, 1.5, "linear")
        assert all(0 <= v <= 1 for v in vels)


class TestSwingLogic:
    """Test the swing calculation logic of apply_swing."""

    def _compute_swing_offset(self, position: int, grid_ticks: int, swing_amount: float) -> int:
        """Replicate swing offset computation from apply_swing."""
        grid_idx = round(position / grid_ticks)
        if grid_idx % 2 == 1:
            return round(grid_ticks * swing_amount / 3)
        return 0

    def test_even_positions_not_shifted(self):
        grid_ticks = 240  # 16th note at 960 PPQN
        # Even grid positions: 0 (grid 0), 480 (grid 2), 960 (grid 4), 1440 (grid 6)
        for pos in [0, 480, 960, 1440, 1920]:
            assert self._compute_swing_offset(pos, grid_ticks, 0.5) == 0

    def test_odd_positions_shifted(self):
        grid_ticks = 240
        # Odd 16th positions: 240, 720, 1200 (grid_idx 1, 3, 5)
        offset = self._compute_swing_offset(240, grid_ticks, 0.5)
        assert offset == round(240 * 0.5 / 3)  # 40

    def test_zero_swing_no_shift(self):
        grid_ticks = 240
        assert self._compute_swing_offset(240, grid_ticks, 0.0) == 0

    def test_full_swing_triplet(self):
        grid_ticks = 240
        offset = self._compute_swing_offset(240, grid_ticks, 1.0)
        # Full swing: grid_ticks * 1.0 / 3 = 80
        assert offset == 80

    def test_8th_grid_uses_double_ticks(self):
        grid_ticks_8th = 480  # Quarter / 2
        grid_ticks_16th = 240
        offset_8th = self._compute_swing_offset(480, grid_ticks_8th, 0.5)
        offset_16th = self._compute_swing_offset(240, grid_ticks_16th, 0.5)
        # Same swing_amount but different grid = proportionally larger offset
        assert offset_8th > offset_16th

    def test_classic_hiphop_swing(self):
        grid_ticks = 240
        # 0.58 swing = classic hip-hop/lofi
        offset = self._compute_swing_offset(240, grid_ticks, 0.58)
        assert offset == round(240 * 0.58 / 3)  # ~46


class TestPolyrhythmGeneration:
    """Test the polyrhythm pattern generation logic of create_polyrhythm."""

    def _generate_polyrhythm(self, primary: int, secondary: int, bars: int = 1):
        """Replicate polyrhythm note generation."""
        total_beats = bars * 4
        notes = []
        primary_step = total_beats / primary
        for i in range(primary):
            notes.append({"pitch": 60, "start": i * primary_step, "stream": "primary"})
        secondary_step = total_beats / secondary
        for i in range(secondary):
            notes.append({"pitch": 72, "start": i * secondary_step, "stream": "secondary"})
        return notes

    def test_total_notes_is_sum(self):
        notes = self._generate_polyrhythm(3, 4)
        assert len(notes) == 7  # 3 + 4

    def test_3_4_ratio(self):
        notes = self._generate_polyrhythm(3, 4, bars=1)
        primary = [n for n in notes if n["stream"] == "primary"]
        secondary = [n for n in notes if n["stream"] == "secondary"]
        assert len(primary) == 3
        assert len(secondary) == 4
        # Total span = 4 beats
        assert primary[-1]["start"] == pytest.approx(4 * 2 / 3)  # 2.667
        assert secondary[-1]["start"] == pytest.approx(4 * 3 / 4)  # 3.0

    def test_2_3_hemiola(self):
        notes = self._generate_polyrhythm(2, 3, bars=1)
        primary = [n for n in notes if n["stream"] == "primary"]
        secondary = [n for n in notes if n["stream"] == "secondary"]
        assert len(primary) == 2
        assert len(secondary) == 3
        # Primary: at 0 and 2 beats (4/2)
        assert primary[0]["start"] == 0
        assert primary[1]["start"] == pytest.approx(2.0)
        # Secondary: at 0, 1.333, 2.667 (4/3)
        assert secondary[1]["start"] == pytest.approx(4 / 3)

    def test_bars_scale_spacing(self):
        notes_1bar = self._generate_polyrhythm(3, 4, bars=1)
        notes_2bar = self._generate_polyrhythm(3, 4, bars=2)
        # Same note count, but 2-bar version has wider spacing
        assert len(notes_1bar) == len(notes_2bar) == 7
        assert notes_2bar[1]["start"] > notes_1bar[1]["start"]

    def test_both_streams_start_at_zero(self):
        notes = self._generate_polyrhythm(5, 7, bars=2)
        primary = [n for n in notes if n["stream"] == "primary"]
        secondary = [n for n in notes if n["stream"] == "secondary"]
        assert primary[0]["start"] == 0
        assert secondary[0]["start"] == 0

    def test_equal_counts_rejected(self):
        """Equal counts is not a polyrhythm — the tool rejects this."""
        # This is tested at the tool level, but verify the logic makes sense
        notes = self._generate_polyrhythm(4, 4, bars=1)
        primary = [n for n in notes if n["stream"] == "primary"]
        secondary = [n for n in notes if n["stream"] == "secondary"]
        # Both streams would have identical timing — not a polyrhythm
        assert [n["start"] for n in primary] == [n["start"] for n in secondary]
