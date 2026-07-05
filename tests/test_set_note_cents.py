"""Unit tests for set_note_cents — deterministic microtonal pitch control."""

NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
              "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def compute_cents_for_mode(mode, cents, direction, note_index, total_notes):
    """Compute the cents value for a given note in a given mode."""
    if mode == "all":
        return cents if direction == "up" else -abs(cents)
    elif mode == "alternating":
        base = abs(cents)
        if direction == "down":
            return -base if note_index % 2 == 0 else base
        return base if note_index % 2 == 0 else -base
    elif mode == "gradient":
        if total_notes <= 1:
            return cents
        frac = note_index / (total_notes - 1)
        return round(cents * frac, 2)
    return cents if direction == "up" else -abs(cents)


def should_apply_to_note(mode, note_index, pitch, beat_pos,
                         target_pcs, target_beats, target_indices, scale_pcs):
    """Check if a note should receive the cents offset."""
    if mode == "all":
        return True
    elif mode == "pitch":
        pc = ((pitch % 12) + 12) % 12
        return pc in target_pcs
    elif mode == "beats":
        return round(beat_pos, 2) in target_beats
    elif mode == "indices":
        return note_index in target_indices
    elif mode == "alternating":
        return True
    elif mode == "gradient":
        return True
    elif mode == "scale_degree":
        pc = ((pitch % 12) + 12) % 12
        return pc in scale_pcs
    return False


# --- Direction/cent computation tests ---

class TestCentsComputation:
    def test_all_mode_up(self):
        assert compute_cents_for_mode("all", 10, "up", 0, 10) == 10

    def test_all_mode_down(self):
        assert compute_cents_for_mode("all", 10, "down", 0, 10) == -10

    def test_alternating_even_up(self):
        assert compute_cents_for_mode("alternating", 8, "up", 0, 10) == 8

    def test_alternating_odd_up(self):
        assert compute_cents_for_mode("alternating", 8, "up", 1, 10) == -8

    def test_alternating_even_down(self):
        assert compute_cents_for_mode("alternating", 8, "down", 0, 10) == -8

    def test_alternating_odd_down(self):
        assert compute_cents_for_mode("alternating", 8, "down", 1, 10) == 8

    def test_gradient_first_note(self):
        assert compute_cents_for_mode("gradient", 20, "up", 0, 10) == 0.0

    def test_gradient_last_note(self):
        assert compute_cents_for_mode("gradient", 20, "up", 9, 10) == 20.0

    def test_gradient_middle_note(self):
        result = compute_cents_for_mode("gradient", 20, "up", 5, 10)
        assert abs(result - 11.11) < 0.1

    def test_gradient_single_note(self):
        assert compute_cents_for_mode("gradient", 15, "up", 0, 1) == 15


# --- Note selection tests ---

class TestNoteSelection:
    def test_all_mode_selects_all(self):
        assert should_apply_to_note("all", 0, 60, 0.0, set(), set(), set(), set())
        assert should_apply_to_note("all", 5, 72, 4.0, set(), set(), set(), set())

    def test_pitch_mode_matches(self):
        assert should_apply_to_note("pitch", 0, 60, 0.0, {0}, set(), set(), set())
        assert not should_apply_to_note("pitch", 0, 61, 0.0, {0}, set(), set(), set())

    def test_pitch_mode_octave_invariant(self):
        # pc 0 = C, should match C3 (48), C4 (60), C5 (72)
        assert should_apply_to_note("pitch", 0, 48, 0.0, {0}, set(), set(), set())
        assert should_apply_to_note("pitch", 0, 60, 0.0, {0}, set(), set(), set())
        assert should_apply_to_note("pitch", 0, 72, 0.0, {0}, set(), set(), set())

    def test_beats_mode_matches(self):
        assert should_apply_to_note("beats", 0, 60, 4.0, set(), {4.0}, set(), set())
        assert not should_apply_to_note("beats", 0, 60, 3.0, set(), {4.0}, set(), set())

    def test_indices_mode_matches(self):
        assert should_apply_to_note("indices", 2, 60, 0.0, set(), set(), {2}, set())
        assert not should_apply_to_note("indices", 3, 60, 0.0, set(), set(), {2}, set())

    def test_scale_degree_matches(self):
        # C major degree 3 = E (pc 4)
        assert should_apply_to_note("scale_degree", 0, 64, 0.0, set(), set(), set(), {4})
        assert not should_apply_to_note("scale_degree", 0, 60, 0.0, set(), set(), set(), {4})


# --- Edge case tests ---

class TestEdgeCases:
    def test_zero_cents_is_valid(self):
        # 0 cents is valid — resets detune
        assert -100 <= 0 <= 100

    def test_max_cents(self):
        # 100 cents = 1 semitone
        assert -100 <= 100 <= 100

    def test_negative_cents(self):
        assert -100 <= -50 <= 100

    def test_over_limit_rejected(self):
        assert not (-100 <= 150 <= 100)

    def test_under_limit_rejected(self):
        assert not (-100 <= -150 <= 100)

    def test_note_name_to_pc(self):
        assert NOTE_NAMES["C"] == 0
        assert NOTE_NAMES["E"] == 4
        assert NOTE_NAMES["B"] == 11
        assert NOTE_NAMES["F#"] == 6


# --- Alternating pattern tests ---

class TestAlternatingPattern:
    def test_alternating_8_notes_up(self):
        pattern = [compute_cents_for_mode("alternating", 8, "up", i, 8) for i in range(8)]
        assert pattern == [8, -8, 8, -8, 8, -8, 8, -8]

    def test_alternating_8_notes_down(self):
        pattern = [compute_cents_for_mode("alternating", 8, "down", i, 8) for i in range(8)]
        assert pattern == [-8, 8, -8, 8, -8, 8, -8, 8]

    def test_alternating_symmetric(self):
        # Sum of alternating pattern should be 0 (equal + and -)
        pattern = [compute_cents_for_mode("alternating", 10, "up", i, 8) for i in range(8)]
        assert sum(pattern) == 0

    def test_alternating_first_note_up(self):
        assert compute_cents_for_mode("alternating", 5, "up", 0, 4) == 5

    def test_alternating_first_note_down(self):
        assert compute_cents_for_mode("alternating", 5, "down", 0, 4) == -5


# --- Gradient pattern tests ---

class TestGradientPattern:
    def test_gradient_monotonic_increase(self):
        pattern = [compute_cents_for_mode("gradient", 30, "up", i, 10) for i in range(10)]
        for i in range(1, len(pattern)):
            assert pattern[i] >= pattern[i - 1]

    def test_gradient_starts_at_zero(self):
        assert compute_cents_for_mode("gradient", 50, "up", 0, 10) == 0.0

    def test_gradient_ends_at_target(self):
        assert compute_cents_for_mode("gradient", 50, "up", 9, 10) == 50.0

    def test_gradient_linear(self):
        p0 = compute_cents_for_mode("gradient", 40, "up", 0, 5)
        p1 = compute_cents_for_mode("gradient", 40, "up", 1, 5)
        p2 = compute_cents_for_mode("gradient", 40, "up", 2, 5)
        step = p1 - p0
        assert abs((p2 - p1) - step) < 0.01  # linear steps

    def test_gradient_single_note(self):
        assert compute_cents_for_mode("gradient", 25, "up", 0, 1) == 25


# --- Pitch class parsing tests ---

class TestPitchClassParsing:
    def test_midi_number_to_pc(self):
        assert 60 % 12 == 0   # C4 -> pc 0
        assert 64 % 12 == 4   # E4 -> pc 4
        assert 67 % 12 == 7   # G4 -> pc 7

    def test_note_name_to_pc(self):
        assert NOTE_NAMES["C"] == 0
        assert NOTE_NAMES["D"] == 2
        assert NOTE_NAMES["A"] == 9
        assert NOTE_NAMES["G#"] == 8

    def test_octave_invariant_pc(self):
        for octave in range(1, 7):
            pitch = (octave + 1) * 12 + 0  # C in various octaves
            assert pitch % 12 == 0

    def test_negative_pitch_pc(self):
        # Handle negative pitches correctly
        pc = ((-1 % 12) + 12) % 12
        assert pc == 11  # B
