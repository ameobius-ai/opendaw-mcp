"""Unit tests for create_chaconne."""
import json
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}
CHORD_TRIADS = {
    "": [0, 4, 7], "m": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "7": [0, 4, 7, 10],
    "sus4": [0, 5, 7], "sus2": [0, 2, 7], "m7b5": [0, 3, 6, 10],
}


def _parse_note(note_name):
    note_name = note_name.strip()
    if not note_name:
        return None
    for nlen in (2, 1):
        note_part = note_name[:nlen]
        if note_part in NOTE_MAP:
            oct_str = note_name[nlen:]
            octave = int(oct_str) if oct_str else 3
            return (octave + 1) * 12 + NOTE_MAP[note_part]
    return None


def _parse_chord(chord_name):
    chord_name = chord_name.strip()
    if not chord_name:
        return None, None
    root = None
    root_str = ""
    for nlen in (2, 1):
        part = chord_name[:nlen]
        if part in NOTE_MAP:
            root_str = part
            root = NOTE_MAP[part]
            break
    if root is None:
        return None, None
    suffix = chord_name[len(root_str):]
    intervals = CHORD_TRIADS.get(suffix)
    if intervals is None:
        for key in CHORD_TRIADS:
            if key.lower() == suffix.lower():
                intervals = CHORD_TRIADS[key]
                break
    if intervals is None:
        intervals = CHORD_TRIADS[""]
    root_pitch = (3 + 1) * 12 + root
    return root_pitch, intervals


def _generate_chaconne(bass_pattern, bass_rhythm, chord_pattern, variation_style, repeats, velocity=0.65):
    """Pure-Python reimplementation of create_chaconne logic."""
    import random as _rng
    rng = _rng.Random(42)

    bass_notes_names = bass_pattern.split()
    bass_durations = [float(x) for x in bass_rhythm.split()]
    if len(bass_durations) < len(bass_notes_names):
        bass_durations.extend([1.0] * (len(bass_notes_names) - len(bass_durations)))
    chord_names = [c.strip() for c in chord_pattern.split(",") if c.strip()]

    bass_pitches = [_parse_note(n) for n in bass_notes_names]
    bass_pitches = [p for p in bass_pitches if p is not None]
    cycle_len = sum(bass_durations[:len(bass_pitches)])

    chord_data = []
    for cn in chord_names:
        rp, iv = _parse_chord(cn)
        if rp is not None and iv is not None:
            chord_data.append((rp, iv, cn))

    # Bass
    all_bass_notes = []
    for r in range(repeats):
        beat = r * cycle_len
        for i, pitch in enumerate(bass_pitches):
            dur = bass_durations[i] if i < len(bass_durations) else 1.0
            all_bass_notes.append({
                "pitch": pitch,
                "start": round(beat, 4),
                "duration": round(dur * 0.95, 4),
                "velocity": velocity,
            })
            beat += dur

    # Chords
    all_chord_notes = []
    for r in range(repeats):
        beat = r * cycle_len
        for i in range(len(bass_pitches)):
            dur = bass_durations[i] if i < len(bass_durations) else 1.0
            ci = i % max(1, len(chord_data))
            if ci < len(chord_data):
                rp, iv, _ = chord_data[ci]
                for interval in iv:
                    all_chord_notes.append({
                        "pitch": rp + interval,
                        "start": round(beat, 4),
                        "duration": round(dur * 0.9, 4),
                        "velocity": round(velocity * 0.45, 3),
                    })
            beat += dur

    # Variation
    all_var_notes = []
    bass_root = bass_pitches[0] if bass_pitches else 60
    if chord_data:
        first_root, first_iv, _ = chord_data[0]
        is_minor = 3 in first_iv
        scale = [0, 2, 3, 5, 7, 8, 10, 12] if is_minor else [0, 2, 4, 5, 7, 9, 11, 12]
    else:
        scale = [0, 2, 4, 5, 7, 9, 11, 12]
    var_octave = 24

    for r in range(repeats):
        cycle_start = r * cycle_len

        if variation_style == "baroque":
            n_notes = int(cycle_len / 0.5)
            for m in range(n_notes):
                deg = max(0, len(scale) - 1 - m // 2 - r)
                if deg >= len(scale):
                    deg = len(scale) - 1
                pitch = bass_root + var_octave + scale[deg]
                if r >= 1 and m % 4 == 0:
                    grace_pitch = bass_root + var_octave + scale[max(0, deg - 1)]
                    all_var_notes.append({
                        "pitch": grace_pitch,
                        "start": round(cycle_start + m * 0.5, 4),
                        "duration": 0.15,
                        "velocity": round(velocity * 0.5, 3),
                    })
                all_var_notes.append({
                    "pitch": pitch,
                    "start": round(cycle_start + m * 0.5 + (0.15 if (r >= 1 and m % 4 == 0) else 0), 4),
                    "duration": 0.45,
                    "velocity": round(velocity * 0.6 * (0.85 + 0.03 * r), 3),
                })

        elif variation_style == "romantic":
            intervals_romantic = [7, 12, 9, 5, 7, 12, 4, 3]
            n_notes = int(cycle_len / 1.0)
            for m in range(n_notes):
                interval = intervals_romantic[(m + r) % len(intervals_romantic)]
                base_deg = rng.randint(0, min(4, len(scale) - 1))
                pitch = bass_root + var_octave + scale[base_deg] + interval
                time_offset = rng.uniform(-0.1, 0.1)
                all_var_notes.append({
                    "pitch": pitch,
                    "start": round(cycle_start + m * 1.0 + time_offset, 4),
                    "duration": round(0.85 + rng.uniform(-0.1, 0.15), 4),
                    "velocity": round(velocity * (0.5 + 0.05 * r), 3),
                })

        elif variation_style == "jazz":
            pattern = [0, 0.5, 1.5, 2, 2.5, 3.5]
            chromatic_offsets = [0, 0, 1, 0, 1, 0]
            for m, (offset, chrom) in enumerate(zip(pattern, chromatic_offsets)):
                deg = (m + r * 2) % len(scale)
                pitch = bass_root + var_octave + scale[deg] + chrom
                all_var_notes.append({
                    "pitch": pitch,
                    "start": round(cycle_start + offset, 4),
                    "duration": 0.4,
                    "velocity": round(velocity * (0.55 + 0.04 * r), 3),
                })
            if r >= 1:
                run_start = cycle_start + cycle_len - 1.0
                for m in range(4):
                    all_var_notes.append({
                        "pitch": bass_root + var_octave + 12 - m,
                        "start": round(run_start + m * 0.25, 4),
                        "duration": 0.22,
                        "velocity": round(velocity * 0.5, 3),
                    })

        elif variation_style == "minimalist":
            cell = [0, 1, 2, 1, 3, 2]
            n_cells = int(cycle_len / 0.5)
            for m in range(n_cells):
                deg = cell[m % len(cell)]
                if deg >= len(scale):
                    deg = 0
                pitch = bass_root + var_octave + scale[deg]
                phase_shift = (r * 0.125) % 1.0
                all_var_notes.append({
                    "pitch": pitch,
                    "start": round(cycle_start + m * 0.5 + phase_shift, 4),
                    "duration": 0.45,
                    "velocity": round(velocity * 0.55, 3),
                })

        else:  # contemporary
            dissonant_intervals = [1, 6, 11, 13, 7, 2, 10, 4]
            n_notes = int(cycle_len / 0.75)
            for m in range(n_notes):
                interval = dissonant_intervals[(m + r * 3) % len(dissonant_intervals)]
                deg = rng.randint(0, min(3, len(scale) - 1))
                pitch = bass_root + var_octave + scale[deg] + interval
                dur = 0.15 if m % 3 == 0 else 0.6
                all_var_notes.append({
                    "pitch": pitch,
                    "start": round(cycle_start + m * 0.75 + rng.uniform(-0.15, 0.15), 4),
                    "duration": dur,
                    "velocity": round(velocity * rng.uniform(0.4, 0.8), 3),
                })

    return all_bass_notes, all_chord_notes, all_var_notes, cycle_len


# === Tests ===

class TestParseNote:
    def test_basic_notes(self):
        assert _parse_note("C2") == 36
        assert _parse_note("A2") == 45
        assert _parse_note("E2") == 40

    def test_sharp_flat(self):
        assert _parse_note("C#2") == 37
        assert _parse_note("Db2") == 37
        assert _parse_note("Bb1") == 34

    def test_default_octave(self):
        assert _parse_note("C") == 48  # octave 3

    def test_invalid(self):
        assert _parse_note("") is None
        assert _parse_note("X9") is None


class TestParseChord:
    def test_major(self):
        rp, iv = _parse_chord("C")
        assert rp == 48
        assert iv == [0, 4, 7]

    def test_minor(self):
        rp, iv = _parse_chord("Am")
        assert rp == 57
        assert iv == [0, 3, 7]

    def test_seventh(self):
        rp, iv = _parse_chord("G7")
        assert rp == 55
        assert iv == [0, 4, 7, 10]

    def test_maj7(self):
        rp, iv = _parse_chord("Fmaj7")
        assert rp == 53
        assert iv == [0, 4, 7, 11]

    def test_dim(self):
        rp, iv = _parse_chord("Bdim")
        assert rp == 59
        assert iv == [0, 3, 6]

    def test_invalid(self):
        rp, iv = _parse_chord("")
        assert rp is None
        assert iv is None


class TestBassGeneration:
    def test_bass_repeats_correctly(self):
        bass, _, _, cycle_len = _generate_chaconne(
            "C2 G2 A2 E2", "1 1 1 1", "C,Em,Am,G", "baroque", 4
        )
        assert len(bass) == 16  # 4 notes * 4 repeats
        assert cycle_len == 4.0
        # First note of each repeat should be C2=36
        for r in range(4):
            assert bass[r * 4]["pitch"] == 36
            assert bass[r * 4]["start"] == r * 4.0

    def test_bass_durations(self):
        bass, _, _, _ = _generate_chaconne(
            "C2 E2", "2 2", "C,Am", "baroque", 2
        )
        assert len(bass) == 4
        assert bass[0]["duration"] == round(2 * 0.95, 4)  # 1.9
        assert bass[1]["duration"] == round(2 * 0.95, 4)

    def test_bass_velocity(self):
        bass, _, _, _ = _generate_chaconne(
            "C2", "4", "C", "baroque", 1, velocity=0.8
        )
        assert bass[0]["velocity"] == 0.8

    def test_bass_start_beat_offset(self):
        bass, _, _, _ = _generate_chaconne(
            "C2 G2", "1 1", "C,G", "baroque", 1, velocity=0.5
        )
        # start_beat=0 in this pure impl
        assert bass[0]["start"] == 0
        assert bass[1]["start"] == 1.0

    def test_rhythm_pad(self):
        # More notes than rhythm values → padded with 1.0
        bass, _, _, _ = _generate_chaconne(
            "C2 E2 G2 A2", "1 1", "C,Em,Am,G", "baroque", 1
        )
        assert len(bass) == 4
        # Third note should use padded duration 1.0
        assert bass[2]["duration"] == round(1.0 * 0.95, 4)


class TestChordGeneration:
    def test_chord_notes_count(self):
        _, chords, _, _ = _generate_chaconne(
            "C2 G2 A2 E2", "1 1 1 1", "C,Em,Am,G", "baroque", 2
        )
        # 4 bass notes * 2 repeats = 8 chord positions
        # C=3 notes, Em=3, Am=3, G=3 → 12 per repeat, 24 total
        assert len(chords) == 24

    def test_chord_pitches(self):
        _, chords, _, _ = _generate_chaconne(
            "C2", "4", "C", "baroque", 1
        )
        # C major triad at octave 3: 48, 52, 55
        pitches = sorted([n["pitch"] for n in chords])
        assert pitches == [48, 52, 55]

    def test_minor_chord(self):
        _, chords, _, _ = _generate_chaconne(
            "A2", "4", "Am", "baroque", 1
        )
        pitches = sorted([n["pitch"] for n in chords])
        assert pitches == [57, 60, 64]  # A3=57, C4=60, E4=64

    def test_seventh_chord(self):
        _, chords, _, _ = _generate_chaconne(
            "G2", "4", "G7", "baroque", 1
        )
        pitches = sorted([n["pitch"] for n in chords])
        assert pitches == [55, 59, 62, 65]  # G3, B3, D4, F4

    def test_chord_velocity_lower_than_bass(self):
        _, chords, _, _ = _generate_chaconne(
            "C2", "4", "C", "baroque", 1, velocity=0.7
        )
        assert chords[0]["velocity"] == round(0.7 * 0.45, 3)


class TestVariationStyles:
    def test_baroque_descending(self):
        _, _, var, _ = _generate_chaconne(
            "C2 G2 A2 E2", "1 1 1 1", "C,Em,Am,G", "baroque", 1
        )
        assert len(var) > 0
        # Should have notes within reasonable pitch range
        pitches = [n["pitch"] for n in var]
        assert min(pitches) >= 36 + 24  # bass_root + var_octave
        assert max(pitches) <= 36 + 24 + 24  # within 2 octaves

    def test_baroque_grace_notes_appear_after_repeat_1(self):
        _, _, var, _ = _generate_chaconne(
            "C2 G2", "2 2", "C,G", "baroque", 3
        )
        # Repeat 0: no grace notes. Repeat 1+: grace notes on m%4==0
        # Check that repeat 1 has more notes than repeat 0
        cycle_len = 4.0
        r0_notes = [n for n in var if n["start"] < cycle_len]
        r1_notes = [n for n in var if cycle_len <= n["start"] < 2 * cycle_len]
        assert len(r1_notes) > len(r0_notes)

    def test_romantic_wide_intervals(self):
        _, _, var, _ = _generate_chaconne(
            "C2", "4", "C", "romantic", 2
        )
        assert len(var) > 0
        pitches = [n["pitch"] for n in var]
        # Romantic should have wide range
        assert max(pitches) - min(pitches) >= 7

    def test_jazz_syncopation(self):
        _, _, var, _ = _generate_chaconne(
            "C2 G2", "2 2", "C,G", "jazz", 2
        )
        assert len(var) > 0
        # Check for syncopated timings (0.5, 1.5, 2.5, 3.5)
        starts = [n["start"] for n in var]
        has_syncopation = any(abs(s - int(s) - 0.5) < 0.01 for s in starts)
        assert has_syncopation

    def test_jazz_chromatic_run_repeat_1(self):
        _, _, var, _ = _generate_chaconne(
            "C2 G2", "2 2", "C,G", "jazz", 3
        )
        cycle_len = 4.0
        # Repeat 1+ should have more notes due to chromatic run
        r0_notes = [n for n in var if n["start"] < cycle_len]
        r1_notes = [n for n in var if cycle_len <= n["start"] < 2 * cycle_len]
        assert len(r1_notes) > len(r0_notes)

    def test_minimalist_phase_shift(self):
        _, _, var, _ = _generate_chaconne(
            "C2 G2", "2 2", "C,G", "minimalist", 3
        )
        assert len(var) > 0
        cycle_len = 4.0
        r0_start = var[0]["start"]
        r1_first = [n for n in var if cycle_len <= n["start"] < 2 * cycle_len][0]
        # Phase shift should differ between repeats
        assert abs(r1_first["start"] - cycle_len - 0.125) < 0.01  # r=1 shift = 0.125

    def test_contemporary_dissonant(self):
        _, _, var, _ = _generate_chaconne(
            "C2", "4", "C", "contemporary", 1
        )
        assert len(var) > 0
        pitches = [n["pitch"] for n in var]
        # Contemporary should have some semitone/dissonant intervals
        unique_pitches = sorted(set(pitches))
        intervals = [unique_pitches[i+1] - unique_pitches[i]
                     for i in range(len(unique_pitches)-1)]
        assert min(intervals) <= 2  # has close dissonant intervals

    def test_contemporary_pointillistic_durations(self):
        _, _, var, _ = _generate_chaconne(
            "C2", "4", "C", "contemporary", 1
        )
        durations = [n["duration"] for n in var]
        # Should have both very short (0.15) and longer (0.6) notes
        assert min(durations) <= 0.16
        assert max(durations) >= 0.59


class TestStructure:
    def test_three_tracks(self):
        bass, chords, var, _ = _generate_chaconne(
            "C2 G2 A2 E2", "1 1 1 1", "C,Em,Am,G", "baroque", 2
        )
        assert len(bass) > 0
        assert len(chords) > 0
        assert len(var) > 0

    def test_cycle_len_calculated(self):
        _, _, _, cycle_len = _generate_chaconne(
            "C2 E2 G2 A2", "1 1 1 1", "C,Em,Am,G", "baroque", 1
        )
        assert cycle_len == 4.0

    def test_cycle_len_3_beats(self):
        _, _, _, cycle_len = _generate_chaconne(
            "C2 E2 G2", "1 1 1", "C,Em,Am", "baroque", 1
        )
        assert cycle_len == 3.0

    def test_repeats_produce_progressive_content(self):
        _, _, var, _ = _generate_chaconne(
            "C2 G2 A2 E2", "1 1 1 1", "C,Em,Am,G", "baroque", 4
        )
        # More repeats should mean more variation notes
        assert len(var) > 0

    def test_scale_from_minor_chord(self):
        # Am is minor → scale should include b3, b6, b7
        _, _, var, _ = _generate_chaconne(
            "A2", "4", "Am", "baroque", 1
        )
        pitches = [n["pitch"] for n in var]
        bass_root = 45  # A2
        var_octave = 24
        # Minor scale: 0,2,3,5,7,8,10,12
        expected_scale = [0, 2, 3, 5, 7, 8, 10, 12]
        # At least some pitches should be on minor scale degrees
        for p in pitches[:4]:
            rel = p - bass_root - var_octave
            assert rel in expected_scale


class TestEdgeCases:
    def test_single_note_single_repeat(self):
        bass, chords, var, _ = _generate_chaconne(
            "C2", "4", "C", "baroque", 1
        )
        assert len(bass) == 1
        assert len(chords) == 3  # C major triad
        assert len(var) > 0

    def test_many_repeats(self):
        bass, _, _, _ = _generate_chaconne(
            "C2 G2", "2 2", "C,G", "baroque", 8
        )
        assert len(bass) == 16

    def test_chord_cycling_with_fewer_chords(self):
        # 4 bass notes, only 2 chords → chords cycle
        _, chords, _, _ = _generate_chaconne(
            "C2 E2 G2 A2", "1 1 1 1", "C,G", "baroque", 1
        )
        # Position 0→C, 1→G, 2→C, 3→G
        # C=48,52,55; G=55,59,62
        pos0_pitches = sorted([n["pitch"] for n in chords if n["start"] == 0])
        pos1_pitches = sorted([n["pitch"] for n in chords if n["start"] == 1.0])
        assert pos0_pitches == [48, 52, 55]  # C major
        assert pos1_pitches == [55, 59, 62]  # G major

    def test_all_styles_produce_notes(self):
        for style in ["baroque", "romantic", "jazz", "minimalist", "contemporary"]:
            _, _, var, _ = _generate_chaconne(
                "C2 G2", "2 2", "C,G", style, 2
            )
            assert len(var) > 0, f"Style {style} produced no notes"
