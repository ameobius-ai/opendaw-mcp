"""Unit tests for create_comparsa."""
import json
import pytest

CONGA_LOW = 54
CONGA_HIGH = 63
CONGA_OPEN = 64
CLAVE = 75
COWBELL = 56
MARACAS = 70
GUIRO = 73


def _generate_comparsa(style="habanera", bars=2, velocity=0.7, start_beat=0.0):
    """Pure-Python reimplementation."""
    beats_per_bar = 4
    notes = []

    def add(pitch, beat_pos, dur, vel):
        notes.append({
            "pitch": pitch,
            "start": round(start_beat + beat_pos, 4),
            "duration": round(dur, 4),
            "velocity": round(max(0.0, min(1.0, vel)), 3),
        })

    for bar in range(bars):
        bar_start = bar * beats_per_bar

        if style == "habanera":
            clave_pattern = [(1.5, 0.3), (2.0, 0.3), (2.5, 0.3)] if bar == 0 else [(0.5, 0.3), (1.5, 0.3)]
            for beat, dur in clave_pattern:
                add(CLAVE, bar_start + beat, dur, velocity * 0.7)
            add(CONGA_LOW, bar_start + 0.0, 0.5, velocity * 0.85)
            add(CONGA_OPEN, bar_start + 1.0, 0.4, velocity * 0.7)
            add(CONGA_LOW, bar_start + 2.0, 0.5, velocity * 0.85)
            add(CONGA_OPEN, bar_start + 3.0, 0.4, velocity * 0.7)
            add(CONGA_HIGH, bar_start + 2.5, 0.2, velocity * 0.6)
            add(CONGA_HIGH, bar_start + 0.5, 0.2, velocity * 0.5)
            for h in range(8):
                add(COWBELL, bar_start + h * 0.5, 0.25, velocity * (0.5 if h % 2 == 0 else 0.4))
            for h in range(4):
                add(MARACAS, bar_start + h * 1.0 + 0.5, 0.2, velocity * 0.35)

        elif style == "santiago":
            clave_pattern = [(0.5, 0.3), (1.5, 0.3)] if bar == 0 else [(1.5, 0.3), (2.0, 0.3), (2.5, 0.3)]
            for beat, dur in clave_pattern:
                add(CLAVE, bar_start + beat, dur, velocity * 0.7)
            add(CONGA_LOW, bar_start + 0.0, 0.5, velocity * 0.8)
            add(CONGA_OPEN, bar_start + 0.75, 0.3, velocity * 0.6)
            add(CONGA_HIGH, bar_start + 1.0, 0.2, velocity * 0.65)
            add(CONGA_OPEN, bar_start + 1.5, 0.3, velocity * 0.6)
            add(CONGA_LOW, bar_start + 2.0, 0.5, velocity * 0.8)
            add(CONGA_OPEN, bar_start + 2.75, 0.3, velocity * 0.6)
            add(CONGA_HIGH, bar_start + 3.0, 0.2, velocity * 0.65)
            add(CONGA_OPEN, bar_start + 3.5, 0.3, velocity * 0.6)
            add(GUIRO, bar_start + 0.0, 0.5, velocity * 0.4)
            add(GUIRO, bar_start + 1.5, 0.25, velocity * 0.35)
            add(GUIRO, bar_start + 2.0, 0.5, velocity * 0.4)
            add(GUIRO, bar_start + 3.5, 0.25, velocity * 0.35)
            for beat in [0, 2.5, 3.0, 3.5]:
                add(COWBELL, bar_start + beat, 0.25, velocity * 0.5)

        elif style == "matanzas":
            add(CONGA_LOW, bar_start + 0.0, 0.6, velocity * 0.75)
            add(CONGA_OPEN, bar_start + 2.0, 0.5, velocity * 0.6)
            quinto_hits = [0.75, 1.5, 1.75, 2.5, 3.25, 3.75]
            for q in quinto_hits:
                add(CONGA_HIGH, bar_start + q, 0.15, velocity * (0.5 + 0.1 * (q % 1)))
            add(CONGA_OPEN, bar_start + 1.0, 0.4, velocity * 0.55)
            add(CONGA_OPEN, bar_start + 3.0, 0.4, velocity * 0.55)
            add(COWBELL, bar_start + 0.0, 0.3, velocity * 0.5)
            add(COWBELL, bar_start + 2.0, 0.3, velocity * 0.5)
            for h in range(8):
                add(MARACAS, bar_start + h * 0.5, 0.15, velocity * 0.3)

        elif style == "conga_line":
            for beat in range(4):
                add(CONGA_LOW, bar_start + beat, 0.5, velocity * 0.8)
            add(CONGA_HIGH, bar_start + 0.5, 0.2, velocity * 0.6)
            add(CONGA_HIGH, bar_start + 1.5, 0.2, velocity * 0.65)
            add(CONGA_HIGH, bar_start + 2.5, 0.2, velocity * 0.6)
            add(CONGA_HIGH, bar_start + 3.5, 0.2, velocity * 0.65)
            for beat in range(4):
                add(CONGA_OPEN, bar_start + beat + 0.5, 0.3, velocity * 0.5)
            add(COWBELL, bar_start + 0.0, 0.3, velocity * 0.7)
            add(COWBELL, bar_start + 2.0, 0.3, velocity * 0.7)
            add(COWBELL, bar_start + 3.5, 0.15, velocity * 0.45)
            add(COWBELL, bar_start + 3.75, 0.15, velocity * 0.45)
            clave_pattern = [(1.5, 0.3), (2.0, 0.3), (2.5, 0.3)] if bar == 0 else [(0.5, 0.3), (1.5, 0.3)]
            for beat, dur in clave_pattern:
                add(CLAVE, bar_start + beat, dur, velocity * 0.6)

        else:  # comparsa_moderna
            for h in range(16):
                add(MARACAS, bar_start + h * 0.25, 0.1, velocity * (0.3 if h % 2 == 0 else 0.25))
            for h in range(8):
                cv = velocity * (0.6 if h == 0 else 0.45)
                add(COWBELL, bar_start + h * 0.5, 0.2, cv)
            for beat in range(4):
                add(CONGA_LOW, bar_start + beat, 0.4, velocity * 0.8)
            open_hits = [0.5, 1.25, 1.75, 2.5, 3.25, 3.75]
            for oh in open_hits:
                add(CONGA_OPEN, bar_start + oh, 0.2, velocity * 0.55)
            add(CONGA_HIGH, bar_start + 1.0, 0.2, velocity * 0.7)
            add(CONGA_HIGH, bar_start + 3.0, 0.2, velocity * 0.7)
            add(CONGA_HIGH, bar_start + 1.75, 0.1, velocity * 0.4)
            add(CONGA_HIGH, bar_start + 3.75, 0.1, velocity * 0.4)
            clave_pattern = [(0.5, 0.3), (1.5, 0.3)] if bar == 0 else [(1.5, 0.3), (2.0, 0.3), (2.5, 0.3)]
            for beat, dur in clave_pattern:
                add(CLAVE, bar_start + beat, dur, velocity * 0.55)

    return notes


# === Habanera ===

class TestHabanera:
    def test_3_2_clave_bar_0(self):
        notes = _generate_comparsa("habanera", 2)
        claves = [n for n in notes if n["pitch"] == CLAVE and n["start"] < 4.0]
        starts = [c["start"] for c in claves]
        # 3-2 clave in bar 0: 1.5, 2.0, 2.5
        assert starts == [1.5, 2.0, 2.5]

    def test_3_2_clave_bar_1(self):
        notes = _generate_comparsa("habanera", 2)
        claves = [n for n in notes if n["pitch"] == CLAVE and n["start"] >= 4.0]
        starts = [c["start"] - 4.0 for c in claves]
        assert starts == [0.5, 1.5]

    def test_conga_low_on_1_and_3(self):
        notes = _generate_comparsa("habanera", 1)
        low_congas = [n for n in notes if n["pitch"] == CONGA_LOW]
        starts = [n["start"] for n in low_congas]
        assert 0.0 in starts and 2.0 in starts

    def test_cowbell_8ths(self):
        notes = _generate_comparsa("habanera", 1)
        cowbells = [n for n in notes if n["pitch"] == COWBELL]
        assert len(cowbells) == 8

    def test_maracas_on_offbeats(self):
        notes = _generate_comparsa("habanera", 1)
        maracas = [n for n in notes if n["pitch"] == MARACAS]
        starts = [m["start"] for m in maracas]
        assert 0.5 in starts and 1.5 in starts


# === Santiago ===

class TestSantiago:
    def test_2_3_clave_bar_0(self):
        notes = _generate_comparsa("santiago", 2)
        claves = [n for n in notes if n["pitch"] == CLAVE and n["start"] < 4.0]
        starts = [c["start"] for c in claves]
        # 2-3 clave in bar 0: 0.5, 1.5
        assert starts == [0.5, 1.5]

    def test_guiro_present(self):
        notes = _generate_comparsa("santiago", 1)
        guiros = [n for n in notes if n["pitch"] == GUIRO]
        assert len(guiros) == 4  # 2 long + 2 short per bar

    def test_syncopated_conga(self):
        notes = _generate_comparsa("santiago", 1)
        open_congas = [n for n in notes if n["pitch"] == CONGA_OPEN]
        # Should have syncopated positions (0.75, 2.75)
        starts = [n["start"] for n in open_congas]
        assert 0.75 in starts


# === Matanzas ===

class TestMatanzas:
    def test_quinto_improvisation(self):
        notes = _generate_comparsa("matanzas", 1)
        quinto = [n for n in notes if n["pitch"] == CONGA_HIGH]
        # Multiple syncopated hits
        assert len(quinto) == 6

    def test_sparse_cowbell(self):
        notes = _generate_comparsa("matanzas", 1)
        cowbells = [n for n in notes if n["pitch"] == COWBELL]
        # Only on 1 and 3
        assert len(cowbells) == 2

    def test_no_clave(self):
        """Matanzas style is rumba columbia — no claves."""
        notes = _generate_comparsa("matanzas", 2)
        claves = [n for n in notes if n["pitch"] == CLAVE]
        assert len(claves) == 0


# === Conga Line ===

class TestCongaLine:
    def test_bass_conga_every_beat(self):
        notes = _generate_comparsa("conga_line", 1)
        low_congas = [n for n in notes if n["pitch"] == CONGA_LOW]
        starts = [n["start"] for n in low_congas]
        assert starts == [0.0, 1.0, 2.0, 3.0]

    def test_cowbell_strong_on_1_and_3(self):
        notes = _generate_comparsa("conga_line", 1)
        cowbells = [n for n in notes if n["pitch"] == COWBELL]
        beat1 = [c for c in cowbells if c["start"] == 0.0]
        beat3 = [c for c in cowbells if c["start"] == 2.0]
        assert beat1[0]["velocity"] >= 0.49  # strong (0.7 * 0.7)
        assert beat3[0]["velocity"] >= 0.49

    def test_cowbell_fill_end(self):
        notes = _generate_comparsa("conga_line", 1)
        cowbells = [n for n in notes if n["pitch"] == COWBELL]
        fills = [c for c in cowbells if c["start"] in [3.5, 3.75]]
        assert len(fills) == 2


# === Comparsa Moderna ===

class TestComparsaModerna:
    def test_16th_maracas(self):
        notes = _generate_comparsa("comparsa_moderna", 1)
        maracas = [n for n in notes if n["pitch"] == MARACAS]
        assert len(maracas) == 16

    def test_cowbell_accent_on_1(self):
        notes = _generate_comparsa("comparsa_moderna", 1)
        cowbells = [n for n in notes if n["pitch"] == COWBELL]
        beat1 = [c for c in cowbells if c["start"] == 0.0]
        beat2 = [c for c in cowbells if c["start"] == 0.5]
        assert beat1[0]["velocity"] > beat2[0]["velocity"]

    def test_quinto_slams_on_2_and_4(self):
        notes = _generate_comparsa("comparsa_moderna", 1)
        quinto = [n for n in notes if n["pitch"] == CONGA_HIGH]
        slams = [q for q in quinto if q["velocity"] >= 0.49]
        starts = [s["start"] for s in slams]
        assert 1.0 in starts and 3.0 in starts


# === Cross-Style ===

class TestCrossStyle:
    def test_all_styles_produce_notes(self):
        for s in ["habanera", "santiago", "matanzas", "conga_line", "comparsa_moderna"]:
            notes = _generate_comparsa(s, 1)
            assert len(notes) > 0, f"Style {s} produced no notes"

    def test_velocity_clamped(self):
        for s in ["habanera", "santiago", "matanzas", "conga_line", "comparsa_moderna"]:
            notes = _generate_comparsa(s, 2, velocity=1.2)
            for n in notes:
                assert n["velocity"] <= 1.0

    def test_velocity_clamped_low(self):
        notes = _generate_comparsa("habanera", 1, velocity=-0.5)
        for n in notes:
            assert n["velocity"] >= 0.0

    def test_start_beat_offset(self):
        notes = _generate_comparsa("habanera", 1, start_beat=8.0)
        assert notes[0]["start"] >= 8.0

    def test_multiple_bars(self):
        notes = _generate_comparsa("habanera", 4)
        assert len(notes) > 0


class TestEdgeCases:
    def test_single_bar(self):
        notes = _generate_comparsa("habanera", 1)
        assert len(notes) > 0

    def test_8_bars(self):
        notes = _generate_comparsa("comparsa_moderna", 8)
        assert len(notes) > 100

    def test_all_instruments_present_habanera(self):
        notes = _generate_comparsa("habanera", 2)
        pitches = set(n["pitch"] for n in notes)
        assert CONGA_LOW in pitches
        assert CONGA_HIGH in pitches
        assert CONGA_OPEN in pitches
        assert CLAVE in pitches
        assert COWBELL in pitches
        assert MARACAS in pitches
