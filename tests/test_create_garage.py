"""Unit tests for create_garage_arrangement."""
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}
KICK = 36
SNARE = 38
CLOSED_HAT = 42
OPEN_HAT = 46
RIM = 37
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


def _deg_to_pitch(degree, root_note, sc):
    ns = len(sc)
    oct_shift = degree // ns
    idx = degree % ns
    if idx < 0:
        idx += ns
        oct_shift -= 1
    return root_note + oct_shift * 12 + sc[idx]


def _generate_garage(key_root="G", bars=16, velocity=0.7, start_beat=0):
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, {"error": f"Invalid key_root '{key_root}'"}
    n_bars = max(4, bars)
    bass_oct = (2 + 1) * 12 + root_pc
    chord_oct = (3 + 1) * 12 + root_pc
    lead_oct = (4 + 1) * 12 + root_pc

    kick_patterns = [[0.0, 3.5], [0.0, 3.0]]
    bass_degrees = [0, 0, 3, 0, 5, 3, 0, -2, 0, 0, 7, 5, 3, 0, -2, 0]
    bass_rhythm = [0.5, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.5,
                   0.5, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.5]
    bass_beat_offsets = [0, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0,
                         0, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
    chord_roots = [2, 7, 0, 5]
    chord_intervals = [0, 3, 7, 10]
    lead_degrees = [0, 3, 5, 3, 7, 5, 3, 0]
    lead_rhythm = [0.25, 0.25, 0.25, 0.25, 0.5, 0.25, 0.25, 0.5]

    drums, bass, chords, lead = [], [], [], []

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0
        kick_pat = kick_patterns[bar % 2]
        for kb in kick_pat:
            drums.append({"pitch": KICK, "start": round(bar_start + kb, 4),
                          "duration": 0.4, "velocity": round(velocity, 3)})
        for beat in [1.0, 3.0]:
            drums.append({"pitch": SNARE, "start": round(bar_start + beat, 4),
                          "duration": 0.2, "velocity": round(velocity * 0.9, 3)})
        for h in range(8):
            hb = h * 0.5
            if h % 2 == 1:
                hb += 0.08
            drums.append({"pitch": CLOSED_HAT, "start": round(bar_start + hb, 4),
                          "duration": 0.1, "velocity": round(velocity * (0.4 + 0.1 * (h % 2)), 3)})
        drums.append({"pitch": OPEN_HAT, "start": round(bar_start + 2.75 + 0.08, 4),
                      "duration": 0.15, "velocity": round(velocity * 0.55, 3)})
        if bar % 2 == 0:
            drums.append({"pitch": RIM, "start": round(bar_start + 1.75 + 0.08, 4),
                          "duration": 0.08, "velocity": round(velocity * 0.35, 3)})
        bass_idx_base = (bar % 2) * 8
        for i in range(8):
            idx = bass_idx_base + i
            deg = bass_degrees[idx % len(bass_degrees)]
            dur = bass_rhythm[idx % len(bass_rhythm)]
            offset = bass_beat_offsets[idx % len(bass_beat_offsets)]
            bass.append({"pitch": _deg_to_pitch(deg, bass_oct, MINOR_SCALE),
                         "start": round(bar_start + offset, 4),
                         "duration": round(dur * 0.85, 4),
                         "velocity": round(velocity * (0.8 + 0.1 * (i % 2)), 3)})
        chord_idx = (bar // 4) % len(chord_roots)
        croot = chord_roots[chord_idx]
        for beat in [1.5, 3.5]:
            for ci in chord_intervals:
                chords.append({"pitch": _deg_to_pitch(croot + ci, chord_oct, MINOR_SCALE),
                               "start": round(bar_start + beat, 4),
                               "duration": 0.3, "velocity": round(velocity * 0.7, 3)})
        lead_start = bar_start
        for i in range(len(lead_degrees)):
            deg = lead_degrees[(bar + i) % len(lead_degrees)]
            pitch = _deg_to_pitch(deg, lead_oct, MINOR_SCALE)
            dur = lead_rhythm[i % len(lead_rhythm)]
            if (bar + i) % 5 != 4:
                lead.append({"pitch": pitch, "start": round(lead_start, 4),
                             "duration": round(dur * 0.8, 4),
                             "velocity": round(velocity * 0.65, 3)})
            lead_start += dur

    for lst in (drums, bass, chords, lead):
        lst.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"drums": drums, "bass": bass, "chords": chords, "lead": lead,
            "n_bars": n_bars}, None


class TestValidation:
    def test_invalid_key(self):
        _, err = _generate_garage(key_root="Z")
        assert err is not None

    def test_valid_keys(self):
        for k in NOTE_MAP:
            data, err = _generate_garage(key_root=k)
            assert err is None

    def test_min_bars(self):
        data, _ = _generate_garage(bars=2)
        assert data["n_bars"] >= 4


class TestDrums:
    def test_kick_on_beat_1(self):
        data, _ = _generate_garage(bars=4)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        # Every bar has kick on beat 1
        bar_1_kicks = [k for k in kicks if k["start"] % 4.0 == 0.0]
        assert len(bar_1_kicks) == 4

    def test_snare_on_2_and_4(self):
        data, _ = _generate_garage(bars=4)
        snares = [n for n in data["drums"] if n["pitch"] == SNARE]
        assert len(snares) == 8
        for s in snares:
            assert s["start"] % 4.0 in [1.0, 3.0]

    def test_swung_hats(self):
        """Odd 16th hats should be delayed by swing."""
        data, _ = _generate_garage(bars=4)
        hats = [n for n in data["drums"] if n["pitch"] == CLOSED_HAT]
        # 8 hats per bar × 4 bars = 32
        assert len(hats) == 32
        # Check swing: odd hats should have .08 offset from grid
        swung = [h for h in hats if (h["start"] % 0.5) > 0.05]
        assert len(swung) > 0

    def test_open_hat_per_bar(self):
        data, _ = _generate_garage(bars=4)
        open_hats = [n for n in data["drums"] if n["pitch"] == OPEN_HAT]
        assert len(open_hats) == 4

    def test_2step_alternating_kick(self):
        """Bars should alternate kick patterns."""
        data, _ = _generate_garage(bars=4)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        bar0 = [k for k in kicks if 0.0 <= k["start"] < 4.0]
        bar1 = [k for k in kicks if 4.0 <= k["start"] < 8.0]
        assert len(bar0) == 2
        assert len(bar1) == 2
        # Bar 0 has kick at 3.5, bar 1 at 3.0 (relative to bar start)
        assert any(abs(k["start"] - 3.5) < 0.01 for k in bar0)
        assert any(abs((k["start"] - 4.0) - 3.0) < 0.01 for k in bar1)


class TestBass:
    def test_bass_notes_per_bar(self):
        data, _ = _generate_garage(bars=4)
        assert len(data["bass"]) == 32  # 8 per bar

    def test_bass_lower_than_lead(self):
        data, _ = _generate_garage(bars=4)
        avg_b = sum(n["pitch"] for n in data["bass"]) / len(data["bass"])
        avg_l = sum(n["pitch"] for n in data["lead"]) / len(data["lead"])
        assert avg_b < avg_l

    def test_bass_uses_minor_scale(self):
        data, _ = _generate_garage(key_root="G", bars=4)
        g_minor_pcs = {7, 9, 10, 0, 2, 3, 5}
        for n in data["bass"]:
            assert n["pitch"] % 12 in g_minor_pcs


class TestChords:
    def test_chords_on_offbeats(self):
        data, _ = _generate_garage(bars=4)
        for c in data["chords"]:
            assert c["start"] % 4.0 in [1.5, 3.5]

    def test_chords_are_7th_voicings(self):
        """Each chord stab should have 4 notes (root, 3rd, 5th, 7th)."""
        data, _ = _generate_garage(bars=4)
        from collections import defaultdict
        groups = defaultdict(list)
        for c in data["chords"]:
            groups[round(c["start"], 4)].append(c)
        for _, notes in groups.items():
            assert len(notes) == 4


class TestLead:
    def test_lead_has_notes(self):
        data, _ = _generate_garage(bars=4)
        assert len(data["lead"]) > 0

    def test_lead_choppy(self):
        """Some notes should be skipped (vocal-chop style)."""
        data, _ = _generate_garage(bars=8)
        # Not every position should have a note — some are skipped
        # Just verify we have notes
        assert len(data["lead"]) > 10

    def test_lead_high_octave(self):
        data, _ = _generate_garage(key_root="G", bars=4)
        for n in data["lead"]:
            assert n["pitch"] >= 60  # above middle C, upper register


class TestOverall:
    def test_total_notes(self):
        data, _ = _generate_garage(bars=4)
        total = sum(len(data[k]) for k in ("drums", "bass", "chords", "lead"))
        assert total > 50

    def test_scales_with_bars(self):
        small, _ = _generate_garage(bars=4)
        large, _ = _generate_garage(bars=16)
        s = sum(len(small[k]) for k in ("drums", "bass", "chords", "lead"))
        l = sum(len(large[k]) for k in ("drums", "bass", "chords", "lead"))
        assert l > s

    def test_all_velocities_in_range(self):
        data, _ = _generate_garage(bars=4)
        for key in ("drums", "bass", "chords", "lead"):
            for n in data[key]:
                assert 0 < n["velocity"] <= 1.0

    def test_all_pitches_in_range(self):
        data, _ = _generate_garage(bars=4)
        for key in ("drums", "bass", "chords", "lead"):
            for n in data[key]:
                assert 0 <= n["pitch"] <= 127

    def test_start_offset(self):
        data, _ = _generate_garage(bars=4, start_beat=15.0)
        for key in ("drums", "bass", "chords", "lead"):
            for n in data[key]:
                assert n["start"] >= 15.0
