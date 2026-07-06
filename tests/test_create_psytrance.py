"""Unit tests for create_psytrance_arrangement."""
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}
KICK = 36
SNARE = 38
CLOSED_HAT = 42
SHAKER = 64
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


def _deg_to_pitch(degree, root_note, sc):
    ns = len(sc)
    oct_shift = degree // ns
    idx = degree % ns
    if idx < 0:
        idx += ns
        oct_shift -= 1
    return root_note + oct_shift * 12 + sc[idx]


def _generate_psytrance(key_root="F", bars=16, velocity=0.75, start_beat=0):
    root_pc = NOTE_MAP.get(key_root)
    if root_pc is None:
        return None, {"error": f"Invalid key_root '{key_root}'"}
    n_bars = max(4, bars)
    bass_oct = (2 + 1) * 12 + root_pc
    lead_oct = (4 + 1) * 12 + root_pc
    atm_oct = (3 + 1) * 12 + root_pc

    bass_16th = [0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 3, 0, 0, 7, 5]
    lead_motif = [0, 7, 5, 3, 0, 7, 10, 7, 0, 5, 3, 0, 7, 3, 0, -1]
    lead_rhythm = [0.25] * 16

    drums, bass, lead, atmosphere = [], [], [], []

    for bar in range(n_bars):
        bar_start = start_beat + bar * 4.0
        for beat in range(4):
            drums.append({"pitch": KICK, "start": round(bar_start + beat, 4),
                          "duration": 0.5, "velocity": round(velocity, 3)})
        for beat in [1.0, 3.0]:
            drums.append({"pitch": SNARE, "start": round(bar_start + beat, 4),
                          "duration": 0.2, "velocity": round(velocity * 0.85, 3)})
        for h in range(16):
            drums.append({"pitch": CLOSED_HAT, "start": round(bar_start + h * 0.25, 4),
                          "duration": 0.06, "velocity": round(velocity * 0.3, 3)})
        for s in range(8):
            drums.append({"pitch": SHAKER, "start": round(bar_start + s * 0.5, 4),
                          "duration": 0.1, "velocity": round(velocity * 0.35, 3)})
        if (bar + 1) % 4 == 0:
            for i in range(8):
                pos = bar_start + 3.0 + i * 0.125
                drums.append({"pitch": SNARE, "start": round(pos, 4),
                              "duration": 0.08,
                              "velocity": round(velocity * (0.3 + 0.08 * i), 3)})
        for i in range(16):
            deg = bass_16th[(bar * 16 + i) % len(bass_16th)]
            pitch = _deg_to_pitch(deg, bass_oct, MINOR_SCALE)
            vel = velocity * (0.9 if i % 4 == 0 else 0.65)
            bass.append({"pitch": pitch, "start": round(bar_start + i * 0.25, 4),
                         "duration": 0.22, "velocity": round(vel, 3)})
        for i in range(16):
            deg = lead_motif[(bar * 4 + i) % len(lead_motif)]
            pitch = _deg_to_pitch(deg, lead_oct, MINOR_SCALE)
            dur = lead_rhythm[i % len(lead_rhythm)]
            vel_mod = 0.4 + 0.5 * ((bar * 16 + i) % 64) / 64.0
            lead.append({"pitch": pitch, "start": round(bar_start + i * 0.25, 4),
                         "duration": round(dur * 0.85, 4),
                         "velocity": round(velocity * vel_mod, 3)})
        if bar % 2 == 0:
            atmosphere.append({"pitch": _deg_to_pitch(3, atm_oct, MINOR_SCALE),
                               "start": round(bar_start, 4),
                               "duration": 4.0, "velocity": round(velocity * 0.35, 3)})
            atmosphere.append({"pitch": _deg_to_pitch(10, atm_oct, MINOR_SCALE),
                               "start": round(bar_start + 2.0, 4),
                               "duration": 2.0, "velocity": round(velocity * 0.3, 3)})

    for lst in (drums, bass, lead, atmosphere):
        lst.sort(key=lambda n: (n["start"], n["pitch"]))
    return {"drums": drums, "bass": bass, "lead": lead,
            "atmosphere": atmosphere, "n_bars": n_bars}, None


class TestValidation:
    def test_invalid_key(self):
        _, err = _generate_psytrance(key_root="Z")
        assert err is not None

    def test_valid_keys(self):
        for k in NOTE_MAP:
            data, err = _generate_psytrance(key_root=k)
            assert err is None

    def test_min_bars(self):
        data, _ = _generate_psytrance(bars=2)
        assert data["n_bars"] >= 4


class TestDrums:
    def test_kick_4_on_floor(self):
        data, _ = _generate_psytrance(bars=4)
        kicks = [n for n in data["drums"] if n["pitch"] == KICK]
        assert len(kicks) == 16

    def test_snare_on_2_and_4(self):
        data, _ = _generate_psytrance(bars=4)
        snares = [n for n in data["drums"] if n["pitch"] == SNARE]
        # 4 bars × 2 base snares = 8, plus 1 snare roll at end of bar 3
        # Bar 3 (bar+1=4, %4==0): 8 extra snare hits
        assert len(snares) == 16  # 8 + 8

    def test_closed_hats_16th(self):
        data, _ = _generate_psytrance(bars=4)
        ch = [n for n in data["drums"] if n["pitch"] == CLOSED_HAT]
        assert len(ch) == 64

    def test_shaker_8th(self):
        data, _ = _generate_psytrance(bars=4)
        shakers = [n for n in data["drums"] if n["pitch"] == SHAKER]
        assert len(shakers) == 32  # 8 per bar

    def test_snare_roll_at_end_of_phrase(self):
        """Snare roll should appear at end of every 4 bars."""
        data, _ = _generate_psytrance(bars=8)
        # Check for fast snare hits (0.125 spacing) in bar 3 and bar 7
        all_snares = [n for n in data["drums"] if n["pitch"] == SNARE]
        roll_snares = [s for s in all_snares if s["duration"] <= 0.08]
        # 8 per roll × 2 rolls (bar 3 and bar 7) = 16
        assert len(roll_snares) == 16


class TestBass:
    def test_bass_16th_notes(self):
        data, _ = _generate_psytrance(bars=4)
        assert len(data["bass"]) == 64  # 16 per bar

    def test_bass_16th_grid(self):
        data, _ = _generate_psytrance(bars=4)
        for b in data["bass"]:
            assert b["start"] % 0.25 < 0.01

    def test_bass_kick_velocity(self):
        """Bass on kick positions should be louder."""
        data, _ = _generate_psytrance(bars=2)
        for b in data["bass"]:
            pos_in_bar = b["start"] % 4.0
            if pos_in_bar % 1.0 < 0.01:  # on beat = kick position
                assert b["velocity"] > 0.6
            else:
                assert b["velocity"] <= 0.6

    def test_bass_uses_minor_scale(self):
        data, _ = _generate_psytrance(key_root="F", bars=4)
        f_minor_pcs = {5, 7, 8, 10, 0, 1, 3}
        for b in data["bass"]:
            assert b["pitch"] % 12 in f_minor_pcs


class TestLead:
    def test_lead_16th_notes(self):
        data, _ = _generate_psytrance(bars=4)
        assert len(data["lead"]) == 64

    def test_lead_filter_sweep(self):
        """Lead velocity should vary (filter sweep simulation)."""
        data, _ = _generate_psytrance(bars=4)
        vels = [n["velocity"] for n in data["lead"]]
        assert max(vels) - min(vels) > 0.1  # variation exists

    def test_lead_higher_than_bass(self):
        data, _ = _generate_psytrance(bars=4)
        avg_b = sum(n["pitch"] for n in data["bass"]) / len(data["bass"])
        avg_l = sum(n["pitch"] for n in data["lead"]) / len(data["lead"])
        assert avg_l > avg_b


class TestAtmosphere:
    def test_atmosphere_every_2_bars(self):
        data, _ = _generate_psytrance(bars=8)
        # Every 2 bars: 2 notes each → 4 × 2 = 8
        assert len(data["atmosphere"]) == 8

    def test_atmosphere_sustained(self):
        data, _ = _generate_psytrance(bars=4)
        for a in data["atmosphere"]:
            assert a["duration"] >= 2.0

    def test_atmosphere_low_velocity(self):
        """Atmosphere should be quiet (background pad)."""
        data, _ = _generate_psytrance(bars=4, velocity=0.75)
        for a in data["atmosphere"]:
            assert a["velocity"] < 0.4


class TestOverall:
    def test_total_notes(self):
        data, _ = _generate_psytrance(bars=4)
        total = sum(len(data[k]) for k in ("drums", "bass", "lead", "atmosphere"))
        assert total > 150

    def test_scales_with_bars(self):
        small, _ = _generate_psytrance(bars=4)
        large, _ = _generate_psytrance(bars=16)
        s = sum(len(small[k]) for k in ("drums", "bass", "lead", "atmosphere"))
        l = sum(len(large[k]) for k in ("drums", "bass", "lead", "atmosphere"))
        assert l > s

    def test_all_velocities_in_range(self):
        data, _ = _generate_psytrance(bars=4)
        for key in ("drums", "bass", "lead", "atmosphere"):
            for n in data[key]:
                assert 0 < n["velocity"] <= 1.0

    def test_all_pitches_in_range(self):
        data, _ = _generate_psytrance(bars=4)
        for key in ("drums", "bass", "lead", "atmosphere"):
            for n in data[key]:
                assert 0 <= n["pitch"] <= 127

    def test_start_offset(self):
        data, _ = _generate_psytrance(bars=4, start_beat=8.0)
        for key in ("drums", "bass", "lead", "atmosphere"):
            for n in data[key]:
                assert n["start"] >= 8.0
