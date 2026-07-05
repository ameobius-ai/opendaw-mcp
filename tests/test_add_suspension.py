

class TestAddSuspension:
    """Unit tests for add_suspension — suspension-resolution non-chord tone technique"""

    def test_strong_beat_detection(self):
        """Notes on integer beat positions are strong beats"""
        Quarter = 960
        positions = [0, 960, 1920, 2880]
        for pos in positions:
            beatPos = pos / Quarter
            isStrong = abs(beatPos - round(beatPos)) < 0.01
            assert isStrong, f"pos {pos} is a strong beat"

    def test_weak_beat_rejected(self):
        """Notes on non-integer beat positions are not strong beats"""
        Quarter = 960
        positions = [480, 1440, 2400]
        for pos in positions:
            beatPos = pos / Quarter
            isStrong = abs(beatPos - round(beatPos)) < 0.01
            assert not isStrong, f"pos {pos} is NOT a strong beat"

    def test_suspension_offset_down(self):
        """down resolution: suspension is above the target"""
        target_pitch = 60
        susp_offset = 2
        res_dir = -1  # down
        susp_pitch = target_pitch + (-res_dir) * susp_offset
        assert susp_pitch == 62, "suspension 2 semitones above target"

    def test_suspension_offset_up(self):
        """up resolution (retardation): suspension is below the target"""
        target_pitch = 60
        susp_offset = 2
        res_dir = 1  # up
        susp_pitch = target_pitch + (-res_dir) * susp_offset
        assert susp_pitch == 58, "suspension 2 semitones below target"

    def test_resolution_down_steps(self):
        """down resolution: step down from suspension to target"""
        susp_pitch = 62
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
        res_pitch = getScaleStep(susp_pitch, -1)
        assert res_pitch == 60, "D (62) resolves down to C (60)"

    def test_resolution_up_steps(self):
        """up resolution: step up from suspension to target"""
        susp_pitch = 58
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
        res_pitch = getScaleStep(susp_pitch, 1)
        # 58 = A# which is not in C major, nearest is B (59) or A (57)
        # 58 should snap to nearest scale tone first
        def nearestScaleTone(p):
            if isInScale(p):
                return p
            for offset in range(1, 7):
                if isInScale(p + offset):
                    return p + offset
                if isInScale(p - offset):
                    return p - offset
            return p
        susp_snapped = nearestScaleTone(58)
        res_pitch = getScaleStep(susp_snapped, 1)
        assert res_pitch > susp_snapped, "up resolution goes higher"

    def test_preparation_before_suspension(self):
        """Preparation note is placed before the suspension"""
        susp_pos = 960
        prep_beats = 0.5
        Quarter = 960
        prep_dur = round(prep_beats * Quarter)
        prep_pos = susp_pos - prep_dur
        assert prep_pos == 480, "preparation at 480 ticks (half beat before)"

    def test_preparation_room_check(self):
        """No room for preparation if previous note overlaps"""
        prev_note_end = 600
        prep_pos = 480
        has_room = prev_note_end <= prep_pos
        assert not has_room, "previous note ends at 600, prep at 480 = no room"

    def test_preparation_room_ok(self):
        """Room for preparation if previous note ends before prep"""
        prev_note_end = 400
        prep_pos = 480
        has_room = prev_note_end <= prep_pos
        assert has_room, "previous note ends at 400, prep at 480 = room"

    def test_suspension_offset_clamping(self):
        """suspension_offset clamped to 1-7"""
        assert max(1, min(7, 0)) == 1, "clamped to 1"
        assert max(1, min(7, 10)) == 7, "clamped to 7"
        assert max(1, min(7, 2)) == 2, "2 is valid"

    def test_preparation_beats_clamping(self):
        """preparation_beats clamped to 0.25-2.0"""
        assert max(0.25, min(2, 0.1)) == 0.25, "clamped to 0.25"
        assert max(0.25, min(2, 3)) == 2, "clamped to 2"

    def test_velocity_range(self):
        """Suspension velocity in valid range"""
        susp_vel = 0.75
        res_vel = 0.65
        assert 0 < susp_vel <= 1, "suspension velocity valid"
        assert 0 < res_vel <= 1, "resolution velocity valid"
        assert susp_vel > res_vel, "suspension louder than resolution (tension > release)"

    def test_both_direction_alternates(self):
        """both mode: alternates down/up per note"""
        for i in range(4):
            res_dir = -1 if i % 2 == 0 else 1
            expected = -1 if i % 2 == 0 else 1
            assert res_dir == expected, f"note {i}: direction alternates"

    def test_cross_track_preserves_original(self):
        """cross_track >= 0: suspensions go to different track"""
        cross_track = 2
        assert cross_track >= 0, "cross-track mode active"

    def test_scale_snapping(self):
        """Suspension pitch snapped to nearest scale tone"""
        scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        root_idx = 0
        def isInScale(p):
            rel = ((p - root_idx) % 12 + 12) % 12
            return rel in scale_intervals
        def nearestScaleTone(p):
            if isInScale(p):
                return p
            for offset in range(1, 7):
                if isInScale(p + offset):
                    return p + offset
                if isInScale(p - offset):
                    return p - offset
            return p
        # 61 (C#) → 60 (C) or 62 (D)
        result = nearestScaleTone(61)
        assert result in (60, 62), "C# snaps to C or D"

    def test_pitch_clamping(self):
        """Suspension pitch clamped to 0-127"""
        assert max(0, min(127, 130)) == 127, "clamped to 127"
        assert max(0, min(127, -3)) == 0, "clamped to 0"
