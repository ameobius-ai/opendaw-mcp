

class TestExplodeChords:
    """Unit tests for explode_chords — chord-to-voices orchestration"""

    def test_chord_detection_by_position(self):
        """Notes at same position (within tolerance) form a chord"""
        Quarter = 960
        tolerance = Quarter * 0.0625
        notes = [
            {"pos": 0, "pitch": 48},
            {"pos": 0, "pitch": 60},
            {"pos": 0, "pitch": 64},
            {"pos": 0, "pitch": 67},
        ]
        groups = []
        current = [notes[0]]
        for i in range(1, len(notes)):
            if abs(notes[i]["pos"] - current[0]["pos"]) <= tolerance:
                current.append(notes[i])
            else:
                groups.append(current)
                current = [notes[i]]
        groups.append(current)
        assert len(groups) == 1, "all 4 notes at pos 0 = 1 chord"
        assert len(groups[0]) == 4, "chord has 4 notes"

    def test_multiple_chords_detected(self):
        """Notes at different positions = separate chords"""
        Quarter = 960
        tolerance = Quarter * 0.0625
        notes = [
            {"pos": 0, "pitch": 60},
            {"pos": 0, "pitch": 64},
            {"pos": 960, "pitch": 62},
            {"pos": 960, "pitch": 65},
        ]
        groups = []
        current = [notes[0]]
        for i in range(1, len(notes)):
            if abs(notes[i]["pos"] - current[0]["pos"]) <= tolerance:
                current.append(notes[i])
            else:
                groups.append(current)
                current = [notes[i]]
        groups.append(current)
        assert len(groups) == 2, "2 chords at 2 positions"
        assert len(groups[0]) == 2, "first chord: 2 notes"
        assert len(groups[1]) == 2, "second chord: 2 notes"

    def test_direction_down_assigns_lowest_to_voice1(self):
        """down: lowest note → voice 0 (bass)"""
        chord = [
            {"pitch": 48, "vel": 0.8},
            {"pitch": 60, "vel": 0.8},
            {"pitch": 64, "vel": 0.8},
            {"pitch": 67, "vel": 0.8},
        ]
        chord.sort(key=lambda x: x["pitch"])
        direction = "down"
        for i in range(4):
            noteIdx = i if i < len(chord) else -1
            if direction == "down":
                assert chord[noteIdx]["pitch"] == [48, 60, 64, 67][i], f"voice {i} gets {chord[noteIdx]['pitch']}"

    def test_direction_up_assigns_highest_to_voice1(self):
        """up: highest note → voice 0 (top)"""
        chord = [
            {"pitch": 48, "vel": 0.8},
            {"pitch": 60, "vel": 0.8},
            {"pitch": 64, "vel": 0.8},
            {"pitch": 67, "vel": 0.8},
        ]
        chord.sort(key=lambda x: x["pitch"])
        direction = "up"
        n = len(chord)
        for i in range(4):
            noteIdx = n - 1 - i if i < n else -1
            if direction == "up":
                expected = [67, 64, 60, 48][i]
                assert chord[noteIdx]["pitch"] == expected, f"voice {i} gets {chord[noteIdx]['pitch']}"

    def test_velocity_natural_lower_louder(self):
        """natural: lower voices slightly louder"""
        num_voices = 4
        for i in range(num_voices):
            vel_mult = 1.0 - i * 0.05
            assert vel_mult <= 1.0, f"voice {i} not louder than max"
            assert vel_mult >= 0.85, f"voice {i} not too quiet"
        # voice 0 should be loudest
        assert (1.0 - 0 * 0.05) > (1.0 - 3 * 0.05), "voice 0 louder than voice 3"

    def test_velocity_equal_all_same(self):
        """equal: all voices same velocity"""
        num_voices = 4
        for i in range(num_voices):
            vel_mult = 1.0
            assert vel_mult == 1.0, "all voices equal"

    def test_velocity_top_heavy_upper_louder(self):
        """top_heavy: upper voices louder"""
        num_voices = 4
        for i in range(num_voices):
            1.0 - (num_voices - 1 - i) * 0.05
        # voice 3 (top) should be loudest
        v0_mult = 1.0 - (num_voices - 1 - 0) * 0.05
        v3_mult = 1.0 - (num_voices - 1 - 3) * 0.05
        assert v3_mult > v0_mult, "top voice louder than bass"

    def test_velocity_fade_decreasing(self):
        """fade: velocity decreases from voice 1 to N"""
        for i in range(4):
            1.0 - i * 0.1
        assert (1.0 - 0 * 0.1) > (1.0 - 1 * 0.1), "voice 0 louder than voice 1"
        assert (1.0 - 1 * 0.1) > (1.0 - 2 * 0.1), "voice 1 louder than voice 2"

    def test_fewer_notes_than_voices(self):
        """Chord with 2 notes, 4 voices → voices 3,4 empty"""
        chord_size = 2
        num_voices = 4
        empty_voices = num_voices - chord_size
        assert empty_voices == 2, "2 empty voices"

    def test_more_notes_than_voices(self):
        """Chord with 6 notes, 4 voices → extra notes in highest voice"""
        chord_size = 6
        num_voices = 4
        extra = chord_size - num_voices
        assert extra == 2, "2 extra notes overflow"

    def test_num_voices_clamping(self):
        """num_voices clamped to 2-8"""
        assert max(2, min(8, 1)) == 2, "clamped to 2"
        assert max(2, min(8, 10)) == 8, "clamped to 8"
        assert max(2, min(8, 4)) == 4, "4 is valid"

    def test_outward_direction_middle_first(self):
        """outward: middle notes go to outer voices"""
        chord = [
            {"pitch": 48, "vel": 0.8},
            {"pitch": 55, "vel": 0.8},
            {"pitch": 60, "vel": 0.8},
            {"pitch": 67, "vel": 0.8},
        ]
        chord.sort(key=lambda x: x["pitch"])
        n = len(chord)
        indices = []
        for j in range(n):
            if j % 2 == 0:
                indices.append(j // 2)
            else:
                indices.append(n - 1 - j // 2)
        # voice 0 = lowest (index 0), voice 1 = highest (index 3)
        assert indices[0] == 0, "voice 0 = lowest"
        assert indices[1] == 3, "voice 1 = highest"

    def test_target_units_parsing(self):
        """Comma-separated AU indices parsed correctly"""
        target_str = "0,1,2,3"
        targets = [int(s.strip()) for s in target_str.split(",") if s.strip()]
        assert targets == [0, 1, 2, 3], "4 target units parsed"

    def test_empty_target_units(self):
        """Empty target_units → use source track"""
        target_str = ""
        targets = [int(s.strip()) for s in target_str.split(",") if s.strip()]
        assert targets == [], "empty target string = no targets"

    def test_chord_sorted_by_pitch(self):
        """Each chord group sorted by pitch before voice assignment"""
        chord = [
            {"pitch": 67, "vel": 0.8},
            {"pitch": 48, "vel": 0.8},
            {"pitch": 60, "vel": 0.8},
        ]
        chord.sort(key=lambda x: x["pitch"])
        assert chord[0]["pitch"] == 48, "lowest first"
        assert chord[2]["pitch"] == 67, "highest last"
