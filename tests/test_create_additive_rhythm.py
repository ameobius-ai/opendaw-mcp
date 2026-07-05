"""Unit tests for create_additive_rhythm — additive rhythm tool."""

NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
              "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "blues": [0, 3, 5, 6, 7, 10],
}

UNIT_BEATS = {
    "eighth": 0.5,
    "quarter": 1.0,
    "sixteenth": 0.25,
    "thirty_second": 0.125,
}


def parse_grouping(grouping):
    parts = grouping.replace(" ", "").split("+")
    return [int(p) for p in parts]


def build_accent_indices(groups, accent_mode):
    """Return set of note indices that get accented."""
    accent_indices = set()
    if accent_mode == "group_start":
        idx = 0
        for g in groups:
            accent_indices.add(idx)
            idx += g
    elif accent_mode == "group_end":
        idx = 0
        for g in groups:
            idx += g - 1
            accent_indices.add(idx)
            idx += 1
    return accent_indices


def build_note_schedule(groups, unit_beats, repeats, accent_mode,
                        accent_velocity, normal_velocity, decay):
    """Build the full note schedule for all bars."""
    accent_indices = build_accent_indices(groups, accent_mode)
    total_notes = sum(groups)
    bar_length = total_notes * unit_beats
    schedule = []
    for bar in range(repeats):
        bar_start = bar * bar_length
        note_idx_in_bar = 0
        group_idx = 0
        for g in groups:
            for within_group in range(g):
                pos = bar_start + note_idx_in_bar * unit_beats
                is_accented = note_idx_in_bar in accent_indices
                base_vel = accent_velocity if is_accented else normal_velocity
                vel = max(0.01, base_vel - decay * within_group)
                schedule.append({
                    "pos": round(pos, 4),
                    "vel": round(vel, 4),
                    "accent": is_accented,
                    "bar": bar,
                    "group": group_idx,
                    "note_in_bar": note_idx_in_bar,
                })
                note_idx_in_bar += 1
            group_idx += 1
    return schedule


def pitch_for_note(idx, pitch_mode, octave, root_pc, scale_pcs):
    if pitch_mode == "root":
        return (octave + 1) * 12 + root_pc
    elif pitch_mode == "scale_up":
        pc = scale_pcs[idx % len(scale_pcs)]
        octave_shift = idx // len(scale_pcs)
        return (octave + 1 + octave_shift) * 12 + (pc + root_pc) % 12
    elif pitch_mode == "scale_down":
        rev_idx = idx % len(scale_pcs)
        pc = scale_pcs[-(rev_idx + 1)]
        octave_shift = idx // len(scale_pcs)
        return max(0, (octave + 1 - octave_shift) * 12 + (pc + root_pc) % 12)
    elif pitch_mode == "alternating":
        if idx % 2 == 0:
            return (octave + 1) * 12 + root_pc
        pc = scale_pcs[1 % len(scale_pcs)]
        return (octave + 1) * 12 + (pc + root_pc) % 12
    elif pitch_mode == "octave_bounce":
        if idx % 2 == 0:
            return (octave + 1) * 12 + root_pc
        return (octave + 2) * 12 + root_pc
    return (octave + 1) * 12 + root_pc


# --- Grouping parsing tests ---

class TestGroupingParsing:
    def test_simple_two_group(self):
        assert parse_grouping("3+2") == [3, 2]

    def test_three_group(self):
        assert parse_grouping("3+2+2") == [3, 2, 2]

    def test_with_spaces(self):
        assert parse_grouping("3 + 2 + 2") == [3, 2, 2]

    def test_shifting_accent(self):
        assert parse_grouping("2+3+2") == [2, 3, 2]

    def test_five_three(self):
        assert parse_grouping("5+3") == [5, 3]

    def test_six_groups(self):
        groups = parse_grouping("2+1+2+1+2+1")
        assert len(groups) == 6

    def test_total_sum(self):
        groups = parse_grouping("3+2+2")
        assert sum(groups) == 7

    def test_eight_notes(self):
        groups = parse_grouping("5+3")
        assert sum(groups) == 8

    def test_two_notes(self):
        groups = parse_grouping("1+1")
        assert sum(groups) == 2


# --- Accent pattern tests ---

class TestAccentPattern:
    def test_group_start_322(self):
        groups = [3, 2, 2]
        accents = build_accent_indices(groups, "group_start")
        assert accents == {0, 3, 5}

    def test_group_start_53(self):
        groups = [5, 3]
        accents = build_accent_indices(groups, "group_start")
        assert accents == {0, 5}

    def test_group_end_322(self):
        groups = [3, 2, 2]
        accents = build_accent_indices(groups, "group_end")
        assert accents == {2, 4, 6}

    def test_group_end_53(self):
        groups = [5, 3]
        accents = build_accent_indices(groups, "group_end")
        assert accents == {4, 7}

    def test_shifting_accent_232(self):
        groups = [2, 3, 2]
        accents = build_accent_indices(groups, "group_start")
        assert accents == {0, 2, 5}

    def test_group_start_2121(self):
        groups = [2, 1, 2, 1]
        accents = build_accent_indices(groups, "group_start")
        assert accents == {0, 2, 3, 5}

    def test_group_end_2121(self):
        groups = [2, 1, 2, 1]
        accents = build_accent_indices(groups, "group_end")
        assert accents == {1, 2, 4, 5}


# --- Note schedule tests ---

class TestNoteSchedule:
    def test_total_notes_single_bar(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.0)
        assert len(schedule) == 7

    def test_total_notes_four_bars(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 4, "group_start", 0.95, 0.6, 0.0)
        assert len(schedule) == 28

    def test_positions_first_bar(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.0)
        expected_positions = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        actual_positions = [n["pos"] for n in schedule]
        assert actual_positions == expected_positions

    def test_bar_start_offset(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 2, "group_start", 0.95, 0.6, 0.0)
        bar_length = 7 * 0.5  # 3.5 beats
        first_of_bar2 = schedule[7]["pos"]
        assert abs(first_of_bar2 - bar_length) < 0.001

    def test_velocity_accents(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.0)
        # Notes 0, 3, 5 are accented (group starts)
        assert schedule[0]["vel"] == 0.95
        assert schedule[3]["vel"] == 0.95
        assert schedule[5]["vel"] == 0.95
        assert schedule[1]["vel"] == 0.6
        assert schedule[2]["vel"] == 0.6

    def test_decay_within_group(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.1)
        # Group 0: notes 0, 1, 2 — accent at 0, then decay
        assert abs(schedule[0]["vel"] - 0.95) < 0.01
        assert abs(schedule[1]["vel"] - 0.5) < 0.01  # 0.6 - 0.1*1
        assert abs(schedule[2]["vel"] - 0.4) < 0.01  # 0.6 - 0.1*2

    def test_bar_assignment(self):
        groups = [5, 3]
        schedule = build_note_schedule(groups, 0.5, 3, "group_start", 0.95, 0.6, 0.0)
        bars = set(n["bar"] for n in schedule)
        assert bars == {0, 1, 2}

    def test_group_assignment(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.0)
        group_assignments = [n["group"] for n in schedule]
        assert group_assignments == [0, 0, 0, 1, 1, 2, 2]

    def test_velocity_floor(self):
        groups = [8]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.3)
        # Heavy decay: note 7 should be 0.6 - 0.3*7 = -1.5, clamped to 0.01
        assert schedule[7]["vel"] == 0.01

    def test_bar_length_eighth_322(self):
        groups = [3, 2, 2]
        total = sum(groups)
        bar_len = total * UNIT_BEATS["eighth"]
        assert abs(bar_len - 3.5) < 0.001

    def test_bar_length_sixteenth_322(self):
        groups = [3, 2, 2]
        total = sum(groups)
        bar_len = total * UNIT_BEATS["sixteenth"]
        assert abs(bar_len - 1.75) < 0.001


# --- Pitch generation tests ---

class TestPitchGeneration:
    def test_root_mode(self):
        pitch = pitch_for_note(0, "root", 4, 0, SCALES["minor"])
        assert pitch == 60  # C4

    def test_root_mode_same_all(self):
        for i in range(10):
            pitch = pitch_for_note(i, "root", 4, 0, SCALES["minor"])
            assert pitch == 60

    def test_scale_up_minor(self):
        root_pc = NOTE_NAMES["C"]
        scale_pcs = SCALES["minor"]
        p0 = pitch_for_note(0, "scale_up", 4, root_pc, scale_pcs)
        p1 = pitch_for_note(1, "scale_up", 4, root_pc, scale_pcs)
        assert p0 == 60  # C
        assert p1 == 62  # D (minor: C, D, Eb, F, G, Ab, Bb)

    def test_scale_up_wraps_octave(self):
        root_pc = NOTE_NAMES["C"]
        scale_pcs = SCALES["minor"]
        # After 7 notes (full scale), should go up an octave
        p7 = pitch_for_note(7, "scale_up", 4, root_pc, scale_pcs)
        assert p7 == 72  # C5

    def test_octave_bounce(self):
        p0 = pitch_for_note(0, "octave_bounce", 4, 0, SCALES["minor"])
        p1 = pitch_for_note(1, "octave_bounce", 4, 0, SCALES["minor"])
        assert p0 == 60  # C4
        assert p1 == 72  # C5

    def test_alternating(self):
        p0 = pitch_for_note(0, "alternating", 4, 0, SCALES["minor"])
        p1 = pitch_for_note(1, "alternating", 4, 0, SCALES["minor"])
        assert p0 == 60  # root
        assert p1 == 62  # second scale degree

    def test_scale_down(self):
        root_pc = NOTE_NAMES["C"]
        scale_pcs = SCALES["minor"]
        p0 = pitch_for_note(0, "scale_down", 4, root_pc, scale_pcs)
        # First note of scale_down = last scale degree
        assert p0 == 70  # Bb (last of C minor: 10)

    def test_root_different_octave(self):
        pitch = pitch_for_note(0, "root", 2, 0, SCALES["minor"])
        assert pitch == 36  # C2


# --- Unit value tests ---

class TestUnitValues:
    def test_eighth(self):
        assert UNIT_BEATS["eighth"] == 0.5

    def test_quarter(self):
        assert UNIT_BEATS["quarter"] == 1.0

    def test_sixteenth(self):
        assert UNIT_BEATS["sixteenth"] == 0.25

    def test_thirty_second(self):
        assert UNIT_BEATS["thirty_second"] == 0.125


# --- Integration: full schedule correctness ---

class TestScheduleIntegration:
    def test_322_eighth_one_bar(self):
        groups = [3, 2, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.0)
        assert len(schedule) == 7
        accents = [n for n in schedule if n["accent"]]
        assert len(accents) == 3
        assert schedule[0]["pos"] == 0.0
        assert schedule[6]["pos"] == 3.0

    def test_53_eighth_two_bars(self):
        groups = [5, 3]
        schedule = build_note_schedule(groups, 0.5, 2, "group_start", 0.95, 0.6, 0.0)
        assert len(schedule) == 16
        # Bar 0: positions 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5
        # Bar 1: positions 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5
        assert schedule[0]["pos"] == 0.0
        assert schedule[8]["pos"] == 4.0
        assert schedule[15]["pos"] == 7.5

    def test_232_shifting_accent(self):
        groups = [2, 3, 2]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.95, 0.6, 0.0)
        # Accents at notes 0, 2, 5 (group starts)
        assert schedule[0]["accent"] is True
        assert schedule[2]["accent"] is True
        assert schedule[5]["accent"] is True
        assert schedule[1]["accent"] is False
        assert schedule[6]["accent"] is False

    def test_decay_accumulates_within_group(self):
        groups = [4, 4]
        schedule = build_note_schedule(groups, 0.5, 1, "group_start", 0.9, 0.7, 0.15)
        # Group 0: notes 0, 1, 2, 3
        assert abs(schedule[0]["vel"] - 0.9) < 0.01   # accent
        assert abs(schedule[1]["vel"] - 0.55) < 0.01  # 0.7 - 0.15
        assert abs(schedule[2]["vel"] - 0.4) < 0.01   # 0.7 - 0.30
        assert abs(schedule[3]["vel"] - 0.25) < 0.01  # 0.7 - 0.45
        # Group 1: notes 4, 5, 6, 7 — decay resets
        assert abs(schedule[4]["vel"] - 0.9) < 0.01   # accent (group start)
        assert abs(schedule[5]["vel"] - 0.55) < 0.01  # 0.7 - 0.15
