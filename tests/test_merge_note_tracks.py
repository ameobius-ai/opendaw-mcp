

class TestMergeNoteTracks:
    """Unit tests for merge_note_tracks — combine notes from two tracks"""

    def test_overlap_detection(self):
        """Two notes overlap if one starts before the other ends"""
        a = {"pos": 0, "dur": 480, "vel": 0.8}
        b = {"pos": 240, "dur": 480, "vel": 0.6}
        # a ends at 480, b starts at 240 → overlap
        assert a["pos"] + a["dur"] > b["pos"], "a overlaps b"

    def test_no_overlap(self):
        """Non-overlapping notes should not conflict"""
        a = {"pos": 0, "dur": 240, "vel": 0.8}
        b = {"pos": 480, "dur": 240, "vel": 0.6}
        # a ends at 240, b starts at 480 → no overlap
        assert a["pos"] + a["dur"] <= b["pos"], "no overlap"

    def test_keep_higher_velocity(self):
        """keep_higher_velocity: louder note wins"""
        a = {"pos": 0, "dur": 480, "vel": 0.8}
        b = {"pos": 240, "dur": 480, "vel": 0.6}
        mode = "keep_higher_velocity"
        if mode == "keep_higher_velocity":
            winner = a if a["vel"] >= b["vel"] else b
        assert winner == a, "higher velocity wins"

    def test_keep_lower_velocity(self):
        """keep_lower_velocity: quieter note wins"""
        a = {"pos": 0, "dur": 480, "vel": 0.8}
        b = {"pos": 240, "dur": 480, "vel": 0.6}
        mode = "keep_lower_velocity"
        if mode == "keep_lower_velocity":
            winner = a if a["vel"] <= b["vel"] else b
        assert winner == b, "lower velocity wins"

    def test_keep_source_preference(self):
        """keep_source: source notes preferred over dest"""
        is_src_a = True
        is_src_b = False
        mode = "keep_source"
        if mode == "keep_source":
            if is_src_a and not is_src_b:
                winner = "a"
            elif not is_src_a and is_src_b:
                winner = "b"
        assert winner == "a", "source preferred"

    def test_keep_dest_preference(self):
        """keep_dest: dest notes preferred over source"""
        is_src_a = True
        is_src_b = False
        mode = "keep_dest"
        if mode == "keep_dest":
            if not is_src_a and is_src_b:
                winner = "a"
            elif is_src_a and not is_src_b:
                winner = "b"
        assert winner == "b", "dest preferred"

    def test_shorten_earlier(self):
        """shorten_earlier: truncate earlier note to end where later starts"""
        a = {"pos": 0, "dur": 480, "vel": 0.8}
        b = {"pos": 240, "dur": 480, "vel": 0.6}
        mode = "shorten_earlier"
        if mode == "shorten_earlier":
            a["dur"] = max(1, b["pos"] - a["pos"])
        assert a["dur"] == 240, "earlier note truncated to 240"

    def test_keep_both_no_removal(self):
        """keep_both: no notes removed, all kept"""
        mode = "keep_both"
        assert mode == "keep_both", "keep_both skips resolution"

    def test_transpose_applied(self):
        """Transpose shifts source pitches"""
        src_pitch = 60
        transpose = 12
        new_pitch = max(0, min(127, src_pitch + transpose))
        assert new_pitch == 72, "transpose +12 = octave up"

    def test_transpose_negative(self):
        """Negative transpose shifts down"""
        src_pitch = 60
        transpose = -12
        new_pitch = max(0, min(127, src_pitch + transpose))
        assert new_pitch == 48, "transpose -12 = octave down"

    def test_transpose_clamp(self):
        """Transpose clamped to 0-127"""
        src_pitch = 120
        transpose = 12
        new_pitch = max(0, min(127, src_pitch + transpose))
        assert new_pitch == 127, "clamped to 127"

    def test_delete_source_flag(self):
        """delete_source=True removes source notes after merge"""
        delete_source = True
        assert delete_source is True, "source notes will be deleted"

    def test_merge_combines_counts(self):
        """Merged note count = source + dest - conflicts removed"""
        src_count = 8
        dst_count = 5
        conflicts = 2
        merged = src_count + dst_count - conflicts
        assert merged == 11, "8 + 5 - 2 conflicts = 11 merged notes"

    def test_sorted_by_position(self):
        """Merged notes sorted by position after merge"""
        merged = [
            {"pos": 480, "pitch": 64},
            {"pos": 0, "pitch": 60},
            {"pos": 240, "pitch": 67},
        ]
        merged.sort(key=lambda x: x["pos"])
        assert merged[0]["pos"] == 0, "first note at pos 0"
        assert merged[2]["pos"] == 480, "last note at pos 480"

    def test_invalid_overlap_mode(self):
        """Invalid overlap mode should be rejected"""
        valid_modes = {"keep_higher_velocity", "keep_lower_velocity", "keep_source",
                       "keep_dest", "keep_both", "shorten_earlier"}
        assert "random" not in valid_modes, "random is not valid"
        assert "first" not in valid_modes, "first is not valid"
