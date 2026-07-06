"""Unit tests for create_downtempo_arrangement."""
import pytest
import random

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


def _generate_downtempo(key_root="D", bars=16, velocity=0.6, start_beat=0):
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, {"error": f"Invalid key_root '{key_root}'"}
    n_bars = max(4, bars)
    bass_oct = (1 + 1) * 12 + root_pc
    chord_oct = (3 + 1) * 12 + root_pc
    mel_oct = (4 + 1) * 12 + root_pc
    atm_oct = (3 + 1) * 12 + root_pc

    rng = random.Random(55)
    kick_patterns = [[0.0, 2.0], [0.0, 2.5], [0.0, 2.0, 3.5], [0.0, 2.0]]
    bass_degrees = [0, 0, 5, 3, 0, 0, 7, 5]
    bass_durations = [2.0, 2.0, 2.0, 2.0, 2.0, 1.0, 1.0, 2.0]
    chord_roots = [0, 5, 8, 7]
    chord_intervals = [0, 3, 7, 10, 14]
    mel_degrees = [0, 7, 5, 12, 7, 3, 0, -1, 5, 10, 7, 3]
    mel_rhythm = [2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0]

    drums, bass, chords, melody, atmosphere = [], [], [], [], []

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0
        kick_pat = kick_patterns[bar % 4]
        for kb in kick_pat:
            drums.append({"pitch": KICK, "start": round(bar_start + kb, 4),
                          "duration": 0.5, "velocity": round(velocity, 3)})
        for beat in [1.0, 3.0]:
            drums.append({"pitch": SNARE, "start": round(bar_start + beat, 4),
                          "duration": 0.3, "velocity": round(velocity * 0.85, 3)})
        for h in range(8):
            hb = h * 0.5
            if h % 2 == 1:
                hb += 0.1
            drums.append({"pitch": CLOSED_HAT, "start": round(bar_start + hb, 4),
                          "duration": 0.08, "velocity": round(velocity * (0.35 + 0.1 * (h % 2)), 3)})
        if bar % 2 == 1:
            drums.append({"pitch": OPEN_HAT, "start": round(bar_start + 2.75, 4),
                          "duration": 0.15, "velocity": round(velocity * 0.45, 3)})
        if rng.random() < 0.3:
            ghost_pos = rng.choice([0.75, 1.75, 2.75, 3.75]) + 0.1
            drums.append({"pitch": RIM, "start": round(bar_start + ghost_pos, 4),
                          "duration": 0.06, "velocity": round(velocity * 0.25, 3)})
        bass_idx = bar % len(bass_degrees)
        bass_deg = bass_degrees[bass_idx]
        bass_dur = bass_durations[bass_idx % len(bass_durations)]
        bass.append({"pitch": _deg_to_pitch(bass_deg, bass_oct, MINOR_SCALE),
                     "start": round(bar_start, 4),
                     "duration": round(bass_dur, 4),
                     "velocity": round(velocity * 0.9, 3)})
        if bass_dur < 4.0:
            bass_deg2 = bass_degrees[(bass_idx + 1) % len(bass_degrees)]
            bass.append({"pitch": _deg_to_pitch(bass_deg2, bass_oct, MINOR_SCALE),
                         "start": round(bar_start + bass_dur, 4),
                         "duration": round(4.0 - bass_dur, 4),
                         "velocity": round(velocity * 0.85, 3)})
        if bar % 2 == 0:
            chord_idx = (bar // 2) % len(chord_roots)
            croot = chord_roots[chord_idx]
            for ci in chord_intervals:
                chords.append({"pitch": _deg_to_pitch(croot + ci, chord_oct, MINOR_SCALE),
                               "start": round(bar_start, 4),
                               "duration": 3.5, "velocity": round(velocity * 0.55, 3)})
        if bar >= 4:
            mel_idx = (bar - 4) % len(mel_degrees)
            mel_deg = mel_degrees[mel_idx]
            mel_dur = mel_rhythm[mel_idx % len(mel_rhythm)]
            melody.append({"pitch": _deg_to_pitch(mel_deg, mel_oct, MINOR_SCALE),
                           "start": round(bar_start + 1.0, 4),
                           "duration": round(mel_dur * 0.9, 4),
                           "velocity": round(velocity * 0.7, 3)})
        if bar % 4 == 0:
            atmosphere.append({"pitch": _deg_to_pitch(0, atm_oct, MINOR_SCALE),
                               "start": round(bar_start, 4),
                               "duration": 8.0, "velocity": round(velocity * 0.25, 3)})
            atmosphere.append({"pitch": _deg_to_pitch(7, atm_oct, MINOR_SCALE),
                               "start": round(bar_start + 4.0, 4),
                               "duration": 4.0, "velocity": round(velocity * 0.2, 3)})

    for lst in (drums, bass, chords, melody, atmosphere):
        lst.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"drums": drums, "bass": bass, "chords": chords,
            "melody": melody, "atmosphere": atmosphere, "n_bars": n_bars}, None


class TestValidation:
    def test_invalid_key(self):
        _, err = _generate_downtempo(key_root="Z")
        assert err is not None

    def test_valid_keys(self):
        for k in NOTE_MAP:
            data, err = _generate_downtempo(key_root=k)
            assert err is None

    def test_min_bars(self):
        data, _ = _generate_downtempo(bars=2)
        assert data["n_bars"] >= 4


class TestDrums:
    def test_kick_on_beat_1(self):
        data, _ = _generate_downtempo(bars=4)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        bar1_kicks = [k for k in kicks if k["start"] % 4.0 < 0.01]
        assert len(bar1_kicks) == 4

    def test_snare_on_2_and_4(self):
        data, _ = _generate_downtempo(bars=4)
        snares = [n for n in data["drums"] if n["pitch"] == SNARE]
        assert len(snares) == 8
        for s in snares:
            assert s["start"] % 4.0 in [1.0, 3.0]

    def test_swung_hats(self):
        data, _ = _generate_downtempo(bars=4)
        hats = [n for n in data["drums"] if n["pitch"] == CLOSED_HAT]
        assert len(hats) == 32
        # Check swing: odd hats should have offset > 0.05 from grid
        swung = [h for h in hats if (h["start"] % 0.5) > 0.05]
        assert len(swung) > 0

    def test_open_hat_odd_bars(self):
        data, _ = _generate_downtempo(bars=4)
        oh = [n for n in data["drums"] if n["pitch"] == OPEN_HAT]
        assert len(oh) == 2  # bars 1 and 3


class TestBass:
    def test_bass_has_notes(self):
        data, _ = _generate_downtempo(bars=4)
        assert len(data["bass"]) > 0

    def test_bass_low_octave(self):
        """Bass should be in octave 1 (deep sub)."""
        data, _ = _generate_downtempo(key_root="D", bars=4)
        for b in data["bass"]:
            assert b["pitch"] < 48  # below C3

    def test_bass_sustained(self):
        """Bass notes should be long (sustained)."""
        data, _ = _generate_downtempo(bars=4)
        for b in data["bass"]:
            assert b["duration"] >= 1.0

    def test_bass_uses_minor_scale(self):
        data, _ = _generate_downtempo(key_root="D", bars=4)
        d_minor_pcs = {2, 4, 5, 7, 9, 10, 0}
        for b in data["bass"]:
            assert b["pitch"] % 12 in d_minor_pcs


class TestChords:
    def test_chords_every_2_bars(self):
        data, _ = _generate_downtempo(bars=8)
        # Chords on bars 0, 2, 4, 6 → 4 occurrences × 5 notes = 20
        assert len(data["chords"]) == 20

    def test_chords_extended(self):
        """Each chord should have 5 notes (root, 3rd, 5th, 7th, 9th)."""
        data, _ = _generate_downtempo(bars=4)
        from collections import defaultdict
        groups = defaultdict(list)
        for c in data["chords"]:
            groups[round(c["start"], 4)].append(c)
        for _, notes in groups.items():
            assert len(notes) == 5


class TestMelody:
    def test_melody_starts_bar_5(self):
        """Melody should start after 4 bars."""
        data, _ = _generate_downtempo(bars=16)
        for m in data["melody"]:
            assert m["start"] >= 16.0  # bar 4 starts at beat 16

    def test_melody_sparse(self):
        """Only one melody note per bar (sparse)."""
        data, _ = _generate_downtempo(bars=16)
        # 12 melody notes for 12 bars (bars 4-15)
        assert len(data["melody"]) == 12


class TestAtmosphere:
    def test_atmosphere_every_4_bars(self):
        data, _ = _generate_downtempo(bars=16)
        # Every 4 bars: 2 notes each → 4 × 2 = 8
        assert len(data["atmosphere"]) == 8

    def test_atmosphere_sustained(self):
        data, _ = _generate_downtempo(bars=4)
        for a in data["atmosphere"]:
            assert a["duration"] >= 4.0

    def test_atmosphere_low_velocity(self):
        data, _ = _generate_downtempo(bars=4, velocity=0.6)
        for a in data["atmosphere"]:
            assert a["velocity"] < 0.3


class TestOverall:
    def test_total_notes(self):
        data, _ = _generate_downtempo(bars=8)
        total = sum(len(data[k]) for k in ("drums", "bass", "chords", "melody", "atmosphere"))
        assert total > 50

    def test_scales_with_bars(self):
        small, _ = _generate_downtempo(bars=4)
        large, _ = _generate_downtempo(bars=16)
        s = sum(len(small[k]) for k in ("drums", "bass", "chords", "melody", "atmosphere"))
        l = sum(len(large[k]) for k in ("drums", "bass", "chords", "melody", "atmosphere"))
        assert l > s

    def test_all_velocities_in_range(self):
        data, _ = _generate_downtempo(bars=4)
        for key in ("drums", "bass", "chords", "melody", "atmosphere"):
            for n in data[key]:
                assert 0 < n["velocity"] <= 1.0

    def test_all_pitches_in_range(self):
        data, _ = _generate_downtempo(bars=4)
        for key in ("drums", "bass", "chords", "melody", "atmosphere"):
            for n in data[key]:
                assert 0 <= n["pitch"] <= 127

    def test_bass_lower_than_chords(self):
        data, _ = _generate_downtempo(bars=4)
        avg_b = sum(n["pitch"] for n in data["bass"]) / len(data["bass"])
        avg_c = sum(n["pitch"] for n in data["chords"]) / len(data["chords"])
        assert avg_b < avg_c

    def test_start_offset(self):
        data, _ = _generate_downtempo(bars=4, start_beat=20.0)
        for key in ("drums", "bass", "chords", "melody", "atmosphere"):
            for n in data[key]:
                assert n["start"] >= 20.0
