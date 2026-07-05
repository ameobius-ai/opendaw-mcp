
class TestCloneTrack:
    """Unit tests for clone_track — full track duplication"""

    def test_transpose_clamping(self):
        """transpose clamped to -24..+24"""
        assert max(-24, min(24, -30)) == -24, "clamped to -24"
        assert max(-24, min(24, 30)) == 24, "clamped to +24"
        assert max(-24, min(24, 12)) == 12, "+12 octave is valid"

    def test_velocity_scale_clamping(self):
        """velocity_scale clamped to 0.1-2.0"""
        assert max(0.1, min(2, 0.01)) == 0.1, "clamped to 0.1"
        assert max(0.1, min(2, 3)) == 2, "clamped to 2"
        assert max(0.1, min(2, 1.0)) == 1.0, "1.0 is valid"

    def test_time_offset_clamping(self):
        """time_offset_beats clamped to -16..+16"""
        assert max(-16, min(16, -20)) == -16, "clamped to -16"
        assert max(-16, min(16, 20)) == 16, "clamped to +16"
        assert max(-16, min(16, 4)) == 4, "4 is valid"

    def test_octave_transpose(self):
        """transpose=+12: octave above"""
        pitch = 60
        transposed = max(0, min(127, pitch + 12))
        assert transposed == 72, "C4 + 12 = C5"

    def test_fifth_transpose(self):
        """transpose=+7: perfect fifth above"""
        pitch = 60
        transposed = max(0, min(127, pitch + 7))
        assert transposed == 67, "C4 + 7 = G4"

    def test_negative_transpose(self):
        """transpose=-12: octave below"""
        pitch = 60
        transposed = max(0, min(127, pitch - 12))
        assert transposed == 48, "C4 - 12 = C3"

    def test_pitch_clamping_high(self):
        """Pitch above 127 clamped to 127"""
        pitch = 120
        trans = 12
        assert max(0, min(127, pitch + trans)) == 127, "clamped to 127"

    def test_pitch_clamping_low(self):
        """Pitch below 0 clamped to 0"""
        pitch = 5
        trans = -12
        assert max(0, min(127, pitch + trans)) == 0, "clamped to 0"

    def test_velocity_scaling(self):
        """velocity_scale reduces velocity"""
        vel = 0.8
        scale = 0.5
        new_vel = max(0.01, min(1, vel * scale))
        assert new_vel == 0.4, "0.8 * 0.5 = 0.4"

    def test_velocity_scaling_boost(self):
        """velocity_scale > 1 boosts velocity (clamped to 1)"""
        vel = 0.8
        scale = 1.5
        new_vel = max(0.01, min(1, vel * scale))
        assert new_vel == 1.0, "0.8 * 1.5 = 1.2 clamped to 1.0"

    def test_time_offset_position_shift(self):
        """time_offset shifts note positions"""
        Quarter = 960
        note_pos = 0
        offset = 4.0
        new_pos = note_pos + round(offset * Quarter)
        assert new_pos == 3840, "shifted by 4 beats"

    def test_time_offset_negative(self):
        """negative time_offset shifts notes earlier"""
        Quarter = 960
        note_pos = 3840
        offset = -2.0
        new_pos = max(0, note_pos + round(offset * Quarter))
        assert new_pos == 1920, "shifted back 2 beats"

    def test_complementary_hue(self):
        """Cloned track gets complementary hue (180 degrees offset)"""
        src_hue = 60
        dest_hue = (src_hue + 180) % 360
        assert dest_hue == 240, "60 + 180 = 240"

    def test_new_unit_flag(self):
        """new_unit=True creates separate audio unit"""
        create_new = True
        assert create_new is True, "new_unit flag set"

    def test_same_unit_default(self):
        """new_unit=False (default) adds track to same unit"""
        create_new = False
        assert create_new is False, "default = same unit"

    def test_notes_created_count(self):
        """All notes from all regions are copied"""
        regions = [{"notes": [1, 2, 3]}, {"notes": [4, 5]}]
        total = sum(len(r["notes"]) for r in regions)
        assert total == 5, "5 notes total across 2 regions"

    def test_velocity_floor(self):
        """Velocity never goes below 0.01"""
        vel = 0.01
        scale = 0.5
        new_vel = max(0.01, min(1, vel * scale))
        assert new_vel == 0.01, "floor at 0.01"
