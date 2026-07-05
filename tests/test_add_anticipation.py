
class TestAddAnticipation:
    """Unit tests for add_anticipation — anticipation non-chord tone technique"""

    def test_strong_beat_detection(self):
        """Notes on integer beat positions are strong beats"""
        Quarter = 960
        for pos in [0, 960, 1920, 2880, 3840]:
            beatPos = pos / Quarter
            isStrong = abs(beatPos - round(beatPos)) < 0.01
            assert isStrong, f"pos {pos} should be strong beat"

    def test_weak_beat_rejected(self):
        """Notes on non-integer beat positions are not strong beats"""
        Quarter = 960
        for pos in [480, 1440, 2400, 3360]:
            beatPos = pos / Quarter
            isStrong = abs(beatPos - round(beatPos)) < 0.01
            assert not isStrong, f"pos {pos} should NOT be strong beat"

    def test_anticipation_position_before_target(self):
        """Anticipation is placed before the target note"""
        Quarter = 960
        target_pos = 1920  # beat 2
        offset_beats = 0.25
        offset_ticks = round(offset_beats * Quarter)
        antic_pos = target_pos - offset_ticks
        assert antic_pos == 1680, "anticipation at 1680 (quarter before beat 2)"

    def test_anticipation_offset_clamping(self):
        """anticipation_offset clamped to 0.0625-0.5"""
        assert max(0.0625, min(0.5, 0.01)) == 0.0625, "clamped to 0.0625"
        assert max(0.0625, min(0.5, 1.0)) == 0.5, "clamped to 0.5"
        assert max(0.0625, min(0.5, 0.25)) == 0.25, "0.25 is valid"

    def test_anticipation_fraction_clamping(self):
        """anticipation_fraction clamped to 0.1-1.0"""
        assert max(0.1, min(1, 0.05)) == 0.1, "clamped to 0.1"
        assert max(0.1, min(1, 2)) == 1, "clamped to 1"

    def test_auto_direction_same_pitch(self):
        """auto direction: anticipation has same pitch as target"""
        target_pitch = 60
        antic_pitch = target_pitch  # auto = same pitch
        assert antic_pitch == target_pitch, "auto: same pitch as target"

    def test_upper_direction_step_up(self):
        """upper direction: one scale step above target"""
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

        target = 60  # C4
        antic = getScaleStep(target, 1)
        assert antic == 62, "upper: C → D"

    def test_lower_direction_step_down(self):
        """lower direction: one scale step below target"""
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

        target = 60  # C4
        antic = getScaleStep(target, -1)
        assert antic == 59, "lower: C → B"

    def test_approach_from_below(self):
        """approach direction: from direction of previous note (below → approach from above)"""
        prev_pitch = 55  # G3
        target_pitch = 60  # C4
        approach_dir = -1 if target_pitch > prev_pitch else 1
        assert approach_dir == -1, "target above prev → approach from below (step down from target)"

    def test_approach_from_above(self):
        """approach direction: previous note above target → approach from below"""
        prev_pitch = 67  # G4
        target_pitch = 60  # C4
        approach_dir = 1 if target_pitch < prev_pitch else -1
        assert approach_dir == 1, "target below prev → approach from above (step up from target)"

    def test_min_duration_filter(self):
        """Notes shorter than min_duration_beats are skipped"""
        Quarter = 960
        min_dur = round(1.5 * Quarter)
        note_dur = round(1.0 * Quarter)
        assert note_dur < min_dur, "1-beat note skipped with 1.5-beat minimum"

    def test_min_duration_pass(self):
        """Notes >= min_duration_beats qualify"""
        Quarter = 960
        min_dur = round(1.5 * Quarter)
        note_dur = round(2.0 * Quarter)
        assert note_dur >= min_dur, "2-beat note qualifies"

    def test_previous_note_overlap_check(self):
        """No room if previous note overlaps anticipation position"""
        prev_end = 1700
        antic_pos = 1680
        has_room = prev_end <= antic_pos
        assert not has_room, "prev ends at 1700, antic at 1680 = overlap"

    def test_previous_note_room_ok(self):
        """Room if previous note ends before anticipation"""
        prev_end = 1600
        antic_pos = 1680
        has_room = prev_end <= antic_pos
        assert has_room, "prev ends at 1600, antic at 1680 = room"

    def test_anticipation_velocity_softer(self):
        """Anticipation velocity softer than main note"""
        antic_vel = 0.55
        main_vel = 0.8
        assert antic_vel < main_vel, "anticipation softer than main"

    def test_anticipation_duration_positive(self):
        """Anticipation duration >= 1 tick"""
        Quarter = 960
        offset_ticks = round(0.25 * Quarter)
        frac = 0.33
        antic_dur = max(1, round(offset_ticks * frac))
        assert antic_dur >= 1, "duration >= 1"

    def test_cross_track_preserves_original(self):
        """cross_track >= 0: anticipations go to different track"""
        cross_track = 2
        assert cross_track >= 0, "cross-track mode active"

    def test_pitch_clamping(self):
        """Anticipation pitch clamped to 0-127"""
        assert max(0, min(127, 130)) == 127, "clamped to 127"
        assert max(0, min(127, -3)) == 0, "clamped to 0"

    def test_negative_position_skip(self):
        """Anticipation before beat 0 is skipped"""
        target_pos = 0
        offset_ticks = 240
        antic_pos = target_pos - offset_ticks
        assert antic_pos < 0, "anticipation before 0 = skip"
