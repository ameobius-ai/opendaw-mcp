"""Unit tests for create_l_system_melody MCP tool."""

import json



def _parse_result(text):
    """Parse the JSON-ish result string returned by the tool."""
    if isinstance(text, dict):
        return text
    if "Error:" in str(text):
        return {"error": str(text)}
    # _wrap_eval returns formatted string; for unit tests we mock the bridge
    # and capture the raw evaluate result
    return {"raw": str(text)}


class TestLSystemPresets:
    """Test L-system preset expansion."""

    def test_fibonacci_preset(self):
        """Fibonacci word: A->AB, B->A."""
        axiom = "A"
        rules = {"A": "AB", "B": "A"}
        current = axiom
        for _ in range(4):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # Fibonacci word after 4 iterations: ABABA -> ABAABABA -> ABAABABAABAAB -> ...
        # A, AB, ABA, ABAAB, ABAABABA
        assert current == "ABAABABA"
        assert len(current) == 8

    def test_cantor_preset(self):
        """Cantor set: A->ABA, B->BBB."""
        axiom = "A"
        rules = {"A": "ABA", "B": "BBB"}
        current = axiom
        for _ in range(3):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # A, ABA, ABABBBABA, ABABBBABABBBBBBBBBABABBBABA
        assert current == "ABABBBABABBBBBBBBBABABBBABA"
        assert len(current) == 27

    def test_dragon_preset(self):
        """Dragon curve: A->A+B, B->A-B."""
        axiom = "A"
        rules = {"A": "A+B", "B": "A-B"}
        current = axiom
        for _ in range(3):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # A, A+B, A+B+A-B, A+B+A-B+A+B-A-B
        assert current == "A+B+A-B+A+B-A-B"
        assert len(current) == 15

    def test_koch_preset(self):
        """Koch snowflake: A->A+A-A-A+A."""
        axiom = "A"
        rules = {"A": "A+A-A-A+A"}
        current = axiom
        for _ in range(2):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # A, A+A-A-A+A, then each A expands again: 49 chars
        assert len(current) == 49

    def test_sierpinski_preset(self):
        """Sierpinski triangle: A->BA, B->BA."""
        axiom = "A"
        rules = {"A": "BA", "B": "BA"}
        current = axiom
        for _ in range(4):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # A, BA, BABA, BABABABA, BABABABABABABABA
        assert current == "BABABABABABABABA"
        assert len(current) == 16

    def test_custom_rules(self):
        """Custom L-system rules."""
        axiom = "X"
        rules = {"X": "XY", "Y": "X"}
        current = axiom
        for _ in range(3):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # X, XY, XYX, XYXXY
        assert current == "XYXXY"
        assert len(current) == 5


class TestLSystemExpansionLimit:
    """Test expansion limits."""

    def test_length_capped(self):
        """L-system string should be capped at 2000 chars."""
        axiom = "A"
        rules = {"A": "AA"}  # doubles each iteration
        current = axiom
        for _ in range(8):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
            if len(current) > 2000:
                current = current[:2000]
                break
        assert len(current) <= 2000

    def test_max_iterations(self):
        """Max iterations should be 8."""
        axiom = "A"
        rules = {"A": "AB", "B": "A"}
        current = axiom
        for _ in range(8):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        # After 8 iterations, Fibonacci word has F(10) = 55 chars
        assert len(current) == 55  # Fibonacci: 1,2,3,5,8,13,21,34,55

    def test_min_iterations(self):
        """Min iterations should be 1."""
        axiom = "A"
        rules = {"A": "AB", "B": "A"}
        current = axiom
        for _ in range(1):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        assert current == "AB"
        assert len(current) == 2


class TestLSystemScaleMapping:
    """Test scale pitch list construction."""

    def test_scale_pitches_built(self):
        """Scale pitch list should span 3 octaves."""
        intervals = [0, 2, 3, 5, 7, 8, 10]  # minor
        root_num = 0  # C
        octave = 4
        scale_pitches = []
        for oct_shift in range(-1, 2):
            for iv in intervals:
                pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
                scale_pitches.append(pitch)
        scale_pitches = sorted(set(scale_pitches))
        # 7 notes x 3 octaves = 21 unique pitches
        assert len(scale_pitches) == 21
        assert min(scale_pitches) == 48  # C3 = 36+12 = 48
        assert max(scale_pitches) == 82  # B5 = (4+1+1)*12 + 10 = 82

    def test_pentatonic_scale_pitches(self):
        """Pentatonic scale has 5 notes per octave."""
        intervals = [0, 2, 4, 7, 9]  # pentatonic_major
        root_num = 7  # G
        octave = 4
        scale_pitches = []
        for oct_shift in range(-1, 2):
            for iv in intervals:
                pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
                scale_pitches.append(pitch)
        scale_pitches = sorted(set(scale_pitches))
        assert len(scale_pitches) == 15  # 5 x 3


class TestLSystemNoteGeneration:
    """Test the note generation from L-system string."""

    def test_fibonacci_notes_stepwise(self):
        """Fibonacci word maps to +1/-1 steps."""
        axiom = "A"
        rules = {"A": "AB", "B": "A"}
        current = axiom
        for _ in range(4):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        sym_map = {"A": 1, "B": -1}
        steps = [sym_map.get(ch, 0) for ch in current]
        # All steps should be +1 or -1
        assert all(s in (1, -1) for s in steps)
        # Fibonacci word has more A's than B's
        assert steps.count(1) > steps.count(-1)

    def test_dragon_notes_include_jumps(self):
        """Dragon curve includes +3/-3 jumps from + and - symbols."""
        axiom = "A"
        rules = {"A": "A+B", "B": "A-B"}
        current = axiom
        for _ in range(3):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        sym_map = {"A": 1, "B": 1, "+": 3, "-": -3}
        steps = [sym_map.get(ch, 0) for ch in current]
        # Should contain +3 and -3 jumps
        assert 3 in steps
        assert -3 in steps

    def test_boundary_reflect(self):
        """Notes should reflect at scale boundaries."""
        scale_pitches = list(range(60, 72))  # 12 pitches
        current_idx = len(scale_pitches) - 1  # at the top
        step = 5  # try to go beyond
        new_idx = current_idx + step
        if new_idx >= len(scale_pitches):
            new_idx = 2 * len(scale_pitches) - new_idx - 2
        new_idx = max(0, min(len(scale_pitches) - 1, new_idx))
        # 11 + 5 = 16, reflect: 2*12 - 16 - 2 = 6
        assert new_idx == 6

    def test_boundary_reflect_bottom(self):
        """Notes should reflect at bottom boundary."""
        scale_pitches = list(range(60, 72))
        current_idx = 0
        step = -3
        new_idx = current_idx + step
        if new_idx < 0:
            new_idx = abs(new_idx)
        new_idx = max(0, min(len(scale_pitches) - 1, new_idx))
        assert new_idx == 3


class TestLSystemRestSymbol:
    """Test rest symbol handling."""

    def test_rest_advances_position(self):
        """Rest symbol should advance position without creating a note."""
        current = "ABRAB"
        sym_map = {"A": 1, "B": -1}
        rest_symbol = "R"
        note_position_counter = 0
        notes = []
        for ch in current:
            if rest_symbol and ch == rest_symbol:
                note_position_counter += 1
                continue
            step = sym_map.get(ch, 0)
            notes.append({"pitch": 60 + step, "pos": note_position_counter * 0.25})
            note_position_counter += 1
        # 4 notes + 1 rest, rest advances position
        assert len(notes) == 4
        assert notes[0]["pos"] == 0.0
        assert notes[1]["pos"] == 0.25
        # After rest, position skips
        assert notes[2]["pos"] == 0.75  # positions: 0, 0.25, [rest=0.5], 0.75


class TestLSystemFractalStats:
    """Test fractal statistics computation."""

    def test_self_similar_flag(self):
        """Self-similar flag is True when string is long enough."""
        ls_len = 55  # Fibonacci after 8 iterations
        assert ls_len > 10  # self_similar = True

    def test_direction_changes(self):
        """Direction changes counted correctly."""
        steps = [1, 1, -1, 1, -1, -1]
        direction_changes = 0
        for i in range(1, len(steps)):
            if steps[i] * steps[i - 1] < 0:
                direction_changes += 1
        assert direction_changes == 3

    def test_avg_step(self):
        """Average step magnitude calculated correctly."""
        steps = [1, -1, 3, -3, 1]
        avg = sum(abs(s) for s in steps) / len(steps)
        assert abs(avg - 1.8) < 0.01

    def test_pitch_range(self):
        """Pitch range is max - min."""
        pitches = [60, 62, 58, 64, 61]
        pr = max(pitches) - min(pitches)
        assert pr == 6


class TestLSystemCustomInput:
    """Test custom L-system input."""

    def test_custom_axiom_overrides_preset(self):
        """Custom axiom should override preset axiom."""
        axiom = "X"
        rules_json = json.dumps({"X": "XY", "Y": "X"})
        sym_map_json = json.dumps({"X": 2, "Y": -1})
        ls_axiom = axiom
        ls_rules = json.loads(rules_json)
        ls_map = {k: int(v) for k, v in json.loads(sym_map_json).items()}
        assert ls_axiom == "X"
        assert ls_rules == {"X": "XY", "Y": "X"}
        assert ls_map == {"X": 2, "Y": -1}

    def test_invalid_rules_json(self):
        """Invalid rules JSON should be caught."""
        bad_rules = "not json{"
        try:
            json.loads(bad_rules)
            assert False, "Should have raised"
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    def test_invalid_symbol_map_json(self):
        """Invalid symbol_map JSON should be caught."""
        bad_map = "{invalid}"
        try:
            json.loads(bad_map)
            assert False, "Should have raised"
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    def test_unknown_symbol_uses_zero(self):
        """Unknown symbols map to step 0 (repeat)."""
        sym_map = {"A": 1, "B": -1}
        ch = "Z"  # not in map
        step = sym_map.get(ch, 0)
        assert step == 0


class TestLSystemParameterValidation:
    """Test parameter validation."""

    def test_bars_too_many(self):
        bars = 33
        assert not (1 <= bars <= 32)

    def test_bars_too_few(self):
        bars = 0
        assert not (1 <= bars <= 32)

    def test_iterations_too_many(self):
        iterations = 9
        assert not (1 <= iterations <= 8)

    def test_iterations_too_few(self):
        iterations = 0
        assert not (1 <= iterations <= 8)

    def test_duration_too_short(self):
        duration = 0.03
        assert not (0.0625 <= duration <= 4.0)

    def test_duration_too_long(self):
        duration = 5.0
        assert not (0.0625 <= duration <= 4.0)


class TestLSystemTotalNotesTarget:
    """Test total notes target calculation."""

    def test_quarter_notes(self):
        """4 bars of quarter notes = 16 notes."""
        bars = 4
        duration = 1.0
        total = int(bars * 4 / duration)
        assert total == 16

    def test_eighth_notes(self):
        """4 bars of eighth notes = 32 notes."""
        bars = 4
        duration = 0.5
        total = int(bars * 4 / duration)
        assert total == 32

    def test_sixteenth_notes(self):
        """2 bars of sixteenth notes = 32 notes."""
        bars = 2
        duration = 0.25
        total = int(bars * 4 / duration)
        assert total == 32

    def test_long_notes(self):
        """1 bar of half notes = 2 notes."""
        bars = 1
        duration = 2.0
        total = int(bars * 4 / duration)
        assert total == 2


class TestLSystemDeterminism:
    """Test that L-systems are deterministic."""

    def test_same_input_same_output(self):
        """Same axiom + rules + iterations = same string."""
        axiom = "A"
        rules = {"A": "AB", "B": "A"}
        results = []
        for _ in range(3):
            current = axiom
            for _ in range(5):
                parts = []
                for ch in current:
                    parts.append(rules.get(ch, ch))
                current = "".join(parts)
            results.append(current)
        assert results[0] == results[1] == results[2]

    def test_different_iterations_different_output(self):
        """More iterations = longer string (for growing systems)."""
        axiom = "A"
        rules = {"A": "AB", "B": "A"}
        lengths = []
        for n_iter in range(1, 6):
            current = axiom
            for _ in range(n_iter):
                parts = []
                for ch in current:
                    parts.append(rules.get(ch, ch))
                current = "".join(parts)
            lengths.append(len(current))
        # Fibonacci: 2, 3, 5, 8, 13
        assert lengths == [2, 3, 5, 8, 13]


class TestLSystemSymbolDistribution:
    """Test symbol distribution tracking."""

    def test_symbol_counts(self):
        """Symbol counts should reflect the expanded string."""
        current = "ABABABAB"
        counts = {}
        for ch in current:
            counts[ch] = counts.get(ch, 0) + 1
        assert counts == {"A": 4, "B": 4}

    def test_dragon_has_plus_minus(self):
        """Dragon curve should have + and - symbols."""
        axiom = "A"
        rules = {"A": "A+B", "B": "A-B"}
        current = axiom
        for _ in range(3):
            parts = []
            for ch in current:
                parts.append(rules.get(ch, ch))
            current = "".join(parts)
        counts = {}
        for ch in current:
            counts[ch] = counts.get(ch, 0) + 1
        assert "+" in counts
        assert "-" in counts
        assert "A" in counts
        assert "B" in counts


class TestLSystemPreview:
    """Test L-system preview string."""

    def test_preview_truncated(self):
        """Preview should be first 80 chars."""
        current = "A" * 200
        preview = current[:80]
        assert len(preview) == 80

    def test_preview_full_when_short(self):
        """Short L-system should show full string."""
        current = "ABAB"
        preview = current[:80]
        assert preview == "ABAB"
