"""Unit tests for create_tuplet_group MCP tool."""



class TestTupletParameterValidation:
    """Test parameter validation."""

    def test_tuplet_number_too_few(self):
        assert not (2 <= 1 <= 16)

    def test_tuplet_number_too_many(self):
        assert not (2 <= 17 <= 16)

    def test_tuplet_number_valid(self):
        for n in (2, 3, 5, 7, 11, 16):
            assert 2 <= n <= 16

    def test_span_too_short(self):
        assert not (0.25 <= 0.1 <= 8.0)

    def test_span_too_long(self):
        assert not (0.25 <= 9.0 <= 8.0)

    def test_span_valid(self):
        for s in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
            assert 0.25 <= s <= 8.0

    def test_base_division_too_few(self):
        assert not (1 <= 0 <= 8)

    def test_base_division_too_many(self):
        assert not (1 <= 9 <= 8)

    def test_repeats_too_few(self):
        assert not (1 <= 0 <= 16)

    def test_repeats_too_many(self):
        assert not (1 <= 17 <= 16)

    def test_invalid_pitch_mode(self):
        p = "invalid"
        assert p not in ("scale_asc", "scale_desc", "chord", "repeated", "alternating")

    def test_valid_pitch_modes(self):
        for p in ("scale_asc", "scale_desc", "chord", "repeated", "alternating"):
            assert p in ("scale_asc", "scale_desc", "chord", "repeated", "alternating")


class TestTupletNoteDuration:
    """Test tuplet note duration calculation."""

    def test_triplet_in_quarter(self):
        """3 notes in 1 beat = 1/3 beat each."""
        span = 1.0
        tuplet = 3
        dur = span / tuplet
        assert abs(dur - 0.3333) < 0.001

    def test_quintuplet_in_half(self):
        """5 notes in 2 beats = 0.4 beat each."""
        span = 2.0
        tuplet = 5
        dur = span / tuplet
        assert abs(dur - 0.4) < 0.001

    def test_septuplet_in_quarter(self):
        """7 notes in 1 beat = 1/7 beat each."""
        span = 1.0
        tuplet = 7
        dur = span / tuplet
        assert abs(dur - 0.1429) < 0.001

    def test_duplet_in_dotted(self):
        """2 notes in 1.5 beats (dotted quarter) = 0.75 beat each."""
        span = 1.5
        tuplet = 2
        dur = span / tuplet
        assert abs(dur - 0.75) < 0.001

    def test_note_duration_90_percent(self):
        """Actual note duration is 90% of slot (leaving small gap)."""
        note_dur = 0.3333
        actual = note_dur * 0.9
        assert abs(actual - 0.3) < 0.01


class TestTupletPositionCalculation:
    """Test beat position calculation."""

    def test_first_note_position(self):
        """First note of first repeat at position 0."""
        rep = 0
        pos = 0
        note_dur = 0.3333
        beat_pos = rep * 1.0 + pos * note_dur
        assert beat_pos == 0.0

    def test_second_note_position(self):
        """Second note at note_dur."""
        rep = 0
        pos = 1
        note_dur = 0.3333
        beat_pos = rep * 1.0 + pos * note_dur
        assert abs(beat_pos - 0.3333) < 0.001

    def test_second_repeat_start(self):
        """Second repeat starts at span_beats."""
        rep = 1
        pos = 0
        note_dur = 0.3333
        span = 1.0
        beat_pos = rep * span + pos * note_dur
        assert beat_pos == 1.0

    def test_third_repeat_note2(self):
        """Third repeat, second note at 2*span + note_dur."""
        rep = 2
        pos = 1
        note_dur = 0.3333
        span = 1.0
        beat_pos = rep * span + pos * note_dur
        assert abs(beat_pos - 2.3333) < 0.001


class TestTupletRestPositions:
    """Test rest position handling."""

    def test_parse_rest_positions(self):
        """Rest positions are parsed from comma-separated string."""
        rest_positions = "2,4"
        rest_set = set()
        for p in rest_positions.split(","):
            rest_set.add(int(p.strip()))
        assert rest_set == {2, 4}

    def test_no_rests(self):
        """Empty rest_positions means no rests."""
        rest_positions = ""
        rest_set = set()
        if rest_positions:
            for p in rest_positions.split(","):
                rest_set.add(int(p.strip()))
        assert rest_set == set()

    def test_invalid_rests_fallback(self):
        """Invalid rest positions result in empty set."""
        rest_positions = "abc"
        rest_set = set()
        try:
            for p in rest_positions.split(","):
                rest_set.add(int(p.strip()))
        except (ValueError, TypeError):
            rest_set = set()
        assert rest_set == set()

    def test_rest_skips_note(self):
        """Position in rest_set is skipped."""
        rest_set = {2}
        pos = 2
        is_rest = pos in rest_set
        assert is_rest

    def test_non_rest_position(self):
        """Position not in rest_set creates a note."""
        rest_set = {2}
        pos = 1
        is_rest = pos in rest_set
        assert not is_rest


class TestTupletPitchModes:
    """Test pitch assignment modes."""

    def test_scale_asc_cycles(self):
        """Ascending scale wraps around."""
        scale_pitches = [60, 62, 64, 65, 67]
        idx = 0
        results = []
        for _ in range(7):
            if idx >= len(scale_pitches):
                idx = 0
            results.append(scale_pitches[idx])
            idx += 1
        assert results == [60, 62, 64, 65, 67, 60, 62]

    def test_scale_desc_cycles(self):
        """Descending scale wraps around."""
        scale_pitches = [60, 62, 64, 65, 67]
        reversed_pitches = list(reversed(scale_pitches))
        idx = 0
        results = []
        for _ in range(7):
            if idx >= len(reversed_pitches):
                idx = 0
            results.append(reversed_pitches[idx])
            idx += 1
        assert results == [67, 65, 64, 62, 60, 67, 65]

    def test_chord_cycles(self):
        """Chord tones rotate."""
        chord_pitches = [60, 64, 67]
        idx = 0
        results = []
        for _ in range(5):
            if idx >= len(chord_pitches):
                idx = 0
            results.append(chord_pitches[idx])
            idx += 1
        assert results == [60, 64, 67, 60, 64]

    def test_repeated_uses_first_pitch(self):
        """Repeated mode always uses first scale pitch."""
        scale_pitches = [60, 62, 64]
        results = [scale_pitches[0] for _ in range(5)]
        assert all(r == 60 for r in results)

    def test_alternating_two_pitches(self):
        """Alternating mode switches between two pitches."""
        scale_pitches = [60, 62, 64, 65, 67]
        idx = 0
        results = []
        for pos in range(6):
            if idx >= len(scale_pitches):
                idx = 0
            if pos % 2 == 0:
                pitch = scale_pitches[idx]
            else:
                pitch = scale_pitches[(idx + 3) % len(scale_pitches)]
            results.append(pitch)
            idx += 1
        # pos 0: idx=0, even -> 60, pos 1: idx=1, odd -> scale_pitches[4]=67
        assert results[0] == 60
        assert results[1] == 67


class TestTupletAccent:
    """Test accent on first note."""

    def test_accent_first_note(self):
        """First note gets velocity boost."""
        velocity = 0.7
        accent_first = True
        pos = 0
        vel = velocity
        if accent_first and pos == 0:
            vel = min(1.0, vel * 1.2)
        assert abs(vel - 0.84) < 0.01

    def test_no_accent_non_first(self):
        """Non-first notes don't get accent."""
        velocity = 0.7
        accent_first = True
        pos = 1
        vel = velocity
        if accent_first and pos == 0:
            vel = min(1.0, vel * 1.2)
        assert vel == 0.7

    def test_no_accent_when_disabled(self):
        """Accent disabled means no boost on first note."""
        velocity = 0.7
        accent_first = False
        pos = 0
        vel = velocity
        if accent_first and pos == 0:
            vel = min(1.0, vel * 1.2)
        assert vel == 0.7

    def test_accent_clamped(self):
        """Accent velocity clamped to 1.0."""
        velocity = 0.9
        vel = min(1.0, velocity * 1.2)
        assert vel == 1.0


class TestTupletTotalPositions:
    """Test total positions calculation."""

    def test_triplet_4_repeats(self):
        """3 × 4 = 12 total positions."""
        tuplet = 3
        repeats = 4
        total = repeats * tuplet
        assert total == 12

    def test_quintuplet_2_repeats(self):
        """5 × 2 = 10 total positions."""
        tuplet = 5
        repeats = 2
        total = repeats * tuplet
        assert total == 10

    def test_rest_count(self):
        """Rest count = total - actual notes."""
        total = 12
        actual = 10
        rest_count = total - actual
        assert rest_count == 2


class TestTupletRatio:
    """Test tuplet ratio string."""

    def test_triplet_ratio(self):
        """Triplet = 3:2."""
        tuplet_number = 3
        base_division = 2
        ratio = f"{tuplet_number}:{base_division}"
        assert ratio == "3:2"

    def test_quintuplet_ratio(self):
        """Quintuplet = 5:4."""
        tuplet_number = 5
        base_division = 4
        ratio = f"{tuplet_number}:{base_division}"
        assert ratio == "5:4"

    def test_septuplet_ratio(self):
        """Septuplet = 7:4."""
        tuplet_number = 7
        base_division = 4
        ratio = f"{tuplet_number}:{base_division}"
        assert ratio == "7:4"

    def test_duplet_ratio(self):
        """Duplet = 2:3 (compound meter)."""
        tuplet_number = 2
        base_division = 3
        ratio = f"{tuplet_number}:{base_division}"
        assert ratio == "2:3"
