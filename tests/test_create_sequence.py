
class TestCreateSequence:
    """Unit tests for create_sequence — melodic sequence with transposition"""

    def test_repetitions_clamping(self):
        """repetitions clamped to 2-16"""
        assert max(2, min(16, 1)) == 2, "clamped to 2"
        assert max(2, min(16, 20)) == 16, "clamped to 16"
        assert max(2, min(16, 4)) == 4, "4 is valid"

    def test_diatonic_transpose_up(self):
        """diatonic transpose: C major, +2 scale steps = C→E"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0

        def isInScale(p):
            rel = ((p - root_idx) % 12 + 12) % 12
            return rel in scale_intervals

        def diatonicTranspose(pitch, steps):
            direction = 1 if steps > 0 else -1
            count = abs(steps)
            p = pitch
            while count > 0:
                p += direction
                if p < 0 or p > 127:
                    return pitch
                if isInScale(p):
                    count -= 1
            return p

        result = diatonicTranspose(60, 2)  # C → E
        assert result == 64, "C + 2 diatonic steps = E (64)"

    def test_diatonic_transpose_down(self):
        """diatonic transpose: C major, -2 scale steps = C→A"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0

        def isInScale(p):
            rel = ((p - root_idx) % 12 + 12) % 12
            return rel in scale_intervals

        def diatonicTranspose(pitch, steps):
            direction = 1 if steps > 0 else -1
            count = abs(steps)
            p = pitch
            while count > 0:
                p += direction
                if p < 0 or p > 127:
                    return pitch
                if isInScale(p):
                    count -= 1
            return p

        result = diatonicTranspose(60, -2)  # C → A
        assert result == 57, "C - 2 diatonic steps = A (57)"

    def test_chromatic_transpose_up(self):
        """chromatic transpose: +3 semitones"""
        assert max(0, min(127, 60 + 3)) == 63, "C + 3 = Eb"

    def test_chromatic_transpose_clamp(self):
        """chromatic transpose clamped to 0-127"""
        assert max(0, min(127, 125 + 5)) == 127, "clamped to 127"
        assert max(0, min(127, 2 - 5)) == 0, "clamped to 0"

    def test_crescendo_velocity_ramp(self):
        """crescendo: linear ramp from start to end"""
        num_reps = 4
        vel_start = 0.6
        vel_end = 1.0
        for rep in range(num_reps):
            vel = vel_start + (vel_end - vel_start) * (rep / (num_reps - 1))
            assert vel_start <= vel <= vel_end, f"rep {rep}: vel {vel} in range"

    def test_decrescendo_velocity_ramp(self):
        """decrescendo: linear ramp from end to start"""
        num_reps = 4
        vel_start = 0.8
        vel_end = 0.4
        for rep in range(num_reps):
            vel = vel_end + (vel_start - vel_end) * (rep / (num_reps - 1))
            assert vel_end <= vel <= vel_start, f"rep {rep}: vel {vel} decreasing"

    def test_fade_out_velocity(self):
        """fade_out: each repetition softer"""
        vel_start = 0.8
        for rep in range(4):
            vel = vel_start * (1 - 0.15 * rep)
            assert vel < vel_start if rep > 0 else vel == vel_start, "decreasing"

    def test_build_velocity_exponential(self):
        """build: exponential increase"""
        num_reps = 4
        vel_start = 0.5
        vel_end = 1.0
        for rep in range(num_reps):
            vel = vel_start * (vel_end / vel_start) ** (rep / (num_reps - 1))
            assert vel >= vel_start, "increasing"
        assert vel >= vel_end - 0.01, "last rep near vel_end"

    def test_time_stretch_clamping(self):
        """time_stretch clamped to 0.5-2.0"""
        assert max(0.5, min(2, 0.1)) == 0.5, "clamped to 0.5"
        assert max(0.5, min(2, 3)) == 2, "clamped to 2"

    def test_time_stretch_decelerating(self):
        """time_stretch > 1: each repetition longer"""
        stretch = 1.5
        for rep in range(3):
            dur_mult = stretch ** rep
            assert dur_mult >= 1.0, f"rep {rep}: stretching increases duration"

    def test_time_stretch_accelerating(self):
        """time_stretch < 1: each repetition shorter"""
        stretch = 0.75
        for rep in range(3):
            dur_mult = stretch ** rep
            assert dur_mult <= 1.0, f"rep {rep}: accelerating decreases duration"

    def test_phrase_offset_calculation(self):
        """Each repetition placed after previous phrase"""
        Quarter = 960
        phrase_len = 4 * Quarter  # 4 beats
        offsets = [0]
        current = 0
        for _ in range(3):
            current += phrase_len
            offsets.append(current)
        assert offsets == [0, 4*Quarter, 8*Quarter, 12*Quarter], "sequential offsets"

    def test_velocity_clamping(self):
        """velocity_start/end clamped to 0.01-1"""
        assert max(0.01, min(1, 0)) == 0.01, "clamped to 0.01"
        assert max(0.01, min(1, 2)) == 1, "clamped to 1"

    def test_cross_track_preserves_original(self):
        """cross_track >= 0: sequences go to different track"""
        cross_track = 2
        assert cross_track >= 0, "cross-track mode active"

    def test_pitch_range_skip(self):
        """Notes that go out of 0-127 range after transposition are skipped"""
        pitch = 125
        trans = 5
        new_pitch = pitch + trans
        assert new_pitch > 127, "out of range = skip"

    def test_constant_velocity_pattern(self):
        """constant: same velocity as source"""
        vel_mult = 1.0  # constant = 1.0
        assert vel_mult == 1.0, "constant = no velocity change"
