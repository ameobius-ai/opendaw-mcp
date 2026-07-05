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
