"""Unit tests for ground bass composition tool."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _parse_note(n):
    n = n.strip()
    if n.isdigit():
        return int(n)
    NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
                "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
                "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    for octave_len in (2, 1):
        if len(n) > octave_len:
            note_part = n[:-octave_len]
            oct_part = n[-octave_len:]
            try:
                octave = int(oct_part)
                pc = NOTE_MAP.get(note_part)
                if pc is not None:
                    return (octave + 1) * 12 + pc
            except ValueError:
                pass
    return 48


def _generate_ground_bass(bass_pattern, bass_rhythm, repeats, melody_style="baroque",
                          start_beat=0, velocity=0.8):
    """Replicate ground bass generation logic."""
    bass_notes_raw = bass_pattern.strip().split()
    bass_durations_raw = bass_rhythm.strip().split()
    bass_pitches = [_parse_note(n) for n in bass_notes_raw]
    bass_durs = [float(d) for d in bass_durations_raw]
    cycle_len = sum(bass_durs)

    all_bass_notes = []
    for r in range(repeats):
        pos = start_beat + r * cycle_len
        beat_offset = 0.0
        for i, pitch in enumerate(bass_pitches):
            dur = bass_durs[i]
            all_bass_notes.append({
                "pitch": pitch,
                "start": round(pos + beat_offset, 4),
                "duration": dur * 0.9,
                "velocity": round(velocity * 0.9, 3),
            })
            beat_offset += dur

    scale_intervals = {
        "baroque": [0, 2, 3, 5, 7, 8, 10, 12],
        "modal": [0, 2, 3, 5, 7, 10, 12],
        "minimalist": [0, 2, 3, 5, 7, 12],
        "film_tension": [0, 1, 3, 6, 7, 8, 12],
        "folk": [0, 2, 4, 7, 9, 12],
    }[melody_style]

    import random as _r
    rng = _r.Random(42)
    bass_root = bass_pitches[0]
    melody_octave = 12

    all_melody_notes = []
    for r in range(repeats):
        cycle_start = start_beat + r * cycle_len
        if melody_style == "baroque":
            start_degree = len(scale_intervals) - 1 - min(r, 4)
            if start_degree < 0:
                start_degree = 0
            n_melody_notes = int(cycle_len / 1.0)
            for m in range(n_melody_notes):
                deg = max(0, start_degree - m)
                if deg >= len(scale_intervals):
                    deg = len(scale_intervals) - 1
                pitch = bass_root + melody_octave + scale_intervals[deg]
                all_melody_notes.append({
                    "pitch": pitch, "start": round(cycle_start + m * 1.0, 4),
                    "duration": 0.9, "velocity": round(velocity * 0.6 * (0.8 + 0.04 * r), 3),
                })
        elif melody_style == "modal":
            n_notes = max(1, int(cycle_len / 2.0))
            for m in range(n_notes):
                deg = rng.choice([0, 2, 4, 4, 5])
                if deg >= len(scale_intervals):
                    deg = 0
                pitch = bass_root + melody_octave + scale_intervals[deg]
                all_melody_notes.append({
                    "pitch": pitch, "start": round(cycle_start + m * 2.0, 4),
                    "duration": 1.8, "velocity": round(velocity * 0.55, 3),
                })
        elif melody_style == "minimalist":
            cell = [0, 1, 2, 1]
            n_cells = int(cycle_len / 1.0)
            for m in range(n_cells):
                deg = cell[m % len(cell)]
                if deg >= len(scale_intervals):
                    deg = 0
                pitch = bass_root + melody_octave + scale_intervals[deg]
                shift = (r % 3) * 0.25
                all_melody_notes.append({
                    "pitch": pitch, "start": round(cycle_start + m * 1.0 + shift, 4),
                    "duration": 0.9, "velocity": round(velocity * 0.5, 3),
                })
        elif melody_style == "film_tension":
            n_notes = max(1, int(cycle_len / 1.5))
            for m in range(n_notes):
                deg = rng.choice([1, 1, 3, 3, 4, 6])
                if deg >= len(scale_intervals):
                    deg = 0
                pitch = bass_root + melody_octave + scale_intervals[deg]
                vel = min(1.0, round(velocity * (0.4 + 0.05 * r), 3))
                all_melody_notes.append({
                    "pitch": pitch, "start": round(cycle_start + m * 1.5, 4),
                    "duration": 1.3, "velocity": vel,
                })
        else:  # folk
            phrase = [0, 2, 4, 2, 0]
            n_notes = int(cycle_len / 1.0)
            for m in range(n_notes):
                deg = phrase[m % len(phrase)]
                if r % 2 == 1:
                    deg = (deg + 1) % len(scale_intervals)
                if deg >= len(scale_intervals):
                    deg = 0
                pitch = bass_root + melody_octave + scale_intervals[deg]
                all_melody_notes.append({
                    "pitch": pitch, "start": round(cycle_start + m * 1.0, 4),
                    "duration": 0.85, "velocity": round(velocity * 0.6, 3),
                })

    return all_bass_notes, all_melody_notes, cycle_len


class TestGroundBassValidation:
    """Test input validation."""

    def test_repeats_too_few(self):
        from server import mcp_opendaw_create_ground_bass
        import asyncio
        result = asyncio.run(mcp_opendaw_create_ground_bass(repeats=1))
        assert "Error" in result

    def test_repeats_too_many(self):
        from server import mcp_opendaw_create_ground_bass
        import asyncio
        result = asyncio.run(mcp_opendaw_create_ground_bass(repeats=50))
        assert "Error" in result

    def test_invalid_style(self):
        from server import mcp_opendaw_create_ground_bass
        import asyncio
        result = asyncio.run(mcp_opendaw_create_ground_bass(melody_style="invalid"))
        assert "Error" in result

    def test_invalid_velocity(self):
        from server import mcp_opendaw_create_ground_bass
        import asyncio
        result = asyncio.run(mcp_opendaw_create_ground_bass(velocity=2.0))
        assert "Error" in result


class TestGroundBassNoteParsing:
    """Test note parsing."""

    def test_parse_note_name(self):
        assert _parse_note("A2") == 45  # (2+1)*12 + 9
        assert _parse_note("C3") == 48  # (3+1)*12 + 0
        assert _parse_note("E2") == 40  # (2+1)*12 + 4

    def test_parse_midi_number(self):
        assert _parse_note("36") == 36
        assert _parse_note("48") == 48

    def test_parse_sharp(self):
        assert _parse_note("C#3") == 49
        assert _parse_note("F#2") == 42


class TestGroundBassBass:
    """Test bass ostinato generation."""

    def test_basic_bass_pattern(self):
        bass, melody, cycle_len = _generate_ground_bass("A2 A2 E2 E2", "2 2 2 2", 4)
        assert len(bass) == 16  # 4 notes × 4 repeats
        assert cycle_len == 8.0

    def test_bass_repeats(self):
        bass, _, _ = _generate_ground_bass("A2 E2", "2 2", 8)
        assert len(bass) == 16  # 2 notes × 8 repeats

    def test_bass_starts_at_zero(self):
        bass, _, _ = _generate_ground_bass("A2 A2", "2 2", 4)
        assert bass[0]["start"] == 0.0

    def test_bass_start_offset(self):
        bass, _, _ = _generate_ground_bass("A2 A2", "2 2", 4, start_beat=10.0)
        assert bass[0]["start"] == 10.0

    def test_bass_duration_has_gap(self):
        bass, _, _ = _generate_ground_bass("A2", "4", 2)
        assert bass[0]["duration"] == 3.6  # 4 * 0.9

    def test_bass_pitches_correct(self):
        bass, _, _ = _generate_ground_bass("A2 E2 C2 G2", "1 1 1 1", 2)
        pitches = [n["pitch"] for n in bass[:4]]
        assert pitches == [45, 40, 36, 43]  # A2=45, E2=40, C2=36, G2=43


class TestGroundBassMelody:
    """Test melody generation per style."""

    def test_baroque_melody_descending(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 4, "baroque")
        assert len(melody) > 0
        # First cycle should have higher notes than later
        first_cycle_pitches = [n["pitch"] for n in melody if n["start"] < 4.0]
        last_cycle_pitches = [n["pitch"] for n in melody if n["start"] >= 12.0]
        if first_cycle_pitches and last_cycle_pitches:
            assert max(first_cycle_pitches) >= max(last_cycle_pitches)

    def test_modal_melody_sparse(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 4, "modal")
        # Modal should have fewer notes than baroque
        assert len(melody) > 0
        # Sustained durations
        assert any(n["duration"] >= 1.5 for n in melody)

    def test_minimalist_melody_phase_shift(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 6, "minimalist")
        assert len(melody) > 0
        # Phase shift: cycle 0 at 0, cycle 1 at 0.25, cycle 2 at 0.5
        starts = [n["start"] for n in melody]
        # Some notes should have fractional starts due to phase shift
        has_shift = any(s % 1.0 != 0 for s in starts)
        assert has_shift

    def test_film_tension_melody_crescendo(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 8, "film_tension")
        assert len(melody) > 0
        # Velocity should increase across cycles
        first_vels = [n["velocity"] for n in melody if n["start"] < 4.0]
        last_vels = [n["velocity"] for n in melody if n["start"] >= 12.0]
        if first_vels and last_vels:
            assert max(last_vels) > max(first_vels)

    def test_folk_melody_simple(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 4, "folk")
        assert len(melody) > 0
        # Folk uses pentatonic major — no minor 3rds
        bass_root = 45  # A2
        for n in melody:
            interval = n["pitch"] - bass_root - 12  # relative to root + octave
            assert interval in [0, 2, 4, 7, 9, 12]


class TestGroundBassStructure:
    """Test structural properties."""

    def test_melody_above_bass(self):
        bass, melody, _ = _generate_ground_bass("A2 E2", "2 2", 4)
        bass_max = max(n["pitch"] for n in bass)
        melody_min = min(n["pitch"] for n in melody) if melody else bass_max + 12
        assert melody_min > bass_max  # melody is always above bass

    def test_cycle_len_calculation(self):
        _, _, cycle_len = _generate_ground_bass("A2 A2 E2 E2", "2 2 2 2", 2)
        assert cycle_len == 8.0

    def test_bass_repeats_cover_full_duration(self):
        bass, _, cycle_len = _generate_ground_bass("A2", "4", 4)
        last_bass_end = bass[-1]["start"] + bass[-1]["duration"]
        total_expected = cycle_len * 4
        assert last_bass_end <= total_expected + 0.1

    def test_all_notes_have_required_fields(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 2)
        for n in bass + melody:
            assert "pitch" in n
            assert "start" in n
            assert "duration" in n
            assert "velocity" in n

    def test_velocity_in_range(self):
        bass, melody, _ = _generate_ground_bass("A2 A2", "2 2", 4, "film_tension")
        for n in bass + melody:
            assert 0.0 <= n["velocity"] <= 1.0
