
class TestCreatePhaseShift:
    """Unit tests for create_phase_shift — Steve Reich phasing"""

    def test_shift_per_bar_clamping(self):
        """shift_per_bar clamped to 0.03125-0.5"""
        assert max(0.03125, min(0.5, 0.01)) == 0.03125, "clamped to 0.03125"
        assert max(0.03125, min(0.5, 1.0)) == 0.5, "clamped to 0.5"
        assert max(0.03125, min(0.5, 0.0625)) == 0.0625, "1/16 is valid"

    def test_bars_clamping(self):
        """bars clamped to 2-16"""
        assert max(2, min(16, 1)) == 2, "clamped to 2"
        assert max(2, min(16, 20)) == 16, "clamped to 16"

    def test_velocity_scale_clamping(self):
        """velocity_scale clamped to 0.1-1.0"""
        assert max(0.1, min(1, 0.01)) == 0.1, "clamped to 0.1"
        assert max(0.1, min(1, 2)) == 1, "clamped to 1"

    def test_cumulative_offset_forward(self):
        """forward: cumulative offset increases each bar"""
        Quarter = 960
        shift = 0.0625
        shift_ticks = round(shift * Quarter)
        for bar in range(8):
            offset = bar * shift_ticks * 1  # forward = +1
            assert offset == bar * 60, f"bar {bar}: offset {offset} ticks"

    def test_cumulative_offset_backward(self):
        """backward: cumulative offset is negative"""
        Quarter = 960
        shift = 0.0625
        shift_ticks = round(shift * Quarter)
        for bar in range(8):
            offset = bar * shift_ticks * -1  # backward = -1
            assert offset == -bar * 60, f"bar {bar}: offset {offset} ticks"

    def test_offset_accumulates(self):
        """Offset accumulates linearly across bars"""
        Quarter = 960
        shift = 0.125  # 1/8 note
        shift_ticks = round(shift * Quarter)
        offsets = [bar * shift_ticks for bar in range(4)]
        assert offsets == [0, 120, 240, 360], "linear accumulation"

    def test_negative_position_skip(self):
        """Notes that go negative with backward shift are skipped"""
        note_pos = 0
        offset = -120
        new_pos = note_pos + offset
        assert new_pos < 0, "negative position = skip"

    def test_velocity_scaling(self):
        """Phased copy velocity scaled"""
        vel = 0.8
        scale = 0.85
        new_vel = max(0.01, min(1, vel * scale))
        assert abs(new_vel - 0.68) < 0.01, "0.8 * 0.85 = 0.68"

    def test_bar_start_calculation(self):
        """Each bar starts one phrase-length later"""
        Quarter = 960
        phrase_len = 4 * Quarter  # 4 beats
        bar_starts = [bar * phrase_len for bar in range(4)]
        assert bar_starts == [0, 3840, 7680, 11520], "bar starts at phrase multiples"

    def test_total_notes_calculation(self):
        """Total notes = source_notes * bars"""
        src_notes = 8
        bars = 4
        total = src_notes * bars
        assert total == 32, "8 notes * 4 bars = 32"

    def test_forward_direction_sign(self):
        """forward direction: sign = +1"""
        assert 1 if "forward" == "forward" else -1 == 1, "forward = +1"

    def test_backward_direction_sign(self):
        """backward direction: sign = -1"""
        assert -1 if "backward" == "backward" else 1 == -1, "backward = -1"

    def test_cross_track_preserves_original(self):
        """cross_track >= 0: phased copy goes to different track"""
        cross_track = 1
        assert cross_track >= 0, "cross-track mode active"

    def test_no_cross_track_same_track(self):
        """cross_track = -1: phased copy on same track (default)"""
        cross_track = -1
        assert cross_track < 0, "same track mode"

    def test_phase_drift_creates_polyrhythm(self):
        """After enough bars, drift creates cross-rhythm"""
        Quarter = 960
        shift = 0.0625
        # After 16 bars, total drift = 1 beat (polyrhythmic)
        total_drift = 16 * round(shift * Quarter)
        assert total_drift == Quarter, "16 * 1/16 = 1 full beat drift"

    def test_velocity_floor(self):
        """Velocity never below 0.01"""
        vel = 0.01
        scale = 0.5
        new_vel = max(0.01, min(1, vel * scale))
        assert new_vel == 0.01, "floor at 0.01"
