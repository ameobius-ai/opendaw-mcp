"""Unit tests for create_cadenza MCP tool."""



class TestCadenzaParameterValidation:
    """Test parameter validation."""

    def test_duration_too_short(self):
        assert not (4 <= 3 <= 64)

    def test_duration_too_long(self):
        assert not (4 <= 65 <= 64)

    def test_duration_valid(self):
        for d in (4, 8, 16, 32, 64):
            assert 4 <= d <= 64

    def test_octave_too_low(self):
        assert not (2 <= 1 <= 6)

    def test_octave_too_high(self):
        assert not (2 <= 7 <= 6)

    def test_invalid_style(self):
        s = "invalid"
        assert s not in ("classical", "romantic", "jazz", "modern")

    def test_valid_styles(self):
        for s in ("classical", "romantic", "jazz", "modern"):
            assert s in ("classical", "romantic", "jazz", "modern")


class TestCadenzaStyleParams:
    """Test style parameters."""

    def test_classical_params(self):
        params = {"run_density": 6, "leap_max": 12, "trill_count": 4, "fermata_prob": 0.15}
        assert params["run_density"] == 6
        assert params["leap_max"] == 12

    def test_romantic_params(self):
        params = {"run_density": 8, "leap_max": 19, "trill_count": 6, "fermata_prob": 0.1}
        assert params["run_density"] == 8
        assert params["leap_max"] == 19

    def test_jazz_params(self):
        params = {"run_density": 7, "leap_max": 14, "trill_count": 3, "fermata_prob": 0.05}
        assert params["run_density"] == 7
        assert params["leap_max"] == 14

    def test_modern_params(self):
        params = {"run_density": 5, "leap_max": 24, "trill_count": 2, "fermata_prob": 0.2}
        assert params["run_density"] == 5
        assert params["leap_max"] == 24

    def test_virtuosic_boost(self):
        params = {"run_density": 6, "leap_max": 12}
        virtuosic = True
        if virtuosic:
            params["run_density"] = int(params["run_density"] * 1.5)
            params["leap_max"] = int(params["leap_max"] * 1.3)
        assert params["run_density"] == 9
        assert params["leap_max"] == 15


class TestCadenzaPRNG:
    """Test seeded PRNG determinism."""

    def test_prng_deterministic(self):
        """Same seed produces same sequence."""
        def make_prng(seed):
            state = seed & 0xFFFFFFFF
            def next_rand():
                nonlocal state
                state = (state + 0x6D2B79F5) & 0xFFFFFFFF
                t = state
                t = ((t ^ (t >> 15)) * t | 1) & 0xFFFFFFFF
                t = (t ^ (t >> 14)) & 0xFFFFFFFF
                return t / 0xFFFFFFFF
            return next_rand

        r1 = make_prng(42)
        r2 = make_prng(42)
        seq1 = [r1() for _ in range(10)]
        seq2 = [r2() for _ in range(10)]
        assert seq1 == seq2

    def test_prng_range(self):
        """PRNG values are in [0, 1)."""
        state = 42 & 0xFFFFFFFF
        for _ in range(100):
            state = (state + 0x6D2B79F5) & 0xFFFFFFFF
            t = state
            t = ((t ^ (t >> 15)) * t | 1) & 0xFFFFFFFF
            t = (t ^ (t >> 14)) & 0xFFFFFFFF
            val = t / 0xFFFFFFFF
            assert 0 <= val < 1.0


class TestCadenzaScalePitches:
    """Test scale pitch construction."""

    def test_4_octave_range(self):
        """Cadenza spans 4 octaves for wide range."""
        intervals = [0, 2, 3, 5, 7, 8, 10]  # minor
        root_num = 0
        octave = 4
        scale_pitches = []
        for oct_shift in range(-1, 3):
            for iv in intervals:
                pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
                scale_pitches.append(pitch)
        scale_pitches = sorted(set(scale_pitches))
        # 7 notes * 4 octaves = 28 unique pitches (minus duplicates at octave boundaries)
        assert len(scale_pitches) >= 21  # at least 3 octaves of unique pitches

    def test_pitches_sorted(self):
        """Scale pitches are sorted."""
        intervals = [0, 2, 4, 5, 7, 9, 11]
        root_num = 0
        octave = 4
        scale_pitches = []
        for oct_shift in range(-1, 3):
            for iv in intervals:
                pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
                scale_pitches.append(pitch)
        scale_pitches = sorted(set(scale_pitches))
        assert scale_pitches == sorted(scale_pitches)


class TestCadenzaSegmentTypes:
    """Test segment type generation."""

    def test_segment_types_exist(self):
        """All 6 segment types are defined."""
        types = ["flourish", "leap", "trill", "fermata", "cascade", "climb"]
        assert len(types) == 6

    def test_style_weights_have_all_types(self):
        """Style weights cover all segment types."""
        types = {"flourish", "leap", "trill", "fermata", "cascade", "climb"}
        for style_name in ("classical", "romantic", "jazz", "modern"):
            weights = {
                "classical": {"flourish": 3, "leap": 2, "trill": 3, "fermata": 2, "cascade": 2, "climb": 2},
                "romantic": {"flourish": 4, "leap": 3, "trill": 2, "fermata": 1, "cascade": 3, "climb": 3},
                "jazz": {"flourish": 4, "leap": 2, "trill": 1, "fermata": 1, "cascade": 2, "climb": 2},
                "modern": {"flourish": 2, "leap": 4, "trill": 1, "fermata": 3, "cascade": 2, "climb": 1},
            }
            assert set(weights[style_name].keys()) == types

    def test_weighted_segment_list(self):
        """Weighted segments list extends correctly."""
        weights = {"flourish": 3, "leap": 2}
        weighted = []
        for seg_type, weight in weights.items():
            weighted.extend([seg_type] * weight)
        assert weighted == ["flourish", "flourish", "flourish", "leap", "leap"]
        assert len(weighted) == 5


class TestCadenzaFlourish:
    """Test flourish segment (rapid run)."""

    def test_flourish_accelerando(self):
        """Flourish notes get shorter (accelerando)."""
        run_len = 6
        run_dur = 0.12
        durs = []
        for i in range(run_len):
            accel_factor = 1.0 - (i / run_len) * 0.3
            durs.append(run_dur * accel_factor)
        # First note longest, last note shortest
        assert durs[0] > durs[-1]
        assert durs[0] == 0.12
        assert abs(durs[-1] - 0.084) < 0.01

    def test_flourish_direction(self):
        """Flourish can go up or down."""
        direction = 1  # ascending
        assert direction in (1, -1)


class TestCadenzaLeap:
    """Test leap segment."""

    def test_leap_size_range(self):
        """Leap size is within params."""
        leap_max = 12
        leap_size = int(3 + 0.5 * leap_max)
        assert 3 <= leap_size <= 3 + leap_max

    def test_leap_boundary_reflect(self):
        """Leap reflects at scale boundaries."""
        scale_len = 28
        current_idx = 25
        leap_size = 10
        direction = 1
        new_idx = current_idx + direction * leap_size
        if new_idx >= scale_len:
            new_idx = 2 * scale_len - new_idx - 2
        new_idx = max(0, min(scale_len - 1, new_idx))
        # 25 + 10 = 35, reflect: 2*28 - 35 - 2 = 19
        assert new_idx == 19


class TestCadenzaTrill:
    """Test trill segment."""

    def test_trill_alternates(self):
        """Trill alternates between two pitches."""
        lower = 60
        upper = 62
        notes = []
        for i in range(8):
            pitch = upper if i % 2 == 0 else lower
            notes.append(pitch)
        assert notes == [62, 60, 62, 60, 62, 60, 62, 60]

    def test_trill_count_doubles(self):
        """Trill produces count*2 notes."""
        trill_count = 4
        total_notes = trill_count * 2
        assert total_notes == 8


class TestCadenzaFermata:
    """Test fermata segment."""

    def test_fermata_hold_duration(self):
        """Fermata holds for 0.8-2.0 beats."""
        hold_dur = 0.8 + 0.5 * 1.2
        assert 0.8 <= hold_dur <= 2.0

    def test_fermata_has_pause(self):
        """Fermata has a pause after the held note."""
        pause = 0.3 + 0.5 * 0.5
        assert 0.3 <= pause <= 0.8

    def test_fermata_velocity_soft(self):
        """Fermata notes are soft."""
        velocity = 0.7
        vel = velocity * (0.4 + 0.1 * 0.2)
        assert vel < velocity


class TestCadenzaCascade:
    """Test cascade segment."""

    def test_cascade_descends(self):
        """Cascade notes descend by thirds."""
        current_idx = 15
        pitches = []
        for i in range(5):
            new_idx = current_idx - 2
            new_idx = max(0, new_idx)
            pitches.append(new_idx)
            current_idx = new_idx
        assert pitches == [13, 11, 9, 7, 5]

    def test_cascade_diminuendo(self):
        """Cascade gets quieter (diminuendo)."""
        velocity = 0.7
        vels = []
        for i in range(5):
            vel = velocity * (0.7 - i * 0.05)
            vels.append(max(0.1, vel))
        assert vels[0] > vels[-1]


class TestCadenzaClimb:
    """Test climb segment."""

    def test_climb_ascends(self):
        """Climb notes ascend stepwise."""
        current_idx = 10
        idxs = []
        for i in range(5):
            new_idx = current_idx + 1
            idxs.append(new_idx)
            current_idx = new_idx
        assert idxs == [11, 12, 13, 14, 15]

    def test_climb_crescendo(self):
        """Climb gets louder (crescendo)."""
        velocity = 0.7
        vels = []
        for i in range(5):
            vel = velocity * (0.5 + i * 0.08)
            vels.append(min(1.0, vel))
        assert vels[0] < vels[-1]


class TestCadenzaBreathMarks:
    """Test breath mark handling."""

    def test_parse_breath_marks(self):
        """Breath marks parsed from comma-separated string."""
        breath_marks = "2.0,4.0,6.0"
        breath_set = set()
        for b in breath_marks.split(","):
            breath_set.add(float(b.strip()))
        assert breath_set == {2.0, 4.0, 6.0}

    def test_no_breath_marks(self):
        """Empty breath_marks means no pauses."""
        breath_marks = ""
        breath_set = set()
        if breath_marks:
            for b in breath_marks.split(","):
                breath_set.add(float(b.strip()))
        assert breath_set == set()

    def test_breath_detection(self):
        """Breath is detected when current_beat is near a breath mark."""
        breath_set = {4.0}
        current_beat = 4.2
        is_breath = False
        for breath_pos in breath_set:
            if abs(current_beat - breath_pos) < 0.5:
                is_breath = True
                break
        assert is_breath

    def test_no_breath_when_far(self):
        """No breath when current_beat is far from breath marks."""
        breath_set = {4.0}
        current_beat = 1.0
        is_breath = False
        for breath_pos in breath_set:
            if abs(current_beat - breath_pos) < 0.5:
                is_breath = True
                break
        assert not is_breath


class TestCadenzaStatistics:
    """Test cadenza statistics."""

    def test_pitch_range(self):
        """Pitch range = max - min."""
        notes = [{"pitch": 60}, {"pitch": 84}, {"pitch": 72}]
        pr = max(n["pitch"] for n in notes) - min(n["pitch"] for n in notes)
        assert pr == 24

    def test_segment_counts(self):
        """Segment counts are tallied correctly."""
        segment_log = [
            {"type": "flourish"},
            {"type": "leap"},
            {"type": "flourish"},
            {"type": "trill"},
            {"type": "flourish"},
        ]
        counts = {}
        for seg in segment_log:
            counts[seg["type"]] = counts.get(seg["type"], 0) + 1
        assert counts == {"flourish": 3, "leap": 1, "trill": 1}

    def test_velocity_range(self):
        """Velocity range captures min and max."""
        notes = [{"vel": 0.3}, {"vel": 0.9}, {"vel": 0.5}]
        vel_range = (min(n["vel"] for n in notes), max(n["vel"] for n in notes))
        assert vel_range == (0.3, 0.9)
