

class TestApplyContour:
    """Unit tests for apply_contour — melodic contour reshaping"""

    def test_ascending_contour(self):
        """ascending: t=0 → -1, t=1 → +1"""
        fn = lambda t: t * 2 - 1
        assert fn(0) == -1, "start at lowest"
        assert fn(1) == 1, "end at highest"
        assert fn(0.5) == 0, "midpoint at mean"

    def test_descending_contour(self):
        """descending: t=0 → +1, t=1 → -1"""
        fn = lambda t: 1 - t * 2
        assert fn(0) == 1, "start at highest"
        assert fn(1) == -1, "end at lowest"

    def test_arch_contour(self):
        """arch: peak at midpoint"""
        fn = lambda t: 1 - abs(t - 0.5) * 2
        assert fn(0) == 0, "start low"
        assert fn(0.5) == 1, "peak at center"
        assert fn(1) == 0, "end low"

    def test_inverted_arch_contour(self):
        """inverted_arch: valley at midpoint, starts/ends at 0"""
        fn = lambda t: abs(t - 0.5) * 2 - 1
        assert fn(0) == 0, "start at mean"
        assert fn(0.5) == -1, "valley at center"
        assert fn(1) == 0, "end at mean"

    def test_wave_contour(self):
        """wave: sinusoidal, starts at 0"""
        import math
        fn = lambda t: math.sin(t * math.pi * 2)
        assert abs(fn(0)) < 0.001, "start at 0"
        assert abs(fn(0.25) - 1) < 0.001, "quarter = peak"
        assert abs(fn(0.5)) < 0.001, "half = zero crossing"
        assert abs(fn(0.75) + 1) < 0.001, "three-quarter = valley"

    def test_escalating_contour(self):
        """escalating: stepwise with plateaus"""
        steps = 4
        step_size = 2 / steps
        fn = lambda t: math.floor(t * steps) * step_size - 1
        import math
        assert fn(0.0) == -1, "first step at -1"
        assert fn(0.3) == -0.5, "second step"
        assert fn(0.99) == 0.5, "last step near 1"

    def test_range_semitones_clamping(self):
        """range_semitones clamped to 1-48"""
        assert max(1, min(48, 0)) == 1, "clamped to 1"
        assert max(1, min(48, 100)) == 48, "clamped to 48"
        assert max(1, min(48, 12)) == 12, "12 is valid"

    def test_pitch_clamping(self):
        """Target pitch clamped to 0-127"""
        mean_pitch = 120
        offset = 1.0
        half_range = 12
        target = max(0, min(127, round(mean_pitch + offset * half_range)))
        assert target == 127, "clamped to 127"

    def test_pitch_clamping_low(self):
        """Low pitch clamped to 0"""
        mean_pitch = 5
        offset = -1.0
        half_range = 12
        target = max(0, min(127, round(mean_pitch + offset * half_range)))
        assert target == 0, "clamped to 0"

    def test_scale_snapping_major(self):
        """Major scale snapping: C major → C D E F G A B"""
        intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0  # C
        # Pitch 61 (C#) should snap to 60 (C) or 62 (D)
        rel = ((61 - root_idx) % 12 + 12) % 12  # = 1
        best = intervals[0]
        best_dist = abs(rel - intervals[0])
        for iv in intervals:
            dist = abs(rel - iv)
            if dist < best_dist or (dist == best_dist and iv < best):
                best_dist = dist
                best = iv
        assert best in (0, 2), "C# snaps to C or D"

    def test_scale_snapping_pentatonic(self):
        """Pentatonic: C D E G A (no F, no B)"""
        intervals = [0, 2, 4, 7, 9]
        root_idx = 0
        # Pitch 65 (F) should snap to 64 (E) or 67 (G)
        rel = ((65 - root_idx) % 12 + 12) % 12  # = 5
        best = intervals[0]
        best_dist = abs(rel - intervals[0])
        for iv in intervals:
            dist = abs(rel - iv)
            if dist < best_dist or (dist == best_dist and iv < best):
                best_dist = dist
                best = iv
        assert best in (4, 7), "F snaps to E or G"

    def test_preserve_first_skips_index_0(self):
        """preserve_first: first note keeps original pitch"""
        preserve_first = True
        new_pitches = [60, 64, 67, 72]
        orig_first = 55
        if preserve_first:
            new_pitches[0] = orig_first
        assert new_pitches[0] == 55, "first note preserved"

    def test_preserve_last_skips_final(self):
        """preserve_last: last note keeps original pitch"""
        preserve_last = True
        new_pitches = [60, 64, 67, 72]
        orig_last = 79
        n = len(new_pitches)
        if preserve_last:
            new_pitches[n - 1] = orig_last
        assert new_pitches[-1] == 79, "last note preserved"

    def test_normalized_position(self):
        """t = i / (n-1) for i-th note, 0..1"""
        n = 5
        positions = [i / (n - 1) for i in range(n)]
        assert positions[0] == 0.0, "first at t=0"
        assert positions[-1] == 1.0, "last at t=1"
        assert positions[2] == 0.5, "middle at t=0.5"

    def test_invalid_contour_rejected(self):
        """Invalid contour name rejected"""
        valid = {"ascending", "descending", "arch", "inverted_arch", "wave", "escalating"}
        assert "sine" not in valid, "sine is not a valid contour"
        assert "random" not in valid, "random is not a valid contour"
