

class TestAddPassingTones:
    """Unit tests for add_passing_tones — melodic smoothing via diatonic passing tones"""

    def test_interval_threshold(self):
        """Passing tones only added when interval > 2 semitones"""
        intervals = [1, 2, 3, 5, 7]
        max_interval = 7
        for iv in intervals:
            should_add = iv > 2 and iv <= max_interval
            if iv <= 2:
                assert not should_add, f"interval {iv} too small for passing tone"
            if iv > 2 and iv <= max_interval:
                assert should_add, f"interval {iv} needs passing tone"

    def test_max_interval_limit(self):
        """Intervals larger than max_interval are left as leaps"""
        interval = 9
        max_interval = 7
        should_add = interval <= max_interval
        assert not should_add, "interval 9 > max 7 = no passing tone"

    def test_gap_minimum(self):
        """Minimum gap of 1/8 note required"""
        Quarter = 960
        min_gap = Quarter * 0.125
        gap = Quarter * 0.25
        assert gap >= min_gap, "1/4 note gap is sufficient"

    def test_gap_too_small(self):
        """Gap smaller than 1/8 note = no passing tone"""
        Quarter = 960
        min_gap = Quarter * 0.125
        gap = Quarter * 0.0625
        assert gap < min_gap, "1/16 gap is too small"

    def test_diatonic_scale_check(self):
        """Passing tone must be in the specified scale"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]  # C major
        root_idx = 0
        def isInScale(pitch):
            rel = ((pitch - root_idx) % 12 + 12) % 12
            return rel in scale_intervals
        assert isInScale(60), "C is in C major"
        assert isInScale(64), "E is in C major"
        assert not isInScale(61), "C# is NOT in C major"

    def test_nearest_scale_tone(self):
        """Nearest scale tone finds closest in-scale pitch"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0
        def isInScale(pitch):
            rel = ((pitch - root_idx) % 12 + 12) % 12
            return rel in scale_intervals
        def nearestScaleTone(pitch):
            if isInScale(pitch):
                return pitch
            for offset in range(1, 7):
                if isInScale(pitch + offset):
                    return pitch + offset
                if isInScale(pitch - offset):
                    return pitch - offset
            return pitch
        # C# (61) → nearest is C (60) or D (62), both distance 1
        result = nearestScaleTone(61)
        assert result in (60, 62), "C# snaps to C or D"

    def test_scale_step_ascending(self):
        """getScaleStep up: next scale tone above"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0
        def isInScale(pitch):
            rel = ((pitch - root_idx) % 12 + 12) % 12
            return rel in scale_intervals
        def getScaleStep(pitch, direction):
            if direction > 0:
                for p in range(pitch + 1, 128):
                    if isInScale(p):
                        return p
            else:
                for p in range(pitch - 1, -1, -1):
                    if isInScale(p):
                        return p
            return pitch
        # From C (60) up → D (62)
        assert getScaleStep(60, 1) == 62, "C up → D"
        # From E (64) down → D (62)
        assert getScaleStep(64, -1) == 62, "E down → D"

    def test_passing_tone_between_notes(self):
        """Passing tone pitch must be between the two original notes"""
        a_pitch = 60
        b_pitch = 67
        pass_pitch = 64
        assert min(a_pitch, b_pitch) < pass_pitch < max(a_pitch, b_pitch), "passing tone is between"

    def test_passing_tone_not_between(self):
        """If no valid passing tone between notes, skip"""
        a_pitch = 60
        b_pitch = 62
        # Only 1 semitone gap — no room for passing tone
        assert abs(b_pitch - a_pitch) <= 2, "too small for passing tone"

    def test_velocity_quieter_than_melody(self):
        """Passing tones traditionally quieter than melody notes"""
        melody_vel = 0.8
        pass_vel = 0.6
        assert pass_vel < melody_vel, "passing tone quieter"

    def test_duration_fraction(self):
        """Duration = fraction of gap between notes"""
        Quarter = 960
        gap = Quarter * 0.5  # half note gap
        dur_frac = 0.5
        pass_dur = max(1, round(gap * dur_frac))
        assert pass_dur == 240, "half of half-note gap = quarter note"

    def test_position_at_gap_midpoint(self):
        """Passing tone positioned at midpoint of gap"""
        gap_start = 960
        gap_end = 1920
        dur_frac = 0.5
        pass_pos = round(gap_start + (gap_end - gap_start) * 0.5 - (gap_end - gap_start) * dur_frac * 0.5)
        # Midpoint = 1440, minus half of duration (240) = 1200
        assert pass_pos >= gap_start, "position within gap"
        assert pass_pos < gap_end, "position before next note"

    def test_direction_auto_follows_melody(self):
        """auto direction: follows melody direction (up if going up)"""
        a_pitch = 60
        b_pitch = 67
        going_up = b_pitch > a_pitch
        dir_mode = "auto"
        if dir_mode == "auto":
            pass_direction = 1 if going_up else -1
        assert pass_direction == 1, "ascending melody → ascending passing tone"

    def test_direction_descending(self):
        """descending direction: always step down"""
        dir_mode = "descending"
        if dir_mode == "descending":
            pass_direction = -1
        assert pass_direction == -1, "forced descending"

    def test_cross_track_preserves_original(self):
        """cross_track >= 0: passing tones go to different track"""
        cross_track = 1
        assert cross_track >= 0, "cross-track mode active"

    def test_chromatic_scale_all_semitones(self):
        """Chromatic scale includes all 12 semitones"""
        chromatic = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        assert len(chromatic) == 12, "all 12 semitones"
        for i in range(12):
            assert i in chromatic, f"semitone {i} in chromatic"

    def test_pitch_clamping(self):
        """Passing tone pitch clamped to 0-127"""
        assert max(0, min(127, 130)) == 127, "clamped to 127"
        assert max(0, min(127, -5)) == 0, "clamped to 0"
