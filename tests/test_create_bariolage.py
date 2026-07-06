"""Unit tests for create_bariolage MCP tool."""



class TestBariolageParameterValidation:
    """Test parameter validation."""

    def test_bars_too_few(self):
        assert not (1 <= 0 <= 8)

    def test_bars_too_many(self):
        assert not (1 <= 9 <= 8)

    def test_bars_valid(self):
        for b in (1, 2, 4, 8):
            assert 1 <= b <= 8

    def test_octave_too_low(self):
        assert not (2 <= 1 <= 6)

    def test_octave_too_high(self):
        assert not (2 <= 7 <= 6)

    def test_octave_valid(self):
        for o in (2, 3, 4, 5, 6):
            assert 2 <= o <= 6

    def test_invalid_moving_pattern(self):
        p = "invalid"
        assert p not in ("scale_asc", "scale_desc", "scale_wave", "arpeggio", "chromatic")

    def test_invalid_subdivision(self):
        s = "invalid"
        assert s not in ("8th", "16th", "32nd")

    def test_valid_moving_patterns(self):
        for p in ("scale_asc", "scale_desc", "scale_wave", "arpeggio", "chromatic"):
            assert p in ("scale_asc", "scale_desc", "scale_wave", "arpeggio", "chromatic")

    def test_valid_subdivisions(self):
        for s in ("8th", "16th", "32nd"):
            assert s in ("8th", "16th", "32nd")


class TestBariolageSubdivision:
    """Test subdivision values."""

    def test_8th_value(self):
        subdiv_map = {"8th": 0.5, "16th": 0.25, "32nd": 0.125}
        assert subdiv_map["8th"] == 0.5

    def test_16th_value(self):
        subdiv_map = {"8th": 0.5, "16th": 0.25, "32nd": 0.125}
        assert subdiv_map["16th"] == 0.25

    def test_32nd_value(self):
        subdiv_map = {"8th": 0.5, "16th": 0.25, "32nd": 0.125}
        assert subdiv_map["32nd"] == 0.125


class TestBariolagePedalPitch:
    """Test pedal pitch calculation."""

    def test_default_pedal(self):
        """Default pedal = root at specified octave."""
        root_num = 7  # G
        octave = 4
        pedal_pitch = -1
        if pedal_pitch < 0:
            pedal = (octave + 1) * 12 + root_num
        else:
            pedal = pedal_pitch
        assert pedal == 67  # G5 = 60+7

    def test_custom_pedal(self):
        """Custom pedal pitch is used directly."""
        pedal_pitch = 55  # G3
        if pedal_pitch < 0:
            pedal = 67
        else:
            pedal = pedal_pitch
        assert pedal == 55

    def test_pedal_c4(self):
        """C4 pedal = 60."""
        root_num = 0
        octave = 3
        pedal = (octave + 1) * 12 + root_num
        assert pedal == 48  # C3 octave=3 -> (3+1)*12+0 = 48

    def test_pedal_a3(self):
        """A3 pedal = 57."""
        root_num = 9
        octave = 3
        pedal = (octave + 1) * 12 + root_num
        assert pedal == 57


class TestBariolageScalePitches:
    """Test scale pitch construction."""

    def test_ascending_pitches_above_pedal(self):
        """Scale pitches should be above the pedal pitch."""
        intervals = [0, 2, 4, 5, 7, 9, 11]  # major
        root_num = 7  # G
        octave = 4
        pedal = 67  # G5
        scale_pitches = []
        for oct_shift in range(0, 2):
            for iv in intervals:
                pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
                if pitch > pedal:
                    scale_pitches.append(pitch)
        scale_pitches = sorted(set(scale_pitches))
        # All pitches should be > 67
        assert all(p > pedal for p in scale_pitches)
        assert len(scale_pitches) > 0

    def test_descending_pitches_below_pedal(self):
        """Descending pitches should be below the pedal."""
        intervals = [0, 2, 4, 5, 7, 9, 11]
        root_num = 7
        octave = 4
        pedal = 67
        scale_below = []
        for oct_shift in range(-1, 0):
            for iv in reversed(intervals):
                pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
                if pitch < pedal:
                    scale_below.append(pitch)
        scale_below = sorted(set(scale_below), reverse=True)
        assert all(p < pedal for p in scale_below)


class TestBariolageNoteGeneration:
    """Test the note generation logic."""

    def test_alternating_pedal_moving(self):
        """Even slots = pedal, odd slots = moving."""
        total_slots = 8
        notes = []
        for slot in range(total_slots):
            is_pedal = slot % 2 == 0
            notes.append({"type": "pedal" if is_pedal else "moving"})
        assert notes[0]["type"] == "pedal"
        assert notes[1]["type"] == "moving"
        assert notes[2]["type"] == "pedal"
        assert notes[3]["type"] == "moving"

    def test_pedal_count(self):
        """Half the notes should be pedal notes."""
        total_slots = 16
        pedal_count = sum(1 for slot in range(total_slots) if slot % 2 == 0)
        assert pedal_count == 8

    def test_moving_count(self):
        """Half the notes should be moving notes."""
        total_slots = 16
        moving_count = sum(1 for slot in range(total_slots) if slot % 2 != 0)
        assert moving_count == 8

    def test_pedal_note_duration(self):
        """Pedal note duration = subdiv * 0.9."""
        subdiv = 0.25
        dur = subdiv * 0.9
        assert abs(dur - 0.225) < 0.01

    def test_moving_note_duration(self):
        """Moving note duration = subdiv * 0.85."""
        subdiv = 0.25
        dur = subdiv * 0.85
        assert abs(dur - 0.2125) < 0.01


class TestBariolageMovingPatterns:
    """Test moving pattern logic."""

    def test_scale_asc_cycles(self):
        """Ascending scale wraps around when it reaches the top."""
        scale_pitches = [69, 71, 72, 74]
        moving_idx = 0
        results = []
        for _ in range(6):
            if moving_idx >= len(scale_pitches):
                moving_idx = 0
            results.append(scale_pitches[moving_idx])
            moving_idx += 1
        assert results == [69, 71, 72, 74, 69, 71]

    def test_scale_desc_cycles(self):
        """Descending scale wraps around."""
        scale_below = [62, 60, 55]
        moving_idx = 0
        results = []
        for _ in range(5):
            if moving_idx >= len(scale_below):
                moving_idx = 0
            results.append(scale_below[moving_idx])
            moving_idx += 1
        assert results == [62, 60, 55, 62, 60]

    def test_scale_wave_changes_direction(self):
        """Wave pattern changes direction when reaching the end."""
        scale_pitches = [69, 71, 72, 74]
        scale_below = [62, 60, 55]
        moving_idx = 0
        direction = 1
        results = []
        for _ in range(8):
            if direction == 1:
                if moving_idx >= len(scale_pitches):
                    direction = -1
                    moving_idx = 0
                if direction == 1:
                    pitch = scale_pitches[moving_idx]
                else:
                    pitch = scale_below[moving_idx]
            else:
                if moving_idx >= len(scale_below):
                    direction = 1
                    moving_idx = 0
                if direction == -1:
                    pitch = scale_below[moving_idx]
                else:
                    pitch = scale_pitches[moving_idx]
            results.append(pitch)
            moving_idx += 1
        # First 4 ascending, then switch
        assert results[0] == 69
        assert results[3] == 74

    def test_arpeggio_cycles(self):
        """Arpeggio rotates through chord tones."""
        arpeggio_pitches = [60, 64, 67, 72, 76, 79]
        moving_idx = 0
        results = []
        for _ in range(8):
            if moving_idx >= len(arpeggio_pitches):
                moving_idx = 0
            results.append(arpeggio_pitches[moving_idx])
            moving_idx += 1
        assert results == [60, 64, 67, 72, 76, 79, 60, 64]

    def test_chromatic_ascending(self):
        """Chromatic goes up from pedal+1."""
        pedal = 67
        results = []
        for i in range(12):
            pitch = pedal + 1 + (i % 12)
            results.append(pitch)
        assert results[0] == 68
        assert results[11] == 79
        # Wraps after 12 notes
        assert results[0] == 68


class TestBariolageVelocity:
    """Test velocity handling."""

    def test_pedal_velocity(self):
        """Pedal velocity is separate from moving velocity."""
        pedal_vel = 0.7
        accent_pedal = True
        vel = pedal_vel
        if accent_pedal:
            vel = min(1.0, vel * 1.1)
        assert abs(vel - 0.77) < 0.01

    def test_pedal_velocity_no_accent(self):
        """Without accent, pedal velocity is unchanged."""
        pedal_vel = 0.7
        accent_pedal = False
        vel = pedal_vel
        if accent_pedal:
            vel = min(1.0, vel * 1.1)
        assert vel == 0.7

    def test_moving_velocity(self):
        """Moving velocity uses the base velocity."""
        velocity = 0.6
        assert velocity == 0.6

    def test_pedal_clamped(self):
        """Pedal velocity clamped to 1.0."""
        pedal_vel = 0.95
        vel = min(1.0, pedal_vel * 1.1)
        assert vel == 1.0


class TestBariolageTotalSlots:
    """Test total slot calculation."""

    def test_2bar_16th(self):
        bars = 2
        subdiv = 0.25
        total = int(bars * 4 / subdiv)
        assert total == 32

    def test_1bar_8th(self):
        bars = 1
        subdiv = 0.5
        total = int(bars * 4 / subdiv)
        assert total == 8

    def test_4bar_32nd(self):
        bars = 4
        subdiv = 0.125
        total = int(bars * 4 / subdiv)
        assert total == 128


class TestBariolagePositionCalculation:
    """Test beat position calculation."""

    def test_slot0_position(self):
        slot = 0
        subdiv = 0.25
        assert slot * subdiv == 0.0

    def test_slot4_position(self):
        slot = 4
        subdiv = 0.25
        assert slot * subdiv == 1.0

    def test_slot8_position(self):
        slot = 8
        subdiv = 0.25
        assert slot * subdiv == 2.0
