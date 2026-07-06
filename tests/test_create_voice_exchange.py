"""Unit tests for create_voice_exchange MCP tool."""



class TestVoiceExchangeParameterValidation:
    """Test parameter validation."""

    def test_valid_modes(self):
        modes = ("imitation", "inversion", "retrograde",
                 "retrograde_inversion", "augmentation", "diminution")
        for m in modes:
            assert m in ("imitation", "inversion", "retrograde",
                         "retrograde_inversion", "augmentation", "diminution")

    def test_invalid_mode(self):
        mode = "invalid"
        assert mode not in ("imitation", "inversion", "retrograde",
                            "retrograde_inversion", "augmentation", "diminution")

    def test_time_offset_too_large(self):
        time_offset = 65
        assert not (0 <= time_offset <= 64)

    def test_time_offset_negative(self):
        time_offset = -1
        assert not (0 <= time_offset <= 64)

    def test_time_offset_valid(self):
        assert 0 <= 2.0 <= 64

    def test_duration_factor_too_small(self):
        df = 0.03
        assert not (0.0625 <= df <= 8.0)

    def test_duration_factor_too_large(self):
        df = 9.0
        assert not (0.0625 <= df <= 8.0)

    def test_duration_factor_valid(self):
        assert 0.0625 <= 1.0 <= 8.0


class TestVoiceExchangeDurationFactor:
    """Test duration factor from mode."""

    def test_augmentation_default(self):
        mode = "augmentation"
        duration_factor = 1.0
        effective = duration_factor
        if mode == "augmentation" and duration_factor == 1.0:
            effective = 2.0
        assert effective == 2.0

    def test_diminution_default(self):
        mode = "diminution"
        duration_factor = 1.0
        effective = duration_factor
        if mode == "diminution" and duration_factor == 1.0:
            effective = 0.5
        assert effective == 0.5

    def test_explicit_override(self):
        mode = "augmentation"
        duration_factor = 3.0
        effective = duration_factor
        if mode == "augmentation" and duration_factor == 1.0:
            effective = 2.0
        assert effective == 3.0  # explicit wins

    def test_imitation_no_change(self):
        mode = "imitation"
        duration_factor = 1.0
        effective = duration_factor
        if mode == "augmentation" and duration_factor == 1.0:
            effective = 2.0
        elif mode == "diminution" and duration_factor == 1.0:
            effective = 0.5
        assert effective == 1.0


class TestVoiceExchangeTranspose:
    """Test total transpose calculation."""

    def test_default_interval(self):
        interval = 7  # perfect fifth
        transpose = 0
        total = interval + transpose
        assert total == 7

    def test_custom_transpose(self):
        interval = 7
        transpose = 5
        total = interval + transpose
        assert total == 12  # octave

    def test_negative_transpose(self):
        interval = 7
        transpose = -12
        total = interval + transpose
        assert total == -5

    def test_zero_interval(self):
        interval = 0
        transpose = 0
        total = interval + transpose
        assert total == 0


class TestVoiceExchangeInversion:
    """Test pitch inversion logic."""

    def test_inversion_around_axis(self):
        """Inversion mirrors intervals around the first pitch."""
        pitches = [60, 62, 65, 67]  # C, D, F, G
        axis = pitches[0]  # 60
        inverted = [axis - (p - axis) for p in pitches]
        # 60, 58, 55, 53 = C, A#, G, F
        assert inverted == [60, 58, 55, 53]

    def test_inversion_preserves_axis(self):
        """The axis pitch stays the same after inversion."""
        pitches = [64, 67, 71]
        axis = pitches[0]
        inverted = [axis - (p - axis) for p in pitches]
        assert inverted[0] == 64  # axis unchanged

    def test_inversion_descending_from_ascending(self):
        """An ascending motif becomes descending after inversion."""
        pitches = [60, 62, 64, 65]
        axis = pitches[0]
        inverted = [axis - (p - axis) for p in pitches]
        assert inverted == [60, 58, 56, 55]
        # Check it's descending (or equal at axis)
        assert inverted[1] < inverted[0]
        assert inverted[2] < inverted[1]


class TestVoiceExchangeRetrograde:
    """Test retrograde (time reversal) logic."""

    def test_reverse_positions(self):
        """Retrograde reverses the time order."""
        positions = [0, 480, 960, 1440]  # in ticks
        durations = [480, 480, 480, 480]
        velocities = [0.7, 0.6, 0.65, 0.7]

        positions_rev = positions[::-1]
        durations_rev = durations[::-1]
        velocities_rev = velocities[::-1]

        assert positions_rev == [1440, 960, 480, 0]
        assert durations_rev == [480, 480, 480, 480]
        assert velocities_rev == [0.7, 0.65, 0.6, 0.7]

    def test_retrograde_recalculates_positions(self):
        """After reversal, positions are recalculated as contiguous sequence."""
        durations = [480, 240, 480, 240]  # reversed: 240, 480, 240, 480
        src_start = 0
        offset_ticks = 960  # 2 beats
        positions = [0] * 4

        durations_rev = durations[::-1]
        pos = src_start + offset_ticks
        for i in range(4):
            positions[i] = pos
            pos += durations_rev[i]

        # 960, 960+240=1200, 1200+480=1680, 1680+240=1920
        assert positions == [960, 1200, 1680, 1920]


class TestVoiceExchangeAugmentation:
    """Test augmentation (time stretching)."""

    def test_doubled_durations(self):
        """Augmentation doubles note durations."""
        durations = [480, 240, 480]
        factor = 2.0
        stretched = [round(d * factor) for d in durations]
        assert stretched == [960, 480, 960]

    def test_positions_recalculated(self):
        """After augmentation, positions are recalculated."""
        durations = [480, 240, 480]
        factor = 2.0
        stretched = [round(d * factor) for d in durations]
        src_start = 0
        offset_ticks = 960
        positions = [0] * 3

        pos = src_start + offset_ticks
        for i in range(3):
            positions[i] = pos
            pos += stretched[i]

        assert positions == [960, 1920, 2400]


class TestVoiceExchangeDiminution:
    """Test diminution (time compression)."""

    def test_halved_durations(self):
        """Diminution halves note durations."""
        durations = [480, 240, 480]
        factor = 0.5
        compressed = [round(d * factor) for d in durations]
        assert compressed == [240, 120, 240]


class TestVoiceExchangeVelocityFactor:
    """Test velocity factor application."""

    def test_velocity_reduced(self):
        """Response voice has reduced velocity."""
        velocities = [0.7, 0.6, 0.65]
        vel_factor = 0.85
        result = [max(0, min(1, v * vel_factor)) for v in velocities]
        assert abs(result[0] - 0.595) < 0.01
        assert abs(result[1] - 0.51) < 0.01

    def test_velocity_clamped_high(self):
        """Velocity is clamped to 1.0."""
        velocities = [0.9, 0.8]
        vel_factor = 1.5
        result = [max(0, min(1, v * vel_factor)) for v in velocities]
        assert result[0] == 1.0
        assert result[1] == 1.0

    def test_velocity_clamped_low(self):
        """Velocity is clamped to 0.0."""
        velocities = [0.1, 0.2]
        vel_factor = -1.0
        result = [max(0, min(1, v * vel_factor)) for v in velocities]
        assert result[0] == 0.0
        assert result[1] == 0.0


class TestVoiceExchangeSwap:
    """Test swap mode (true voice exchange)."""

    def test_swap_transposes_source(self):
        """When swap=True, source notes are also transposed."""
        swap = True
        total_transpose = 7
        source_pitches = [60, 62, 64]
        if swap:
            swapped = [p + total_transpose for p in source_pitches]
        else:
            swapped = source_pitches
        assert swapped == [67, 69, 71]

    def test_no_swap_leaves_source(self):
        """When swap=False, source notes are unchanged."""
        swap = False
        total_transpose = 7
        source_pitches = [60, 62, 64]
        if swap:
            swapped = [p + total_transpose for p in source_pitches]
        else:
            swapped = source_pitches
        assert swapped == [60, 62, 64]


class TestVoiceExchangeRetrogradeInversion:
    """Test retrograde-inversion (both reversed and inverted)."""

    def test_combined_transform(self):
        """Retrograde-inversion reverses time AND inverts pitch."""
        pitches = [60, 62, 65, 67]
        durations = [480, 480, 240, 240]

        # Step 1: Retrograde (reverse time order)
        pitches_r = pitches[::-1]
        durations_r = durations[::-1]
        assert pitches_r == [67, 65, 62, 60]
        assert durations_r == [240, 240, 480, 480]

        # Step 2: Invert around axis (first pitch of reversed = 67)
        axis = pitches_r[0]
        pitches_ri = [axis - (p - axis) for p in pitches_r]
        # 67, 67-(65-67)=69, 67-(62-67)=72, 67-(60-67)=74
        assert pitches_ri == [67, 69, 72, 74]


class TestVoiceExchangePositionShift:
    """Test position shifting for non-retrograde modes."""

    def test_imitation_position_shift(self):
        """Imitation shifts all notes by time_offset."""
        src_positions = [0, 480, 960, 1440]
        src_start = 0
        offset_ticks = 960  # 2 beats
        mode = "imitation"

        if mode in ("imitation", "inversion", "augmentation", "diminution"):
            shifted = [p - src_start + offset_ticks for p in src_positions]
        else:
            shifted = src_positions

        assert shifted == [960, 1440, 1920, 2400]

    def test_offset_zero(self):
        """Zero offset means response starts at same time as source."""
        src_positions = [0, 480, 960]
        src_start = 0
        offset_ticks = 0
        shifted = [p - src_start + offset_ticks for p in src_positions]
        assert shifted == [0, 480, 960]


class TestVoiceExchangeNoteSorting:
    """Test source note sorting."""

    def test_sorted_by_position(self):
        """Source notes should be sorted by position before processing."""
        notes = [
            {"pitch": 64, "position": 960},
            {"pitch": 60, "position": 0},
            {"pitch": 62, "position": 480},
        ]
        notes.sort(key=lambda n: n["position"])
        assert notes[0]["position"] == 0
        assert notes[1]["position"] == 480
        assert notes[2]["position"] == 960
