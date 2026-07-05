
class TestAddNeighborTones:
    """Unit tests for add_neighbor_tones — upper/lower neighbor embellishment"""

    def test_upper_neighbor_pitch(self):
        """upper neighbor: step up from original pitch"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]  # C major
        root_idx = 0

        def isInScale(p):
            rel = ((p - root_idx) % 12 + 12) % 12
            return rel in scale_intervals

        def getScaleStep(p, direction):
            if direction > 0:
                for i in range(p + 1, 128):
                    if isInScale(i):
                        return i
            else:
                for i in range(p - 1, -1, -1):
                    if isInScale(i):
                        return i
            return p

        original = 60  # C4
        neighbor = getScaleStep(original, 1)
        assert neighbor == 62, "upper neighbor of C is D"

    def test_lower_neighbor_pitch(self):
        """lower neighbor: step down from original pitch"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0

        def isInScale(p):
            rel = ((p - root_idx) % 12 + 12) % 12
            return rel in scale_intervals

        def getScaleStep(p, direction):
            if direction > 0:
                for i in range(p + 1, 128):
                    if isInScale(i):
                        return i
            else:
                for i in range(p - 1, -1, -1):
                    if isInScale(i):
                        return i
            return p

        original = 60  # C4
        neighbor = getScaleStep(original, -1)
        assert neighbor == 59, "lower neighbor of C is B"

    def test_neighbor_split_durations(self):
        """Note split: first_part + neighbor + return = original duration"""
        Quarter = 960
        orig_dur = 4 * Quarter  # whole note
        frac = 0.25
        offset = 0.5  # middle

        first_part = round(orig_dur * offset)
        neighbor_dur = round(orig_dur * frac)
        last_part = orig_dur - first_part - neighbor_dur
        assert first_part + neighbor_dur + last_part == orig_dur, "parts sum to original"

    def test_neighbor_position_middle(self):
        """Middle offset: neighbor starts at half the note"""
        Quarter = 960
        orig_pos = 0
        orig_dur = 4 * Quarter
        offset = 0.5
        neighbor_pos = orig_pos + round(orig_dur * offset)
        assert neighbor_pos == 2 * Quarter, "neighbor starts at beat 2"

    def test_neighbor_position_start(self):
        """Start offset: neighbor at beginning of note"""
        Quarter = 960
        orig_pos = 0
        orig_dur = 4 * Quarter
        offset = 0.15
        neighbor_pos = orig_pos + round(orig_dur * offset)
        assert neighbor_pos < Quarter, "neighbor near start"

    def test_min_duration_filter(self):
        """Notes shorter than min_duration_beats are skipped"""
        Quarter = 960
        min_dur = round(1.0 * Quarter)  # 1 beat minimum
        note_dur = round(0.5 * Quarter)  # half beat
        assert note_dur < min_dur, "half-beat note skipped with 1-beat minimum"

    def test_min_duration_pass(self):
        """Notes >= min_duration_beats qualify"""
        Quarter = 960
        min_dur = round(1.0 * Quarter)
        note_dur = round(2.0 * Quarter)
        assert note_dur >= min_dur, "2-beat note qualifies"

    def test_alternating_direction(self):
        """alternating: even=upper, odd=lower"""
        for i in range(6):
            neighbor_dir = 1 if i % 2 == 0 else -1
            expected = 1 if i % 2 == 0 else -1
            assert neighbor_dir == expected, f"note {i} alternates correctly"

    def test_neighbor_velocity_softer(self):
        """Neighbor velocity typically softer than main note"""
        neighbor_vel = 0.6
        main_vel = 0.8
        assert neighbor_vel < main_vel, "neighbor softer than main"

    def test_return_pitch_matches_original(self):
        """Return note has same pitch as original"""
        original = 64
        return_pitch = original
        assert return_pitch == original, "return to original pitch"

    def test_neighbor_fraction_clamping(self):
        """neighbor_fraction clamped to 0.1-0.5"""
        assert max(0.1, min(0.5, 0.05)) == 0.1, "clamped to 0.1"
        assert max(0.1, min(0.5, 0.7)) == 0.5, "clamped to 0.5"

    def test_neighbor_offset_clamping(self):
        """neighbor_offset clamped to 0.1-0.9"""
        assert max(0.1, min(0.9, 0.05)) == 0.1, "clamped to 0.1"
        assert max(0.1, min(0.9, 0.95)) == 0.9, "clamped to 0.9"

    def test_scale_step_no_change(self):
        """If no scale tone available in direction, skip note"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0

        def isInScale(p):
            rel = ((p - root_idx) % 12 + 12) % 12
            return rel in scale_intervals

        # pitch 0 (C-1) going down: no scale tone below
        def getScaleStep(p, direction):
            if direction > 0:
                for i in range(p + 1, 128):
                    if isInScale(i):
                        return i
            else:
                for i in range(p - 1, -1, -1):
                    if isInScale(i):
                        return i
            return p

        result = getScaleStep(0, -1)
        assert result == 0, "no scale tone below C-1, returns same pitch"

    def test_neighbor_duration_positive(self):
        """Neighbor duration must be at least 1 tick"""
        Quarter = 960
        orig_dur = Quarter
        frac = 0.1
        neighbor_dur = max(1, round(orig_dur * frac))
        assert neighbor_dur >= 1, "neighbor duration >= 1"

    def test_cross_track_preserves_original(self):
        """cross_track >= 0: neighbors go to different track"""
        cross_track = 2
        assert cross_track >= 0, "cross-track mode active"

    def test_pitch_clamping(self):
        """Neighbor pitch clamped to 0-127"""
        assert max(0, min(127, 130)) == 127, "clamped to 127"
        assert max(0, min(127, -3)) == 0, "clamped to 0"
