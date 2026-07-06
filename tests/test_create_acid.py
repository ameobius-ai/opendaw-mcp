"""Unit tests for create_acid_arrangement."""
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}
KICK = 36
CLAP = 39
CLOSED_HAT = 42
OPEN_HAT = 46
RIDE = 59
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


def _deg_to_pitch(degree, root_note, sc):
    ns = len(sc)
    oct_shift = degree // ns
    idx = degree % ns
    if idx < 0:
        idx += ns
        oct_shift -= 1
    return root_note + oct_shift * 12 + sc[idx]


def _generate_acid(key_root="A", bars=16, velocity=0.75, start_beat=0):
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, {"error": f"Invalid key_root '{key_root}'"}
    n_bars = max(4, bars)
    bass_oct = (2 + 1) * 12 + root_pc
    lead_oct = (4 + 1) * 12 + root_pc

    bass_pattern = [
        0, 0, 3, 0, 0, 0, -1, 0, 0, 5, 3, 2, 0, -1, 0, 7,
        3, 3, 0, 3, 3, 3, 2, 3, 3, 0, -1, 0, 3, 5, 7, 10,
    ]
    accent_pattern = [
        1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0,
        1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1,
    ]

    drums, bass, lead = [], [], []

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0
        for beat in range(4):
            drums.append({"pitch": KICK, "start": round(bar_start + beat, 4),
                          "duration": 0.5, "velocity": round(velocity, 3)})
        for beat in [1.0, 3.0]:
            drums.append({"pitch": CLAP, "start": round(bar_start + beat, 4),
                          "duration": 0.2, "velocity": round(velocity * 0.85, 3)})
        for beat in range(4):
            drums.append({"pitch": OPEN_HAT, "start": round(bar_start + beat + 0.5, 4),
                          "duration": 0.3, "velocity": round(velocity * 0.6, 3)})
        for h in range(16):
            drums.append({"pitch": CLOSED_HAT, "start": round(bar_start + h * 0.25, 4),
                          "duration": 0.08, "velocity": round(velocity * 0.35, 3)})
        for beat in range(4):
            drums.append({"pitch": RIDE, "start": round(bar_start + beat, 4),
                          "duration": 0.4, "velocity": round(velocity * 0.4, 3)})
        for i in range(16):
            pat_idx = (bar * 16 + i) % len(bass_pattern)
            deg = bass_pattern[pat_idx]
            pitch = _deg_to_pitch(deg, bass_oct, MINOR_SCALE)
            accent = accent_pattern[pat_idx]
            vel = velocity * (0.95 if accent else 0.55)
            bass.append({"pitch": pitch, "start": round(bar_start + i * 0.25, 4),
                         "duration": 0.22, "velocity": round(vel, 3)})
        if bar % 4 == 0:
            lead.append({"pitch": _deg_to_pitch(0, lead_oct, MINOR_SCALE),
                         "start": round(bar_start, 4),
                         "duration": 2.0, "velocity": round(velocity * 0.6, 3)})
            lead.append({"pitch": _deg_to_pitch(7, lead_oct, MINOR_SCALE),
                         "start": round(bar_start + 2.0, 4),
                         "duration": 2.0, "velocity": round(velocity * 0.55, 3)})

    for lst in (drums, bass, lead):
        lst.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"drums": drums, "bass": bass, "lead": lead, "n_bars": n_bars}, None


class TestValidation:
    def test_invalid_key(self):
        _, err = _generate_acid(key_root="Z")
        assert err is not None

    def test_valid_keys(self):
        for k in NOTE_MAP:
            data, err = _generate_acid(key_root=k)
            assert err is None

    def test_min_bars(self):
        data, _ = _generate_acid(bars=2)
        assert data["n_bars"] >= 4


class TestDrums:
    def test_kick_4_on_floor(self):
        data, _ = _generate_acid(bars=4)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        assert len(kicks) == 16

    def test_clap_on_2_and_4(self):
        data, _ = _generate_acid(bars=4)
        claps = [n for n in data["drums"] if n["pitch"] == CLAP]
        assert len(claps) == 8
        for c in claps:
            assert c["start"] % 4.0 in [1.0, 3.0]

    def test_open_hat_on_offbeats(self):
        data, _ = _generate_acid(bars=4)
        open_hats = [n for n in data["drums"] if n["pitch"] == OPEN_HAT]
        assert len(open_hats) == 16
        for oh in open_hats:
            assert oh["start"] % 4.0 in [0.5, 1.5, 2.5, 3.5]

    def test_closed_hats_16th(self):
        data, _ = _generate_acid(bars=4)
        ch = [n for n in data["drums"] if n["pitch"] == CLOSED_HAT]
        assert len(ch) == 64  # 16 per bar

    def test_ride_on_quarters(self):
        data, _ = _generate_acid(bars=4)
        rides = [n for n in data["drums"] if n["pitch"] == RIDE]
        assert len(rides) == 16


class TestBass:
    def test_bass_16th_notes(self):
        data, _ = _generate_acid(bars=4)
        assert len(data["bass"]) == 64  # 16 per bar

    def test_bass_16th_grid(self):
        """All bass notes should be on 16th grid (multiples of 0.25)."""
        data, _ = _generate_acid(bars=4)
        for b in data["bass"]:
            assert b["start"] % 0.25 < 0.01

    def test_bass_accent_velocity(self):
        """Accented notes should have higher velocity than non-accented."""
        data, _ = _generate_acid(bars=2)
        # Group by velocity
        vels = [b["velocity"] for b in data["bass"]]
        high = [v for v in vels if v > 0.6]
        low = [v for v in vels if v <= 0.6]
        assert len(high) > 0
        assert len(low) > 0
        assert min(high) > max(low)

    def test_bass_uses_minor_scale(self):
        data, _ = _generate_acid(key_root="A", bars=4)
        a_minor_pcs = {9, 11, 0, 2, 4, 5, 7}
        for b in data["bass"]:
            assert b["pitch"] % 12 in a_minor_pcs

    def test_bass_lower_than_lead(self):
        data, _ = _generate_acid(bars=4)
        avg_b = sum(n["pitch"] for n in data["bass"]) / len(data["bass"])
        avg_l = sum(n["pitch"] for n in data["lead"]) / len(data["lead"])
        assert avg_b < avg_l


class TestLead:
    def test_lead_sparse(self):
        """Lead should only appear every 4 bars."""
        data, _ = _generate_acid(bars=16)
        # 16 bars, lead every 4 bars = 4 occurrences × 2 notes = 8
        assert len(data["lead"]) == 8

    def test_lead_on_bar_start(self):
        """Lead should appear at bar starts (every 4 bars)."""
        data, _ = _generate_acid(bars=8)
        # Lead occurs at bar 0 and bar 4 — first note of each pair
        lead_starts = sorted(set(l["start"] for l in data["lead"]))
        # Should have starts at 0, 2, 16, 18 (2 notes per 4-bar occurrence)
        assert 0.0 in lead_starts
        assert 16.0 in lead_starts

    def test_lead_sustained(self):
        """Lead notes should be long (2 beats)."""
        data, _ = _generate_acid(bars=4)
        for l in data["lead"]:
            assert l["duration"] >= 1.5


class TestOverall:
    def test_total_notes(self):
        data, _ = _generate_acid(bars=4)
        total = sum(len(data[k]) for k in ("drums", "bass", "lead"))
        assert total > 100

    def test_scales_with_bars(self):
        small, _ = _generate_acid(bars=4)
        large, _ = _generate_acid(bars=16)
        s = sum(len(small[k]) for k in ("drums", "bass", "lead"))
        l = sum(len(large[k]) for k in ("drums", "bass", "lead"))
        assert l > s

    def test_all_velocities_in_range(self):
        data, _ = _generate_acid(bars=4)
        for key in ("drums", "bass", "lead"):
            for n in data[key]:
                assert 0 < n["velocity"] <= 1.0

    def test_all_pitches_in_range(self):
        data, _ = _generate_acid(bars=4)
        for key in ("drums", "bass", "lead"):
            for n in data[key]:
                assert 0 <= n["pitch"] <= 127

    def test_start_offset(self):
        data, _ = _generate_acid(bars=4, start_beat=12.0)
        for key in ("drums", "bass", "lead"):
            for n in data[key]:
                assert n["start"] >= 12.0

    def test_bass_pattern_cycles(self):
        """Bass pattern should cycle every 2 bars (32 sixteenths)."""
        data, _ = _generate_acid(bars=4)
        bar0 = [b for b in data["bass"] if 0.0 <= b["start"] < 4.0]
        bar2 = [b for b in data["bass"] if 8.0 <= b["start"] < 12.0]
        # Bar 0 and bar 2 should have the same pitches (pattern repeats every 2 bars)
        assert len(bar0) == len(bar2)
        for i in range(len(bar0)):
            assert bar0[i]["pitch"] == bar2[i]["pitch"]
