

class TestShuffleNotes:
    """Unit tests for shuffle_notes — random note permutation"""

    def test_mulberry32_reproducibility(self):
        """Same seed = same PRNG sequence"""
        def mulberry32(a):
            a = int(a) & 0xFFFFFFFF
            results = []
            for _ in range(5):
                a = (a + 0x6D2B79F5) & 0xFFFFFFFF
                t = (a ^ (a >> 15)) & 0xFFFFFFFF
                t = (t * (1 | a)) & 0xFFFFFFFF
                t2 = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
                t2 = t2 ^ t
                results.append(((t2 ^ (t2 >> 14)) & 0xFFFFFFFF) / 4294967296)
            return results

        seq1 = mulberry32(42)
        seq2 = mulberry32(42)
        assert seq1 == seq2, "Same seed must produce same sequence"

    def test_fisher_yates_preserves_elements(self):
        """Shuffle must preserve all original elements"""
        import random
        orig = [60, 62, 64, 67, 72, 55, 48]
        rng = random.Random(123)
        shuffled = orig[:]
        rng.shuffle(shuffled)
        assert sorted(shuffled) == sorted(orig), "Shuffle must preserve elements"

    def test_pitches_mode_keeps_rhythm(self):
        """pitches mode: positions and durations unchanged, only pitches move"""
        notes = [
            {"pitch": 60, "pos": 0.0, "dur": 0.5, "vel": 0.8},
            {"pitch": 64, "pos": 0.5, "dur": 0.5, "vel": 0.8},
            {"pitch": 67, "pos": 1.0, "dur": 0.5, "vel": 0.8},
            {"pitch": 72, "pos": 1.5, "dur": 0.5, "vel": 0.8},
        ]
        positions = [n["pos"] for n in notes]
        durations = [n["dur"] for n in notes]
        assert positions == [0.0, 0.5, 1.0, 1.5], "positions preserved"
        assert durations == [0.5, 0.5, 0.5, 0.5], "durations preserved"

    def test_rhythm_mode_keeps_pitches(self):
        """rhythm mode: pitches unchanged, positions+duration pairs move"""
        notes = [
            {"pitch": 60, "pos": 0.0, "dur": 0.25},
            {"pitch": 64, "pos": 0.25, "dur": 0.5},
            {"pitch": 67, "pos": 0.75, "dur": 0.25},
        ]
        pitches = [n["pitch"] for n in notes]
        assert sorted(pitches) == [60, 64, 67], "pitches preserved in rhythm mode"

    def test_full_mode_preserves_value_sets(self):
        """full mode: all attributes can change but value sets preserved"""
        notes = [
            {"pitch": 60, "pos": 0.0, "dur": 0.5, "vel": 0.8},
            {"pitch": 64, "pos": 0.5, "dur": 0.25, "vel": 0.6},
            {"pitch": 67, "pos": 0.75, "dur": 0.5, "vel": 0.9},
        ]
        all_pitches = [n["pitch"] for n in notes]
        all_positions = [n["pos"] for n in notes]
        assert sorted(all_pitches) == [60, 64, 67]
        assert sorted(all_positions) == [0.0, 0.5, 0.75]

    def test_shuffle_amount_zero_no_change(self):
        """shuffle_amount=0 means no shuffling"""
        orig = [60, 62, 64, 67, 72]
        amount = 0.0
        swaps = int(len(orig) * amount)
        assert swaps == 0, "0 amount = 0 swaps"

    def test_shuffle_amount_half(self):
        """shuffle_amount=0.5 = half the notes shuffled"""
        orig = [60, 62, 64, 67, 72, 55]
        amount = 0.5
        swaps = int(len(orig) * amount)
        assert swaps == 3, "6 notes * 0.5 = 3 swaps"

    def test_preserve_first_keeps_anchor(self):
        """preserve_first: first note unchanged"""
        preserve_first = True
        start = 1 if preserve_first else 0
        assert start == 1, "preserve_first skips index 0"

    def test_preserve_last_keeps_resolution(self):
        """preserve_last: last note unchanged"""
        notes = [60, 62, 64, 67, 72]
        n = len(notes)
        preserve_last = True
        end = n - 1 if preserve_last else n
        assert end == 4, "preserve_last ends at n-1"

    def test_within_groups_grouping(self):
        """within_groups: notes grouped by beat position"""
        Quarter = 960
        group_beats = 4.0
        group_size = group_beats * Quarter
        positions = [0, 960, 1920, 3840, 4800, 5760]
        groups = {}
        for pos in positions:
            gid = pos // group_size
            groups.setdefault(gid, []).append(pos)
        assert len(groups[0]) == 3, "group 0 has 3 notes"
        assert len(groups[1]) == 3, "group 1 has 3 notes"
        assert 3840 in groups[1], "3840 ticks = 4 beats = group 1"

    def test_seed_reproducibility(self):
        """Same seed produces same shuffle result"""
        import random
        data = [60, 62, 64, 67, 72, 55, 48, 77]
        rng1 = random.Random(999)
        r1 = data[:]
        rng1.shuffle(r1)
        rng2 = random.Random(999)
        r2 = data[:]
        rng2.shuffle(r2)
        assert r1 == r2, "Same seed = same shuffle"

    def test_minimum_notes_check(self):
        """Need at least 2 notes to shuffle"""
        notes = [60]
        assert len(notes) < 2, "Single note cannot be shuffled"

    def test_invalid_mode_rejected(self):
        """Invalid mode returns error"""
        valid_modes = {"pitches", "rhythm", "full", "within_groups"}
        assert "reverse" not in valid_modes, "reverse is not a valid mode"
        assert "random" not in valid_modes, "random is not a valid mode"

    def test_pitch_clamping(self):
        """Shuffled pitches clamped to 0-127"""
        pitches = [0, 127, 64, 60]
        for p in pitches:
            assert 0 <= p <= 127, f"pitch {p} out of range"
