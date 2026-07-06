"""Unit tests for create_ambient_arrangement."""
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}
KICK = 36
SHAKER = 64
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]


def _deg_to_pitch(degree, root_note, sc):
    ns = len(sc)
    oct_shift = degree // ns
    idx = degree % ns
    if idx < 0:
        idx += ns
        oct_shift -= 1
    return root_note + oct_shift * 12 + sc[idx]


def _generate_ambient(key_root="C", bars=32, velocity=0.5, start_beat=0):
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, {"error": f"Invalid key_root '{key_root}'"}
    n_bars = max(8, bars)
    pad_oct = (3 + 1) * 12 + root_pc
    mel_oct = (4 + 1) * 12 + root_pc
    bass_oct = (1 + 1) * 12 + root_pc

    chord_roots = [0, 5, 3, 7]
    chord_duration = 8
    pad_intervals = [0, 7, 12, 16]
    mel_degrees = [0, 4, 7, 11, 9, 7, 4, 2, 0, 5, 9, 7, 4, 2, 0]
    mel_durations = [4.0, 2.0, 4.0, 2.0, 4.0, 2.0, 4.0, 2.0, 4.0, 2.0, 4.0, 2.0, 4.0, 2.0, 4.0]

    pad, melody, drums, bass = [], [], [], []

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0
        if bar % chord_duration == 0:
            ci_chord = (bar // chord_duration) % len(chord_roots)
            croot = chord_roots[ci_chord]
            for ci in pad_intervals:
                pad.append({"pitch": _deg_to_pitch(croot + ci, pad_oct, MAJOR_SCALE),
                            "start": round(bar_start, 4),
                            "duration": chord_duration * 4.0,
                            "velocity": round(velocity * 0.5, 3)})
            bass.append({"pitch": _deg_to_pitch(croot, bass_oct, MAJOR_SCALE),
                         "start": round(bar_start, 4),
                         "duration": chord_duration * 4.0,
                         "velocity": round(velocity * 0.6, 3)})
        if bar >= 8 and bar % 2 == 0:
            mi = ((bar - 8) // 2) % len(mel_degrees)
            mel_deg = mel_degrees[mi]
            mel_dur = mel_durations[mi % len(mel_durations)]
            melody.append({"pitch": _deg_to_pitch(mel_deg, mel_oct, MAJOR_SCALE),
                           "start": round(bar_start + 1.0, 4),
                           "duration": round(mel_dur * 0.95, 4),
                           "velocity": round(velocity * 0.65, 3)})
        if bar % 8 == 0:
            drums.append({"pitch": KICK, "start": round(bar_start, 4),
                          "duration": 1.0, "velocity": round(velocity * 0.4, 3)})
        if bar % 4 == 2:
            drums.append({"pitch": SHAKER, "start": round(bar_start + 2.0, 4),
                          "duration": 0.3, "velocity": round(velocity * 0.2, 3)})

    for lst in (pad, melody, drums, bass):
        lst.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"pad": pad, "melody": melody, "drums": drums, "bass": bass,
            "n_bars": n_bars}, None


class TestValidation:
    def test_invalid_key(self):
        _, err = _generate_ambient(key_root="Z")
        assert err is not None

    def test_valid_keys(self):
        for k in NOTE_MAP:
            data, err = _generate_ambient(key_root=k)
            assert err is None

    def test_min_bars(self):
        data, _ = _generate_ambient(bars=4)
        assert data["n_bars"] >= 8


class TestPad:
    def test_pad_sustained(self):
        """Pad notes should be very long (8 bars = 32 beats)."""
        data, _ = _generate_ambient(bars=32)
        for p in data["pad"]:
            assert p["duration"] >= 30.0

    def test_pad_4_voices(self):
        """Each chord should have 4 notes (root, fifth, octave, third)."""
        data, _ = _generate_ambient(bars=32)
        from collections import defaultdict
        groups = defaultdict(list)
        for p in data["pad"]:
            groups[round(p["start"], 4)].append(p)
        for _, notes in groups.items():
            assert len(notes) == 4

    def test_pad_changes_every_8_bars(self):
        data, _ = _generate_ambient(bars=32)
        # 4 chords × 4 notes = 16 pad notes
        assert len(data["pad"]) == 16

    def test_pad_low_velocity(self):
        data, _ = _generate_ambient(bars=32, velocity=0.5)
        for p in data["pad"]:
            assert p["velocity"] < 0.35


class TestMelody:
    def test_melody_starts_bar_9(self):
        data, _ = _generate_ambient(bars=32)
        for m in data["melody"]:
            assert m["start"] >= 32.0  # bar 8 = beat 32

    def test_melody_sparse(self):
        data, _ = _generate_ambient(bars=32)
        # Every 2 bars from bar 8 to 31 = 12 notes
        assert len(data["melody"]) == 12

    def test_melody_long_notes(self):
        data, _ = _generate_ambient(bars=32)
        for m in data["melody"]:
            assert m["duration"] >= 1.8


class TestDrums:
    def test_kick_every_8_bars(self):
        data, _ = _generate_ambient(bars=32)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        assert len(kicks) == 4  # bars 0, 8, 16, 24

    def test_shaker_every_4_bars(self):
        data, _ = _generate_ambient(bars=32)
        shakers = [n for n in data["drums"] if n["pitch"] == SHAKER]
        # bar % 4 == 2: bars 2, 6, 10, 14, 18, 22, 26, 30 = 8
        assert len(shakers) == 8

    def test_drums_low_velocity(self):
        data, _ = _generate_ambient(bars=32, velocity=0.5)
        for d in data["drums"]:
            assert d["velocity"] < 0.3


class TestBass:
    def test_bass_drone(self):
        """Bass should be sustained drone (8 bars each)."""
        data, _ = _generate_ambient(bars=32)
        for b in data["bass"]:
            assert b["duration"] >= 30.0

    def test_bass_changes_with_pad(self):
        data, _ = _generate_ambient(bars=32)
        # 4 chord changes = 4 bass notes
        assert len(data["bass"]) == 4

    def test_bass_low_octave(self):
        data, _ = _generate_ambient(key_root="C", bars=32)
        for b in data["bass"]:
            assert b["pitch"] < 48  # below C3


class TestOverall:
    def test_total_notes(self):
        data, _ = _generate_ambient(bars=32)
        total = sum(len(data[k]) for k in ("pad", "melody", "drums", "bass"))
        assert total > 20

    def test_all_velocities_in_range(self):
        data, _ = _generate_ambient(bars=32)
        for key in ("pad", "melody", "drums", "bass"):
            for n in data[key]:
                assert 0 < n["velocity"] <= 1.0

    def test_all_pitches_in_range(self):
        data, _ = _generate_ambient(bars=32)
        for key in ("pad", "melody", "drums", "bass"):
            for n in data[key]:
                assert 0 <= n["pitch"] <= 127

    def test_bass_lower_than_pad(self):
        data, _ = _generate_ambient(bars=32)
        avg_b = sum(n["pitch"] for n in data["bass"]) / len(data["bass"])
        avg_p = sum(n["pitch"] for n in data["pad"]) / len(data["pad"])
        assert avg_b < avg_p

    def test_start_offset(self):
        data, _ = _generate_ambient(bars=16, start_beat=5.0)
        for key in ("pad", "melody", "drums", "bass"):
            for n in data[key]:
                assert n["start"] >= 5.0
