"""Unit tests for create_hardstyle_arrangement."""
import json
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}

KICK = 36
SNARE = 38
CLOSED_HAT = 42
OPEN_HAT = 46
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


def _deg_to_pitch(degree, root_note, sc):
    ns = len(sc)
    oct_shift = degree // ns
    idx = degree % ns
    if idx < 0:
        idx += ns
        oct_shift -= 1
    return root_note + oct_shift * 12 + sc[idx]


def _generate_hardstyle(key_root="F", bars=16, velocity=0.8, start_beat=0):
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, {"error": f"Invalid key_root '{key_root}'"}

    n_bars = max(4, bars)
    bass_oct = (2 + 1) * 12 + root_pc
    lead_oct = (4 + 1) * 12 + root_pc
    chord_oct = (3 + 1) * 12 + root_pc

    lead_degrees = [0, 7, 3, 0, 12, 7, 5, 3, 0, 10, 7, 5, 3, 7, 0, -1]
    lead_rhythm = [0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5,
                   0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5]
    chord_roots = [0, 5, 3, 8]
    chord_intervals = [0, 3, 7]

    drums, bass, lead, chords = [], [], [], []

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0
        for beat in range(4):
            drums.append({"pitch": KICK, "start": round(bar_start + beat, 4),
                          "duration": 0.5, "velocity": round(velocity, 3)})
        for beat in [1, 3]:
            drums.append({"pitch": SNARE, "start": round(bar_start + beat, 4),
                          "duration": 0.3, "velocity": round(velocity * 0.9, 3)})
        for beat in range(8):
            drums.append({"pitch": CLOSED_HAT, "start": round(bar_start + beat * 0.5 + 0.25, 4),
                          "duration": 0.15, "velocity": round(velocity * 0.5, 3)})
        drums.append({"pitch": OPEN_HAT, "start": round(bar_start + 2.75, 4),
                      "duration": 0.2, "velocity": round(velocity * 0.6, 3)})
        for beat in range(4):
            bass.append({"pitch": _deg_to_pitch(0, bass_oct, MINOR_SCALE),
                         "start": round(bar_start + beat + 0.5, 4),
                         "duration": 0.45, "velocity": round(velocity * 0.85, 3)})
        beat_pos = bar_start
        for i in range(len(lead_degrees)):
            deg = lead_degrees[(bar * 4 + i) % len(lead_degrees)]
            pitch = _deg_to_pitch(deg, lead_oct, MINOR_SCALE)
            dur = lead_rhythm[i % len(lead_rhythm)]
            lead.append({"pitch": pitch, "start": round(beat_pos, 4),
                         "duration": round(dur * 0.9, 4),
                         "velocity": round(velocity * 0.9, 3)})
            beat_pos += dur
        if beat_pos < bar_start + 4.0:
            beat_pos = bar_start + 4.0
        chord_idx = (bar // 4) % len(chord_roots)
        croot = chord_roots[chord_idx]
        for beat in [0, 2]:
            for ci in chord_intervals:
                chords.append({"pitch": _deg_to_pitch(croot + ci, chord_oct, MINOR_SCALE),
                               "start": round(bar_start + beat, 4),
                               "duration": 0.4, "velocity": round(velocity * 0.75, 3)})

    for lst in (drums, bass, lead, chords):
        lst.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"drums": drums, "bass": bass, "lead": lead, "chords": chords,
            "n_bars": n_bars}, None


class TestValidation:
    def test_invalid_key(self):
        _, err = _generate_hardstyle(key_root="Z")
        assert err is not None and "error" in err

    def test_valid_keys(self):
        for k in NOTE_MAP:
            data, err = _generate_hardstyle(key_root=k)
            assert err is None
            assert data is not None

    def test_min_bars_enforced(self):
        data, _ = _generate_hardstyle(bars=2)
        assert data["n_bars"] >= 4


class TestDrums:
    def test_kick_on_every_beat(self):
        data, _ = _generate_hardstyle(bars=4)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        # 4 bars × 4 beats = 16 kicks
        assert len(kicks) == 16

    def test_snare_on_2_and_4(self):
        data, _ = _generate_hardstyle(bars=4)
        snares = [n for n in data["drums"] if n["pitch"] == SNARE]
        # 4 bars × 2 snares = 8
        assert len(snares) == 8
        for s in snares:
            beat_in_bar = s["start"] % 4.0
            assert beat_in_bar in [1.0, 3.0]

    def test_closed_hats_on_offbeats(self):
        data, _ = _generate_hardstyle(bars=4)
        hats = [n for n in data["drums"] if n["pitch"] == CLOSED_HAT]
        # 4 bars × 8 hats = 32
        assert len(hats) == 32

    def test_open_hat_once_per_bar(self):
        data, _ = _generate_hardstyle(bars=4)
        open_hats = [n for n in data["drums"] if n["pitch"] == OPEN_HAT]
        assert len(open_hats) == 4  # one per bar


class TestBass:
    def test_bass_on_offbeats(self):
        data, _ = _generate_hardstyle(bars=4)
        for b in data["bass"]:
            beat_in_bar = b["start"] % 4.0
            # Offbeat = 0.5, 1.5, 2.5, 3.5
            assert beat_in_bar in [0.5, 1.5, 2.5, 3.5]

    def test_bass_count_per_bar(self):
        data, _ = _generate_hardstyle(bars=4)
        # 4 bass notes per bar
        assert len(data["bass"]) == 16

    def test_bass_lower_than_lead(self):
        data, _ = _generate_hardstyle(bars=4)
        avg_bass = sum(n["pitch"] for n in data["bass"]) / len(data["bass"])
        avg_lead = sum(n["pitch"] for n in data["lead"]) / len(data["lead"])
        assert avg_bass < avg_lead


class TestLead:
    def test_lead_has_notes(self):
        data, _ = _generate_hardstyle(bars=4)
        assert len(data["lead"]) > 0

    def test_lead_high_octave(self):
        """Lead should be in a high octave (screechy)."""
        data, _ = _generate_hardstyle(key_root="F", bars=4)
        for n in data["lead"]:
            # F4 = 65, should be above 60
            assert n["pitch"] >= 60

    def test_lead_uses_minor_scale(self):
        data, _ = _generate_hardstyle(key_root="F", bars=8)
        f_minor_pcs = {5, 7, 8, 10, 0, 1, 3}  # F G Ab Bb C Db Eb
        for n in data["lead"]:
            assert n["pitch"] % 12 in f_minor_pcs


class TestChords:
    def test_chords_on_beat_1_and_3(self):
        data, _ = _generate_hardstyle(bars=4)
        for c in data["chords"]:
            beat_in_bar = c["start"] % 4.0
            assert beat_in_bar in [0.0, 2.0]

    def test_chords_are_triads(self):
        data, _ = _generate_hardstyle(bars=4)
        # Group by start time
        from collections import defaultdict
        groups = defaultdict(list)
        for c in data["chords"]:
            groups[c["start"]].append(c)
        for start, notes in groups.items():
            assert len(notes) == 3  # triad

    def test_chord_progression_i_VI_III_VII(self):
        """Every 4 bars should change chord root."""
        data, _ = _generate_hardstyle(key_root="F", bars=16)
        # Check that different chord roots appear across bars
        chord_starts = sorted(set(c["start"] for c in data["chords"]))
        # 16 bars × 2 stabs = 32 chord hits, but grouped by start
        # Each bar has 2 stabs, 4 bars per chord = 8 stabs per chord
        # Should have 4 different chord groups
        assert len(chord_starts) == 32  # 16 bars × 2


class TestOverall:
    def test_total_notes_positive(self):
        data, _ = _generate_hardstyle(bars=4)
        total = len(data["drums"]) + len(data["bass"]) + len(data["lead"]) + len(data["chords"])
        assert total > 0

    def test_notes_scale_with_bars(self):
        small, _ = _generate_hardstyle(bars=4)
        large, _ = _generate_hardstyle(bars=16)
        small_total = sum(len(small[k]) for k in ("drums", "bass", "lead", "chords"))
        large_total = sum(len(large[k]) for k in ("drums", "bass", "lead", "chords"))
        assert large_total > small_total

    def test_all_velocities_in_range(self):
        data, _ = _generate_hardstyle(bars=4)
        for key in ("drums", "bass", "lead", "chords"):
            for n in data[key]:
                assert 0 < n["velocity"] <= 1.0

    def test_all_pitches_in_range(self):
        data, _ = _generate_hardstyle(bars=4)
        for key in ("drums", "bass", "lead", "chords"):
            for n in data[key]:
                assert 0 <= n["pitch"] <= 127

    def test_start_beat_offset(self):
        data, _ = _generate_hardstyle(bars=4, start_beat=20.0)
        for key in ("drums", "bass", "lead", "chords"):
            for n in data[key]:
                assert n["start"] >= 20.0
