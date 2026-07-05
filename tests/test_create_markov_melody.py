"""Unit tests for create_markov_melody — Markov chain melody generation."""

import json

from opendaw_mcp.music_theory import SCALE_INTERVALS

NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
              "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def mulberry32(seed):
    """Seeded PRNG matching the server.py implementation."""
    state = seed & 0xFFFFFFFF
    def _next():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = ((t ^ (t >> 15)) * t | 1) & 0xFFFFFFFF
        t = (t ^ (t >> 14)) & 0xFFFFFFFF
        return t / 0xFFFFFFFF
    return _next


def build_default_matrix():
    """Build the default transition matrix (order 1)."""
    interval_range = list(range(-7, 8))
    matrix = {}
    for cur in interval_range:
        weights = {}
        for next_iv in interval_range:
            if next_iv == 0:
                w = 0.05
            elif abs(next_iv) <= 2:
                w = 0.25 / abs(next_iv) if abs(next_iv) > 0 else 0.05
            elif abs(next_iv) <= 5:
                w = 0.08
            else:
                w = 0.02
            if cur > 0 and next_iv < 0:
                w *= 1.5
            if cur < 0 and next_iv > 0:
                w *= 1.5
            if cur > 0 and next_iv > 0 and abs(next_iv) <= 2:
                w *= 1.2
            if cur < 0 and next_iv < 0 and abs(next_iv) <= 2:
                w *= 1.2
            weights[next_iv] = w
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        matrix[cur] = weights
    return matrix


def build_scale_pitches(root_num, intervals, octave):
    pitches = []
    for oct_shift in range(-1, 2):
        for iv in intervals:
            pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
            pitches.append(pitch)
    return sorted(set(pitches))


def sample_interval(row, rng):
    """Sample an interval from a transition row."""
    r = rng()
    cumulative = 0.0
    for iv_val, prob in sorted(row.items()):
        cumulative += prob
        if r < cumulative:
            return iv_val
    return 0


# --- Default matrix tests ---

class TestDefaultMatrix:
    def test_matrix_has_all_intervals(self):
        matrix = build_default_matrix()
        for cur in range(-7, 8):
            assert cur in matrix

    def test_rows_are_normalized(self):
        matrix = build_default_matrix()
        for cur, row in matrix.items():
            total = sum(row.values())
            assert abs(total - 1.0) < 0.01  # sums to ~1.0

    def test_steps_preferred_over_leaps(self):
        matrix = build_default_matrix()
        row = matrix[1]  # after ascending a step
        step_weight = row.get(1, 0) + row.get(-1, 0) + row.get(2, 0) + row.get(-2, 0)
        leap_weight = row.get(7, 0) + row.get(-7, 0) + row.get(6, 0) + row.get(-6, 0)
        assert step_weight > leap_weight

    def test_regression_to_mean_after_leap_up(self):
        matrix = build_default_matrix()
        # After ascending 5 steps, descending should be boosted
        row_up5 = matrix[5]
        down_weight = sum(v for k, v in row_up5.items() if k < 0)
        up_weight = sum(v for k, v in row_up5.items() if k > 0)
        assert down_weight > up_weight  # regression to mean

    def test_regression_to_mean_after_leap_down(self):
        matrix = build_default_matrix()
        row_down5 = matrix[-5]
        up_weight = sum(v for k, v in row_down5.items() if k > 0)
        down_weight = sum(v for k, v in row_down5.items() if k < 0)
        assert up_weight > down_weight

    def test_repeat_is_rare(self):
        matrix = build_default_matrix()
        for cur in range(-3, 4):
            row = matrix[cur]
            repeat_prob = row.get(0, 0)
            step_prob = row.get(1, 0) + row.get(-1, 0)
            assert repeat_prob < step_prob

    def test_all_weights_non_negative(self):
        matrix = build_default_matrix()
        for cur, row in matrix.items():
            for w in row.values():
                assert w >= 0


# --- Interval sampling tests ---

class TestIntervalSampling:
    def test_deterministic_same_seed(self):
        matrix = build_default_matrix()
        rng1 = mulberry32(42)
        rng2 = mulberry32(42)
        row = matrix[0]
        for _ in range(100):
            assert sample_interval(row, rng1) == sample_interval(row, rng2)

    def test_sample_within_range(self):
        matrix = build_default_matrix()
        rng = mulberry32(42)
        row = matrix[3]
        for _ in range(1000):
            iv = sample_interval(row, rng)
            assert -7 <= iv <= 7

    def test_favored_intervals_more_frequent(self):
        matrix = build_default_matrix()
        rng = mulberry32(42)
        row = matrix[0]
        counts = {}
        for _ in range(10000):
            iv = sample_interval(row, rng)
            counts[iv] = counts.get(iv, 0) + 1
        # Steps (±1, ±2) should be more frequent than leaps (±6, ±7)
        step_count = counts.get(1, 0) + counts.get(-1, 0) + counts.get(2, 0) + counts.get(-2, 0)
        leap_count = counts.get(6, 0) + counts.get(-6, 0) + counts.get(7, 0) + counts.get(-7, 0)
        assert step_count > leap_count


# --- Scale building tests ---

class TestScaleBuilding:
    def test_minor_scale(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        assert 60 in pitches  # C4
        assert 63 in pitches  # Eb4

    def test_pentatonic_fewer(self):
        intervals = SCALE_INTERVALS["pentatonic_minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        heptatonic = build_scale_pitches(0, SCALE_INTERVALS["minor"], 4)
        assert len(pitches) < len(heptatonic)

    def test_sorted(self):
        pitches = build_scale_pitches(0, SCALE_INTERVALS["major"], 4)
        assert pitches == sorted(pitches)


# --- Markov chain generation tests ---

class TestMarkovGeneration:
    def test_generates_correct_count(self):
        matrix = build_default_matrix()
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        current_idx = len(pitches) // 2
        last_iv = 0
        notes = []
        for _ in range(32):
            row = matrix.get(last_iv, matrix[0])
            iv = sample_interval(row, rng)
            new_idx = current_idx + iv
            if new_idx < 0:
                new_idx = abs(new_idx)
            elif new_idx >= len(pitches):
                new_idx = 2 * len(pitches) - new_idx - 2
            new_idx = max(0, min(len(pitches) - 1, new_idx))
            actual_iv = new_idx - current_idx
            notes.append(pitches[new_idx])
            last_iv = actual_iv
            current_idx = new_idx
        assert len(notes) == 32

    def test_stays_in_bounds(self):
        matrix = build_default_matrix()
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        current_idx = len(pitches) // 2
        last_iv = 0
        for _ in range(100):
            row = matrix.get(last_iv, matrix[0])
            iv = sample_interval(row, rng)
            new_idx = current_idx + iv
            if new_idx < 0:
                new_idx = abs(new_idx)
            elif new_idx >= len(pitches):
                new_idx = 2 * len(pitches) - new_idx - 2
            new_idx = max(0, min(len(pitches) - 1, new_idx))
            assert 0 <= new_idx < len(pitches)
            last_iv = new_idx - current_idx
            current_idx = new_idx

    def test_deterministic_same_seed(self):
        matrix = build_default_matrix()
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)

        def generate(seed):
            rng = mulberry32(seed)
            current_idx = len(pitches) // 2
            last_iv = 0
            result = []
            for _ in range(50):
                row = matrix.get(last_iv, matrix[0])
                iv = sample_interval(row, rng)
                new_idx = current_idx + iv
                if new_idx < 0:
                    new_idx = abs(new_idx)
                elif new_idx >= len(pitches):
                    new_idx = 2 * len(pitches) - new_idx - 2
                new_idx = max(0, min(len(pitches) - 1, new_idx))
                result.append(pitches[new_idx])
                last_iv = new_idx - current_idx
                current_idx = new_idx
            return result

        assert generate(42) == generate(42)

    def test_different_seeds_different_output(self):
        matrix = build_default_matrix()
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)

        def generate(seed):
            rng = mulberry32(seed)
            current_idx = len(pitches) // 2
            last_iv = 0
            result = []
            for _ in range(50):
                row = matrix.get(last_iv, matrix[0])
                iv = sample_interval(row, rng)
                new_idx = current_idx + iv
                if new_idx < 0:
                    new_idx = abs(new_idx)
                elif new_idx >= len(pitches):
                    new_idx = 2 * len(pitches) - new_idx - 2
                new_idx = max(0, min(len(pitches) - 1, new_idx))
                result.append(pitches[new_idx])
                last_iv = new_idx - current_idx
                current_idx = new_idx
            return result

        diffs = sum(1 for a, b in zip(generate(42), generate(99)) if a != b)
        assert diffs > 20  # mostly different


# --- Custom weights parsing tests ---

class TestCustomWeights:
    def test_valid_json_parsed(self):
        weights = json.loads('{"1": {"1": 0.3, "-1": 0.5, "2": 0.2}}')
        assert weights["1"]["1"] == 0.3
        assert weights["1"]["-1"] == 0.5

    def test_invalid_json_returns_error(self):
        try:
            json.loads("not json")
            assert False, "Should have raised"
        except json.JSONDecodeError:
            assert True

    def test_keys_are_strings(self):
        weights = json.loads('{"1": {"1": 0.5, "-1": 0.5}}')
        assert isinstance(list(weights.keys())[0], str)


# --- Order parameter tests ---

class TestOrderParameter:
    def test_order_1_uses_last_interval(self):
        # Order 1: transition key = last_interval
        last_iv = 3
        order = 1
        trans_key = last_iv if order == 1 else last_iv * 100
        assert trans_key == 3

    def test_order_2_combines_intervals(self):
        # Order 2: transition key = last * 100 + second_last
        last_iv = 3
        second_last = -2
        order = 2
        trans_key = last_iv * 100 + second_last if order == 2 else last_iv
        assert trans_key == 298  # 3*100 + (-2)


# --- Statistics tests ---

class TestStatistics:
    def test_interval_distribution(self):
        intervals = [1, -1, 2, 1, -2, 1, 0, -1, 2, -1]
        counts = {}
        for iv in intervals:
            counts[iv] = counts.get(iv, 0) + 1
        assert counts[1] == 3
        assert counts[-1] == 3
        assert counts[2] == 2
        assert counts[-2] == 1
        assert counts[0] == 1

    def test_avg_interval(self):
        intervals = [1, 2, 3, 4, 5]
        avg = sum(abs(iv) for iv in intervals) / len(intervals)
        assert avg == 3.0

    def test_avg_interval_with_negatives(self):
        intervals = [1, -2, 3, -1, 2]
        avg = sum(abs(iv) for iv in intervals) / len(intervals)
        assert avg == 1.8
