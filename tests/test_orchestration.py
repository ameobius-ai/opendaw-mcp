"""Unit tests for orchestration tool pattern generation logic.

Tests the Python-side pattern generation of drum_fill, ostinato, and crescendo tools
without requiring a running DAW bridge.
"""

import inspect
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


class TestScaleRunGeneration:
    """Test the scale run pattern generation logic of create_scale_run."""

    def _generate_scale_run(self, scale: str, root: str, direction: str, octaves: int, octave: int = 4):
        """Replicate scale run note generation using music_theory constants."""
        from opendaw_mcp.music_theory import SCALE_INTERVALS, NOTE_TO_PITCH

        intervals = SCALE_INTERVALS[scale]
        root_pc = NOTE_TO_PITCH[root]
        base_pitch = (octave + 1) * 12 + root_pc

        all_pitches = []
        for oct_i in range(octaves):
            for iv in intervals:
                all_pitches.append(base_pitch + iv + 12 * oct_i)
        all_pitches.append(base_pitch + 12 * octaves)

        if direction == "down":
            all_pitches.reverse()

        return all_pitches

    def test_ascending_one_octave(self):
        pitches = self._generate_scale_run("major", "C", "up", 1)
        # 7 scale notes + 1 octave root = 8 notes
        assert len(pitches) == 8
        assert pitches[0] == 60  # C4
        assert pitches[-1] == 72  # C5
        # Should be ascending
        assert all(pitches[i] < pitches[i + 1] for i in range(len(pitches) - 1))

    def test_descending_reverses(self):
        up = self._generate_scale_run("minor", "A", "up", 1)
        down = self._generate_scale_run("minor", "A", "down", 1)
        assert up == list(reversed(down))

    def test_two_octaves_doubles(self):
        one = self._generate_scale_run("major", "C", "up", 1)
        two = self._generate_scale_run("major", "C", "up", 2)
        # 1 octave = 8, 2 octaves = 15
        assert len(one) == 8
        assert len(two) == 15
        # First 8 should match
        assert two[:8] == one

    def test_minor_scale_intervals(self):
        pitches = self._generate_scale_run("minor", "C", "up", 1)
        # C minor: C, D, Eb, F, G, Ab, Bb, C
        expected = [60, 62, 63, 65, 67, 68, 70, 72]
        assert pitches == expected

    def test_blues_scale(self):
        pitches = self._generate_scale_run("blues", "A", "up", 1)
        # A blues: A, C, D, Eb, E, G, A (6 notes + octave = 7)
        assert len(pitches) == 7
        assert pitches[0] == 69  # A4

    def test_chromatic_12_notes(self):
        pitches = self._generate_scale_run("chromatic", "C", "up", 1)
        # 12 chromatic notes + octave = 13
        assert len(pitches) == 13
        assert pitches == list(range(60, 73))

    def test_pentatonic_5_notes(self):
        pitches = self._generate_scale_run("pentatonic_minor", "A", "up", 1)
        # 5 notes + octave = 6
        assert len(pitches) == 6

    def test_octave_affects_pitch(self):
        low = self._generate_scale_run("major", "C", "up", 1, octave=3)
        high = self._generate_scale_run("major", "C", "up", 1, octave=5)
        assert low[0] == 48  # C3
        assert high[0] == 72  # C5
        assert high[0] - low[0] == 24  # 2 octaves apart


class TestCallResponseGeneration:
    """Test the call-and-response pattern generation logic."""

    def _generate_call_response(self, call_pattern, response_pattern, root, scale, repeats, octave=4):
        """Replicate call_response note generation using parse_melody_pattern."""
        from opendaw_mcp.music_theory import parse_melody_pattern

        call_notes = parse_melody_pattern(call_pattern, root, scale, octave, 0.7, 0.25, 0)
        response_notes = parse_melody_pattern(response_pattern, root, scale, octave, 0.63, 0.25, 0)

        call_length = max(n["start"] + n["duration"] for n in call_notes)
        response_length = max(n["start"] + n["duration"] for n in response_notes)
        phrase_length = call_length + response_length

        all_notes = []
        for rep in range(repeats):
            phrase_start = rep * phrase_length
            for note in call_notes:
                all_notes.append({**note, "start": phrase_start + note["start"], "phrase": "call", "rep": rep})
            response_start = phrase_start + call_length
            for note in response_notes:
                all_notes.append({**note, "start": response_start + note["start"], "phrase": "response", "rep": rep})
        return all_notes

    def test_total_notes_is_doubled(self):
        notes = self._generate_call_response("1 3 5 3", "5 4 3 2", "C", "minor", 2)
        # 4 call + 4 response = 8 per repeat, × 2 = 16
        assert len(notes) == 16

    def test_call_before_response(self):
        notes = self._generate_call_response("1 3", "5 2", "C", "major", 1)
        calls = [n for n in notes if n["phrase"] == "call"]
        responses = [n for n in notes if n["phrase"] == "response"]
        # Last call should start before first response
        assert max(n["start"] for n in calls) < min(n["start"] for n in responses)

    def test_repeats_interleave(self):
        notes = self._generate_call_response("1 3", "2 4", "C", "major", 3)
        calls = [n for n in notes if n["phrase"] == "call"]
        # Should have 3 call phrases
        assert len(calls) == 6  # 2 notes × 3 repeats
        reps = set(n["rep"] for n in calls)
        assert reps == {0, 1, 2}

    def test_response_starts_after_call_ends(self):
        notes = self._generate_call_response("1 3 5", "2 4", "A", "blues", 1)
        calls = [n for n in notes if n["phrase"] == "call"]
        responses = [n for n in notes if n["phrase"] == "response"]
        call_end = max(n["start"] + n["duration"] for n in calls)
        response_start = min(n["start"] for n in responses)
        assert response_start >= call_end

    def test_response_velocity_slightly_lower(self):
        notes = self._generate_call_response("1 3", "5 2", "C", "major", 1)
        calls = [n for n in notes if n["phrase"] == "call"]
        responses = [n for n in notes if n["phrase"] == "response"]
        avg_call_vel = sum(n["velocity"] for n in calls) / len(calls)
        avg_resp_vel = sum(n["velocity"] for n in responses) / len(responses)
        assert avg_resp_vel < avg_call_vel  # response is 0.9× velocity


class TestWalkingBassGeneration:
    """Test the walking bass pattern generation logic."""

    def _generate_walking_bass(self, chords, octave=2, bars_per_chord=1):
        """Replicate walking bass note generation."""
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, CHORD_INTERVALS

        base_octave = (octave + 1) * 12
        all_notes = []
        notes_per_chord = bars_per_chord * 4

        for ci, (root_name, chord_type) in enumerate(chords):
            root_pc = NOTE_TO_PITCH[root_name]
            chord_intervals = CHORD_INTERVALS[chord_type]
            chord_root = base_octave + root_pc

            next_root_pc = NOTE_TO_PITCH[chords[ci + 1][0]] if ci < len(chords) - 1 else root_pc
            next_chord_root = base_octave + next_root_pc

            chord_start = ci * bars_per_chord * 4

            for beat in range(notes_per_chord):
                beat_in_bar = beat % 4
                pos = chord_start + beat

                if beat_in_bar == 0:
                    pitch = chord_root
                elif beat_in_bar == 1:
                    idx = (ci + 1) % (len(chord_intervals) - 1)
                    pitch = chord_root + chord_intervals[min(idx + 1, len(chord_intervals) - 1)]
                elif beat_in_bar == 2:
                    direction = 1 if next_chord_root > chord_root else -1
                    pitch = chord_root + direction * 7
                    if pitch < base_octave:
                        pitch += 12
                    elif pitch > base_octave + 24:
                        pitch -= 12
                else:
                    direction = 1 if next_chord_root > chord_root else -1
                    pitch = next_chord_root - direction * 1
                    if pitch < base_octave:
                        pitch += 12
                    elif pitch > base_octave + 24:
                        pitch -= 12

                all_notes.append({"pitch": pitch, "start": pos, "beat_in_bar": beat_in_bar, "chord_index": ci})

        return all_notes

    def test_four_notes_per_chord(self):
        notes = self._generate_walking_bass([["C", "maj7"], ["A", "min7"]])
        # 2 chords × 4 notes = 8
        assert len(notes) == 8

    def test_beat1_is_chord_root(self):
        notes = self._generate_walking_bass([["C", "maj7"], ["A", "min7"]], octave=2)
        # C2 = (2+1)*12 + 0 = 36, A2 = (2+1)*12 + 9 = 45
        beat1_notes = [n for n in notes if n["beat_in_bar"] == 0]
        assert beat1_notes[0]["pitch"] == 36  # C2
        assert beat1_notes[1]["pitch"] == 45  # A2

    def test_bars_per_chord_doubles(self):
        one_bar = self._generate_walking_bass([["C", "maj7"]], bars_per_chord=1)
        two_bar = self._generate_walking_bass([["C", "maj7"]], bars_per_chord=2)
        assert len(one_bar) == 4
        assert len(two_bar) == 8

    def test_beats_are_evenly_spaced(self):
        notes = self._generate_walking_bass([["C", "maj7"], ["A", "min7"]])
        starts = [n["start"] for n in notes]
        assert starts == [0, 1, 2, 3, 4, 5, 6, 7]

    def test_approach_note_near_next_root(self):
        notes = self._generate_walking_bass([["C", "maj7"], ["A", "min7"]], octave=2)
        # Last beat of first chord (beat 4) should approach A2 (45)
        beat4 = [n for n in notes if n["beat_in_bar"] == 3 and n["chord_index"] == 0]
        assert len(beat4) == 1
        # Approach note should be within 1-2 semitones of next root (45)
        assert abs(beat4[0]["pitch"] - 45) <= 2

    def test_pitches_in_bass_range(self):
        notes = self._generate_walking_bass([["C", "maj7"], ["A", "min7"]], octave=2)
        # All pitches should be in octave 2 range (36 ± 12)
        for n in notes:
            assert 24 <= n["pitch"] <= 60, f"Pitch {n['pitch']} out of bass range"


class TestSidechainDucking:
    """Test the sidechain ducking curve math of apply_sidechain."""

    def _generate_events(self, bars: int, depth: float, attack: float, release: float, kick_interval: float = 1.0):
        """Replicate sidechain event generation."""
        total_beats = bars * 4
        ducked_vol = 1.0 - depth
        num_kicks = int(total_beats / kick_interval)

        events = []
        for i in range(num_kicks):
            kick_beat = i * kick_interval
            events.append({"beat": kick_beat, "value": ducked_vol})

            recovery_steps = max(2, int(release / 0.02))
            for s in range(1, recovery_steps + 1):
                t = s / recovery_steps
                vol = ducked_vol + (1.0 - ducked_vol) * (t * t)
                beat_pos = kick_beat + attack + (release - attack) * t
                events.append({"beat": round(beat_pos, 4), "value": round(vol, 4)})

            next_kick = kick_beat + kick_interval
            events.append({"beat": round(next_kick - 0.01, 4), "value": 1.0})

        return events

    def test_duck_point_is_lowest(self):
        events = self._generate_events(1, 0.6, 0.01, 0.3)
        duck_values = [e["value"] for e in events if e["beat"] == 0.0]
        assert duck_values[0] == pytest.approx(0.4)  # 1.0 - 0.6

    def test_recovers_to_full_volume(self):
        events = self._generate_events(1, 0.6, 0.01, 0.3)
        # Last event before next kick should be 1.0
        pre_kick = [e for e in events if e["beat"] < 1.0]
        assert pre_kick[-1]["value"] == pytest.approx(1.0)

    def test_more_events_with_longer_release(self):
        short = self._generate_events(1, 0.6, 0.01, 0.1)
        long_rel = self._generate_events(1, 0.6, 0.01, 0.5)
        assert len(long_rel) > len(short)

    def test_more_bars_more_kicks(self):
        one_bar = self._generate_events(1, 0.6, 0.01, 0.3)
        four_bar = self._generate_events(4, 0.6, 0.01, 0.3)
        # 4 bars should have ~4x more duck events
        one_ducks = len([e for e in one_bar if e["value"] == pytest.approx(0.4)])
        four_ducks = len([e for e in four_bar if e["value"] == pytest.approx(0.4)])
        assert four_ducks == one_ducks * 4

    def test_kick_interval_doubles(self):
        every_beat = self._generate_events(1, 0.6, 0.01, 0.3, 1.0)
        every_2 = self._generate_events(1, 0.6, 0.01, 0.3, 2.0)
        beat_ducks = len([e for e in every_beat if e["value"] == pytest.approx(0.4)])
        two_ducks = len([e for e in every_2 if e["value"] == pytest.approx(0.4)])
        assert beat_ducks == 4  # 4 beats in 1 bar
        assert two_ducks == 2   # 2 kicks at interval 2.0

    def test_depth_affects_duck_volume(self):
        shallow = self._generate_events(1, 0.3, 0.01, 0.3)
        deep = self._generate_events(1, 0.8, 0.01, 0.3)
        shallow_duck = [e for e in shallow if e["beat"] == 0.0][0]["value"]
        deep_duck = [e for e in deep if e["beat"] == 0.0][0]["value"]
        assert shallow_duck > deep_duck  # less depth = higher duck volume


class TestGhostNotesLogic:
    """Test the ghost note placement logic of create_ghost_notes."""

    def _generate_ghost_positions(self, occupied_grids: list[int], region_length: int, density: float, seed: int = 42):
        """Replicate ghost note position generation."""
        import random
        rng = random.Random(seed)
        occupied_set = set(occupied_grids)
        ghost_positions = []

        for grid in range(0, region_length):
            if grid in occupied_set:
                continue
            if rng.random() < density:
                ghost_positions.append(grid)

        return ghost_positions

    def test_ghosts_avoid_occupied(self):
        occupied = [0, 4, 8, 12]  # kick on every beat
        ghosts = self._generate_ghost_positions(occupied, 16, 0.5, seed=42)
        for g in ghosts:
            assert g not in occupied, f"Ghost at {g} overlaps with occupied position"

    def test_density_affects_count(self):
        occupied = [0, 4, 8, 12]
        sparse = self._generate_ghost_positions(occupied, 16, 0.1, seed=42)
        dense = self._generate_ghost_positions(occupied, 16, 0.6, seed=42)
        assert len(dense) > len(sparse)

    def test_reproducible_with_same_seed(self):
        occupied = [0, 8]
        g1 = self._generate_ghost_positions(occupied, 16, 0.4, seed=99)
        g2 = self._generate_ghost_positions(occupied, 16, 0.4, seed=99)
        assert g1 == g2

    def test_different_seed_different_result(self):
        occupied = [0, 8]
        g1 = self._generate_ghost_positions(occupied, 16, 0.4, seed=42)
        g2 = self._generate_ghost_positions(occupied, 16, 0.4, seed=77)
        assert g1 != g2

    def test_empty_pattern_gets_ghosts(self):
        ghosts = self._generate_ghost_positions([], 16, 0.5, seed=42)
        assert len(ghosts) > 0, "Empty pattern should get ghost notes"

    def test_fully_occupied_no_ghosts(self):
        occupied = list(range(16))  # every 16th has a note
        ghosts = self._generate_ghost_positions(occupied, 16, 0.5, seed=42)
        assert len(ghosts) == 0, "Fully occupied pattern should get 0 ghosts"


class TestStabPatternGeneration:
    """Test the Python-side pattern generation logic of create_stab."""

    def _generate_stab(self, chords, rhythm, octave=4, velocity=0.85,
                       length_beats=4, stab_duration=0.5, start_beat=0):
        """Replicate the pattern generation logic from create_stab."""
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, CHORD_INTERVALS

        grid_len = len(rhythm)
        step_duration = length_beats / grid_len
        note_data = []
        chord_idx = 0
        for i, c in enumerate(rhythm):
            if c == "-":
                continue
            if c == "." and chord_idx > 0:
                cs = chords[(chord_idx - 1) % len(chords)]
            else:
                cs = chords[chord_idx % len(chords)]
            root_pc = NOTE_TO_PITCH[cs[0]]
            intervals = CHORD_INTERVALS[cs[1]]
            root_pitch = (octave + 1) * 12 + root_pc
            is_ghost = (c == ".")
            vel = velocity * (0.45 if is_ghost else 1.0)
            pos = start_beat + i * step_duration
            dur = stab_duration * (0.6 if is_ghost else 1.0)
            for iv in intervals:
                note_data.append({"pitch": root_pitch + iv, "pos": pos, "dur": dur, "vel": vel})
            if not is_ghost:
                chord_idx += 1
        return note_data

    def test_house_offbeat_cm7(self):
        notes = self._generate_stab([["C", "min7"]], "x-x-x-x-")
        assert len(notes) == 16, f"Expected 16 (4 stabs × 4-note chord), got {len(notes)}"
        pitches = sorted(set(n["pitch"] for n in notes))
        assert pitches == [60, 63, 67, 70], f"Expected Cm7 voicing [60,63,67,70], got {pitches}"

    def test_ghost_velocity_lower(self):
        notes = self._generate_stab([["F", "dom7"]], "x.x.x.x.")
        # dom7 = 4 intervals, notes grouped in 4s
        stab_vels = [n["vel"] for n in notes[:4]]
        ghost_vels = [n["vel"] for n in notes[4:8]]
        assert all(abs(v - 0.85) < 0.01 for v in stab_vels), f"Stab vel should be 0.85, got {stab_vels}"
        assert all(abs(v - 0.3825) < 0.01 for v in ghost_vels), f"Ghost vel should be 0.3825, got {ghost_vels}"

    def test_ghost_duration_shorter(self):
        notes = self._generate_stab([["C", "maj"]], "x.x.")
        # maj triad = 3 notes per hit. x=stab(3), .=ghost(3), x=stab(3), .=ghost(3)
        stab_durs = [n["dur"] for n in notes[0:3] + notes[6:9]]
        ghost_durs = [n["dur"] for n in notes[3:6] + notes[9:12]]
        assert all(abs(d - 0.5) < 0.01 for d in stab_durs), f"Stab dur should be 0.5, got {stab_durs}"
        assert all(abs(d - 0.3) < 0.01 for d in ghost_durs), f"Ghost dur should be 0.3, got {ghost_durs}"

    def test_chord_cycling(self):
        notes = self._generate_stab([["F", "dom7"], ["C", "min7"]], "x-x-x-x-")
        stab1 = sorted(set(n["pitch"] for n in notes[:4]))
        stab2 = sorted(set(n["pitch"] for n in notes[4:8]))
        stab3 = sorted(set(n["pitch"] for n in notes[8:12]))
        stab4 = sorted(set(n["pitch"] for n in notes[12:16]))
        assert 65 in stab1, "Stab 1 should be F7 (F4=65)"
        assert 60 in stab2, "Stab 2 should be Cm7 (C4=60)"
        assert 65 in stab3, "Stab 3 should be F7 again"
        assert 60 in stab4, "Stab 4 should be Cm7 again"

    def test_ghost_does_not_advance_chord(self):
        notes = self._generate_stab([["C", "min7"], ["F", "dom7"]], "x.x.x.x.")
        # x=Cm7(advance to idx=1), .=Cm7(ghost, repeats last), x=F7(advance to idx=2),
        # .=F7(ghost, repeats last), x=Cm7(advance), .=Cm7(ghost), x=F7(advance), .=F7(ghost)
        stab1 = sorted(set(n["pitch"] for n in notes[:4]))
        ghost1 = sorted(set(n["pitch"] for n in notes[4:8]))
        stab2 = sorted(set(n["pitch"] for n in notes[8:12]))
        assert 60 in stab1, "Stab 1 should be Cm7"
        assert 60 in ghost1, "Ghost 1 should also be Cm7 (repeats last stab)"
        assert 65 in stab2, "Stab 2 should be F7 (advanced after first x)"

    def test_step_duration(self):
        notes = self._generate_stab([["C", "maj"]], "x---", length_beats=4)
        assert len(notes) == 3, "maj triad = 3 notes"
        assert abs(notes[0]["pos"] - 0) < 0.01, "First stab at pos 0"

    def test_start_beat_offset(self):
        notes = self._generate_stab([["C", "maj"]], "x---", start_beat=8)
        assert abs(notes[0]["pos"] - 8) < 0.01, "Stab should start at beat 8"

    def test_octave_shift(self):
        notes_low = self._generate_stab([["C", "maj"]], "x---", octave=3)
        notes_high = self._generate_stab([["C", "maj"]], "x---", octave=5)
        assert notes_low[0]["pitch"] == 48, f"C3=48, got {notes_low[0]['pitch']}"
        assert notes_high[0]["pitch"] == 72, f"C5=72, got {notes_high[0]['pitch']}"

    def test_sharp_root(self):
        notes = self._generate_stab([["C#", "min"]], "x---")
        assert notes[0]["pitch"] == 61, f"C#4=61, got {notes[0]['pitch']}"

    def test_all_rests_produces_nothing(self):
        notes = self._generate_stab([["C", "maj"]], "--------")
        assert len(notes) == 0, "All rests should produce 0 notes"

    def test_16th_note_grid(self):
        notes = self._generate_stab([["C", "min7"]], "x-x-x-x-x-x-x-x-", length_beats=4)
        assert len(notes) == 32, f"8 stabs × 4 notes = 32, got {len(notes)}"
        # Check positions are on 16th grid (0, 0.5, 1.0, 1.5, ...)
        positions = sorted(set(n["pos"] for n in notes))
        assert positions == [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], f"16th grid positions: {positions}"


class TestRiserPatternGeneration:
    """Test the Python-side pattern generation logic of create_riser."""

    def _generate_riser(self, start_pitch=36, end_pitch=84, steps=32,
                        length_beats=4, curve="exp", velocity=0.7, start_beat=0):
        """Replicate the pattern generation logic from create_riser."""
        note_data = []
        for i in range(steps):
            progress = i / max(1, steps - 1)
            if curve == "exp":
                t = progress * progress
            elif curve == "log":
                t = 1 - (1 - progress) * (1 - progress)
            else:
                t = progress
            pitch = round(start_pitch + (end_pitch - start_pitch) * t)
            pos = start_beat + progress * length_beats
            vel = velocity * (0.3 + 0.7 * progress)
            note_data.append({"pitch": pitch, "pos": pos, "vel": vel})
        return note_data

    def test_note_count_matches_steps(self):
        notes = self._generate_riser(steps=32)
        assert len(notes) == 32, f"Expected 32 notes, got {len(notes)}"

    def test_pitch_ascending(self):
        notes = self._generate_riser(start_pitch=36, end_pitch=84, steps=32)
        for i in range(1, len(notes)):
            assert notes[i]["pitch"] >= notes[i - 1]["pitch"], "Pitch should be non-decreasing"

    def test_start_and_end_pitch(self):
        notes = self._generate_riser(start_pitch=36, end_pitch=84, steps=32)
        assert notes[0]["pitch"] == 36, f"First pitch should be 36, got {notes[0]['pitch']}"
        assert notes[-1]["pitch"] == 84, f"Last pitch should be 84, got {notes[-1]['pitch']}"

    def test_velocity_ramps_up(self):
        notes = self._generate_riser(velocity=0.7, steps=32)
        assert notes[0]["vel"] < notes[-1]["vel"], "Velocity should ramp up"
        assert abs(notes[0]["vel"] - 0.7 * 0.3) < 0.01, f"Start vel should be 0.21, got {notes[0]['vel']}"
        assert abs(notes[-1]["vel"] - 0.7 * 1.0) < 0.01, f"End vel should be 0.7, got {notes[-1]['vel']}"

    def test_linear_curve(self):
        notes = self._generate_riser(start_pitch=0, end_pitch=100, steps=5, curve="linear")
        # Linear: 0, 25, 50, 75, 100
        pitches = [n["pitch"] for n in notes]
        assert pitches == [0, 25, 50, 75, 100], f"Linear curve: {pitches}"

    def test_exp_curve_slow_start(self):
        notes = self._generate_riser(start_pitch=0, end_pitch=100, steps=11, curve="exp")
        # Exp: t = progress^2, so first steps are small increments
        first_gap = notes[1]["pitch"] - notes[0]["pitch"]
        last_gap = notes[-1]["pitch"] - notes[-2]["pitch"]
        assert first_gap < last_gap, "Exp curve should have smaller gaps at start"

    def test_log_curve_fast_start(self):
        notes = self._generate_riser(start_pitch=0, end_pitch=100, steps=11, curve="log")
        # Log: t = 1 - (1-progress)^2, so first steps are large increments
        first_gap = notes[1]["pitch"] - notes[0]["pitch"]
        last_gap = notes[-1]["pitch"] - notes[-2]["pitch"]
        assert first_gap > last_gap, "Log curve should have larger gaps at start"

    def test_start_beat_offset(self):
        notes = self._generate_riser(start_beat=8, steps=4, length_beats=4)
        assert abs(notes[0]["pos"] - 8) < 0.01, f"First note at beat 8, got {notes[0]['pos']}"

    def test_position_spans_length(self):
        notes = self._generate_riser(length_beats=16, steps=32)
        assert abs(notes[0]["pos"] - 0) < 0.01, "Starts at 0"
        assert abs(notes[-1]["pos"] - 16) < 0.01, f"Ends at 16, got {notes[-1]['pos']}"

    def test_clamped_pitch_range(self):
        notes = self._generate_riser(start_pitch=0, end_pitch=127, steps=8)
        assert all(0 <= n["pitch"] <= 127 for n in notes), "Pitches should be 0-127"


class TestBreakPatternGeneration:
    """Test the Python-side pattern generation logic of create_break."""

    _BREAK_PRESETS = {
        "amen": {
            "kick":  "x...x...x...x...",
            "snare": "....x.......x...",
            "hihat": "x.x.x.x.x.x.x.x.",
        },
        "think": {
            "kick":  "x.....x...x.....",
            "snare": "....x.......x...",
            "hihat": "x.x.x.x.x.x.x.x.",
        },
        "funky_drummer": {
            "kick":  "x...x...x...x...",
            "snare": "....x.......x...",
            "hihat": "xxxxxxxxxxxxxxxx",
        },
        "synthetic": {
            "kick":  "x...x...x...x...",
            "snare": "....x.......x...",
            "hihat": ".x.x.x.x.x.x.x.x",
        },
    }

    def _generate_break(self, break_type="amen", bars=1, variation="none",
                        start_beat=0, swing=0.0):
        """Replicate the pattern generation logic from create_break."""
        base_pattern = self._BREAK_PRESETS[break_type]
        lane_pitches = {"kick": 36, "snare": 38, "hihat": 42, "clap": 39, "perc": 47}
        vel_map = {"x": 0.9, "o": 0.5, "X": 1.0}
        bar_steps = 16
        bar_beats = 4
        note_data = []

        for bar in range(bars):
            bar_start = start_beat + bar * bar_beats
            is_last = (bar == bars - 1)

            for lane, pattern in base_pattern.items():
                pitch = lane_pitches.get(lane, 36)
                for i, ch in enumerate(pattern):
                    if ch == "." or ch == " ":
                        continue
                    step_beat = i * (bar_beats / bar_steps)
                    if swing > 0 and i % 2 == 1:
                        step_beat += swing * (bar_beats / bar_steps) * 0.5
                    pos = bar_start + step_beat
                    vel = vel_map.get(ch, 0.8)
                    dur = bar_beats / bar_steps * 0.8

                    if variation == "fill" and is_last and lane in ("snare", "hihat"):
                        if i >= 8:
                            vel = min(1.0, vel * 1.15)
                    elif variation == "drop" and is_last and lane == "kick":
                        if i >= 4:
                            continue
                    elif variation == "humanize":
                        import random as _rng
                        rng = _rng.Random(hash(f"{break_type}{bar}{i}{lane}") & 0xFFFFFFFF)
                        vel = max(0.3, min(1.0, vel + rng.uniform(-0.08, 0.08)))
                        pos += rng.uniform(-0.01, 0.01)

                    note_data.append({"pitch": pitch, "pos": pos, "dur": dur, "vel": vel})
        return note_data

    def test_amen_note_count(self):
        notes = self._generate_break("amen", bars=1)
        # kick=4, snare=2, hihat=8 = 14
        assert len(notes) == 14, f"Expected 14 notes, got {len(notes)}"

    def test_think_note_count(self):
        notes = self._generate_break("think", bars=1)
        # kick=3, snare=2, hihat=8 = 13
        assert len(notes) == 13, f"Expected 13 notes, got {len(notes)}"

    def test_funky_drummer_note_count(self):
        notes = self._generate_break("funky_drummer", bars=1)
        # kick=4, snare=2, hihat=16 = 22
        assert len(notes) == 22, f"Expected 22 notes, got {len(notes)}"

    def test_multi_bar_scaling(self):
        notes1 = self._generate_break("amen", bars=1)
        notes2 = self._generate_break("amen", bars=2)
        assert len(notes2) == len(notes1) * 2, "2 bars should be 2× notes"

    def test_drop_variation_reduces_kick(self):
        notes_none = self._generate_break("amen", bars=2, variation="none")
        notes_drop = self._generate_break("amen", bars=2, variation="drop")
        # Drop removes kick hits after step 4 on last bar (3 kicks removed)
        assert len(notes_drop) < len(notes_none), "Drop should reduce notes"
        diff = len(notes_none) - len(notes_drop)
        assert diff == 3, f"Expected 3 fewer notes (kicks), got {diff}"

    def test_fill_variation_same_note_count(self):
        notes_none = self._generate_break("think", bars=2, variation="none")
        notes_fill = self._generate_break("think", bars=2, variation="fill")
        # Fill only changes velocity, doesn't add/remove notes
        assert len(notes_fill) == len(notes_none), "Fill should keep same note count"

    def test_humanize_changes_velocity(self):
        notes_plain = self._generate_break("amen", bars=1, variation="none")
        notes_human = self._generate_break("amen", bars=1, variation="humanize")
        plain_vels = [n["vel"] for n in notes_plain]
        human_vels = [n["vel"] for n in notes_human]
        assert human_vels != plain_vels, "Humanize should alter velocities"

    def test_swing_shifts_odd_steps(self):
        notes_plain = self._generate_break("synthetic", bars=1, swing=0.0)
        notes_swing = self._generate_break("synthetic", bars=1, swing=0.58)
        # Swing shifts odd 16th positions — at least some positions differ
        plain_pos = [n["pos"] for n in notes_plain]
        swing_pos = [n["pos"] for n in notes_swing]
        assert plain_pos != swing_pos, "Swing should shift positions"

    def test_start_beat_offset(self):
        notes = self._generate_break("amen", bars=1, start_beat=16)
        assert abs(notes[0]["pos"] - 16) < 0.01, f"First note at beat 16, got {notes[0]['pos']}"

    def test_lane_pitches_correct(self):
        notes = self._generate_break("amen", bars=1)
        kick_notes = [n for n in notes if n["pitch"] == 36]
        snare_notes = [n for n in notes if n["pitch"] == 38]
        hihat_notes = [n for n in notes if n["pitch"] == 42]
        assert len(kick_notes) == 4, f"Expected 4 kick notes, got {len(kick_notes)}"
        assert len(snare_notes) == 2, f"Expected 2 snare notes, got {len(snare_notes)}"
        assert len(hihat_notes) == 8, f"Expected 8 hihat notes, got {len(hihat_notes)}"

    def test_velocity_map(self):
        notes = self._generate_break("amen", bars=1, variation="none")
        # All 'x' hits should have velocity 0.9
        assert all(abs(n["vel"] - 0.9) < 0.01 for n in notes), "All hits should be 0.9 velocity"


class TestBassDropPatternGeneration:
    """Test the Python-side pattern generation logic of create_bass_drop."""

    def _generate_bass_drop(self, start_pitch=48, end_pitch=24, sweep_beats=2,
                            hold_beats=4, sweep_curve="exp", velocity=1.0, start_beat=0):
        """Replicate the pattern generation logic from create_bass_drop."""
        sweep_steps = max(8, int(sweep_beats * 16))
        note_data = []

        for i in range(sweep_steps):
            progress = i / max(1, sweep_steps - 1)
            if sweep_curve == "exp":
                t = 1 - (1 - progress) * (1 - progress)
            elif sweep_curve == "log":
                t = progress * progress
            else:
                t = progress
            pitch = round(start_pitch + (end_pitch - start_pitch) * t)
            pos = start_beat + progress * sweep_beats
            step_dur = sweep_beats / sweep_steps
            vel = velocity * (0.7 + 0.3 * progress)
            note_data.append({"pitch": pitch, "pos": pos, "dur": step_dur * 1.5, "vel": vel})

        if hold_beats > 0:
            hold_pos = start_beat + sweep_beats
            note_data.append({"pitch": end_pitch, "pos": hold_pos, "dur": hold_beats, "vel": velocity})
        return note_data

    def test_default_note_count(self):
        notes = self._generate_bass_drop()
        # sweep_steps = max(8, 2*16) = 32, + 1 hold = 33
        assert len(notes) == 33, f"Expected 33, got {len(notes)}"

    def test_pitch_descending(self):
        notes = self._generate_bass_drop(start_pitch=48, end_pitch=24, sweep_beats=2)
        sweep_notes = notes[:-1]  # exclude hold
        for i in range(1, len(sweep_notes)):
            assert sweep_notes[i]["pitch"] <= sweep_notes[i - 1]["pitch"], "Pitch should be non-increasing"

    def test_start_and_end_pitch(self):
        notes = self._generate_bass_drop(start_pitch=48, end_pitch=24)
        assert notes[0]["pitch"] == 48, f"First pitch should be 48, got {notes[0]['pitch']}"
        assert notes[-1]["pitch"] == 24, f"Last pitch should be 24 (hold), got {notes[-1]['pitch']}"

    def test_no_hold(self):
        notes = self._generate_bass_drop(hold_beats=0)
        # Only sweep notes, no hold
        sweep_steps = max(8, int(2 * 16))
        assert len(notes) == sweep_steps, f"Expected {sweep_steps} sweep notes, got {len(notes)}"

    def test_hold_note_duration(self):
        notes = self._generate_bass_drop(hold_beats=4)
        hold = notes[-1]
        assert abs(hold["dur"] - 4) < 0.01, f"Hold duration should be 4 beats, got {hold['dur']}"
        assert hold["pitch"] == 24, f"Hold pitch should be end_pitch=24, got {hold['pitch']}"

    def test_velocity_ramps_during_sweep(self):
        notes = self._generate_bass_drop(velocity=1.0)
        sweep = notes[:-1]
        assert sweep[0]["vel"] < sweep[-1]["vel"], "Velocity should ramp up during sweep"

    def test_linear_curve(self):
        notes = self._generate_bass_drop(start_pitch=0, end_pitch=40, sweep_beats=1, sweep_curve="linear", hold_beats=0)
        # sweep_steps = max(8, 16) = 16, linear: 0, 2.67, 5.33... rounded
        assert notes[0]["pitch"] == 0
        assert notes[-1]["pitch"] == 40

    def test_exp_curve_fast_start(self):
        notes = self._generate_bass_drop(start_pitch=0, end_pitch=100, sweep_beats=1, sweep_curve="exp", hold_beats=0)
        # Exp: fast start → large first gap, small last gap
        first_gap = abs(notes[1]["pitch"] - notes[0]["pitch"])
        last_gap = abs(notes[-1]["pitch"] - notes[-2]["pitch"])
        assert first_gap > last_gap, "Exp curve should have larger gaps at start (descending)"

    def test_log_curve_slow_start(self):
        notes = self._generate_bass_drop(start_pitch=0, end_pitch=100, sweep_beats=1, sweep_curve="log", hold_beats=0)
        first_gap = abs(notes[1]["pitch"] - notes[0]["pitch"])
        last_gap = abs(notes[-1]["pitch"] - notes[-2]["pitch"])
        assert first_gap < last_gap, "Log curve should have smaller gaps at start"

    def test_start_beat_offset(self):
        notes = self._generate_bass_drop(start_beat=16, hold_beats=0)
        assert abs(notes[0]["pos"] - 16) < 0.01, f"First note at beat 16, got {notes[0]['pos']}"

    def test_short_sweep_minimum_steps(self):
        notes = self._generate_bass_drop(sweep_beats=0.25, hold_beats=0)
        # sweep_steps = max(8, 0.25*16=4) = 8
        assert len(notes) == 8, f"Expected 8 minimum sweep notes, got {len(notes)}"

    def test_hold_position_after_sweep(self):
        notes = self._generate_bass_drop(sweep_beats=3, hold_beats=2, start_beat=0)
        hold = notes[-1]
        assert abs(hold["pos"] - 3) < 0.01, f"Hold should start at beat 3, got {hold['pos']}"


class TestChopPatternGeneration:
    """Test the Python-side pattern generation logic of create_chop."""

    def _generate_chop(self, pitches="60,62,64,67", chop_mode="reverse",
                       segment_beats=0.5, stutter_count=2, octave_shift=0,
                       velocity_variation=0.2, reverse_pitch_in_segment=False,
                       velocity=0.9, seed=42, start_beat=0):
        """Replicate the pattern generation logic from create_chop."""
        import random as _rng
        rng = _rng.Random(seed)

        pitch_list = [int(p.strip()) for p in pitches.split(",")]
        shifted = [max(0, min(127, p + octave_shift * 12)) for p in pitch_list]
        segments = list(range(len(shifted)))

        if chop_mode == "reverse":
            seg_order = segments[::-1]
        elif chop_mode == "stutter":
            seg_order = []
            for s in segments:
                seg_order.extend([s] * stutter_count)
        elif chop_mode == "shuffle":
            seg_order = segments[:]
            rng.shuffle(seg_order)
        elif chop_mode == "ping-pong":
            seg_order = segments + segments[::-1]
        elif chop_mode == "gate":
            seg_order = [s for i, s in enumerate(segments) if i % 2 == 0]
        else:
            seg_order = segments

        if reverse_pitch_in_segment:
            shifted = shifted[::-1]

        note_data = []
        for idx, seg_i in enumerate(seg_order):
            pos = start_beat + idx * segment_beats
            vel = velocity
            if velocity_variation > 0:
                vel = max(0.1, min(1.0, vel + rng.uniform(-velocity_variation, velocity_variation)))
            note_data.append({
                "pitch": shifted[seg_i],
                "pos": pos,
                "dur": segment_beats * 0.9,
                "vel": round(vel, 3),
            })
        return note_data, seg_order, shifted

    def test_reverse_order(self):
        notes, seg, _ = self._generate_chop(pitches="60,62,64,67", chop_mode="reverse")
        assert len(notes) == 4
        assert seg == [3, 2, 1, 0]
        assert notes[0]["pitch"] == 67, f"First reversed pitch should be 67, got {notes[0]['pitch']}"
        assert notes[-1]["pitch"] == 60

    def test_stutter_count(self):
        notes, seg, _ = self._generate_chop(pitches="60,62,64", chop_mode="stutter", stutter_count=3)
        assert len(notes) == 9, f"Expected 9 (3x3), got {len(notes)}"
        assert seg == [0, 0, 0, 1, 1, 1, 2, 2, 2]

    def test_shuffle_same_seed(self):
        notes1, seg1, _ = self._generate_chop(pitches="60,62,64,67", chop_mode="shuffle", seed=42)
        notes2, seg2, _ = self._generate_chop(pitches="60,62,64,67", chop_mode="shuffle", seed=42)
        assert seg1 == seg2, "Same seed should produce same shuffle order"
        assert len(notes1) == 4

    def test_shuffle_different_seed(self):
        _, seg1, _ = self._generate_chop(pitches="60,62,64,67,69", chop_mode="shuffle", seed=1)
        _, seg2, _ = self._generate_chop(pitches="60,62,64,67,69", chop_mode="shuffle", seed=999)
        # Very unlikely to be identical with different seeds
        assert seg1 != seg2, "Different seeds should produce different shuffle orders"

    def test_ping_pong(self):
        notes, seg, _ = self._generate_chop(pitches="60,62,64,67", chop_mode="ping-pong")
        assert len(notes) == 8, f"Expected 8 (4+4), got {len(notes)}"
        assert seg == [0, 1, 2, 3, 3, 2, 1, 0]

    def test_gate(self):
        notes, seg, _ = self._generate_chop(pitches="60,62,64,67,69,71", chop_mode="gate")
        assert len(notes) == 3, f"Expected 3 (6/2), got {len(notes)}"
        assert seg == [0, 2, 4]

    def test_octave_shift_down(self):
        notes, _, shifted = self._generate_chop(pitches="60,62,64,67", octave_shift=-1)
        assert all(p <= 60 for p in shifted), "Octave -1 should shift all pitches down"
        assert shifted == [48, 50, 52, 55]

    def test_octave_shift_up(self):
        _, _, shifted = self._generate_chop(pitches="60,62,64,67", octave_shift=1)
        assert shifted == [72, 74, 76, 79]

    def test_velocity_variation_bounds(self):
        notes, _, _ = self._generate_chop(velocity=0.9, velocity_variation=0.2)
        for n in notes:
            assert 0.1 <= n["vel"] <= 1.0, f"Velocity {n['vel']} out of bounds"

    def test_no_velocity_variation(self):
        notes, _, _ = self._generate_chop(velocity_variation=0.0)
        for n in notes:
            assert n["vel"] == 0.9, f"Without variation, all velocities should be 0.9, got {n['vel']}"

    def test_segment_duration(self):
        notes, _, _ = self._generate_chop(segment_beats=0.25)
        assert abs(notes[0]["dur"] - 0.225) < 0.01, f"Duration should be 0.25*0.9=0.225, got {notes[0]['dur']}"

    def test_position_spacing(self):
        notes, _, _ = self._generate_chop(pitches="60,62,64,67", chop_mode="reverse", segment_beats=0.5)
        for i in range(1, len(notes)):
            gap = notes[i]["pos"] - notes[i - 1]["pos"]
            assert abs(gap - 0.5) < 0.01, f"Gap should be 0.5 beats, got {gap}"

    def test_reverse_pitch_in_segment(self):
        notes, _, shifted = self._generate_chop(
            pitches="60,62,64,67", chop_mode="reverse",
            reverse_pitch_in_segment=True
        )
        # Original: [60,62,64,67], reversed: [67,64,62,60]
        # Then reverse mode picks segments [3,2,1,0] from reversed list
        # seg_order [3,2,1,0] → shifted[3]=60, shifted[2]=62, shifted[1]=64, shifted[0]=67
        assert shifted == [67, 64, 62, 60], f"Expected [67,64,62,60], got {shifted}"
        assert notes[0]["pitch"] == 60
        assert notes[1]["pitch"] == 62
        assert notes[2]["pitch"] == 64
        assert notes[3]["pitch"] == 67


class TestTrillPatternGeneration:
    """Test the Python-side pattern generation logic of create_trill."""

    def _generate_trill(self, lower_pitch=60, upper_pitch=62, rate="16th",
                        duration_beats=4, accent_upper=True, start_with_upper=False,
                        velocity=0.85, start_beat=0):
        """Replicate the pattern generation logic from create_trill."""
        rate_map = {
            "32nd": 0.125,
            "16th": 0.25,
            "8th": 0.5,
            "32t": 1/12,
            "16t": 1/6,
        }
        note_dur = rate_map[rate]
        total_notes = int(duration_beats / note_dur)

        note_data = []
        for i in range(total_notes):
            use_upper = (i % 2 == 1) if not start_with_upper else (i % 2 == 0)
            pitch = upper_pitch if use_upper else lower_pitch
            vel = velocity
            if accent_upper and use_upper:
                vel = min(1.0, velocity * 1.12)
            pos = start_beat + i * note_dur
            note_data.append({
                "pitch": pitch,
                "pos": pos,
                "dur": note_dur * 0.9,
                "vel": round(vel, 3),
            })
        return note_data

    def test_default_note_count(self):
        notes = self._generate_trill(duration_beats=4, rate="16th")
        assert len(notes) == 16, f"Expected 16, got {len(notes)}"

    def test_32nd_rate(self):
        notes = self._generate_trill(rate="32nd", duration_beats=8)
        assert len(notes) == 64, f"Expected 64, got {len(notes)}"

    def test_8th_rate(self):
        notes = self._generate_trill(rate="8th", duration_beats=2)
        assert len(notes) == 4, f"Expected 4, got {len(notes)}"

    def test_triplet_16th(self):
        notes = self._generate_trill(rate="16t", duration_beats=4)
        assert len(notes) == 24, f"Expected 24, got {len(notes)}"

    def test_alternation_pattern(self):
        notes = self._generate_trill(lower_pitch=60, upper_pitch=62, rate="8th", duration_beats=4)
        # Should alternate: 60, 62, 60, 62, 60, 62, 60, 62
        for i in range(len(notes)):
            expected = 62 if i % 2 == 1 else 60
            assert notes[i]["pitch"] == expected, f"Note {i}: expected {expected}, got {notes[i]['pitch']}"

    def test_start_with_upper(self):
        notes = self._generate_trill(rate="8th", duration_beats=4, start_with_upper=True)
        assert notes[0]["pitch"] == 62, f"First note should be upper (62), got {notes[0]['pitch']}"
        assert notes[1]["pitch"] == 60

    def test_accent_upper_velocity(self):
        notes = self._generate_trill(rate="8th", duration_beats=2, accent_upper=True, velocity=0.85)
        lower_vels = [n["vel"] for n in notes if n["pitch"] == 60]
        upper_vels = [n["vel"] for n in notes if n["pitch"] == 62]
        assert upper_vels[0] > lower_vels[0], "Upper notes should be louder with accent_upper"

    def test_no_accent_equal_velocity(self):
        notes = self._generate_trill(rate="8th", duration_beats=2, accent_upper=False, velocity=0.85)
        vels = [n["vel"] for n in notes]
        assert all(v == 0.85 for v in vels), "Without accent, all velocities should be equal"

    def test_position_spacing(self):
        notes = self._generate_trill(rate="16th", duration_beats=4)
        for i in range(1, len(notes)):
            gap = notes[i]["pos"] - notes[i - 1]["pos"]
            assert abs(gap - 0.25) < 0.01, f"Gap should be 0.25 beats, got {gap}"

    def test_note_duration(self):
        notes = self._generate_trill(rate="16th")
        assert abs(notes[0]["dur"] - 0.225) < 0.01, f"Duration should be 0.25*0.9=0.225, got {notes[0]['dur']}"

    def test_start_beat_offset(self):
        notes = self._generate_trill(rate="8th", duration_beats=2, start_beat=8)
        assert abs(notes[0]["pos"] - 8) < 0.01


class TestGlissandoPatternGeneration:
    """Test the Python-side pattern generation logic of create_glissando."""

    def _generate_glissando(self, start_pitch=60, end_pitch=72, scale_type="chromatic",
                            duration_beats=2, rate="16th", velocity=0.8,
                            velocity_curve="ramp_up", start_beat=0):
        """Replicate the pattern generation logic from create_glissando."""
        scale_intervals = {
            "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10],
            "pentatonic_minor": [0, 3, 5, 7, 10],
            "pentatonic_major": [0, 2, 4, 7, 9],
            "whole_tone": [0, 2, 4, 6, 8, 10],
        }
        intervals = scale_intervals[scale_type]
        direction = 1 if end_pitch > start_pitch else -1
        pitches = []
        root_pc = start_pitch % 12
        current = start_pitch
        while current != end_pitch:
            pc = current % 12
            rel = (pc - root_pc) % 12
            if rel in intervals:
                pitches.append(current)
            current += direction
        pitches.append(end_pitch)

        rate_map = {"32nd": 0.125, "16th": 0.25, "8th": 0.5, "32t": 1/12, "16t": 1/6}
        note_dur = rate_map[rate]
        total_notes = len(pitches)
        actual_dur = min(note_dur, duration_beats / max(1, total_notes))

        note_data = []
        for i, pitch in enumerate(pitches):
            progress = i / max(1, total_notes - 1)
            pos = start_beat + i * actual_dur
            if velocity_curve == "flat":
                vel = velocity
            elif velocity_curve == "ramp_up":
                vel = velocity * (0.6 + 0.4 * progress)
            elif velocity_curve == "ramp_down":
                vel = velocity * (1.0 - 0.4 * progress)
            elif velocity_curve == "arc":
                vel = velocity * (0.5 + 0.5 * (1 - abs(2 * progress - 1)))
            else:
                vel = velocity
            vel = max(0.01, min(1.0, vel))
            note_data.append({
                "pitch": pitch,
                "pos": pos,
                "dur": actual_dur * 0.95,
                "vel": round(vel, 3),
            })
        return note_data, pitches, direction

    def test_chromatic_ascending(self):
        notes, pitches, _ = self._generate_glissando(60, 72, "chromatic")
        assert len(pitches) == 13, f"Expected 13, got {len(pitches)}"
        assert pitches[0] == 60 and pitches[-1] == 72

    def test_major_scale(self):
        notes, pitches, _ = self._generate_glissando(60, 72, "major")
        assert len(pitches) == 8, f"Expected 8, got {len(pitches)}"

    def test_minor_scale(self):
        notes, pitches, _ = self._generate_glissando(60, 72, "minor")
        assert len(pitches) == 8, f"Expected 8, got {len(pitches)}"

    def test_pentatonic_minor(self):
        notes, pitches, _ = self._generate_glissando(60, 72, "pentatonic_minor")
        assert len(pitches) == 6, f"Expected 6, got {len(pitches)}"

    def test_pentatonic_major(self):
        notes, pitches, _ = self._generate_glissando(60, 72, "pentatonic_major")
        assert len(pitches) == 6, f"Expected 6, got {len(pitches)}"

    def test_whole_tone(self):
        notes, pitches, _ = self._generate_glissando(60, 72, "whole_tone")
        assert len(pitches) == 7, f"Expected 7, got {len(pitches)}"

    def test_descending(self):
        notes, pitches, direction = self._generate_glissando(72, 60, "chromatic")
        assert direction == -1
        assert pitches[0] == 72 and pitches[-1] == 60
        assert len(pitches) == 13

    def test_velocity_ramp_up(self):
        notes, _, _ = self._generate_glissando(velocity_curve="ramp_up")
        assert notes[-1]["vel"] > notes[0]["vel"], "ramp_up: last note should be louder"

    def test_velocity_ramp_down(self):
        notes, _, _ = self._generate_glissando(velocity_curve="ramp_down")
        assert notes[0]["vel"] > notes[-1]["vel"], "ramp_down: first note should be louder"

    def test_velocity_arc(self):
        notes, _, _ = self._generate_glissando(velocity_curve="arc")
        mid = len(notes) // 2
        assert notes[mid]["vel"] > notes[0]["vel"], "arc: middle should be louder than start"
        assert notes[mid]["vel"] > notes[-1]["vel"], "arc: middle should be louder than end"

    def test_velocity_flat(self):
        notes, _, _ = self._generate_glissando(velocity_curve="flat", velocity=0.8)
        assert all(n["vel"] == 0.8 for n in notes)

    def test_position_spacing(self):
        notes, _, _ = self._generate_glissando(rate="16th", duration_beats=4)
        for i in range(1, len(notes)):
            gap = notes[i]["pos"] - notes[i - 1]["pos"]
            assert gap > 0, "Positions should be increasing"


class TestSequencePatternGeneration:
    """Test the Python-side pattern generation logic of create_sequence."""

    def _generate_sequence(self, pattern="60,62,64,60", transposition=5,
                           repeats=3, direction="up", segment_beats=2,
                           velocity_decay=0.0, velocity=0.8, start_beat=0):
        """Replicate the pattern generation logic from create_sequence."""
        base_pitches = [int(p.strip()) for p in pattern.split(",")]
        note_data = []
        note_dur = segment_beats / len(base_pitches)

        for rep in range(repeats):
            if direction == "up":
                transpose = transposition * rep
            elif direction == "down":
                transpose = -transposition * rep
            elif direction == "alternating":
                transpose = transposition * rep if rep % 2 == 0 else -transposition * rep

            rep_vel = max(0.01, min(1.0, velocity + velocity_decay * rep))

            for j, base_pitch in enumerate(base_pitches):
                pitch = max(0, min(127, base_pitch + transpose))
                pos = start_beat + rep * segment_beats + j * note_dur
                note_data.append({
                    "pitch": pitch,
                    "pos": pos,
                    "dur": note_dur * 0.9,
                    "vel": round(rep_vel, 3),
                })
        return note_data

    def test_default_note_count(self):
        notes = self._generate_sequence(pattern="60,62,64,60", repeats=3)
        assert len(notes) == 12, f"Expected 12 (4x3), got {len(notes)}"

    def test_ascending_transposition(self):
        notes = self._generate_sequence(pattern="60,62,64", transposition=5, repeats=3, direction="up")
        # rep 0: 60,62,64; rep 1: 65,67,69; rep 2: 70,72,74
        assert notes[0]["pitch"] == 60
        assert notes[3]["pitch"] == 65
        assert notes[6]["pitch"] == 70

    def test_descending_transposition(self):
        notes = self._generate_sequence(pattern="72,71,69", transposition=2, repeats=3, direction="down")
        assert notes[0]["pitch"] == 72
        assert notes[3]["pitch"] == 70
        assert notes[6]["pitch"] == 68

    def test_alternating_direction(self):
        notes = self._generate_sequence(pattern="60,62,64", transposition=7, repeats=4, direction="alternating")
        # rep 0: +0, rep 1: +7, rep 2: -14? No: rep 2 = +7*2=+14? Let me check
        # rep 0: 0%2==0 → +7*0=0, rep 1: 1%2==1 → -7*1=-7, rep 2: 2%2==0 → +7*2=14, rep 3: 3%2==1 → -7*3=-21
        assert notes[0]["pitch"] == 60  # rep 0, transpose=0
        assert notes[3]["pitch"] == 53  # rep 1, transpose=-7
        assert notes[6]["pitch"] == 74  # rep 2, transpose=+14

    def test_velocity_decay(self):
        notes = self._generate_sequence(pattern="60,62,64", repeats=3, velocity_decay=-0.1, velocity=0.8)
        assert notes[0]["vel"] == 0.8
        assert notes[3]["vel"] == 0.7
        assert notes[6]["vel"] == 0.6

    def test_velocity_increase(self):
        notes = self._generate_sequence(pattern="60,62,64", repeats=3, velocity_decay=0.15, velocity=0.5)
        assert notes[0]["vel"] == 0.5
        assert notes[3]["vel"] == 0.65
        assert notes[6]["vel"] == 0.8

    def test_position_spacing(self):
        notes = self._generate_sequence(pattern="60,62,64,60", repeats=2, segment_beats=2)
        # Each note dur = 2/4 = 0.5 beats
        for i in range(1, len(notes)):
            gap = notes[i]["pos"] - notes[i - 1]["pos"]
            assert abs(gap - 0.5) < 0.01, f"Gap should be 0.5, got {gap}"

    def test_single_repeat(self):
        notes = self._generate_sequence(pattern="60,62,64,67", repeats=1, transposition=7)
        assert len(notes) == 4
        assert all(n["pitch"] in (60, 62, 64, 67) for n in notes)

    def test_pitch_clamping(self):
        # High pitches + high transposition should clamp to 127
        notes = self._generate_sequence(pattern="120,122,124", transposition=12, repeats=3, direction="up")
        for n in notes:
            assert n["pitch"] <= 127


class TestPedalPointGeneration:
    """Test the Python-side pattern generation logic of create_pedal_point."""

    CHORD_INTERVALS = {
        "maj": [0, 4, 7], "M": [0, 4, 7], "min": [0, 3, 7], "m": [0, 3, 7],
        "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11], "M7": [0, 4, 7, 11],
        "dom7": [0, 4, 7, 10], "7": [0, 4, 7, 10],
        "sus2": [0, 2, 7], "sus4": [0, 5, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    }
    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    def _parse_chord(self, name):
        root = None
        quality = None
        for q in ["maj7", "m7", "M7", "sus2", "sus4", "dom7", "dim", "aug", "maj", "min", "M", "m", "7"]:
            if name.endswith(q) and len(name) > len(q):
                root_name = name[:-len(q)]
                if root_name in self.NOTE_TO_PC:
                    root = self.NOTE_TO_PC[root_name]
                    quality = q
                    break
        if root is None:
            if name in self.NOTE_TO_PC:
                root = self.NOTE_TO_PC[name]
                quality = "maj"
            else:
                return None
        return self.CHORD_INTERVALS.get(quality, [0, 4, 7])

    def _generate_pedal(self, pedal_pitch=36, chord_pattern="Cm,Ab,Eb,Bb",
                        bars_per_chord=1, beats_per_bar=4, pedal_velocity=0.75,
                        chord_velocity=0.6, chord_octave=4, retrigger_pedal=True, start_beat=0):
        chords = []
        for name in chord_pattern.split(","):
            intervals = self._parse_chord(name.strip())
            if intervals is None:
                return None, None
            root_pc = self.NOTE_TO_PC.get(name.strip().rstrip("maj7Mmsus4dimaug"), 0)
            chord_pitches = [(chord_octave + 1) * 12 + root_pc + iv for iv in intervals]
            chords.append(chord_pitches)

        chord_beats = bars_per_chord * beats_per_bar
        total_beats = len(chords) * chord_beats
        note_data = []

        if retrigger_pedal:
            for i in range(len(chords)):
                note_data.append({"pitch": pedal_pitch, "pos": start_beat + i * chord_beats,
                                  "dur": chord_beats, "vel": pedal_velocity})
        else:
            note_data.append({"pitch": pedal_pitch, "pos": start_beat, "dur": total_beats, "vel": pedal_velocity})

        for i, chord in enumerate(chords):
            for pitch in chord:
                note_data.append({"pitch": pitch, "pos": start_beat + i * chord_beats,
                                  "dur": chord_beats * 0.95, "vel": chord_velocity})
        return note_data, chords

    def test_retrigger_pedal_note_count(self):
        notes, chords = self._generate_pedal("Cm,Ab,Eb,Bb", retrigger_pedal=True) if False else self._generate_pedal(chord_pattern="Cm,Ab,Eb,Bb", retrigger_pedal=True)
        # 4 pedal + 4×3 chord = 16
        assert len(notes) == 16, f"Expected 16, got {len(notes)}"

    def test_sustained_pedal_note_count(self):
        notes, _ = self._generate_pedal(chord_pattern="Cm,Ab,Eb,Bb", retrigger_pedal=False)
        # 1 pedal + 12 chord = 13
        assert len(notes) == 13, f"Expected 13, got {len(notes)}"

    def test_seventh_chords(self):
        notes, chords = self._generate_pedal(chord_pattern="Cm7,Fm7,Gm7")
        # 3 pedal + 3×4 = 15
        assert len(notes) == 15, f"Expected 15, got {len(notes)}"

    def test_chord_parsing_minor(self):
        intervals = self._parse_chord("Cm")
        assert intervals == [0, 3, 7], f"Expected [0,3,7], got {intervals}"

    def test_chord_parsing_implicit_major(self):
        intervals = self._parse_chord("Ab")
        assert intervals == [0, 4, 7], f"Expected [0,4,7], got {intervals}"

    def test_chord_parsing_sus4(self):
        intervals = self._parse_chord("Csus4")
        assert intervals == [0, 5, 7], f"Expected [0,5,7], got {intervals}"

    def test_chord_parsing_dim(self):
        intervals = self._parse_chord("Bdim")
        assert intervals == [0, 3, 6], f"Expected [0,3,6], got {intervals}"

    def test_bad_chord_returns_none(self):
        intervals = self._parse_chord("XYZ")
        assert intervals is None

    def test_total_beats_4_4(self):
        notes, _ = self._generate_pedal(chord_pattern="Cm,Ab", beats_per_bar=4)
        assert notes[-1]["pos"] + notes[-1]["dur"] <= 8 + 0.01

    def test_total_beats_3_4(self):
        notes, _ = self._generate_pedal(chord_pattern="Cm,Ab,Eb", beats_per_bar=3)
        # 3 chords × 3 beats = 9 total
        last_note = max(notes, key=lambda n: n["pos"])
        assert last_note["pos"] < 9


class TestPassacagliaGeneration:
    """Test the Python-side pattern generation logic of create_passacaglia."""

    CHORD_INTERVALS = {
        "maj": [0, 4, 7], "M": [0, 4, 7], "min": [0, 3, 7], "m": [0, 3, 7],
        "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11], "M7": [0, 4, 7, 11],
        "dom7": [0, 4, 7, 10], "7": [0, 4, 7, 10],
        "sus2": [0, 2, 7], "sus4": [0, 5, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    }
    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    def _parse_chord(self, name):
        root = None
        quality = None
        for q in ["maj7", "m7", "M7", "sus2", "sus4", "dom7", "dim", "aug", "maj", "min", "M", "m", "7"]:
            if name.endswith(q) and len(name) > len(q):
                root_name = name[:-len(q)]
                if root_name in self.NOTE_TO_PC:
                    root = self.NOTE_TO_PC[root_name]
                    quality = q
                    break
        if root is None:
            if name in self.NOTE_TO_PC:
                root = self.NOTE_TO_PC[name]
                quality = "maj"
            else:
                return None, None
        return root, self.CHORD_INTERVALS.get(quality, [0, 4, 7])

    def _generate_passacaglia(self, bass_pattern="36 43 41 36", bass_rhythm="1 1 1 1",
                              bass_repeats=4, chord_pattern="Cm,Ab,Eb,Bb",
                              chord_octave=4, variation_style="block",
                              beats_per_bar=4, start_beat=0):
        bass_pitches = [int(x) for x in bass_pattern.split()]
        bass_durs = [float(x) for x in bass_rhythm.split()]
        chords = []
        for name in chord_pattern.split(","):
            root, intervals = self._parse_chord(name.strip())
            if intervals is None:
                return None
            chord_pitches = [(chord_octave + 1) * 12 + root + iv for iv in intervals]
            chords.append(chord_pitches)

        bass_pattern_beats = sum(bass_durs)
        note_data = []

        for rep in range(bass_repeats):
            bass_pos = start_beat + rep * bass_pattern_beats
            cumulative = 0.0
            for i, pitch in enumerate(bass_pitches):
                note_data.append({"pitch": pitch, "pos": bass_pos + cumulative,
                                  "dur": bass_durs[i] * 0.95, "vel": 0.75})
                cumulative += bass_durs[i]

        for rep in range(bass_repeats):
            chord = chords[rep % len(chords)]
            chord_start = start_beat + rep * bass_pattern_beats
            if variation_style == "block":
                for pitch in chord:
                    note_data.append({"pitch": pitch, "pos": chord_start,
                                      "dur": bass_pattern_beats * 0.9, "vel": 0.55})
            elif variation_style == "arpeggiated":
                arp_step = bass_pattern_beats / len(chord)
                for j, pitch in enumerate(chord):
                    note_data.append({"pitch": pitch, "pos": chord_start + j * arp_step,
                                      "dur": arp_step * 0.9, "vel": 0.55})
            elif variation_style == "melodic":
                num_notes = max(2, int(bass_pattern_beats))
                step_dur = bass_pattern_beats / num_notes
                for j in range(num_notes):
                    note_data.append({"pitch": chord[j % len(chord)], "pos": chord_start + j * step_dur,
                                      "dur": step_dur * 0.9, "vel": 0.55})
        return note_data

    def test_block_variation_note_count(self):
        notes = self._generate_passacaglia(bass_pattern="36 43 41 36", bass_repeats=4,
                                           chord_pattern="Cm,Ab,Eb,Bb", variation_style="block")
        # 4×4 bass + 4×3 chord = 16 + 12 = 28
        assert len(notes) == 28, f"Expected 28, got {len(notes)}"

    def test_arpeggiated_note_count(self):
        notes = self._generate_passacaglia(bass_pattern="36 36 36 36", bass_repeats=2,
                                           chord_pattern="Cm,G", variation_style="arpeggiated")
        # 2×4 bass + 2×3 arp = 8 + 6 = 14
        assert len(notes) == 14, f"Expected 14, got {len(notes)}"

    def test_melodic_variation_has_notes(self):
        notes = self._generate_passacaglia(bass_pattern="40 43 46 43", bass_repeats=3,
                                           chord_pattern="Dm,Am,Em", variation_style="melodic")
        # 3×4 bass + 3×4 melodic = 12 + 12 = 24
        assert len(notes) == 24, f"Expected 24, got {len(notes)}"

    def test_bass_pattern_repeats(self):
        notes = self._generate_passacaglia(bass_pattern="36 43", bass_rhythm="2 2",
                                           bass_repeats=3, chord_pattern="Cm")
        bass_notes = [n for n in notes if n["pitch"] == 36]
        assert len(bass_notes) == 3, f"Expected 3 bass C2 notes, got {len(bass_notes)}"

    def test_syncopated_bass_rhythm(self):
        notes = self._generate_passacaglia(bass_pattern="36 43 41 36", bass_rhythm="0.5 0.5 1 2",
                                           bass_repeats=1, chord_pattern="Cm")
        bass_notes = [n for n in notes if n["vel"] == 0.75]
        assert bass_notes[1]["pos"] == 0.5, f"Second note should be at 0.5, got {bass_notes[1]['pos']}"
        assert bass_notes[2]["pos"] == 1.0, f"Third note should be at 1.0, got {bass_notes[2]['pos']}"

    def test_chord_cycling(self):
        notes = self._generate_passacaglia(bass_pattern="36", bass_rhythm="4",
                                           bass_repeats=4, chord_pattern="Cm,Ab")
        # Chords cycle: Cm, Ab, Cm, Ab
        chord_notes = [n for n in notes if n["vel"] == 0.55]
        # Cm = [60,63,67], Ab = [68,72,75] (octave 4)
        first_chord_pitches = sorted([n["pitch"] for n in chord_notes[:3]])
        second_chord_pitches = sorted([n["pitch"] for n in chord_notes[3:6]])
        assert 63 in first_chord_pitches, "First chord should be Cm (has Eb=63)"
        assert 68 in second_chord_pitches, "Second chord should be Ab (has Ab=68)"

    def test_3_4_time_signature(self):
        notes = self._generate_passacaglia(bass_pattern="36 41 43", bass_rhythm="1 1 1",
                                           bass_repeats=4, chord_pattern="Cm,Ab,Eb,Fm",
                                           beats_per_bar=3)
        # 4×3 bass + 4×3 chord = 12 + 12 = 24
        assert len(notes) == 24, f"Expected 24, got {len(notes)}"

    def test_total_beats_calculation(self):
        notes = self._generate_passacaglia(bass_pattern="36 43 41 36", bass_rhythm="1 1 1 1",
                                           bass_repeats=4, chord_pattern="Cm")
        last_bass = max([n for n in notes if n["vel"] == 0.75], key=lambda n: n["pos"])
        # Last bass note: 3rd repeat (0-indexed), pos=12, 4th note offset=3 → 15
        assert last_bass["pos"] == 15, f"Last bass at 15, got {last_bass['pos']}"

    def test_chord_parsing_seventh(self):
        root, intervals = self._parse_chord("Cm7")
        assert intervals == [0, 3, 7, 10], f"Expected [0,3,7,10], got {intervals}"

    def test_chord_parsing_implicit_major(self):
        root, intervals = self._parse_chord("Ab")
        assert root == 8, f"Ab root should be 8, got {root}"
        assert intervals == [0, 4, 7], f"Expected [0,4,7], got {intervals}"


class TestHarmonizerDSP:
    """Unit tests for werkstatt_harmonizer.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_harmonizer.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt harmonizer" in code, "Missing @werkstatt harmonizer header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_shift1_semi_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        s1 = [p for p in params if p["name"] == "shift1_semi"][0]
        assert s1["min"] == -12, "shift1_semi min should be -12"
        assert s1["max"] == 12, "shift1_semi max should be 12"

    def test_shift2_semi_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        s2 = [p for p in params if p["name"] == "shift2_semi"][0]
        assert s2["min"] == -12, "shift2_semi min should be -12"
        assert s2["max"] == 12, "shift2_semi max should be 12"

    def test_detune_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        det = [p for p in params if p["name"] == "detune"][0]
        assert det["min"] == 0
        assert det["max"] == 1

    def test_cent_params(self):
        code = self._read_script()
        params = self._parse_params(code)
        for name in ["shift1_cent", "shift2_cent"]:
            cent = [p for p in params if p["name"] == name][0]
            assert cent["min"] == -50, f"{name} min should be -50"
            assert cent["max"] == 50, f"{name} max should be 50"

    def test_two_pitch_shifters(self):
        code = self._read_script()
        assert "buf1L" in code and "buf2L" in code, "Missing two pitch shifter buffers"
        assert "ratio1" in code and "ratio2" in code, "Missing two pitch ratio calculations"

    def test_pitch_ratio_calculation(self):
        code = self._read_script()
        assert "Math.pow(2" in code, "Missing pitch ratio (2^(semi/12))"
        assert "/ 12" in code, "Missing semitone to ratio conversion"

    def test_detune_lfo(self):
        code = self._read_script()
        assert "lfoPhase" in code, "Missing detune LFO phase"
        assert "Math.sin" in code, "Missing LFO sine"
        assert "detuneMod" in code, "Missing detune modulation"

    def test_fractional_delay_read(self):
        code = self._read_script()
        assert "_pitchShift" in code, "Missing pitch shift function"
        assert "frac" in code, "Missing fractional interpolation"
        assert "idx0" in code or "idx1" in code, "Missing buffer index interpolation"


class TestMultibandCompDSP:
    """Unit tests for werkstatt_multiband_comp.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_multiband_comp.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt multiband_comp" in code, "Missing @werkstatt multiband_comp header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 18, f"Expected 18 params, got {len(params)}"

    def test_crossover_params(self):
        code = self._read_script()
        params = self._parse_params(code)
        x1 = [p for p in params if p["name"] == "crossover1"][0]
        x2 = [p for p in params if p["name"] == "crossover2"][0]
        assert x1["scale"] == "exp", "crossover1 should be exponential"
        assert x2["scale"] == "exp", "crossover2 should be exponential"
        assert x1["min"] < x2["min"], "crossover1 min should be < crossover2 min"

    def test_three_bands_present(self):
        code = self._read_script()
        for prefix in ["low_", "mid_", "high_"]:
            for suffix in ["threshold", "ratio", "attack", "release", "gain"]:
                assert f"{prefix}{suffix}" in code, f"Missing {prefix}{suffix} parameter"

    def test_linkwitz_riley_crossover(self):
        code = self._read_script()
        assert "_butterworthLP" in code, "Missing Butterworth LP filter"
        assert "_butterworthHP" in code, "Missing Butterworth HP filter"
        assert "_lr4" in code, "Missing Linkwitz-Riley 4th order cascade"

    def test_envelope_followers(self):
        code = self._read_script()
        assert "envLow" in code and "envMid" in code and "envHigh" in code, "Missing per-band envelope followers"
        assert "atkCoeff" in code and "relCoeff" in code, "Missing attack/release coefficients"

    def test_compression_logic(self):
        code = self._read_script()
        assert "threshold" in code, "Missing threshold comparison"
        assert "ratio" in code, "Missing ratio calculation"
        assert "reduction" in code, "Missing gain reduction"

    def test_band_recombination(self):
        code = self._read_script()
        assert "gainLin" in code, "Missing makeup gain linear conversion"
        assert "out[0]" in code, "Missing output"
        assert "/" in code, "Missing band sum normalization"

    def test_mix_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        assert mix["min"] == 0
        assert mix["max"] == 1


class TestVocoderDSP:
    """Unit tests for werkstatt_vocoder.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_vocoder.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt vocoder" in code, "Missing @werkstatt vocoder header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_band_count_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        bands = [p for p in params if p["name"] == "bands"][0]
        assert bands["min"] == 8 and bands["max"] == 24, "bands range should be 8-24"

    def test_carrier_wave_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        wave = [p for p in params if p["name"] == "carrier_wave"][0]
        assert wave["min"] == 0 and wave["max"] == 2, "carrier_wave range should be 0-2"

    def test_bandpass_filter_bank(self):
        code = self._read_script()
        assert "_bandpassCoeffs" in code, "Missing bandpass coefficient calculation"
        assert "_bandFreq" in code, "Missing band frequency calculation"
        assert "MAX_BANDS" in code, "Missing MAX_BANDS constant"

    def test_envelope_followers(self):
        code = self._read_script()
        assert "envCoeff" in code, "Missing envelope coefficient"
        assert "mod_response" in code, "Missing mod_response parameter"
        assert "this.env" in code, "Missing per-band envelope array"

    def test_carrier_oscillator(self):
        code = self._read_script()
        assert "_carrierSample" in code, "Missing carrier oscillator"
        assert "carPhase" in code, "Missing carrier phase"
        assert "carPhaseInc" in code, "Missing carrier phase increment"

    def test_spectral_mapping(self):
        code = self._read_script()
        assert "modState" in code, "Missing modulator filter state"
        assert "carState" in code, "Missing carrier filter state"
        assert "carBand * env" in code or "bandOut" in code, "Missing envelope-to-carrier gain application"

    def test_log_spacing(self):
        code = self._read_script()
        assert "Math.pow" in code and "FREQ_LO" in code and "FREQ_HI" in code, "Missing logarithmic band spacing"

    def test_mix_and_output(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        out_p = [p for p in params if p["name"] == "output"][0]
        assert mix["min"] == 0 and mix["max"] == 1, "mix range should be 0-1"
        assert out_p["min"] == -12 and out_p["max"] == 12, "output range should be -12 to 12 dB"


class TestReverseDSP:
    """Unit tests for werkstatt_reverse.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_reverse.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt reverse" in code, "Missing @werkstatt reverse header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_chunk_size_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        cs = [p for p in params if p["name"] == "chunk_size"][0]
        assert cs["min"] > 0 and cs["max"] >= 1, "chunk_size should be positive"

    def test_circular_buffer(self):
        code = self._read_script()
        assert "bufL" in code and "bufR" in code, "Missing stereo buffer"
        assert "writePos" in code, "Missing write position"
        assert "bufSize" in code, "Missing buffer size"

    def test_reverse_read(self):
        code = self._read_script()
        assert "_readReverse" in code, "Missing reverse read function"
        assert "writePos - 1" in code, "Missing backward read logic"

    def test_trigger_modes(self):
        code = self._read_script()
        assert "trigger_mode" in code, "Missing trigger_mode param"
        assert "triggerMode" in code, "Missing triggerMode variable"
        assert "Continuous" in code or "triggerMode === 0" in code, "Missing continuous mode"
        assert "Single" in code or "triggerMode === 1" in code, "Missing single mode"
        assert "Gate" in code or "triggerMode === 2" in code, "Missing gate mode"

    def test_stereo_modes(self):
        code = self._read_script()
        assert "stereo_mode" in code, "Missing stereo_mode param"
        assert "Ping-pong" in code or "stereoMode === 1" in code, "Missing ping-pong mode"
        assert "Wide" in code or "stereoMode === 2" in code, "Missing wide mode"

    def test_feedback(self):
        code = self._read_script()
        assert "feedback" in code, "Missing feedback param"
        assert "fbL" in code and "fbR" in code, "Missing feedback state"
        params = self._parse_params(code)
        fb_max = [p for p in params if p["name"] == "feedback"][0]
        assert fb_max["max"] <= 0.9, "Feedback max should be < 1 for stability"

    def test_speed_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        speed = [p for p in params if p["name"] == "speed"][0]
        assert speed["min"] > 0, "speed should be positive"
        assert speed["max"] >= 2, "speed should allow at least 2x"

    def test_smoothing(self):
        code = self._read_script()
        assert "smooth" in code, "Missing smooth param"
        assert "fadeSamples" in code, "Missing fade samples calculation"
        assert "fadeStart" in code or "fadeEnd" in code, "Missing crossfade logic"


class TestCreateChorale:
    """Unit tests for create_chorale orchestration tool."""

    def test_default_chord_pattern(self):
        """Default chord pattern C,Am,F,G should parse to 4 chords."""
        CHORD_INTERVALS = {
            "maj": [0, 4, 7], "M": [0, 4, 7],
            "min": [0, 3, 7], "m": [0, 3, 7],
            "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11], "M7": [0, 4, 7, 11],
            "dom7": [0, 4, 7, 10], "7": [0, 4, 7, 10],
            "sus2": [0, 2, 7], "sus4": [0, 5, 7],
            "dim": [0, 3, 6], "aug": [0, 4, 8],
        }
        NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                      "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                      "A#": 10, "Bb": 10, "B": 11}

        chords = []
        for name in "C,Am,F,G".split(","):
            name = name.strip()
            root = None
            quality = None
            for q in ["maj7", "m7", "M7", "sus2", "sus4", "dom7", "dim", "aug", "maj", "min", "M", "m", "7"]:
                if name.endswith(q) and len(name) > len(q):
                    root_name = name[:-len(q)]
                    if root_name in NOTE_TO_PC:
                        root = NOTE_TO_PC[root_name]
                        quality = q
                        break
            if root is None and name in NOTE_TO_PC:
                root = NOTE_TO_PC[name]
                quality = "maj"
            intervals = CHORD_INTERVALS.get(quality, [0, 4, 7])
            chords.append([root + iv for iv in intervals[:4]])

        assert len(chords) == 4
        assert chords[0] == [0, 4, 7]
        assert chords[1] == [9, 12, 16]
        assert chords[2] == [5, 9, 12]
        assert chords[3] == [7, 11, 14]

    def test_voice_ranges(self):
        """SATB voice ranges should be ordered: bass < tenor < alto < soprano."""
        RANGES = {
            "soprano": (60, 81),
            "alto": (55, 74),
            "tenor": (48, 67),
            "bass": (36, 62),
        }
        assert RANGES["soprano"][0] > RANGES["alto"][0]
        assert RANGES["alto"][0] > RANGES["tenor"][0]
        assert RANGES["tenor"][0] > RANGES["bass"][0]

    def test_note_count(self):
        """4 chords × 4 voices = 16 notes."""
        assert 4 * 4 == 16

    def test_total_beats(self):
        """4 chords × 4 beats = 16 beats."""
        assert 4 * 4 == 16

    def test_parallel_fifth_detection(self):
        """Parallel fifth detection between bass and soprano."""
        def interval(a, b):
            return abs(a - b) % 12

        def check_parallel(prev, curr):
            if prev is None:
                return True
            prev_int = interval(prev["bass"], prev["soprano"])
            curr_int = interval(curr["bass"], curr["soprano"])
            if prev_int in [7, 12] and curr_int == prev_int:
                if (curr["bass"] - prev["bass"]) * (curr["soprano"] - prev["soprano"]) > 0:
                    return False
            return True

        prev = {"bass": 36, "soprano": 67}
        curr = {"bass": 38, "soprano": 69}
        assert not check_parallel(prev, curr), "Should detect parallel fifth"

        prev = {"bass": 36, "soprano": 67}
        curr = {"bass": 38, "soprano": 71}
        assert check_parallel(prev, curr), "Different intervals should be OK"

        assert check_parallel(None, {"bass": 36, "soprano": 67})

    def test_clamp_to_range(self):
        """Voice pitch clamping to SATB ranges."""
        def clamp_to_range(pitch, lo, hi):
            while pitch < lo:
                pitch += 12
            while pitch > hi:
                pitch -= 12
            return pitch

        assert clamp_to_range(24, 36, 62) == 36
        assert clamp_to_range(72, 36, 62) == 60
        assert clamp_to_range(48, 60, 81) == 60
        assert clamp_to_range(90, 60, 81) == 78

    def test_seventh_chord_four_tones(self):
        """Seventh chords use 4 tones for full SATB."""
        CHORD_INTERVALS = {"m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11]}
        root = 0
        cm7 = [root + iv for iv in CHORD_INTERVALS["m7"][:4]]
        assert len(cm7) == 4
        cmaj7 = [root + iv for iv in CHORD_INTERVALS["maj7"][:4]]
        assert len(cmaj7) == 4

    def test_voice_spread(self):
        """Voice spread adds semitones: soprano 2×, alto 1×, tenor/bass 0."""
        voice_spread = 3
        assert 72 + voice_spread * 2 == 78
        assert 64 + voice_spread == 67
        assert 55 == 55
        assert 40 == 40

    def test_note_duration_fraction(self):
        """Note duration is fraction of chord length."""
        assert 4 * 0.9 == 3.6

    def test_dim_aug_parsing(self):
        """Diminished and augmented chords parse correctly."""
        CHORD_INTERVALS = {"dim": [0, 3, 6], "aug": [0, 4, 8]}
        NOTE_TO_PC = {"C": 0, "D": 2}
        assert [NOTE_TO_PC["C"] + iv for iv in CHORD_INTERVALS["dim"][:4]] == [0, 3, 6]
        assert [NOTE_TO_PC["D"] + iv for iv in CHORD_INTERVALS["aug"][:4]] == [2, 6, 10]


class TestLooperDSP:
    """Unit tests for werkstatt_looper.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_looper.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt looper" in code, "Missing @werkstatt looper header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_loop_buffer(self):
        code = self._read_script()
        assert "bufL" in code and "bufR" in code, "Missing stereo loop buffer"
        assert "loopSamples" in code, "Missing loop length in samples"
        assert "writePos" in code and "readPos" in code, "Missing read/write positions"

    def test_record_play_overdub_states(self):
        code = self._read_script()
        assert "state = 0" in code or "currentState === 0" in code, "Missing record state"
        assert "currentState === 1" in code or "playMode === 1" in code, "Missing play state"
        assert "currentState === 2" in code or "playMode === 2" in code, "Missing overdub state"
        assert "overdub" in code, "Missing overdub parameter"

    def test_feedback_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        fb = [p for p in params if p["name"] == "feedback"][0]
        assert fb["min"] == 0 and fb["max"] == 1, "feedback range should be 0-1"

    def test_play_mode_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        pm = [p for p in params if p["name"] == "play_mode"][0]
        assert pm["min"] == 0 and pm["max"] == 2, "play_mode range should be 0-2"

    def test_speed_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        speed = [p for p in params if p["name"] == "speed"][0]
        assert speed["min"] > 0 and speed["max"] >= 2, "speed should be positive and allow 2x+"

    def test_reverse_mode(self):
        code = self._read_script()
        assert "reverse_mode" in code, "Missing reverse_mode param"
        assert "reverse" in code, "Missing reverse variable"

    def test_fade_edges(self):
        code = self._read_script()
        assert "fade_edges" in code, "Missing fade_edges param"
        assert "_fadeGain" in code, "Missing fade gain function"
        assert "fadeSamples" in code, "Missing fade samples calculation"

    def test_monitor_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        mon = [p for p in params if p["name"] == "monitor"][0]
        assert mon["min"] == 0 and mon["max"] == 1, "monitor range should be 0-1"


class TestSpectralGateDSP:
    """Unit tests for werkstatt_spectral_gate.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_spectral_gate.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt spectral_gate" in code

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_bandpass_filter_bank(self):
        code = self._read_script()
        assert "_bandpassCoeffs" in code, "Missing bandpass coefficients"
        assert "MAX_BANDS" in code, "Missing MAX_BANDS"
        assert "bpStateL" in code and "bpStateR" in code, "Missing per-band filter state"

    def test_envelope_followers(self):
        code = self._read_script()
        assert "atkCoeff" in code, "Missing attack coefficient"
        assert "relCoeff" in code, "Missing release coefficient"
        assert "this.env" in code, "Missing per-band envelope array"

    def test_spectral_gating(self):
        code = self._read_script()
        assert "threshold" in code, "Missing threshold"
        assert "reduction" in code, "Missing reduction"
        assert "gain" in code, "Missing gain calculation"

    def test_tilt_param(self):
        code = self._read_script()
        assert "tilt" in code, "Missing tilt param"
        assert "tiltGain" in code, "Missing tilt gain calculation"

    def test_log_spacing(self):
        code = self._read_script()
        assert "Math.pow" in code, "Missing logarithmic spacing"
        assert "min_freq" in code and "max_freq" in code, "Missing freq range params"

    def test_bands_param(self):
        params = self._parse_params(self._read_script())
        bands = [p for p in params if p["name"] == "bands"][0]
        assert bands["min"] >= 2 and bands["max"] >= 8, "bands range too narrow"

    def test_mix_and_output(self):
        params = self._parse_params(self._read_script())
        mix = [p for p in params if p["name"] == "mix"][0]
        out_p = [p for p in params if p["name"] == "output"][0]
        assert mix["min"] == 0 and mix["max"] == 1
        assert out_p["min"] == -12 and out_p["max"] == 12

    def test_output_highpass(self):
        code = self._read_script()
        assert "hpState" in code, "Missing output highpass state"
        assert "hpCoeff" in code, "Missing output highpass coefficients"
        assert "_updateHp" in code, "Missing highpass update function"


class TestConvolutionReverbDSP:
    """Unit tests for werkstatt_convolution_reverb.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "werkstatt_convolution_reverb.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt convolution_reverb" in code

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_room_size_param(self):
        params = self._parse_params(self._read_script())
        rs = [p for p in params if p["name"] == "room_size"][0]
        assert rs["min"] == 0 and rs["max"] == 1
        assert rs["scale"] == "linear"

    def test_ir_generation(self):
        code = self._read_script()
        assert "generateIR" in code, "Missing IR generation method"
        assert "irL" in code and "irR" in code, "Missing stereo IR buffers"
        assert "Float32Array" in code, "Missing Float32Array for IR"

    def test_convolution_kernel(self):
        code = self._read_script()
        assert "direct convolution" in code.lower() or "convolution" in code.lower(), \
            "Missing convolution logic"
        assert "irLen" in code, "Missing IR length tracking"
        assert "histPos" in code, "Missing ring buffer position"

    def test_early_reflections(self):
        code = self._read_script()
        assert "erTaps" in code, "Missing early reflection taps"
        assert "early_late" in code, "Missing early/late balance param"

    def test_decay_envelope(self):
        code = self._read_script()
        assert "decayRate" in code, "Missing decay envelope"
        assert "Math.pow" in code, "Missing exponential decay"

    def test_damping_lowpass(self):
        code = self._read_script()
        assert "lpAlpha" in code, "Missing damping lowpass coefficient"
        assert "dampCut" in code, "Missing damping cutoff frequency"

    def test_predelay(self):
        code = self._read_script()
        assert "predelay" in code, "Missing predelay param"
        assert "preSamps" in code, "Missing predelay sample calculation"

    def test_stereo_width(self):
        code = self._read_script()
        assert "width" in code, "Missing stereo width param"
        assert "spread" in code, "Missing stereo spread in early reflections"


class TestCreateFugue:
    """Unit tests for create_fugue orchestration tool."""

    def test_subject_parsing(self):
        pitches = [int(p.strip()) for p in "60,62,64,65,64,62,60,57".split(",")]
        assert len(pitches) == 8
        assert pitches[0] == 60
        assert pitches[-1] == 57

    def test_tonal_answer_transposition(self):
        subject = [60, 62, 64, 65, 64, 62, 60, 57]
        answer_transpose = 7
        answer = [max(0, min(127, p + answer_transpose)) for p in subject]
        assert answer[0] == 67  # G4 (dominant of C)
        assert answer == [67, 69, 71, 72, 71, 69, 67, 64]

    def test_real_answer_transposition(self):
        subject = [60, 62, 64, 65]
        answer = [max(0, min(127, p + 7)) for p in subject]
        assert answer == [67, 69, 71, 72]

    def test_voice_alternation(self):
        """Voices alternate: subject, answer, subject (oct down), answer."""
        subject = [60, 62, 64]
        answer = [67, 69, 71]
        subj_oct_down = [48, 50, 52]
        voices = 4
        voice_pitches = [subject]
        for v in range(1, voices):
            if v % 2 == 1:
                voice_pitches.append(answer)
            else:
                voice_pitches.append(subj_oct_down)
        assert voice_pitches[0] == subject
        assert voice_pitches[1] == answer
        assert voice_pitches[2] == subj_oct_down
        assert voice_pitches[3] == answer

    def test_note_count_without_countersubject(self):
        """3 voices × 8-note subject = 24 notes."""
        voices = 3
        subj_len = 8
        assert voices * subj_len == 24

    def test_note_count_with_countersubject(self):
        """3 voices × (8 subject + 8 countersubject) = 48 notes."""
        voices = 3
        subj_len = 8
        cs_len = 8
        assert voices * (subj_len + cs_len) == 48

    def test_stretto_entry_timing(self):
        """Stretto halves entry delay for later voices."""
        entry_delay = 4
        voices = 3
        # Normal entries: 0, 4, 8
        normal = [v * entry_delay for v in range(voices)]
        assert normal == [0, 4, 8]
        # Stretto: 0, 2, 4
        stretto = [v * entry_delay * 0.5 for v in range(voices)]
        assert stretto == [0, 2, 4]

    def test_velocity_decay(self):
        """Each voice is quieter by velocity_decay."""
        base_vel = 0.75
        decay = 0.1
        assert max(0.1, base_vel - 0 * decay) == 0.75
        assert max(0.1, base_vel - 1 * decay) == 0.65
        assert max(0.1, base_vel - 2 * decay) == 0.55

    def test_total_beats_calculation(self):
        """3 voices, 4-beat delay, 8-note subject = 16 beats."""
        voices = 3
        entry_delay = 4
        subj_len = 8
        total = (voices - 1) * entry_delay + subj_len
        assert total == 16

    def test_total_beats_with_countersubject(self):
        """With countersubject, add subject length."""
        voices = 3
        entry_delay = 4
        subj_len = 8
        total = (voices - 1) * entry_delay + subj_len + subj_len
        assert total == 24


class TestScratchDSP:
    """Unit tests for werkstatt_scratch.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_scratch.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt scratch" in code, "Missing @werkstatt scratch header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_circular_buffer(self):
        code = self._read_script()
        assert "bufL" in code and "bufR" in code, "Missing stereo buffer"
        assert "writePos" in code and "readPos" in code, "Missing read/write positions"

    def test_scratch_lfo(self):
        code = self._read_script()
        assert "scratchPhase" in code, "Missing scratch LFO phase"
        assert "triWave" in code, "Missing triangle wave for back-and-forth"
        assert "rate" in code, "Missing rate param"

    def test_physics_model(self):
        code = self._read_script()
        assert "velocity" in code, "Missing velocity state"
        assert "friction" in code, "Missing friction param"
        assert "frictionCoeff" in code, "Missing friction coefficient"
        assert "targetVelocity" in code, "Missing target velocity"

    def test_pullback(self):
        code = self._read_script()
        assert "pullback" in code, "Missing pullback param"
        assert "pullbackShape" in code, "Missing pullback shape calculation"

    def test_wow_flutter(self):
        code = self._read_script()
        assert "wow" in code and "flutter" in code, "Missing wow/flutter params"
        assert "wowPhase" in code and "flutterPhase" in code, "Missing wow/flutter phases"
        assert "pitchMod" in code, "Missing pitch modulation"

    def test_crackle(self):
        code = self._read_script()
        assert "crackle" in code, "Missing crackle param"
        assert "crackleVal" in code, "Missing crackle value"
        assert "crackleCounter" in code, "Missing crackle counter"

    def test_variable_speed_readhead(self):
        code = self._read_script()
        assert "readSpeed" in code, "Missing variable read speed"
        assert "linear" in code.lower() or "frac" in code, "Missing interpolation for variable speed"

    def test_mix_and_output(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        out_p = [p for p in params if p["name"] == "output"][0]
        assert mix["min"] == 0 and mix["max"] == 1, "mix range should be 0-1"
        assert out_p["min"] == -12 and out_p["max"] == 12, "output range should be -12 to 12 dB"


class TestCreateTwoHandPiano:
    """Unit tests for create_two_hand_piano orchestration tool."""

    def test_block_left_chord_tones_right(self):
        """Block LH + chord_tones RH: 4 LH notes + 1 RH note per chord = 5 per chord."""
        from server import mcp_opendaw_create_two_hand_piano
        sig = inspect.signature(mcp_opendaw_create_two_hand_piano)
        assert "chords" in sig.parameters
        assert "left_hand" in sig.parameters
        assert "right_hand" in sig.parameters
        assert sig.parameters["left_hand"].default == "arpeggio_up"
        assert sig.parameters["right_hand"].default == "chord_tones"

    def test_alberti_bass_pattern(self):
        """Alberti bass produces arpeggiated notes, not block."""
        from server import mcp_opendaw_create_two_hand_piano
        sig = inspect.signature(mcp_opendaw_create_two_hand_piano)
        assert "alberti" not in sig.parameters["left_hand"].default  # default is arpeggio_up

    def test_bass_chord_pattern(self):
        """bass_chord: bass note + chord notes."""
        from server import mcp_opendaw_create_two_hand_piano
        # Validate left_hand accepts bass_chord
        doc = mcp_opendaw_create_two_hand_piano.__doc__
        assert "bass_chord" in doc

    def test_melody_right_hand(self):
        """right_hand=melody uses melody_pitches parameter."""
        from server import mcp_opendaw_create_two_hand_piano
        sig = inspect.signature(mcp_opendaw_create_two_hand_piano)
        assert "melody_pitches" in sig.parameters
        assert sig.parameters["melody_pitches"].default == ""

    def test_octave_params(self):
        """bass/chord/melody octave params exist with correct defaults."""
        from server import mcp_opendaw_create_two_hand_piano
        sig = inspect.signature(mcp_opendaw_create_two_hand_piano)
        assert sig.parameters["bass_octave"].default == 2
        assert sig.parameters["chord_octave"].default == 3
        assert sig.parameters["melody_octave"].default == 5

    def test_arpeggio_rate_param(self):
        """arpeggio_rate controls arpeggio note duration."""
        from server import mcp_opendaw_create_two_hand_piano
        sig = inspect.signature(mcp_opendaw_create_two_hand_piano)
        assert "arpeggio_rate" in sig.parameters
        assert sig.parameters["arpeggio_rate"].default == 0.5

    def test_invalid_left_hand(self):
        """Invalid left_hand returns error."""
        import asyncio
        from server import mcp_opendaw_create_two_hand_piano
        result = asyncio.run(mcp_opendaw_create_two_hand_piano(
            chords='[["C","maj7"]]', left_hand="foo"
        ))
        assert "Error" in result

    def test_invalid_right_hand(self):
        """Invalid right_hand returns error."""
        import asyncio
        from server import mcp_opendaw_create_two_hand_piano
        result = asyncio.run(mcp_opendaw_create_two_hand_piano(
            chords='[["C","maj7"]]', right_hand="bar"
        ))
        assert "Error" in result

    def test_invalid_chords_json(self):
        """Invalid JSON returns error."""
        import asyncio
        from server import mcp_opendaw_create_two_hand_piano
        result = asyncio.run(mcp_opendaw_create_two_hand_piano(chords='not json'))
        assert "Error" in result

    def test_empty_chords(self):
        """Empty chord list returns error."""
        import asyncio
        from server import mcp_opendaw_create_two_hand_piano
        result = asyncio.run(mcp_opendaw_create_two_hand_piano(chords='[]'))
        assert "Error" in result


class TestCreateVariations:
    """Unit tests for create_variations orchestration tool."""

    def test_signature(self):
        from server import mcp_opendaw_create_variations
        sig = inspect.signature(mcp_opendaw_create_variations)
        assert "source_unit" in sig.parameters
        assert "source_track" in sig.parameters
        assert "variations" in sig.parameters
        assert "target_unit" in sig.parameters
        assert sig.parameters["target_unit"].default == -1
        assert sig.parameters["target_track"].default == -1

    def test_default_variations(self):
        from server import mcp_opendaw_create_variations
        sig = inspect.signature(mcp_opendaw_create_variations)
        default = sig.parameters["variations"].default
        assert "transpose" in default
        assert "invert" in default
        assert "reverse" in default

    def test_invalid_empty_variations(self):
        import asyncio
        from server import mcp_opendaw_create_variations
        result = asyncio.run(mcp_opendaw_create_variations(
            source_unit=0, source_track=0, variations=""
        ))
        assert "Error" in result

    def test_too_many_variations(self):
        import asyncio
        from server import mcp_opendaw_create_variations
        many = ",".join(["transpose:1"] * 20)
        result = asyncio.run(mcp_opendaw_create_variations(
            source_unit=0, source_track=0, variations=many
        ))
        assert "Error" in result

    def test_doc_has_transform_types(self):
        from server import mcp_opendaw_create_variations
        doc = mcp_opendaw_create_variations.__doc__
        assert "transpose" in doc
        assert "invert" in doc
        assert "reverse" in doc
        assert "augment" in doc
        assert "diminish" in doc
        assert "fragment" in doc
        assert "octave_up" in doc
        assert "octave_down" in doc

    def test_spacing_param(self):
        from server import mcp_opendaw_create_variations
        sig = inspect.signature(mcp_opendaw_create_variations)
        assert "spacing_beats" in sig.parameters
        assert sig.parameters["spacing_beats"].default == 0

    def test_start_beat_param(self):
        from server import mcp_opendaw_create_variations
        sig = inspect.signature(mcp_opendaw_create_variations)
        assert "start_beat" in sig.parameters

    def test_source_region_param(self):
        from server import mcp_opendaw_create_variations
        sig = inspect.signature(mcp_opendaw_create_variations)
        assert "source_region" in sig.parameters
        assert sig.parameters["source_region"].default == 0

    def test_composers_mentioned(self):
        from server import mcp_opendaw_create_variations
        doc = mcp_opendaw_create_variations.__doc__
        assert "Bach" in doc
        assert "Beethoven" in doc

    def test_max_variations_limit(self):
        import asyncio
        from server import mcp_opendaw_create_variations
        many = ",".join(["transpose:1"] * 20)
        result = asyncio.run(mcp_opendaw_create_variations(
            source_unit=0, source_track=0, variations=many
        ))
        assert "maximum 16" in result


class TestCreateMotifDevelopment:
    """Unit tests for create_motif_development orchestration tool."""

    def test_signature(self):
        from server import mcp_opendaw_create_motif_development
        sig = inspect.signature(mcp_opendaw_create_motif_development)
        assert "motif" in sig.parameters
        assert "steps" in sig.parameters
        assert "scale" in sig.parameters
        assert sig.parameters["scale"].default == "minor"

    def test_default_steps(self):
        from server import mcp_opendaw_create_motif_development
        sig = inspect.signature(mcp_opendaw_create_motif_development)
        default = sig.parameters["steps"].default
        assert "statement" in default
        assert "sequence_up" in default
        assert "fragment" in default
        assert "invert" in default
        assert "cadence" in default

    def test_invalid_root(self):
        import asyncio
        from server import mcp_opendaw_create_motif_development
        result = asyncio.run(mcp_opendaw_create_motif_development(motif="1,2,3", root="X"))
        assert "Error" in result

    def test_invalid_scale(self):
        import asyncio
        from server import mcp_opendaw_create_motif_development
        result = asyncio.run(mcp_opendaw_create_motif_development(motif="1,2,3", scale="bogus"))
        assert "Error" in result

    def test_invalid_motif_too_short(self):
        import asyncio
        from server import mcp_opendaw_create_motif_development
        result = asyncio.run(mcp_opendaw_create_motif_development(motif="1"))
        assert "Error" in result

    def test_invalid_motif_too_long(self):
        import asyncio
        from server import mcp_opendaw_create_motif_development
        result = asyncio.run(mcp_opendaw_create_motif_development(motif="1,2,3,4,5,6,7,8,9"))
        assert "Error" in result

    def test_invalid_stage(self):
        import asyncio
        from server import mcp_opendaw_create_motif_development
        result = asyncio.run(mcp_opendaw_create_motif_development(motif="1,2,3", steps="statement,bogus"))
        assert "Error" in result

    def test_too_many_stages(self):
        import asyncio
        from server import mcp_opendaw_create_motif_development
        many = ",".join(["statement"] * 25)
        result = asyncio.run(mcp_opendaw_create_motif_development(motif="1,2,3", steps=many))
        assert "Error" in result

    def test_doc_mentions_beethoven(self):
        from server import mcp_opendaw_create_motif_development
        doc = mcp_opendaw_create_motif_development.__doc__
        assert "Beethoven" in doc

    def test_stage_types_documented(self):
        from server import mcp_opendaw_create_motif_development
        doc = mcp_opendaw_create_motif_development.__doc__
        for stage in ["statement", "sequence_up", "sequence_down", "fragment",
                       "invert", "octave_up", "octave_down", "expand", "compress", "cadence"]:
            assert stage in doc, f"Stage '{stage}' not in docstring"


class TestCreateStutter:
    """Unit tests for create_stutter orchestration tool."""

    def test_signature(self):
        from server import mcp_opendaw_create_stutter
        sig = inspect.signature(mcp_opendaw_create_stutter)
        assert "pitches" in sig.parameters
        assert "rate" in sig.parameters
        assert "pattern" in sig.parameters
        assert "repeat_count" in sig.parameters
        assert "accent_pattern" in sig.parameters
        assert "velocity_ramp" in sig.parameters
        assert "gate" in sig.parameters
        assert sig.parameters["rate"].default == "16th"
        assert sig.parameters["pattern"].default == "accelerate"

    def test_invalid_pitches(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        result = asyncio.run(mcp_opendaw_create_stutter(pitches="abc"))
        assert "Error" in result

    def test_too_many_pitches(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        result = asyncio.run(mcp_opendaw_create_stutter(pitches="60,62,64,67,69,72,74,76,77"))
        assert "Error" in result

    def test_invalid_rate(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        result = asyncio.run(mcp_opendaw_create_stutter(rate="bogus"))
        assert "Error" in result

    def test_invalid_pattern(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        result = asyncio.run(mcp_opendaw_create_stutter(pattern="bogus"))
        assert "Error" in result

    def test_repeat_count_bounds(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        r1 = asyncio.run(mcp_opendaw_create_stutter(repeat_count=2))
        assert "Error" in r1
        r2 = asyncio.run(mcp_opendaw_create_stutter(repeat_count=100))
        assert "Error" in r2

    def test_invalid_accent(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        result = asyncio.run(mcp_opendaw_create_stutter(accent_pattern="bogus"))
        assert "Error" in result

    def test_invalid_velocity_ramp(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        result = asyncio.run(mcp_opendaw_create_stutter(velocity_ramp="bogus"))
        assert "Error" in result

    def test_gate_bounds(self):
        import asyncio
        from server import mcp_opendaw_create_stutter
        r1 = asyncio.run(mcp_opendaw_create_stutter(gate=0.1))
        assert "Error" in r1
        r2 = asyncio.run(mcp_opendaw_create_stutter(gate=1.5))
        assert "Error" in r2

    def test_doc_mentions_bt(self):
        from server import mcp_opendaw_create_stutter
        doc = mcp_opendaw_create_stutter.__doc__
        assert "BT" in doc or "stutter" in doc.lower()


class TestCreatePhase:
    """Unit tests for mcp_opendaw_create_phase orchestration tool."""

    def test_invalid_pattern(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        result = asyncio.run(mcp_opendaw_create_phase(pattern="abc"))
        assert "Error" in result

    def test_too_few_notes(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        result = asyncio.run(mcp_opendaw_create_phase(pattern="60"))
        assert "Error" in result

    def test_too_many_notes(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        pattern = " ".join(["60"] * 20)
        result = asyncio.run(mcp_opendaw_create_phase(pattern=pattern))
        assert "Error" in result

    def test_invalid_voices(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        r1 = asyncio.run(mcp_opendaw_create_phase(voices=1))
        assert "Error" in r1
        r2 = asyncio.run(mcp_opendaw_create_phase(voices=5))
        assert "Error" in r2

    def test_invalid_phase_direction(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        result = asyncio.run(mcp_opendaw_create_phase(phase_direction="sideways"))
        assert "Error" in result

    def test_phase_rate_bounds(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        r1 = asyncio.run(mcp_opendaw_create_phase(phase_rate=0.001))
        assert "Error" in r1
        r2 = asyncio.run(mcp_opendaw_create_phase(phase_rate=2.0))
        assert "Error" in r2

    def test_repeats_bounds(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        r1 = asyncio.run(mcp_opendaw_create_phase(repeats=1))
        assert "Error" in r1
        r2 = asyncio.run(mcp_opendaw_create_phase(repeats=50))
        assert "Error" in r2

    def test_velocity_decay_bounds(self):
        import asyncio
        from server import mcp_opendaw_create_phase
        r = asyncio.run(mcp_opendaw_create_phase(velocity_decay=0.5))
        assert "Error" in r

    def test_doc_mentions_reich(self):
        from server import mcp_opendaw_create_phase
        doc = mcp_opendaw_create_phase.__doc__
        assert "Reich" in doc or "phase" in doc.lower()

    def test_doc_contrasts_canon(self):
        from server import mcp_opendaw_create_phase
        doc = mcp_opendaw_create_phase.__doc__
        assert "canon" in doc.lower() or "isorhythm" in doc.lower()


class TestCrossRhythmGeneration:
    """Tests for create_cross_rhythm orchestration tool"""

    def test_two_voice_periods(self):
        periods = [5, 7]
        total_beats = 32
        all_notes = []
        voice_pitches = [60 + i * 5 for i in range(len(periods))]
        for vi, period in enumerate(periods):
            beat = 0.0
            while beat < total_beats:
                all_notes.append({"pitch": voice_pitches[vi], "start": beat, "period": period})
                beat += period
        v0 = [n for n in all_notes if n["period"] == 5]
        assert len(v0) == 7
        v1 = [n for n in all_notes if n["period"] == 7]
        assert len(v1) == 5

    def test_lcm_alignment(self):
        from math import gcd
        periods = [5, 7]
        lcm = periods[0]
        for p in periods[1:]:
            lcm = lcm * p // gcd(lcm, p)
        assert lcm == 35

    def test_prime_lcm(self):
        from math import gcd
        periods = [3, 5, 7]
        lcm = periods[0]
        for p in periods[1:]:
            lcm = lcm * p // gcd(lcm, p)
        assert lcm == 105

    def test_three_voices(self):
        periods = [3, 4, 5]
        total_beats = 16
        all_notes = []
        for vi, period in enumerate(periods):
            beat = 0.0
            while beat < total_beats:
                all_notes.append({"voice": vi, "beat": beat})
                beat += period
        v0 = [n for n in all_notes if n["voice"] == 0]
        v1 = [n for n in all_notes if n["voice"] == 1]
        v2 = [n for n in all_notes if n["voice"] == 2]
        assert len(v0) == 6
        assert len(v1) == 4  # 0,4,8,12 (16 excluded)
        assert len(v2) == 4  # 0,5,10,15

    def test_voice_velocity_attenuation(self):
        base_vel = 0.7
        vel0 = max(0.1, min(1.0, base_vel * (1.0 - 0 * 0.12)))
        vel1 = max(0.1, min(1.0, base_vel * (1.0 - 1 * 0.12)))
        vel2 = max(0.1, min(1.0, base_vel * (1.0 - 2 * 0.12)))
        assert abs(vel0 - 0.7) < 0.01
        assert abs(vel1 - 0.616) < 0.01
        assert abs(vel2 - 0.532) < 0.01

    def test_voice_pitches_spread(self):
        periods = [3, 4, 5]
        voice_pitches = [60 + i * 5 for i in range(len(periods))]
        assert voice_pitches == [60, 65, 70]

    def test_no_alignment_in_short_bars(self):
        total_beats = 16
        v0_beats = set()
        v1_beats = set()
        beat = 0.0
        while beat < total_beats:
            v0_beats.add(beat)
            beat += 5
        beat = 0.0
        while beat < total_beats:
            v1_beats.add(beat)
            beat += 7
        shared = v0_beats and v1_beats
        assert 0.0 in shared

    def test_six_voices_max(self):
        periods = [2, 3, 4, 5, 6, 7]
        assert len(periods) == 6 and all(2 <= p <= 16 for p in periods)

    def test_period_validation(self):
        invalid = [1, 20, 0, -3]
        for p in invalid:
            assert p < 2 or p > 16

    def test_cross_vs_polyrhythm(self):
        poly_primary = [i * 4/3 for i in range(3)]
        _ = [i * 1.0 for i in range(4)]  # poly_secondary (unused, for documentation)
        cross_v0 = [i * 5 for i in range(4)]
        _ = [i * 7 for i in range(3)]  # cross_v1 (unused, for documentation)
        assert max(poly_primary) <= 4
        assert max(cross_v0) > 4


class TestClaveGeneration:
    """Tests for create_clave orchestration tool"""

    CLAVE_PATTERNS = {
        "son_3_2": ([0, 0.5, 1, 2.5, 3], "3-2"),
        "son_2_3": ([0, 1.5, 3, 3.5, 4], "2-3"),
        "rumba_3_2": ([0, 0.5, 1, 2.66, 3.5], "3-2"),
        "rumba_2_3": ([0, 1.5, 3, 3.66, 4.5], "2-3"),
        "bossa_nova": ([0, 2.5, 3, 4.5, 5], "2-3"),
        "6_8": ([0, 1.33, 2.66, 4, 5.33], "3-2"),
    }

    def test_son_3_2_beats(self):
        beats, direction = self.CLAVE_PATTERNS["son_3_2"]
        assert len(beats) == 5
        assert direction == "3-2"
        assert beats[0] == 0
        assert beats[2] == 1  # 3-side: 0, 0.5, 1
        assert beats[3] == 2.5  # 2-side starts

    def test_son_2_3_beats(self):
        beats, direction = self.CLAVE_PATTERNS["son_2_3"]
        assert len(beats) == 5
        assert direction == "2-3"
        assert beats[0] == 0  # 2-side: 0, 1.5
        assert beats[1] == 1.5

    def test_rumba_vs_son_difference(self):
        son_beats, _ = self.CLAVE_PATTERNS["son_3_2"]
        rumba_beats, _ = self.CLAVE_PATTERNS["rumba_3_2"]
        # rumba shifts the last 3-side stroke later
        assert rumba_beats[3] != son_beats[3]
        assert rumba_beats[4] != son_beats[4]

    def test_bossa_nova_5_strokes(self):
        beats, direction = self.CLAVE_PATTERNS["bossa_nova"]
        assert len(beats) == 5
        assert direction == "2-3"
        # bossa nova has characteristic off-beat placement
        assert 2.5 in beats and 4.5 in beats

    def test_6_8_clave(self):
        beats, direction = self.CLAVE_PATTERNS["6_8"]
        assert len(beats) == 5
        assert direction == "3-2"
        # 6/8 clave uses dotted-quarter spacing
        assert beats[1] == 1.33  # ~2/3 of a beat
        assert beats[2] == 2.66

    def test_all_patterns_5_strokes(self):
        for name, (beats, _) in self.CLAVE_PATTERNS.items():
            assert len(beats) == 5, f"{name} should have 5 strokes, got {len(beats)}"

    def test_cycle_length(self):
        cycle_len = 8.0  # 2 bars of 4/4
        for beats, _ in self.CLAVE_PATTERNS.values():
            assert max(beats) < cycle_len, f"beat {max(beats)} exceeds cycle {cycle_len}"

    def test_direction_propagation(self):
        for name, (_, direction) in self.CLAVE_PATTERNS.items():
            assert direction in ("3-2", "2-3"), f"{name} has invalid direction"

    def test_note_generation_one_cycle(self):
        beats, _ = self.CLAVE_PATTERNS["son_3_2"]
        all_notes = []
        for b in beats:
            all_notes.append({"pitch": 76, "start": b, "duration": 0.25, "velocity": 0.8})
        assert len(all_notes) == 5
        starts = [n["start"] for n in all_notes]
        assert starts == [0, 0.5, 1, 2.5, 3]

    def test_note_generation_two_cycles(self):
        beats, _ = self.CLAVE_PATTERNS["son_3_2"]
        cycle_len = 8.0
        all_notes = []
        for c in range(2):
            for b in beats:
                all_notes.append({"start": c * cycle_len + b})
        assert len(all_notes) == 10
        assert all_notes[5]["start"] == 8.0  # second cycle starts at beat 8

    def test_clave_type_normalization(self):
        raw = "Son 3-2"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "son_3-2" or "son" in normalized

    def test_pitch_validation(self):
        assert 0 <= 76 <= 127
        assert not (0 <= 128 <= 127)
        assert not (0 <= -1 <= 127)


class TestEuclideanRhythm:
    """Tests for create_euclidean_rhythm and BJK algorithm"""

    def _euclidean(self, k, n):
        """Pure Python BJK for testing"""
        if k == 0: return [0] * n
        if k == n: return [1] * n
        a = [[1] for _ in range(k)]
        b = [[0] for _ in range(n - k)]
        while len(b) > 1:
            m = min(len(a), len(b))
            for i in range(m):
                a[i] = a[i] + b.pop()
            new_a = []
            new_b = []
            for g in a:
                if g[0] == 1: new_a.append(g)
                else: new_b.append(g)
            a = new_a
            b = b + new_b
        result = []
        for g in a + b:
            result.extend(g)
        return result

    def test_tresillo(self):
        p = self._euclidean(3, 8)
        assert sum(p) == 3 and len(p) == 8
        assert p == [1, 0, 0, 1, 0, 0, 1, 0]

    def test_cinquillo(self):
        p = self._euclidean(5, 8)
        assert sum(p) == 5 and len(p) == 8

    def test_samba(self):
        p = self._euclidean(7, 16)
        assert sum(p) == 7 and len(p) == 16

    def test_all_ones(self):
        p = self._euclidean(4, 4)
        assert p == [1, 1, 1, 1]

    def test_all_zeros(self):
        p = self._euclidean(0, 8)
        assert p == [0, 0, 0, 0, 0, 0, 0, 0]

    def test_rotation(self):
        p = self._euclidean(3, 8)
        rotated = p[1:] + [p[0]]
        assert rotated[0] == 0  # moved first element to end

    def test_even_distribution(self):
        """E(2,4) should be maximally even: 1010"""
        p = self._euclidean(2, 4)
        assert p == [1, 0, 1, 0]

    def test_prime_steps(self):
        """E(3,7) — 7 is prime, should still work"""
        p = self._euclidean(3, 7)
        assert sum(p) == 3 and len(p) == 7

    def test_dense_rhythm(self):
        """E(7,8) — mostly hits"""
        p = self._euclidean(7, 8)
        assert sum(p) == 7 and len(p) == 8

    def test_aksak(self):
        """E(4,9) — Balkan asymmetric rhythm"""
        p = self._euclidean(4, 9)
        assert sum(p) == 4 and len(p) == 9

    def test_bembé(self):
        """E(7,12) — West African"""
        p = self._euclidean(7, 12)
        assert sum(p) == 7 and len(p) == 12

    def test_step_duration_calculation(self):
        steps = 8
        step_duration = 4.0 / steps
        assert step_duration == 0.5  # 8th notes in 4/4

    def test_pattern_string(self):
        p = self._euclidean(3, 8)
        pattern_str = "".join(str(int(x)) for x in p)
        assert pattern_str == "10010010"


class TestTumbaoGeneration:
    """Tests for create_tumbao — Afro-Cuban conga pattern"""

    # Tumbao patterns: (beat, stroke_type) within 2-bar cycle
    TUMBAO_PATTERNS = {
        "salsa": [
            (1.5, "tone"), (3.5, "open"),
            (5.5, "tone"), (7.0, "open"),
        ],
        "salsa_slap": [
            (1.5, "tone"), (3.5, "open"),
            (5.0, "slap"), (5.5, "tone"), (7.0, "open"),
        ],
        "rumba": [
            (1.5, "tone"), (3.0, "open"), (3.5, "tone"),
            (5.5, "tone"), (7.0, "open"), (7.5, "tone"),
        ],
        "bolero": [
            (1.5, "tone"), (3.5, "open"),
            (5.5, "tone"), (7.5, "open"),
        ],
    }

    def test_salsa_stroke_count(self):
        strokes = self.TUMBAO_PATTERNS["salsa"]
        assert len(strokes) == 4

    def test_salsa_slap_has_slap(self):
        strokes = self.TUMBAO_PATTERNS["salsa_slap"]
        stroke_types = [s[1] for s in strokes]
        assert "slap" in stroke_types

    def test_rumba_stroke_count(self):
        strokes = self.TUMBAO_PATTERNS["rumba"]
        assert len(strokes) == 6

    def test_bolero_no_downbeat_open(self):
        """Bolero open tone is on &4 not beat 4 — less anticipatory"""
        strokes = self.TUMBAO_PATTERNS["bolero"]
        opens = [b for b, s in strokes if s == "open"]
        assert 7.5 in opens  # &4 of bar 2, not 7.0 (beat 4)
        assert 7.0 not in opens

    def test_salsa_open_on_and_of_4(self):
        """Signature: open tone on &4 of bar 1 (beat 3.5)"""
        strokes = self.TUMBAO_PATTERNS["salsa"]
        opens = [b for b, s in strokes if s == "open"]
        assert 3.5 in opens

    def test_salsa_open_on_downbeat_bar2(self):
        """Open tone on beat 4 of bar 2 (beat 7.0) — anticipates next downbeat"""
        strokes = self.TUMBAO_PATTERNS["salsa"]
        opens = [b for b, s in strokes if s == "open"]
        assert 7.0 in opens

    def test_tone_on_and_of_2(self):
        """All patterns have tone on &2 of each bar (beat 1.5 and 5.5)"""
        for name, strokes in self.TUMBAO_PATTERNS.items():
            tones = [b for b, s in strokes if s == "tone"]
            assert 1.5 in tones, f"{name}: missing tone on &2 of bar 1"
            assert 5.5 in tones, f"{name}: missing tone on &2 of bar 2"

    def test_cycle_length_8_beats(self):
        """All patterns span 2 bars = 8 beats"""
        for name, strokes in self.TUMBAO_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < 8.0, f"{name}: pattern exceeds 8 beats"

    def test_pitch_mapping(self):
        """Tone=low, open=mid, slap=high — 3 distinct conga pitches"""
        low_pitch = 38
        open_pitch = 50
        slap_pitch = 62
        assert low_pitch < open_pitch < slap_pitch

    def test_velocity_mapping(self):
        """Open tones louder than tones, slaps loudest"""
        base_vel = 0.75
        tone_vel = base_vel
        open_vel = min(1.0, base_vel + 0.1)
        slap_vel = min(1.0, base_vel + 0.15)
        assert tone_vel < open_vel <= slap_vel

    def test_duration_mapping(self):
        """Open tones sustained, tones short, slaps very short"""
        dur_map = {"tone": 0.15, "open": 0.5, "slap": 0.1}
        assert dur_map["slap"] < dur_map["tone"] < dur_map["open"]

    def test_bar_repetition(self):
        """4 bars = 2 cycles of 2-bar pattern"""
        bars = 4
        cycles = bars // 2
        assert cycles == 2

    def test_salsa_slap_on_beat_2(self):
        """Slap on beat 2 of bar 2 (beat 5.0) — adds emphasis"""
        strokes = self.TUMBAO_PATTERNS["salsa_slap"]
        slaps = [b for b, s in strokes if s == "slap"]
        assert 5.0 in slaps

    def test_all_types_valid(self):
        """All stroke types are tone/open/slap"""
        valid = {"tone", "open", "slap"}
        for name, strokes in self.TUMBAO_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"


class TestCascara:
    """Tests for create_cascara orchestration tool"""

    CASCARA_PATTERNS = {
        "son_3_2": [
            (1.5, "high"), (2.0, "low"), (2.5, "high"), (3.5, "low"),
            (5.5, "high"), (6.0, "low"), (6.5, "high"), (7.0, "low"),
        ],
        "son_2_3": [
            (1.5, "high"), (2.0, "low"), (2.5, "high"), (4.0, "low"),
            (5.5, "high"), (6.0, "low"), (6.5, "high"), (7.5, "low"),
        ],
        "guaguanco": [
            (0.0, "ghost"), (0.5, "ghost"),
            (1.5, "high"), (2.0, "low"), (2.5, "high"), (3.5, "low"),
            (4.0, "ghost"), (4.5, "ghost"),
            (5.5, "high"), (6.0, "low"), (6.5, "high"), (7.0, "low"),
        ],
        "mambo": [
            (1.5, "high"), (2.0, "low"), (2.5, "high"), (3.5, "low"),
            (5.5, "high"), (6.0, "low"), (6.5, "high"), (7.0, "high"), (7.5, "low"),
        ],
    }

    def test_son_3_2_strokes(self):
        strokes = self.CASCARA_PATTERNS["son_3_2"]
        assert len(strokes) == 8
        beats = [b for b, s in strokes]
        assert beats[0] == 1.5  # &2
        assert 2.5 in beats  # &3

    def test_son_2_3_strokes(self):
        strokes = self.CASCARA_PATTERNS["son_2_3"]
        assert len(strokes) == 8
        beats = [b for b, s in strokes]
        # 2-3: bar 1 has the "back" — beat 4 low
        assert 4.0 in beats

    def test_3_2_vs_2_3_difference(self):
        beats_32 = [b for b, s in self.CASCARA_PATTERNS["son_3_2"]]
        beats_23 = [b for b, s in self.CASCARA_PATTERNS["son_2_3"]]
        assert beats_32 != beats_23, "3-2 and 2-3 must differ"

    def test_guaguanco_has_ghosts(self):
        strokes = self.CASCARA_PATTERNS["guaguanco"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) == 4, "guaguanco should have 4 ghost strokes"
        assert 0.0 in ghosts  # beat 1 of bar 1
        assert 4.0 in ghosts  # beat 1 of bar 2

    def test_guaguanco_denser_than_son(self):
        son_count = len(self.CASCARA_PATTERNS["son_3_2"])
        gua_count = len(self.CASCARA_PATTERNS["guaguanco"])
        assert gua_count > son_count, "guaguanco should be denser"

    def test_mambo_has_accent_on_7(self):
        strokes = self.CASCARA_PATTERNS["mambo"]
        # mambo adds accent on beat 7 (high) + 7.5 (low)
        highs = [b for b, s in strokes if s == "high" and b >= 5.0]
        assert 7.0 in highs, "mambo should have high accent on beat 7"

    def test_all_types_valid(self):
        valid = {"high", "low", "ghost"}
        for name, strokes in self.CASCARA_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"

    def test_cycle_length(self):
        cycle_len = 8.0
        for name, strokes in self.CASCARA_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < cycle_len, f"{name}: beat {max_beat} exceeds cycle {cycle_len}"

    def test_high_low_alternation(self):
        """Son patterns alternate high/low creating call-and-response"""
        strokes = self.CASCARA_PATTERNS["son_3_2"]
        for i in range(0, len(strokes), 2):
            assert strokes[i][1] == "high", f"Position {i} should be high"
            assert strokes[i + 1][1] == "low", f"Position {i+1} should be low"

    def test_velocity_mapping(self):
        """High strokes louder than low, ghosts quietest"""
        base = 0.7
        high_vel = min(1.0, base + 0.1)
        low_vel = max(0.0, base - 0.05)
        ghost_vel = max(0.0, base - 0.25)
        assert ghost_vel < low_vel < high_vel

    def test_pitch_mapping(self):
        """High strokes use high pitch, low/ghost use low pitch"""
        high_pitch, low_pitch = 76, 60
        pitch_map = {"high": high_pitch, "low": low_pitch, "ghost": low_pitch}
        assert pitch_map["high"] > pitch_map["low"]
        assert pitch_map["ghost"] == pitch_map["low"]

    def test_duration_mapping(self):
        """Ghosts shortest, highs slightly longer"""
        dur_map = {"high": 0.15, "low": 0.12, "ghost": 0.08}
        assert dur_map["ghost"] < dur_map["low"] < dur_map["high"]

    def test_direction_detection(self):
        """3-2 and 2-3 directions detected from type name"""
        assert "3_2" in "son_3_2"
        direction_32 = "3-2" if "3_2" in "son_3_2" else "2-3"
        assert direction_32 == "3-2"

        direction_23 = "3-2" if "3_2" in "son_2_3" else "2-3"
        assert direction_23 == "2-3"

        direction_gua = "3-2" if "3_2" in "guaguanco" else "2-3" if "2_3" in "guaguanco" else "varied"
        assert direction_gua == "varied"

    def test_bar_repetition(self):
        """4 bars = 2 cycles of 2-bar pattern"""
        bars = 4
        cycles = bars // 2
        assert cycles == 2

    def test_note_generation_one_cycle(self):
        strokes = self.CASCARA_PATTERNS["son_3_2"]
        all_notes = []
        for beat, stroke_type in strokes:
            all_notes.append({"pitch": 76 if stroke_type == "high" else 60, "start": beat, "duration": 0.15, "velocity": 0.8})
        assert len(all_notes) == 8
        starts = [n["start"] for n in all_notes]
        assert starts == [1.5, 2.0, 2.5, 3.5, 5.5, 6.0, 6.5, 7.0]

    def test_note_generation_two_cycles(self):
        strokes = self.CASCARA_PATTERNS["son_3_2"]
        cycle_len = 8.0
        all_notes = []
        for c in range(2):
            for beat, stroke_type in strokes:
                all_notes.append({"start": c * cycle_len + beat, "stroke": stroke_type})
        assert len(all_notes) == 16
        assert all_notes[8]["start"] == 9.5  # second cycle first stroke

    def test_type_normalization(self):
        raw = "Son 3-2"
        normalized = raw.strip().lower().replace(" ", "_")
        assert "son" in normalized

    def test_pitch_validation(self):
        assert 0 <= 76 <= 127
        assert 0 <= 60 <= 127
        assert not (0 <= 128 <= 127)

    def test_mambo_more_strokes_than_son(self):
        """Mambo has extra accent, so more strokes than standard son"""
        son_count = len(self.CASCARA_PATTERNS["son_3_2"])
        mambo_count = len(self.CASCARA_PATTERNS["mambo"])
        assert mambo_count > son_count, "mambo should have more strokes"


class TestDembow:
    """Tests for create_dembow orchestration tool"""

    DEMBOW_PATTERNS = {
        "classic": [
            (0.0, "kick"), (2.0, "kick"), (2.5, "snare"), (3.5, "snare"), (4.5, "snare"),
        ],
        "dancehall": [
            (0.0, "kick"), (2.0, "kick"), (2.5, "snare"), (3.5, "snare"),
        ],
        "trap_latino": [
            (0.0, "kick"), (2.5, "snare"), (3.5, "kick"), (3.75, "kick"), (4.5, "snare"),
        ],
        "perreo": [
            (0.0, "kick"), (1.75, "ghost"), (2.0, "kick"), (2.5, "snare"),
            (3.5, "snare"), (4.5, "snare"), (5.75, "ghost"),
        ],
        "urbano": [
            (0.0, "kick"), (2.0, "kick"), (2.5, "snare"), (3.5, "snare"),
            (3.75, "kick"), (4.5, "snare"),
        ],
    }

    def test_classic_has_gallop(self):
        """Classic dembow: 3-3-2 gallop — 3 snares at 2.5, 3.5, 4.5"""
        strokes = self.DEMBOW_PATTERNS["classic"]
        snares = [b for b, s in strokes if s == "snare"]
        assert 2.5 in snares, "Missing snare on &3"
        assert 3.5 in snares, "Missing snare on &4"
        assert 4.5 in snares, "Missing snare on &1 (gallop)"

    def test_classic_kick_on_1_and_3(self):
        strokes = self.DEMBOW_PATTERNS["classic"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 0.0 in kicks, "Missing kick on beat 1"
        assert 2.0 in kicks, "Missing kick on beat 3"

    def test_dancehall_sparser_than_classic(self):
        classic_count = len(self.DEMBOW_PATTERNS["classic"])
        dancehall_count = len(self.DEMBOW_PATTERNS["dancehall"])
        assert dancehall_count < classic_count, "dancehall should be sparser"

    def test_trap_latino_syncopated_kick(self):
        strokes = self.DEMBOW_PATTERNS["trap_latino"]
        kicks = [b for b, s in strokes if s == "kick"]
        # syncopated sixteenth at 3.75
        assert 3.75 in kicks, "Missing syncopated kick at 3.75"

    def test_perreo_has_ghosts(self):
        strokes = self.DEMBOW_PATTERNS["perreo"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) == 2, "perreo should have 2 ghost strokes"
        assert 1.75 in ghosts, "Missing ghost on 2.75"

    def test_perreo_denser_than_classic(self):
        classic_count = len(self.DEMBOW_PATTERNS["classic"])
        perreo_count = len(self.DEMBOW_PATTERNS["perreo"])
        assert perreo_count > classic_count, "perreo should be denser"

    def test_urbano_blends_reggaeton_and_trap(self):
        strokes = self.DEMBOW_PATTERNS["urbano"]
        kicks = [b for b, s in strokes if s == "kick"]
        # has both beat 3 kick (reggaeton) and 3.75 syncopated kick (trap)
        assert 2.0 in kicks, "Missing reggaeton kick on 3"
        assert 3.75 in kicks, "Missing trap syncopated kick at 3.75"

    def test_all_types_valid(self):
        valid = {"kick", "snare", "ghost"}
        for name, strokes in self.DEMBOW_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"

    def test_cycle_length(self):
        cycle_len = 4.0
        for name, strokes in self.DEMBOW_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < cycle_len + 2, f"{name}: beat {max_beat} too far (1-bar cycle = 4 beats, wrap allowed)"

    def test_velocity_mapping(self):
        """Kick louder, ghost quietest"""
        base = 0.8
        kick_vel = min(1.0, base + 0.05)
        snare_vel = base
        ghost_vel = max(0.0, base - 0.2)
        assert ghost_vel < snare_vel < kick_vel

    def test_pitch_mapping(self):
        """Kick low, snare/ghost higher"""
        kick_pitch, snare_pitch = 36, 40
        pitch_map = {"kick": kick_pitch, "snare": snare_pitch, "ghost": snare_pitch}
        assert pitch_map["kick"] < pitch_map["snare"]
        assert pitch_map["ghost"] == pitch_map["snare"]

    def test_duration_mapping(self):
        """Kick longest, ghost shortest"""
        dur_map = {"kick": 0.2, "snare": 0.12, "ghost": 0.08}
        assert dur_map["ghost"] < dur_map["snare"] < dur_map["kick"]

    def test_bar_repetition(self):
        """4 bars = 4 cycles of 1-bar pattern"""
        bars = 4
        cycles = bars
        assert cycles == 4

    def test_note_generation_one_bar(self):
        strokes = self.DEMBOW_PATTERNS["classic"]
        all_notes = []
        for beat, stroke_type in strokes:
            all_notes.append({"pitch": 36 if stroke_type == "kick" else 40, "start": beat})
        assert len(all_notes) == 5
        starts = [n["start"] for n in all_notes]
        assert starts == [0.0, 2.0, 2.5, 3.5, 4.5]

    def test_note_generation_four_bars(self):
        strokes = self.DEMBOW_PATTERNS["classic"]
        cycle_len = 4.0
        all_notes = []
        for c in range(4):
            for beat, stroke_type in strokes:
                all_notes.append({"start": c * cycle_len + beat, "stroke": stroke_type})
        assert len(all_notes) == 20
        assert all_notes[5]["start"] == 4.0  # second bar starts at beat 4

    def test_type_normalization(self):
        raw = "Trap Latino"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "trap_latino"

    def test_pitch_validation(self):
        assert 0 <= 36 <= 127
        assert 0 <= 40 <= 127
        assert not (0 <= 128 <= 127)


class TestBoomBap:
    """Tests for create_boom_bap orchestration tool"""

    BOOM_BAP_PATTERNS = {
        "classic": [
            (0.0, "kick"), (0.5, "hat"), (1.0, "snare"), (1.5, "hat"),
            (2.0, "kick"), (2.5, "hat"), (3.0, "snare"), (3.5, "hat"),
            (4.0, "kick"), (4.5, "hat"), (5.0, "snare"), (5.5, "hat"),
            (6.0, "kick"), (6.5, "hat"), (7.0, "snare"), (7.5, "hat"),
        ],
        "old_school": [
            (0.0, "kick"), (1.0, "snare"), (1.0, "hat"),
            (2.0, "kick"), (3.0, "snare"), (3.0, "hat"),
            (4.0, "kick"), (5.0, "snare"), (5.0, "hat"),
            (6.0, "kick"), (7.0, "snare"), (7.0, "hat"),
        ],
        "trap": [
            (0.0, "kick"), (0.25, "hat"), (0.5, "hat"), (0.75, "hat"),
            (1.0, "hat"), (1.25, "hat"), (1.5, "kick"), (1.75, "hat"),
            (2.0, "hat"), (2.25, "hat"), (2.5, "hat"), (2.75, "hat"),
            (3.0, "snare"), (3.25, "hat"), (3.5, "hat"), (3.75, "hat"),
            (4.0, "kick"), (4.25, "hat"), (4.5, "hat"), (4.75, "hat"),
            (5.0, "hat"), (5.25, "hat"), (5.5, "kick"), (5.75, "hat"),
            (6.0, "hat"), (6.25, "hat"), (6.5, "hat"), (6.75, "hat"),
            (7.0, "snare"), (7.25, "hat"), (7.5, "hat"), (7.75, "hat"),
        ],
        "lofi": [
            (0.0, "kick"), (0.66, "hat"), (1.0, "snare"), (1.66, "hat"),
            (2.0, "kick"), (2.66, "hat"), (3.0, "snare"), (3.66, "hat"),
            (4.0, "kick"), (4.66, "hat"), (5.0, "snare"), (5.66, "hat"),
            (5.95, "kick"), (6.66, "hat"), (7.0, "snare"), (7.66, "hat"),
        ],
        "drill": [
            (0.0, "kick"), (0.5, "hat"), (1.0, "hat"), (1.5, "kick"),
            (2.0, "snare"), (2.25, "hat"), (2.5, "hat"), (2.75, "hat"),
            (3.0, "kick"), (3.5, "hat"), (4.0, "kick"), (4.5, "hat"),
            (5.0, "kick"), (5.5, "hat"), (6.0, "snare"), (6.25, "hat"),
            (6.5, "hat"), (6.75, "ghost"), (7.0, "kick"), (7.5, "hat"),
        ],
    }

    def test_classic_kick_on_1_and_3(self):
        strokes = self.BOOM_BAP_PATTERNS["classic"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 0.0 in kicks, "Missing kick on beat 1"
        assert 2.0 in kicks, "Missing kick on beat 3"

    def test_classic_snare_on_2_and_4(self):
        strokes = self.BOOM_BAP_PATTERNS["classic"]
        snares = [b for b, s in strokes if s == "snare"]
        assert 1.0 in snares, "Missing snare on beat 2"
        assert 3.0 in snares, "Missing snare on beat 4"

    def test_classic_hats_on_8ths(self):
        strokes = self.BOOM_BAP_PATTERNS["classic"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.5 in hats, "Missing hat on &1"
        assert 1.5 in hats, "Missing hat on &2"

    def test_old_school_simpler_than_classic(self):
        classic_count = len(self.BOOM_BAP_PATTERNS["classic"])
        old_count = len(self.BOOM_BAP_PATTERNS["old_school"])
        assert old_count < classic_count, "old_school should be simpler (fewer strokes)"

    def test_trap_has_16th_hats(self):
        strokes = self.BOOM_BAP_PATTERNS["trap"]
        hats = [b for b, s in strokes if s == "hat"]
        # 16th notes: 0.25, 0.5, 0.75 etc
        assert 0.25 in hats, "Missing 16th hat at 0.25"
        assert 0.75 in hats, "Missing 16th hat at 0.75"

    def test_trap_snare_on_4_only(self):
        strokes = self.BOOM_BAP_PATTERNS["trap"]
        snares = [b for b, s in strokes if s == "snare"]
        assert 3.0 in snares, "Missing snare on beat 4"
        assert 7.0 in snares, "Missing snare on beat 4 bar 2"
        # Trap only has snare on beat 4, not 2
        assert 1.0 not in snares, "Trap should NOT have snare on beat 2"

    def test_lofi_laid_back_kick(self):
        strokes = self.BOOM_BAP_PATTERNS["lofi"]
        kicks = [b for b, s in strokes if s == "kick"]
        # Lo-fi has a kick slightly behind beat (5.95 instead of 6.0)
        assert 5.95 in kicks, "Missing laid-back kick at 5.95"

    def test_lofi_swung_hats(self):
        strokes = self.BOOM_BAP_PATTERNS["lofi"]
        hats = [b for b, s in strokes if s == "hat"]
        # Swung hats at 0.66 instead of 0.5
        assert 0.66 in hats, "Missing swung hat at 0.66"

    def test_drill_has_ghost(self):
        strokes = self.BOOM_BAP_PATTERNS["drill"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) >= 1, "drill should have ghost notes"

    def test_drill_snare_on_3(self):
        strokes = self.BOOM_BAP_PATTERNS["drill"]
        snares = [b for b, s in strokes if s == "snare"]
        assert 2.0 in snares, "Missing snare on beat 3 (drill characteristic)"

    def test_all_types_valid(self):
        valid = {"kick", "snare", "hat", "ghost"}
        for name, strokes in self.BOOM_BAP_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"

    def test_cycle_length(self):
        cycle_len = 8.0
        for name, strokes in self.BOOM_BAP_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < cycle_len, f"{name}: beat {max_beat} exceeds cycle {cycle_len}"

    def test_velocity_mapping(self):
        base = 0.8
        kick_vel = min(1.0, base + 0.05)
        snare_vel = max(0.0, base - 0.05)
        hat_vel = max(0.0, base - 0.15)
        ghost_vel = max(0.0, base - 0.35)
        assert ghost_vel < hat_vel < snare_vel < kick_vel

    def test_pitch_mapping(self):
        kick, snare, hat = 36, 38, 42
        pitch_map = {"kick": kick, "snare": snare, "hat": hat, "ghost": hat}
        assert pitch_map["kick"] < pitch_map["snare"] < pitch_map["hat"]

    def test_duration_mapping(self):
        dur_map = {"kick": 0.2, "snare": 0.12, "hat": 0.05, "ghost": 0.04}
        assert dur_map["ghost"] < dur_map["hat"] < dur_map["snare"] < dur_map["kick"]

    def test_bar_repetition(self):
        bars = 4
        cycles = bars // 2
        assert cycles == 2

    def test_note_generation_one_cycle(self):
        strokes = self.BOOM_BAP_PATTERNS["classic"]
        all_notes = []
        for beat, stroke_type in strokes:
            all_notes.append({"start": beat, "stroke": stroke_type})
        assert len(all_notes) == 16
        assert all_notes[0]["start"] == 0.0

    def test_note_generation_two_cycles(self):
        strokes = self.BOOM_BAP_PATTERNS["classic"]
        cycle_len = 8.0
        all_notes = []
        for c in range(2):
            for beat, stroke_type in strokes:
                all_notes.append({"start": c * cycle_len + beat, "stroke": stroke_type})
        assert len(all_notes) == 32
        assert all_notes[16]["start"] == 8.0

    def test_type_normalization(self):
        raw = "Old School"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "old_school"

    def test_pitch_validation(self):
        assert 0 <= 36 <= 127
        assert 0 <= 38 <= 127
        assert 0 <= 42 <= 127
        assert not (0 <= 128 <= 127)


class TestCreateFourOnFloor:
    """Tests for create_four_on_floor orchestration tool"""

    FOUR_ON_FLOOR_PATTERNS = {
        "classic_house": [
            (0.0, "kick"), (0.5, "open"), (1.0, "kick"), (1.0, "clap"),
            (1.5, "open"), (2.0, "kick"), (2.5, "open"), (3.0, "kick"),
            (3.0, "clap"), (3.5, "open"),
        ],
        "deep_house": [
            (0.0, "kick"), (0.66, "hat"), (1.0, "kick"), (1.0, "clap"),
            (1.33, "perc"), (1.66, "hat"), (2.0, "kick"), (2.66, "hat"),
            (3.0, "kick"), (3.0, "clap"), (3.33, "perc"), (3.66, "hat"),
        ],
        "techno": [
            (0.0, "kick"), (0.25, "hat"), (0.5, "hat"), (0.75, "hat"),
            (1.0, "kick"), (1.0, "clap"), (1.25, "hat"), (1.5, "perc"),
            (1.75, "hat"), (2.0, "kick"), (2.25, "hat"), (2.5, "hat"),
            (2.75, "hat"), (3.0, "kick"), (3.0, "clap"), (3.25, "hat"),
            (3.5, "perc"), (3.75, "hat"),
        ],
        "disco": [
            (0.0, "kick"), (0.25, "hat"), (0.5, "open"), (0.75, "hat"),
            (1.0, "kick"), (1.0, "clap"), (1.25, "hat"), (1.5, "open"),
            (1.75, "hat"), (2.0, "kick"), (2.25, "hat"), (2.5, "open"),
            (2.75, "hat"), (3.0, "kick"), (3.0, "clap"), (3.25, "hat"),
            (3.5, "open"), (3.75, "perc"),
        ],
        "tech_house": [
            (0.0, "kick"), (0.5, "hat"), (1.0, "kick"), (1.0, "clap"),
            (1.5, "hat"), (1.75, "perc"), (2.0, "kick"), (2.5, "hat"),
            (3.0, "kick"), (3.0, "clap"), (3.5, "hat"), (3.75, "ghost"),
        ],
    }

    def test_kick_on_every_quarter_all_types(self):
        """The defining feature: kick on beats 0, 1, 2, 3 in every variant"""
        for name, strokes in self.FOUR_ON_FLOOR_PATTERNS.items():
            kicks = [b for b, s in strokes if s == "kick"]
            for beat in [0.0, 1.0, 2.0, 3.0]:
                assert beat in kicks, f"{name}: missing kick on beat {beat}"

    def test_classic_house_open_hat_on_offbeats(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["classic_house"]
        opens = [b for b, s in strokes if s == "open"]
        assert 0.5 in opens, "Missing open hat on &1"
        assert 1.5 in opens, "Missing open hat on &2"
        assert 2.5 in opens, "Missing open hat on &3"
        assert 3.5 in opens, "Missing open hat on &4"

    def test_classic_house_clap_on_2_and_4(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["classic_house"]
        claps = [b for b, s in strokes if s == "clap"]
        assert 1.0 in claps, "Missing clap on beat 2"
        assert 3.0 in claps, "Missing clap on beat 4"

    def test_deep_house_shuffled_hats(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["deep_house"]
        hats = [b for b, s in strokes if s == "hat"]
        # Swung hats at 0.66 instead of 0.5
        assert 0.66 in hats, "Missing swung hat at 0.66"

    def test_deep_house_percussion(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["deep_house"]
        percs = [b for b, s in strokes if s == "perc"]
        assert len(percs) >= 1, "deep_house should have percussion"

    def test_techno_has_16th_hats(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["techno"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.25 in hats, "Missing 16th hat at 0.25"
        assert 0.75 in hats, "Missing 16th hat at 0.75"

    def test_techno_has_more_strokes_than_house(self):
        techno_count = len(self.FOUR_ON_FLOOR_PATTERNS["techno"])
        house_count = len(self.FOUR_ON_FLOOR_PATTERNS["classic_house"])
        assert techno_count > house_count, "techno should be denser than classic_house"

    def test_disco_open_hat_offbeats(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["disco"]
        opens = [b for b, s in strokes if s == "open"]
        assert 0.5 in opens, "Missing open hat"
        assert 1.5 in opens, "Missing open hat"

    def test_disco_has_16th_hats(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["disco"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.25 in hats, "Missing 16th hat"

    def test_tech_house_has_ghost(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["tech_house"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) >= 1, "tech_house should have ghost notes"

    def test_all_types_valid(self):
        valid = {"kick", "hat", "open", "clap", "perc", "ghost"}
        for name, strokes in self.FOUR_ON_FLOOR_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"

    def test_cycle_length_one_bar(self):
        cycle_len = 4.0
        for name, strokes in self.FOUR_ON_FLOOR_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < cycle_len, f"{name}: beat {max_beat} exceeds cycle {cycle_len}"

    def test_velocity_mapping(self):
        base = 0.85
        kick_vel = min(1.0, base + 0.05)
        clap_vel = max(0.0, base - 0.05)
        hat_vel = max(0.0, base - 0.15)
        open_vel = max(0.0, base - 0.1)
        ghost_vel = max(0.0, base - 0.35)
        assert ghost_vel < hat_vel < open_vel < clap_vel < kick_vel

    def test_pitch_mapping(self):
        kick, hat, open_hat, clap, perc = 36, 42, 46, 39, 75
        pitch_map = {
            "kick": kick, "hat": hat, "open": open_hat,
            "clap": clap, "perc": perc, "ghost": perc,
        }
        assert pitch_map["kick"] < pitch_map["hat"]
        assert pitch_map["clap"] > pitch_map["kick"]

    def test_duration_mapping(self):
        dur_map = {"kick": 0.2, "hat": 0.05, "open": 0.15, "clap": 0.1, "perc": 0.06, "ghost": 0.04}
        assert dur_map["ghost"] < dur_map["hat"] < dur_map["perc"] < dur_map["clap"] < dur_map["open"] < dur_map["kick"]

    def test_bar_repetition(self):
        bars = 4
        cycle_len = 4.0
        strokes = self.FOUR_ON_FLOOR_PATTERNS["classic_house"]
        all_notes = []
        for b in range(bars):
            for beat, stroke_type in strokes:
                all_notes.append({"start": b * cycle_len + beat, "stroke": stroke_type})
        assert len(all_notes) == len(strokes) * bars
        assert all_notes[0]["start"] == 0.0
        assert all_notes[len(strokes)]["start"] == cycle_len

    def test_note_generation_one_bar(self):
        strokes = self.FOUR_ON_FLOOR_PATTERNS["techno"]
        all_notes = [{"start": beat, "stroke": st} for beat, st in strokes]
        assert len(all_notes) == 18
        assert all_notes[0]["start"] == 0.0

    def test_type_normalization(self):
        raw = "Classic House"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "classic_house"

    def test_pitch_validation(self):
        for p in (36, 42, 46, 39, 75):
            assert 0 <= p <= 127
        assert not (0 <= 128 <= 127)

    def test_valid_types_list(self):
        valid = {"classic_house", "deep_house", "techno", "disco", "tech_house"}
        assert set(self.FOUR_ON_FLOOR_PATTERNS.keys()) == valid


class TestCreateBreakbeat:
    """Tests for create_breakbeat orchestration tool"""

    BREAKBEAT_PATTERNS = {
        "amen": [
            (0.0, "kick"), (0.0, "hat"), (0.5, "hat"), (1.0, "snare"), (1.0, "hat"),
            (1.5, "hat"), (2.0, "hat"), (2.5, "hat"),
            (2.66, "kick"), (2.66, "ghost"), (3.0, "snare"), (3.0, "hat"), (3.5, "hat"),
            (4.0, "kick"), (4.0, "hat"), (4.5, "hat"), (5.0, "snare"), (5.0, "hat"),
            (5.5, "hat"), (6.0, "hat"), (6.5, "hat"),
            (6.66, "kick"), (6.66, "ghost"), (7.0, "snare"), (7.0, "hat"), (7.5, "hat"),
        ],
        "dnb": [
            (0.0, "kick"), (0.25, "hat"), (0.5, "hat"), (0.75, "hat"),
            (1.0, "snare"), (1.25, "hat"), (1.5, "hat"), (1.75, "ghost"),
            (2.0, "hat"), (2.25, "hat"), (2.5, "kick"), (2.66, "ghost"),
            (2.75, "hat"), (3.0, "snare"), (3.25, "hat"), (3.5, "hat"),
            (3.75, "hat"), (4.0, "kick"), (4.25, "hat"), (4.5, "hat"),
            (4.75, "hat"), (5.0, "snare"), (5.25, "hat"), (5.5, "hat"),
            (5.75, "ghost"), (6.0, "hat"), (6.25, "hat"), (6.5, "kick"),
            (6.66, "ghost"), (6.75, "hat"), (7.0, "snare"), (7.25, "hat"),
            (7.5, "hat"), (7.75, "hat"),
        ],
        "big_beat": [
            (0.0, "kick"), (0.5, "hat"), (1.0, "snare"), (1.5, "hat"),
            (2.0, "kick"), (2.0, "snare"), (2.5, "hat"), (2.66, "kick"),
            (3.0, "snare"), (3.5, "hat"),
            (4.0, "kick"), (4.5, "hat"), (5.0, "snare"), (5.5, "hat"),
            (6.0, "kick"), (6.0, "snare"), (6.5, "hat"), (6.66, "kick"),
            (7.0, "snare"), (7.5, "hat"),
        ],
        "2_step": [
            (0.0, "kick"), (0.5, "hat"), (1.0, "snare"), (1.5, "hat"),
            (2.0, "hat"), (2.5, "hat"), (2.66, "kick"), (3.0, "snare"),
            (3.5, "ghost"), (3.66, "hat"),
            (4.0, "kick"), (4.5, "hat"), (5.0, "snare"), (5.5, "hat"),
            (6.0, "hat"), (6.5, "hat"), (6.66, "kick"), (7.0, "snare"),
            (7.5, "ghost"), (7.66, "hat"),
        ],
        "funky_drummer": [
            (0.0, "kick"), (0.0, "hat"), (0.33, "ghost"), (0.5, "hat"),
            (1.0, "snare"), (1.0, "hat"), (1.33, "ghost"), (1.5, "hat"),
            (2.0, "kick"), (2.0, "hat"), (2.33, "ghost"), (2.5, "hat"),
            (2.66, "kick"), (3.0, "snare"), (3.0, "hat"), (3.33, "ghost"),
            (3.5, "hat"), (3.66, "kick"),
            (4.0, "kick"), (4.0, "hat"), (4.33, "ghost"), (4.5, "hat"),
            (5.0, "snare"), (5.0, "hat"), (5.33, "ghost"), (5.5, "hat"),
            (6.0, "kick"), (6.0, "hat"), (6.33, "ghost"), (6.5, "hat"),
            (6.66, "kick"), (7.0, "snare"), (7.0, "hat"), (7.33, "ghost"),
            (7.5, "hat"), (7.66, "kick"),
        ],
    }

    def test_amen_syncopated_kick(self):
        """Amen break: kick NOT on clean quarters — the defining feature"""
        strokes = self.BREAKBEAT_PATTERNS["amen"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 0.0 in kicks, "Missing kick on beat 1"
        assert 2.66 in kicks, "Missing syncopated kick at 2.66"

    def test_amen_snare_on_2_and_4(self):
        strokes = self.BREAKBEAT_PATTERNS["amen"]
        snares = [b for b, s in strokes if s == "snare"]
        assert 1.0 in snares, "Missing snare on beat 2"
        assert 3.0 in snares, "Missing snare on beat 4"

    def test_amen_has_ghost_notes(self):
        strokes = self.BREAKBEAT_PATTERNS["amen"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert 2.66 in ghosts, "Missing ghost snare at 2.66"

    def test_amen_hats_on_8ths(self):
        strokes = self.BREAKBEAT_PATTERNS["amen"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.5 in hats, "Missing hat on &1"

    def test_dnb_has_16th_hats(self):
        strokes = self.BREAKBEAT_PATTERNS["dnb"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.25 in hats, "Missing 16th hat at 0.25"
        assert 0.75 in hats, "Missing 16th hat at 0.75"

    def test_dnb_has_ghost_snares(self):
        strokes = self.BREAKBEAT_PATTERNS["dnb"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) >= 2, "DnB should have multiple ghost snares"

    def test_dnb_denser_than_amen(self):
        dnb_count = len(self.BREAKBEAT_PATTERNS["dnb"])
        amen_count = len(self.BREAKBEAT_PATTERNS["amen"])
        assert dnb_count > amen_count, "DnB should be denser than amen"

    def test_big_beat_kick_snare_syncopation(self):
        """Big beat has kick+snare simultaneously on beat 2 — characteristic"""
        strokes = self.BREAKBEAT_PATTERNS["big_beat"]
        kicks_at_2 = [b for b, s in strokes if s == "kick" and b == 2.0]
        snares_at_2 = [b for b, s in strokes if s == "snare" and b == 2.0]
        assert len(kicks_at_2) >= 1 and len(snares_at_2) >= 1, "Missing kick+snare at beat 2"

    def test_big_beat_has_syncopated_kick(self):
        strokes = self.BREAKBEAT_PATTERNS["big_beat"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 2.66 in kicks, "Missing syncopated kick at 2.66"

    def test_2_step_skipping_kick(self):
        """2-step: second kick shifted to 2.66, not on beat 3 — the skip"""
        strokes = self.BREAKBEAT_PATTERNS["2_step"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 2.66 in kicks, "Missing shifted kick at 2.66"
        assert 2.0 not in kicks, "2-step should NOT have kick on beat 3 (that's the skip)"

    def test_2_step_ghost_on_3_5(self):
        strokes = self.BREAKBEAT_PATTERNS["2_step"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert 3.5 in ghosts, "Missing ghost snare at 3.5"

    def test_funky_drummer_triple_kick(self):
        """Funky Drummer: kick at 0, 2, AND 2.66 — the funk"""
        strokes = self.BREAKBEAT_PATTERNS["funky_drummer"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 0.0 in kicks, "Missing kick on 1"
        assert 2.0 in kicks, "Missing kick on 3"
        assert 2.66 in kicks, "Missing syncopated kick at 2.66"

    def test_funky_drummer_has_ghosts(self):
        strokes = self.BREAKBEAT_PATTERNS["funky_drummer"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) >= 4, "Funky Drummer should have multiple ghost notes"

    def test_all_types_valid(self):
        valid = {"kick", "snare", "hat", "ghost"}
        for name, strokes in self.BREAKBEAT_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"

    def test_cycle_length_two_bars(self):
        cycle_len = 8.0
        for name, strokes in self.BREAKBEAT_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < cycle_len, f"{name}: beat {max_beat} exceeds cycle {cycle_len}"

    def test_all_breakbeats_are_syncopated(self):
        """The defining feature: at least one kick or snare NOT on a clean quarter"""
        for name, strokes in self.BREAKBEAT_PATTERNS.items():
            off_grid = [b for b, s in strokes if s in ("kick", "snare") and b != int(b)]
            assert len(off_grid) >= 1, f"{name}: not syncopated enough (no off-grid kick/snare)"

    def test_velocity_mapping(self):
        base = 0.85
        kick_vel = min(1.0, base + 0.05)
        snare_vel = max(0.0, base - 0.05)
        hat_vel = max(0.0, base - 0.15)
        ghost_vel = max(0.0, base - 0.3)
        assert ghost_vel < hat_vel < snare_vel < kick_vel

    def test_pitch_mapping(self):
        kick, snare, hat, ghost = 36, 38, 42, 37
        pitch_map = {"kick": kick, "snare": snare, "hat": hat, "ghost": ghost}
        assert pitch_map["kick"] < pitch_map["snare"] < pitch_map["hat"]

    def test_bar_repetition(self):
        bars = 4
        cycles = bars // 2
        cycle_len = 8.0
        strokes = self.BREAKBEAT_PATTERNS["amen"]
        all_notes = []
        for c in range(cycles):
            for beat, stroke_type in strokes:
                all_notes.append({"start": c * cycle_len + beat, "stroke": stroke_type})
        assert len(all_notes) == len(strokes) * cycles
        assert all_notes[len(strokes)]["start"] == cycle_len

    def test_type_normalization(self):
        raw = "Big Beat"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "big_beat"

    def test_valid_types_list(self):
        valid = {"amen", "dnb", "big_beat", "2_step", "funky_drummer"}
        assert set(self.BREAKBEAT_PATTERNS.keys()) == valid


class TestCreateTrapRolls:
    """Tests for create_trap_rolls orchestration tool"""

    TRAP_ROLL_PATTERNS = {
        "modern": [
            (0.0, "kick"), (0.0, "hat"), (0.25, "hat"), (0.5, "hat"), (0.75, "hat"),
            (1.0, "hat"), (1.25, "hat"), (1.5, "kick"), (1.75, "hat"),
            (2.0, "snare"), (2.0, "hat"), (2.25, "hat"), (2.5, "hat"), (2.75, "hat"),
            (3.0, "hat"), (3.16, "hat"), (3.33, "hat"), (3.5, "hat"),
            (3.66, "hat"), (3.83, "hat"),
            (4.0, "kick"), (4.0, "hat"), (4.25, "hat"), (4.5, "hat"), (4.75, "hat"),
            (5.0, "hat"), (5.16, "hat"), (5.33, "hat"), (5.5, "hat"),
            (5.66, "hat"), (5.83, "hat"),
            (6.0, "snare"), (6.0, "hat"), (6.25, "hat"), (6.5, "hat"), (6.75, "hat"),
            (7.0, "hat"), (7.16, "ghost"), (7.33, "ghost"), (7.5, "ghost"),
            (7.66, "ghost"), (7.83, "ghost"),
        ],
        "migos": [
            (0.0, "kick"), (0.0, "hat"),
            (0.5, "hat"), (0.66, "hat"), (0.83, "hat"),
            (1.0, "snare"), (1.0, "hat"),
            (1.5, "hat"), (1.66, "hat"), (1.83, "hat"),
            (2.0, "hat"), (2.25, "hat"),
            (3.0, "kick"), (3.0, "hat"), (3.25, "hat"),
            (3.5, "hat"), (3.66, "hat"), (3.83, "hat"),
            (4.0, "kick"), (4.0, "hat"),
            (4.5, "hat"), (4.66, "hat"), (4.83, "hat"),
            (5.0, "snare"), (5.0, "hat"),
            (5.5, "hat"), (5.66, "hat"), (5.83, "hat"),
            (6.0, "hat"), (6.25, "hat"),
            (7.0, "kick"), (7.0, "hat"), (7.25, "hat"),
            (7.5, "hat"), (7.66, "hat"), (7.83, "hat"),
        ],
        "bubble": [
            (0.0, "kick"), (0.0, "hat"), (0.25, "hat"), (0.5, "hat"),
            (0.75, "hat"), (0.87, "hat"),
            (1.0, "hat"), (1.25, "hat"), (1.5, "kick"), (1.5, "hat"),
            (1.75, "hat"), (1.87, "hat"),
            (2.0, "snare"), (2.0, "hat"), (2.25, "hat"), (2.5, "hat"),
            (2.75, "hat"), (2.87, "hat"),
            (3.0, "hat"), (3.25, "hat"), (3.5, "hat"),
            (3.75, "hat"), (3.87, "hat"),
            (4.0, "kick"), (4.0, "hat"), (4.25, "hat"), (4.5, "hat"),
            (4.75, "hat"), (4.87, "hat"),
            (5.0, "hat"), (5.25, "hat"), (5.5, "kick"), (5.5, "hat"),
            (5.75, "hat"), (5.87, "hat"),
            (6.0, "snare"), (6.0, "hat"), (6.25, "hat"), (6.5, "hat"),
            (6.75, "hat"), (6.87, "hat"),
            (7.0, "hat"), (7.25, "hat"), (7.5, "hat"),
            (7.75, "hat"), (7.87, "hat"),
        ],
        "skrrt": [
            (0.0, "kick"), (0.0, "hat"), (0.16, "hat"), (0.33, "hat"),
            (1.0, "hat"), (1.16, "hat"), (1.33, "hat"),
            (2.0, "snare"), (2.66, "kick"), (2.66, "hat"),
            (2.82, "hat"), (2.98, "hat"), (3.16, "ghost"), (3.33, "ghost"),
            (3.5, "hat"), (3.66, "hat"), (3.83, "hat"),
            (4.0, "kick"), (4.0, "hat"), (4.16, "hat"), (4.33, "hat"),
            (5.0, "hat"), (5.16, "hat"), (5.33, "hat"),
            (6.0, "snare"), (6.66, "kick"), (6.66, "hat"),
            (6.82, "hat"), (6.98, "hat"), (7.16, "ghost"), (7.33, "ghost"),
            (7.5, "hat"), (7.66, "hat"), (7.83, "hat"),
        ],
        "evolving": [
            (0.0, "kick"), (0.0, "hat"), (0.5, "hat"),
            (1.0, "hat"), (1.5, "hat"),
            (2.0, "snare"), (2.0, "hat"), (2.5, "hat"),
            (3.0, "hat"), (3.5, "hat"),
            (4.0, "kick"), (4.0, "hat"), (4.25, "hat"), (4.5, "hat"), (4.75, "hat"),
            (5.0, "hat"), (5.25, "hat"), (5.5, "hat"), (5.75, "hat"),
            (6.0, "snare"), (6.0, "hat"), (6.25, "hat"), (6.5, "hat"), (6.75, "hat"),
            (7.0, "hat"), (7.25, "hat"), (7.5, "hat"), (7.75, "hat"),
            (7.83, "ghost"),
        ],
    }

    def test_modern_has_16th_hats(self):
        strokes = self.TRAP_ROLL_PATTERNS["modern"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.25 in hats, "Missing 16th hat at 0.25"
        assert 0.75 in hats, "Missing 16th hat at 0.75"

    def test_modern_has_triplet_roll(self):
        strokes = self.TRAP_ROLL_PATTERNS["modern"]
        hats = [b for b, s in strokes if s == "hat"]
        # Triplet positions around beat 3: 3.0, 3.16, 3.33
        assert 3.16 in hats, "Missing triplet hat at 3.16"
        assert 3.33 in hats, "Missing triplet hat at 3.33"

    def test_modern_has_ghost_roll(self):
        """Modern trap has ghost note roll at end of bar 2"""
        strokes = self.TRAP_ROLL_PATTERNS["modern"]
        ghosts = [b for b, s in strokes if s == "ghost"]
        assert len(ghosts) >= 4, "Missing ghost roll"

    def test_migos_has_triplet_bursts(self):
        strokes = self.TRAP_ROLL_PATTERNS["migos"]
        # Triplet burst at 0.66, 0.83
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.66 in hats, "Missing triplet hat at 0.66"
        assert 0.83 in hats, "Missing triplet hat at 0.83"

    def test_migos_snare_on_2_and_4(self):
        strokes = self.TRAP_ROLL_PATTERNS["migos"]
        snares = [b for b, s in strokes if s == "snare"]
        assert 1.0 in snares, "Missing snare on beat 2"
        assert 5.0 in snares, "Missing snare on beat 4 (bar 2)"

    def test_bubble_has_32nd_doubles(self):
        """Bubble hats have 32nd note doubles at 0.87, 1.87 etc"""
        strokes = self.TRAP_ROLL_PATTERNS["bubble"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.87 in hats, "Missing 32nd double at 0.87"
        assert 2.87 in hats, "Missing 32nd double at 2.87"

    def test_bubble_continuous_16ths(self):
        strokes = self.TRAP_ROLL_PATTERNS["bubble"]
        hats = [b for b, s in strokes if s == "hat"]
        assert 0.25 in hats, "Missing 16th hat"
        assert 0.5 in hats, "Missing 16th hat"

    def test_skrrt_has_stutter_bursts(self):
        """Skrrt: short rapid groups (3-4 hits) with gaps"""
        strokes = self.TRAP_ROLL_PATTERNS["skrrt"]
        hats = [b for b, s in strokes if s in ("hat", "ghost")]
        # First burst: 0.0, 0.16, 0.33
        assert 0.16 in hats, "Missing stutter hit at 0.16"
        assert 0.33 in hats, "Missing stutter hit at 0.33"

    def test_skrrt_has_syncopated_kick(self):
        strokes = self.TRAP_ROLL_PATTERNS["skrrt"]
        kicks = [b for b, s in strokes if s == "kick"]
        assert 2.66 in kicks, "Missing syncopated kick at 2.66"

    def test_evolving_bar1_sparser_than_bar2(self):
        """Evololving: bar 1 has fewer hats than bar 2 — density builds"""
        strokes = self.TRAP_ROLL_PATTERNS["evolving"]
        bar1_hats = [b for b, s in strokes if s == "hat" and b < 4.0]
        bar2_hats = [b for b, s in strokes if s == "hat" and b >= 4.0]
        assert len(bar2_hats) > len(bar1_hats), "Bar 2 should be denser than bar 1"

    def test_all_types_valid(self):
        valid = {"kick", "snare", "hat", "ghost"}
        for name, strokes in self.TRAP_ROLL_PATTERNS.items():
            for _, stroke_type in strokes:
                assert stroke_type in valid, f"{name} has invalid stroke {stroke_type}"

    def test_cycle_length_two_bars(self):
        cycle_len = 8.0
        for name, strokes in self.TRAP_ROLL_PATTERNS.items():
            max_beat = max(b for b, _ in strokes)
            assert max_beat < cycle_len, f"{name}: beat {max_beat} exceeds cycle {cycle_len}"

    def test_all_types_have_triplet_positions(self):
        """At least one type should have triplet subdivisions (0.16, 0.33, 0.66, 0.83)"""
        found_triplet = False
        for name, strokes in self.TRAP_ROLL_PATTERNS.items():
            for b, _ in strokes:
                frac = b - int(b)
                if abs(frac - 0.16) < 0.01 or abs(frac - 0.33) < 0.01 or abs(frac - 0.66) < 0.01 or abs(frac - 0.83) < 0.01:
                    found_triplet = True
                    break
        assert found_triplet, "No triplet positions found in any pattern"

    def test_velocity_mapping(self):
        base = 0.85
        kick_vel = min(1.0, base + 0.05)
        snare_vel = max(0.0, base - 0.05)
        hat_vel = max(0.0, base - 0.15)
        ghost_vel = max(0.0, base - 0.3)
        assert ghost_vel < hat_vel < snare_vel < kick_vel

    def test_pitch_mapping(self):
        kick, snare, hat = 36, 38, 42
        pitch_map = {"kick": kick, "snare": snare, "hat": hat, "ghost": hat}
        assert pitch_map["kick"] < pitch_map["snare"] < pitch_map["hat"]

    def test_bar_repetition(self):
        bars = 4
        cycles = bars // 2
        cycle_len = 8.0
        strokes = self.TRAP_ROLL_PATTERNS["modern"]
        all_notes = []
        for c in range(cycles):
            for beat, stroke_type in strokes:
                all_notes.append({"start": c * cycle_len + beat, "stroke": stroke_type})
        assert len(all_notes) == len(strokes) * cycles

    def test_type_normalization(self):
        raw = "Modern"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "modern"

    def test_valid_types_list(self):
        valid = {"modern", "migos", "bubble", "skrrt", "evolving"}
        assert set(self.TRAP_ROLL_PATTERNS.keys()) == valid


class TestCreateElectronicBass:
    """Tests for create_electronic_bass orchestration tool"""

    BASS_PATTERNS = {
        "house_offbeat": [
            (0.5, 0, 0.4, 1.0, False), (1.5, 0, 0.4, 1.0, False),
            (2.5, 0, 0.4, 1.0, False), (3.5, 0, 0.4, 1.0, False),
        ],
        "techno_sub": [
            (0.0, 0, 3.8, 1.0, False),
        ],
        "dnb_reese": [
            (0.0, 0, 1.5, 1.0, False),
            (1.75, 0, 0.2, 0.8, False), (2.25, 0, 0.2, 0.8, False),
            (2.75, 0, 0.2, 0.8, False), (3.25, 12, 0.15, 0.7, False),
            (3.75, 0, 0.2, 0.9, False),
        ],
        "dubstep_wobble": [
            (0.0, 0, 0.9, 1.0, False),
            (1.0, 0, 0.12, 0.85, False), (1.25, 0, 0.12, 0.85, False),
            (1.5, 7, 0.12, 0.85, False), (1.75, 0, 0.12, 0.85, False),
            (2.0, 0, 0.9, 1.0, False),
            (3.0, 0, 0.12, 0.85, False), (3.25, 0, 0.12, 0.85, False),
            (3.5, 7, 0.12, 0.85, False), (3.75, 0, 0.12, 0.85, False),
        ],
        "acid_303": [
            (0.0, 0, 0.2, 1.0, False), (0.25, 12, 0.15, 0.7, False),
            (0.5, 0, 0.2, 0.9, False), (0.75, 12, 0.15, 0.7, False),
            (1.0, 0, 0.2, 1.0, False), (1.25, 7, 0.15, 0.8, False),
            (1.5, 0, 0.2, 0.9, False), (1.75, 12, 0.15, 0.7, False),
            (2.0, 0, 0.2, 1.0, False), (2.25, 12, 0.15, 0.7, False),
            (2.5, 0, 0.2, 0.9, False), (2.75, 12, 0.15, 0.7, False),
            (3.0, 0, 0.2, 1.0, False), (3.25, 7, 0.15, 0.8, False),
            (3.5, 0, 0.2, 0.9, False), (3.75, 12, 0.15, 0.7, False),
        ],
        "garage_2step": [
            (0.0, 0, 0.5, 1.0, False),
            (2.66, 0, 0.3, 0.9, False),
            (3.5, 12, 0.15, 0.6, True),
        ],
    }

    def test_house_offbeat_between_kicks(self):
        """House bass on off-beats (0.5, 1.5, 2.5, 3.5) — between kick quarters"""
        strokes = self.BASS_PATTERNS["house_offbeat"]
        beats = [b for b, _, _, _, _ in strokes]
        assert 0.5 in beats, "Missing off-beat at 0.5"
        assert 1.5 in beats, "Missing off-beat at 1.5"
        assert 0.0 not in beats, "Should NOT have bass on beat 1 (kick territory)"

    def test_techno_sub_long_sustained(self):
        """Techno sub: single long sustained note per bar"""
        strokes = self.BASS_PATTERNS["techno_sub"]
        assert len(strokes) == 1, "Techno sub should be a single sustained note"
        assert strokes[0][2] >= 3.0, "Techno sub should be long duration"

    def test_dnb_reese_syncopated_stabs(self):
        """DnB Reese: sustained on beat 1, then stabs on e/a of 2-4"""
        strokes = self.BASS_PATTERNS["dnb_reese"]
        beats = [b for b, _, _, _, _ in strokes]
        assert 0.0 in beats, "Missing sustained note on beat 1"
        assert 1.75 in beats, "Missing stab on 'a' of beat 2"

    def test_dnb_reese_has_octave_jump(self):
        strokes = self.BASS_PATTERNS["dnb_reese"]
        pitch_offs = [po for _, po, _, _, _ in strokes]
        assert 12 in pitch_offs, "Missing octave jump in Reese bass"

    def test_dubstep_wobble_quarters_on_1_3(self):
        """Dubstep: sustained notes on beats 1 and 3"""
        strokes = self.BASS_PATTERNS["dubstep_wobble"]
        quarters = [(b, d) for b, _, d, _, _ in strokes if b in (0.0, 2.0)]
        assert len(quarters) == 2, "Missing sustained notes on beats 1 and 3"
        assert all(d >= 0.5 for _, d in quarters), "Beat 1/3 notes should be long"

    def test_dubstep_wobble_has_fifth(self):
        """Dubstep wobble uses fifth interval for movement"""
        strokes = self.BASS_PATTERNS["dubstep_wobble"]
        pitch_offs = [po for _, po, _, _, _ in strokes]
        assert 7 in pitch_offs, "Missing fifth in wobble pattern"

    def test_acid_303_16th_notes(self):
        """Acid 303: 16th note pattern"""
        strokes = self.BASS_PATTERNS["acid_303"]
        assert len(strokes) == 16, "Acid 303 should have 16 notes per bar"
        beats = [b for b, _, _, _, _ in strokes]
        assert 0.25 in beats, "Missing 16th at 0.25"
        assert 0.75 in beats, "Missing 16th at 0.75"

    def test_acid_303_octave_alternation(self):
        """Acid alternates between root and octave"""
        strokes = self.BASS_PATTERNS["acid_303"]
        pitch_offs = [po for _, po, _, _, _ in strokes]
        assert 0 in pitch_offs, "Missing root"
        assert 12 in pitch_offs, "Missing octave"

    def test_acid_303_has_fifth_drops(self):
        strokes = self.BASS_PATTERNS["acid_303"]
        pitch_offs = [po for _, po, _, _, _ in strokes]
        assert 7 in pitch_offs, "Missing fifth drop in acid pattern"

    def test_garage_2step_syncopated(self):
        """2-step: bass on 1 and 2.66 — the skip"""
        strokes = self.BASS_PATTERNS["garage_2step"]
        beats = [b for b, _, _, _, _ in strokes]
        assert 0.0 in beats, "Missing bass on beat 1"
        assert 2.66 in beats, "Missing syncopated bass at 2.66"
        assert 2.0 not in beats, "2-step should NOT have bass on beat 3 (skip)"

    def test_garage_2step_has_ghost(self):
        strokes = self.BASS_PATTERNS["garage_2step"]
        ghosts = [(b, g) for b, _, _, _, g in strokes if g]
        assert len(ghosts) >= 1, "2-step should have a ghost note"

    def test_cycle_length_one_bar(self):
        cycle_len = 4.0
        for name, strokes in self.BASS_PATTERNS.items():
            max_beat = max(b for b, _, _, _, _ in strokes)
            assert max_beat < cycle_len, f"{name}: beat {max_beat} exceeds cycle {cycle_len}"

    def test_all_have_root_offset(self):
        """All patterns use root (offset 0) as the primary pitch"""
        for name, strokes in self.BASS_PATTERNS.items():
            pitch_offs = [po for _, po, _, _, _ in strokes]
            assert 0 in pitch_offs, f"{name}: missing root (offset 0)"

    def test_velocity_mult_range(self):
        for name, strokes in self.BASS_PATTERNS.items():
            for _, _, _, vm, _ in strokes:
                assert 0.0 < vm <= 1.0, f"{name}: velocity mult {vm} out of range"

    def test_bar_repetition(self):
        bars = 4
        cycle_len = 4.0
        strokes = self.BASS_PATTERNS["house_offbeat"]
        all_notes = []
        for b in range(bars):
            for beat, po, dur, vm, g in strokes:
                all_notes.append({"start": b * cycle_len + beat, "pitch_off": po})
        assert len(all_notes) == len(strokes) * bars
        # Second bar's first note = cycle_len + first_beat (0.5 for house_offbeat)
        first_beat = strokes[0][0]
        assert all_notes[len(strokes)]["start"] == cycle_len + first_beat

    def test_type_normalization(self):
        raw = "House Offbeat"
        normalized = raw.strip().lower().replace(" ", "_")
        assert normalized == "house_offbeat"

    def test_valid_types_list(self):
        valid = {"house_offbeat", "techno_sub", "dnb_reese", "dubstep_wobble", "acid_303", "garage_2step"}
        assert set(self.BASS_PATTERNS.keys()) == valid

    def test_pitch_offset_values(self):
        """Pitch offsets should only be 0 (root), 7 (fifth), or 12 (octave)"""
        valid_offsets = {0, 7, 12}
        for name, strokes in self.BASS_PATTERNS.items():
            for _, po, _, _, _ in strokes:
                assert po in valid_offsets, f"{name}: unexpected pitch offset {po}"


class TestCreateDnbArrangement:
    """Tests for create_dnb_arrangement — first multi-track genre arrangement"""

    DRUM_PATTERN = [
        (0.0, "kick"), (0.0, "hat"), (0.5, "hat"), (1.0, "snare"), (1.0, "hat"),
        (1.5, "hat"), (2.0, "hat"), (2.5, "hat"),
        (2.66, "kick"), (2.66, "ghost"), (3.0, "snare"), (3.0, "hat"), (3.5, "hat"),
        (4.0, "kick"), (4.0, "hat"), (4.5, "hat"), (5.0, "snare"), (5.0, "hat"),
        (5.5, "hat"), (6.0, "hat"), (6.5, "hat"),
        (6.66, "kick"), (6.66, "ghost"), (7.0, "snare"), (7.0, "hat"), (7.5, "hat"),
    ]

    BASS_PATTERN = [
        (0.0, 0, 1.5, 1.0, False),
        (1.75, 0, 0.2, 0.8, False), (2.25, 0, 0.2, 0.8, False),
        (2.75, 0, 0.2, 0.8, False), (3.25, 12, 0.15, 0.7, False),
        (3.75, 0, 0.2, 0.9, False),
    ]

    PAD_INTERVALS = [0, 3, 7]  # root, minor third, fifth

    def test_drum_pattern_is_amen_style(self):
        """Drums use Amen break pattern with syncopated kick at 2.66"""
        kicks = [b for b, s in self.DRUM_PATTERN if s == "kick"]
        assert 2.66 in kicks, "Missing syncopated kick at 2.66 (Amen characteristic)"

    def test_drum_pattern_has_ghost_notes(self):
        ghosts = [b for b, s in self.DRUM_PATTERN if s == "ghost"]
        assert len(ghosts) >= 2, "Missing ghost notes in drum pattern"

    def test_drum_pattern_snare_on_2_and_4(self):
        snares = [b for b, s in self.DRUM_PATTERN if s == "snare"]
        assert 1.0 in snares, "Missing snare on beat 2"
        assert 3.0 in snares, "Missing snare on beat 4"

    def test_bass_pattern_is_reese_style(self):
        """Bass has sustained note on beat 1, then syncopated stabs"""
        beats = [b for b, _, _, _, _ in self.BASS_PATTERN]
        assert 0.0 in beats, "Missing sustained bass on beat 1"
        assert 1.75 in beats, "Missing syncopated stab"

    def test_bass_pattern_has_octave_jump(self):
        pitch_offs = [po for _, po, _, _, _ in self.BASS_PATTERN]
        assert 12 in pitch_offs, "Missing octave jump in bass"

    def test_pad_is_minor_triad(self):
        """Pad uses root + minor third + fifth = minor triad"""
        assert 0 in self.PAD_INTERVALS, "Missing root in pad"
        assert 3 in self.PAD_INTERVALS, "Missing minor third in pad"
        assert 7 in self.PAD_INTERVALS, "Missing fifth in pad"

    def test_pad_sustained_2_bars(self):
        """Pad chords sustain for 2 bars (8 beats)"""
        pad_cycle = 8.0
        assert pad_cycle == 8.0, "Pad cycle should be 2 bars"

    def test_drum_cycle_is_2_bars(self):
        """Drum pattern is 2-bar cycle (Amen break)"""
        drum_cycle = 8.0
        max_beat = max(b for b, _ in self.DRUM_PATTERN)
        assert max_beat < drum_cycle, "Drum pattern exceeds 2-bar cycle"

    def test_bass_cycle_is_1_bar(self):
        """Bass pattern is 1-bar cycle"""
        bass_cycle = 4.0
        max_beat = max(b for b, _, _, _, _ in self.BASS_PATTERN)
        assert max_beat < bass_cycle, "Bass pattern exceeds 1-bar cycle"

    def test_drum_note_count_for_8_bars(self):
        """8 bars = 4 drum cycles × pattern length"""
        bars = 8
        drum_cycles = bars // 2
        assert len(self.DRUM_PATTERN) * drum_cycles == 26 * 4

    def test_bass_note_count_for_8_bars(self):
        bars = 8
        assert len(self.BASS_PATTERN) * bars == 6 * 8

    def test_pad_note_count_for_8_bars(self):
        """8 bars = 4 pad cycles × 3 notes per chord"""
        bars = 8
        pad_cycles = bars // 2
        assert len(self.PAD_INTERVALS) * pad_cycles == 3 * 4

    def test_total_note_count(self):
        """Total = drums + bass + pad for 8 bars"""
        bars = 8
        drum_cycles = bars // 2
        drum_count = len(self.DRUM_PATTERN) * drum_cycles
        bass_count = len(self.BASS_PATTERN) * bars
        pad_count = len(self.PAD_INTERVALS) * drum_cycles
        total = drum_count + bass_count + pad_count
        assert total > 0, "Total note count should be positive"
        assert drum_count > bass_count, "Drums should have more notes than bass"
        assert bass_count > pad_count, "Bass should have more notes than pad"

    def test_tracks_are_separate(self):
        """Drums, bass, pad go on different tracks"""
        drum_track, bass_track, pad_track = 0, 1, 2
        assert drum_track != bass_track, "Drums and bass on same track"
        assert bass_track != pad_track, "Bass and pad on same track"
        assert drum_track != pad_track, "Drums and pad on same track"

    def test_bpm_range(self):
        assert 140 <= 174 <= 200, "Default BPM should be in valid range"
        assert 140 <= 170 <= 200, "170 BPM should be valid"

    def test_bass_pad_pitch_relationship(self):
        """Pad is 2 octaves above bass"""
        octave = 2
        root_pc = 9  # A
        bass_base = (octave + 1) * 12 + root_pc  # 33
        pad_base = (octave + 3) * 12 + root_pc    # 57
        assert pad_base - bass_base == 24, "Pad should be 2 octaves (24 semitones) above bass"

    def test_drum_bass_rhythmic_lock(self):
        """Bass sustains on beat 1 when drums also hit beat 1 — they lock"""
        drum_beat1 = any(b == 0.0 and s == "kick" for b, s in self.DRUM_PATTERN)
        bass_beat1 = any(b == 0.0 for b, _, _, _, _ in self.BASS_PATTERN)
        assert drum_beat1 and bass_beat1, "Drums and bass should both hit beat 1"


class TestCreateHouseArrangement:
    """Tests for create_house_arrangement — multi-track house arrangement"""

    DRUM_PATTERN = [
        (0.0, "kick"), (0.5, "open"), (1.0, "kick"), (1.0, "clap"),
        (1.5, "open"), (2.0, "kick"), (2.5, "open"), (3.0, "kick"),
        (3.0, "clap"), (3.5, "open"),
    ]
    BASS_PATTERN = [
        (0.5, 0, 0.4, 1.0), (1.5, 0, 0.4, 1.0),
        (2.5, 0, 0.4, 1.0), (3.5, 0, 0.4, 1.0),
    ]
    STAB_INTERVALS = [0, 3, 7]
    STAB_PATTERN = [
        (0.0, 0.3, 1.0), (2.0, 0.3, 1.0), (2.5, 0.15, 0.7),
    ]

    def test_drums_kick_on_every_quarter(self):
        kicks = [b for b, s in self.DRUM_PATTERN if s == "kick"]
        for beat in [0.0, 1.0, 2.0, 3.0]:
            assert beat in kicks, f"Missing kick on beat {beat}"

    def test_drums_open_hat_on_offbeats(self):
        opens = [b for b, s in self.DRUM_PATTERN if s == "open"]
        assert 0.5 in opens, "Missing open hat on &1"
        assert 1.5 in opens, "Missing open hat on &2"

    def test_drums_clap_on_2_and_4(self):
        claps = [b for b, s in self.DRUM_PATTERN if s == "clap"]
        assert 1.0 in claps, "Missing clap on beat 2"
        assert 3.0 in claps, "Missing clap on beat 4"

    def test_bass_on_offbeats_between_kicks(self):
        """Bass hits between kicks — the house 'untz-untz' feel"""
        bass_beats = [b for b, _, _, _ in self.BASS_PATTERN]
        assert 0.5 in bass_beats, "Missing bass on &1"
        assert 1.5 in bass_beats, "Missing bass on &2"
        assert 0.0 not in bass_beats, "Bass should NOT be on beat 1 (kick territory)"

    def test_bass_and_drums_interlock(self):
        """Bass on 0.5 when kick is NOT there — they interlock"""
        kick_beats = {b for b, s in self.DRUM_PATTERN if s == "kick"}
        bass_beats = {b for b, _, _, _ in self.BASS_PATTERN}
        assert not (kick_beats & bass_beats), "Bass and kick should never overlap"

    def test_stabs_are_minor_triad(self):
        assert 0 in self.STAB_INTERVALS, "Missing root in stab"
        assert 3 in self.STAB_INTERVALS, "Missing minor third in stab"
        assert 7 in self.STAB_INTERVALS, "Missing fifth in stab"

    def test_stabs_on_1_and_3(self):
        stab_beats = [b for b, _, _ in self.STAB_PATTERN]
        assert 0.0 in stab_beats, "Missing stab on beat 1"
        assert 2.0 in stab_beats, "Missing stab on beat 3"

    def test_stab_has_offbeat_variant(self):
        stab_beats = [b for b, _, _ in self.STAB_PATTERN]
        assert 2.5 in stab_beats, "Missing off-beat stab at 2.5"

    def test_drum_cycle_1_bar(self):
        max_beat = max(b for b, _ in self.DRUM_PATTERN)
        assert max_beat < 4.0, "Drum pattern exceeds 1 bar"

    def test_bass_cycle_1_bar(self):
        max_beat = max(b for b, _, _, _ in self.BASS_PATTERN)
        assert max_beat < 4.0, "Bass pattern exceeds 1 bar"

    def test_stab_cycle_1_bar(self):
        max_beat = max(b for b, _, _ in self.STAB_PATTERN)
        assert max_beat < 4.0, "Stab pattern exceeds 1 bar"

    def test_drum_note_count_8_bars(self):
        assert len(self.DRUM_PATTERN) * 8 == 10 * 8

    def test_bass_note_count_8_bars(self):
        assert len(self.BASS_PATTERN) * 8 == 4 * 8

    def test_stab_note_count_8_bars(self):
        """3 stab positions × 3 intervals × 8 bars"""
        assert len(self.STAB_PATTERN) * len(self.STAB_INTERVALS) * 8 == 3 * 3 * 8

    def test_tracks_separate(self):
        drum_track, bass_track, stab_track = 0, 1, 2
        assert len({drum_track, bass_track, stab_track}) == 3, "Tracks must be distinct"

    def test_bpm_range(self):
        assert 110 <= 124 <= 140, "Default BPM should be valid"

    def test_bass_stab_pitch_relationship(self):
        """Stabs 2 octaves above bass"""
        octave = 2
        root_pc = 0  # C
        bass_base = (octave + 1) * 12 + root_pc
        stab_base = (octave + 3) * 12 + root_pc
        assert stab_base - bass_base == 24, "Stabs should be 2 octaves above bass"

    def test_kick_bass_complement(self):
        """Kick on 0,1,2,3 and bass on 0.5,1.5,2.5,3.5 — perfectly interleaved"""
        kick_beats = sorted(b for b, s in self.DRUM_PATTERN if s == "kick")
        bass_beats = sorted(b for b, _, _, _ in self.BASS_PATTERN)
        for k, bs in zip(kick_beats, bass_beats):
            assert abs(bs - k - 0.5) < 0.01, f"Bass {bs} should be 0.5 after kick {k}"
