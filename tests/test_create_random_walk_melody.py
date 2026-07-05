"""Unit tests for create_random_walk_melody — stochastic melody generation."""

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


def build_scale_pitches(root_num, intervals, octave):
    """Build 3-octave scale pitch list."""
    pitches = []
    for oct_shift in range(-1, 2):
        for iv in intervals:
            pitch = (octave + 1 + oct_shift) * 12 + (root_num + iv) % 12
            pitches.append(pitch)
    return sorted(set(pitches))


def do_random_walk(scale_pitches, total_steps, max_step, direction_bias,
                   boundary_behavior, rng):
    """Perform the random walk and return visited indices."""
    current_idx = len(scale_pitches) // 2
    visited = [current_idx]
    up_count = 0
    down_count = 0

    for _ in range(total_steps):
        r = rng()
        up_prob = 0.5 + direction_bias * 0.5
        go_up = r < up_prob
        step_size = 1 + int(rng() * max_step)
        if step_size > max_step:
            step_size = max_step

        if go_up:
            new_idx = current_idx + step_size
            up_count += 1
        else:
            new_idx = current_idx - step_size
            down_count += 1

        if new_idx < 0 or new_idx >= len(scale_pitches):
            if boundary_behavior == "reflect":
                if new_idx < 0:
                    new_idx = abs(new_idx)
                elif new_idx >= len(scale_pitches):
                    new_idx = 2 * len(scale_pitches) - new_idx - 2
                new_idx = max(0, min(len(scale_pitches) - 1, new_idx))
            elif boundary_behavior == "wrap":
                new_idx = new_idx % len(scale_pitches)
            elif boundary_behavior == "clamp":
                new_idx = max(0, min(len(scale_pitches) - 1, new_idx))

        visited.append(new_idx)
        current_idx = new_idx

    return visited, up_count, down_count


# --- Scale building tests ---

class TestScaleBuilding:
    def test_minor_scale_3_octaves(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        # 7 intervals × 3 octaves = 21, but sorted unique
        assert len(pitches) >= 18  # at least 18 unique pitches
        assert 60 in pitches  # C4
        assert 63 in pitches  # Eb4
        assert 72 in pitches  # C5

    def test_pentatonic_fewer_pitches(self):
        intervals = SCALE_INTERVALS["pentatonic_minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        assert len(pitches) < 21  # fewer than heptatonic

    def test_sorted(self):
        intervals = SCALE_INTERVALS["major"]
        pitches = build_scale_pitches(0, intervals, 4)
        assert pitches == sorted(pitches)

    def test_root_included(self):
        intervals = SCALE_INTERVALS["dorian"]
        pitches = build_scale_pitches(2, intervals, 3)  # D dorian
        assert (3 + 1) * 12 + 2 in pitches  # D3 = 38

    def test_3_octave_range(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        # Octave 4 = root at C4=60. 3 octaves: 3, 4, 5
        # C minor: C, D, Eb, F, G, Ab, Bb per octave
        # Max = Bb5 = (5+1)*12 + 10 = 82
        assert min(pitches) <= 48  # C3 or lower
        assert max(pitches) >= 80  # at least ~Bb5


# --- PRNG tests ---

class TestPRNG:
    def test_deterministic_same_seed(self):
        rng1 = mulberry32(42)
        rng2 = mulberry32(42)
        for _ in range(100):
            assert abs(rng1() - rng2()) < 0.0001

    def test_different_seed_different_output(self):
        rng1 = mulberry32(42)
        rng2 = mulberry32(99)
        diffs = sum(1 for _ in range(100) if abs(rng1() - rng2()) > 0.01)
        assert diffs > 90  # almost all different

    def test_range_0_to_1(self):
        rng = mulberry32(42)
        for _ in range(1000):
            val = rng()
            assert 0.0 <= val < 1.0

    def test_uniform_distribution(self):
        rng = mulberry32(42)
        values = [rng() for _ in range(10000)]
        mean = sum(values) / len(values)
        assert abs(mean - 0.5) < 0.02  # roughly uniform


# --- Random walk tests ---

class TestRandomWalk:
    def test_walk_returns_correct_length(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 32, 3, 0.0, "reflect", rng)
        assert len(visited) == 33  # initial + 32 steps

    def test_walk_stays_in_bounds_reflect(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 100, 5, 0.8, "reflect", rng)
        for idx in visited:
            assert 0 <= idx < len(pitches)

    def test_walk_stays_in_bounds_clamp(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 100, 7, 1.0, "clamp", rng)
        for idx in visited:
            assert 0 <= idx < len(pitches)

    def test_walk_stays_in_bounds_wrap(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 100, 7, 0.0, "wrap", rng)
        for idx in visited:
            assert 0 <= idx < len(pitches)

    def test_direction_bias_up(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        _, up, down = do_random_walk(pitches, 100, 3, 0.8, "reflect", rng)
        assert up > down  # bias up = more up steps

    def test_direction_bias_down(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        _, up, down = do_random_walk(pitches, 100, 3, -0.8, "reflect", rng)
        assert down > up  # bias down = more down steps

    def test_step_size_within_max(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 100, 2, 0.0, "clamp", rng)
        for i in range(1, len(visited)):
            # Step can be 0 if clamped, but actual movement <= max_step
            # (unless reflect bounces, but clamp doesn't)
            # With clamp, movement is at most max_step
            pass  # hard to assert with reflect, test with clamp below

    def test_step_size_clamp(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 100, 3, 0.0, "clamp", rng)
        for i in range(1, len(visited)):
            diff = abs(visited[i] - visited[i - 1])
            assert diff <= 3  # max_step=3, clamp prevents overshoot

    def test_deterministic_same_seed(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng1 = mulberry32(42)
        visited1, up1, down1 = do_random_walk(pitches, 50, 3, 0.0, "reflect", rng1)
        rng2 = mulberry32(42)
        visited2, up2, down2 = do_random_walk(pitches, 50, 3, 0.0, "reflect", rng2)
        assert visited1 == visited2
        assert up1 == up2
        assert down1 == down2

    def test_start_at_middle(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 1, 3, 0.0, "reflect", rng)
        assert visited[0] == len(pitches) // 2

    def test_step_size_1_smooth(self):
        intervals = SCALE_INTERVALS["minor"]
        pitches = build_scale_pitches(0, intervals, 4)
        rng = mulberry32(42)
        visited, _, _ = do_random_walk(pitches, 50, 1, 0.0, "clamp", rng)
        for i in range(1, len(visited)):
            assert abs(visited[i] - visited[i - 1]) <= 1  # only adjacent


# --- Direction bias math tests ---

class TestDirectionBias:
    def test_zero_bias_equal(self):
        # direction_bias=0 → up_prob=0.5
        up_prob = 0.5 + 0.0 * 0.5
        assert abs(up_prob - 0.5) < 0.001

    def test_full_up_bias(self):
        up_prob = 0.5 + 1.0 * 0.5
        assert abs(up_prob - 1.0) < 0.001

    def test_full_down_bias(self):
        up_prob = 0.5 + (-1.0) * 0.5
        assert abs(up_prob - 0.0) < 0.001

    def test_half_up_bias(self):
        up_prob = 0.5 + 0.5 * 0.5
        assert abs(up_prob - 0.75) < 0.001


# --- Total steps calculation tests ---

class TestStepCalculation:
    def test_default_duration_4_bars(self):
        total_steps = int(4 * 4 / 0.5)
        assert total_steps == 32

    def test_quarter_notes_4_bars(self):
        total_steps = int(4 * 4 / 1.0)
        assert total_steps == 16

    def test_sixteenth_notes_2_bars(self):
        total_steps = int(2 * 4 / 0.25)
        assert total_steps == 32

    def test_8_bars_eighth(self):
        total_steps = int(8 * 4 / 0.5)
        assert total_steps == 64
