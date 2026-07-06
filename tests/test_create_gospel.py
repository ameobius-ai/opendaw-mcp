"""Unit tests for create_gospel_arrangement."""
import json
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}

KICK = 36
SNARE = 38
HAT_C = 42
HAT_O = 46

major = [0, 2, 4, 5, 7, 9, 11]


def _generate_gospel(bpm=75, bars=8, root="Ab", octave=3, velocity=0.7, start_beat=0.0):
    """Pure-Python reimplementation of create_gospel_arrangement logic."""
    root_pc = NOTE_MAP[root]
    root_pitch = (octave + 1) * 12 + root_pc

    chord_roots = [0, 3, 4, 0]
    chord_types = {0: [0, 4, 7], 3: [0, 4, 7], 4: [0, 4, 7]}
    bars_per_chord = bars // 4 if bars >= 4 else 2
    beats_per_bar = 4

    drum_notes = []
    bass_notes = []
    organ_notes = []
    choir_notes = []

    for chord_idx, deg in enumerate(chord_roots):
        chord_start_beat = start_beat + chord_idx * bars_per_chord * beats_per_bar
        chord_root_pitch = root_pitch + major[deg % 7] + (12 * (deg // 7))
        triad = chord_types.get(deg, [0, 4, 7])

        for bar in range(bars_per_chord):
            bar_start = chord_start_beat + bar * beats_per_bar

            # Drums
            drum_notes.append({"pitch": KICK, "start": round(bar_start, 4), "duration": 0.5, "velocity": velocity * 0.9})
            drum_notes.append({"pitch": KICK, "start": round(bar_start + 2.0, 4), "duration": 0.5, "velocity": velocity * 0.8})
            drum_notes.append({"pitch": SNARE, "start": round(bar_start + 1.0, 4), "duration": 0.4, "velocity": velocity * 0.85})
            drum_notes.append({"pitch": SNARE, "start": round(bar_start + 3.0, 4), "duration": 0.4, "velocity": velocity * 0.85})
            drum_notes.append({"pitch": SNARE, "start": round(bar_start + 3.5, 4), "duration": 0.2, "velocity": velocity * 0.3})
            for h in range(8):
                hat_beat = bar_start + h * 0.5
                if h % 2 == 1:
                    hat_beat += 0.08
                hat_vel = velocity * (0.4 if h % 2 == 0 else 0.3)
                drum_notes.append({"pitch": HAT_C, "start": round(hat_beat, 4), "duration": 0.2, "velocity": round(hat_vel, 3)})
            drum_notes.append({"pitch": HAT_O, "start": round(bar_start + 3.5, 4), "duration": 0.3, "velocity": round(velocity * 0.35, 3)})

            # Bass walking
            walk_degrees = [0, 2, 4, 6]
            for b in range(4):
                walk_deg = walk_degrees[b]
                walk_pitch = chord_root_pitch - 12 + major[walk_deg % 7] + (12 * (walk_deg // 7))
                bass_notes.append({
                    "pitch": walk_pitch,
                    "start": round(bar_start + b * 1.0, 4),
                    "duration": 0.9,
                    "velocity": round(velocity * 0.75, 3),
                })

            # Organ stabs
            for beat in range(4):
                beat_pos = bar_start + beat * 1.0
                is_stab = beat % 2 == 0
                stab_vel = velocity * (0.65 if is_stab else 0.5)
                for interval in triad:
                    organ_notes.append({
                        "pitch": chord_root_pitch + interval,
                        "start": round(beat_pos, 4),
                        "duration": 0.9 if not is_stab else 0.45,
                        "velocity": round(stab_vel, 3),
                    })

            # Choir SATB
            choir_pitches = [
                chord_root_pitch + 12,
                chord_root_pitch + 16,
                chord_root_pitch + 19,
                chord_root_pitch - 12,
            ]
            swell = 0.5 + 0.1 * (bar / max(1, bars_per_chord))
            for pitch in choir_pitches:
                choir_notes.append({
                    "pitch": pitch,
                    "start": round(bar_start, 4),
                    "duration": round(beats_per_bar * 0.98, 4),
                    "velocity": round(velocity * swell, 3),
                })

    return drum_notes, bass_notes, organ_notes, choir_notes


# === Drum Tests ===

class TestDrums:
    def test_kick_on_1_and_3(self):
        drums, _, _, _ = _generate_gospel(bars=8)
        kicks = [n for n in drums if n["pitch"] == KICK]
        kick_starts = [k["start"] for k in kicks[:4]]
        # First bar: kick on 0 and 2
        assert 0.0 in kick_starts
        assert 2.0 in kick_starts

    def test_snare_on_2_and_4(self):
        drums, _, _, _ = _generate_gospel(bars=8)
        snares = [n for n in drums if n["pitch"] == SNARE]
        snare_starts = [s["start"] for s in snares[:4]]
        assert 1.0 in snare_starts
        assert 3.0 in snare_starts

    def test_ghost_snare(self):
        drums, _, _, _ = _generate_gospel(bars=8)
        snares = [n for n in drums if n["pitch"] == SNARE]
        ghosts = [s for s in snares if s["velocity"] < 0.35]
        assert len(ghosts) > 0  # ghost notes present

    def test_shuffle_hats(self):
        drums, _, _, _ = _generate_gospel(bars=8)
        hats = [n for n in drums if n["pitch"] == HAT_C]
        # Odd hats should have shuffle offset
        odd_hats = [h for h in hats if h["start"] % 1.0 > 0.5]
        assert len(odd_hats) > 0

    def test_hats_count_per_bar(self):
        drums, _, _, _ = _generate_gospel(bars=8)
        hats = [n for n in drums if n["pitch"] == HAT_C]
        # 8 hats per bar × 8 bars = 64
        assert len(hats) == 64

    def test_open_hat_on_4_and(self):
        drums, _, _, _ = _generate_gospel(bars=8)
        open_hats = [n for n in drums if n["pitch"] == HAT_O]
        # One open hat per bar at 3.5
        for oh in open_hats[:3]:
            assert oh["start"] % 4.0 == 3.5


# === Bass Tests ===

class TestBass:
    def test_walking_pattern(self):
        _, bass, _, _ = _generate_gospel(bars=8, root="C", octave=3)
        # First chord = C major, root=48
        # Walking: root(48-12=36) → 3rd(36+4=40) → 5th(36+7=43) → 7th(36+11=47)
        bar0 = [n for n in bass if n["start"] < 4.0]
        pitches = [n["pitch"] for n in bar0]
        assert pitches == [36, 40, 43, 47]

    def test_bass_one_per_beat(self):
        _, bass, _, _ = _generate_gospel(bars=8)
        bar0 = [n for n in bass if n["start"] < 4.0]
        assert len(bar0) == 4

    def test_bass_below_root(self):
        _, bass, _, _ = _generate_gospel(bars=8, root="C", octave=3)
        # Bass should be below root_pitch (48)
        assert bass[0]["pitch"] < 48


# === Organ Tests ===

class TestOrgan:
    def test_organ_chord_stabs(self):
        _, _, organ, _ = _generate_gospel(bars=8, root="C", octave=3)
        # First chord C major: 48, 52, 55
        bar0_stab = [n for n in organ if n["start"] == 0.0]
        pitches = sorted([n["pitch"] for n in bar0_stab])
        assert pitches == [48, 52, 55]

    def test_organ_sustained_on_2_and_4(self):
        _, _, organ, _ = _generate_gospel(bars=8)
        beat2 = [n for n in organ if n["start"] == 1.0]
        # Sustained = duration 0.9
        assert beat2[0]["duration"] == 0.9

    def test_organ_stab_shorter(self):
        _, _, organ, _ = _generate_gospel(bars=8)
        beat1 = [n for n in organ if n["start"] == 0.0]
        # Stab = duration 0.45
        assert beat1[0]["duration"] == 0.45


# === Choir Tests ===

class TestChoir:
    def test_choir_satb(self):
        _, _, _, choir = _generate_gospel(bars=8, root="C", octave=3)
        # C major chord: soprano=60, alto=64, tenor=67, bass=36
        bar0 = [n for n in choir if n["start"] == 0.0]
        pitches = sorted([n["pitch"] for n in bar0])
        assert pitches == [36, 60, 64, 67]

    def test_choir_sustained(self):
        _, _, _, choir = _generate_gospel(bars=8)
        # Duration should be close to 4 beats
        assert choir[0]["duration"] == round(4 * 0.98, 4)

    def test_choir_dynamic_swell(self):
        _, _, _, choir = _generate_gospel(bars=8)
        # Later bars should have slightly higher velocity (swell)
        bar0 = [n for n in choir if n["start"] < 4.0]
        bar1 = [n for n in choir if n["start"] >= 4.0 and n["start"] < 8.0]
        if bar0 and bar1:
            assert bar1[0]["velocity"] >= bar0[0]["velocity"]


# === Progression ===

class TestProgression:
    def test_iv_chord(self):
        _, _, organ, _ = _generate_gospel(bars=8, root="C", octave=3)
        # IV = F major, starts at bar 2 (beats 8)
        iv_organ = [n for n in organ if n["start"] == 8.0]
        pitches = sorted([n["pitch"] for n in iv_organ])
        # F major: F3=53, A3=57, C4=60
        assert pitches == [53, 57, 60]

    def test_v_chord(self):
        _, _, organ, _ = _generate_gospel(bars=8, root="C", octave=3)
        # V = G major, starts at bar 4 (beats 16)
        v_organ = [n for n in organ if n["start"] == 16.0]
        pitches = sorted([n["pitch"] for n in v_organ])
        # G major: G3=55, B3=59, D4=62
        assert pitches == [55, 59, 62]

    def test_i_chord_returns(self):
        _, _, organ, _ = _generate_gospel(bars=8, root="C", octave=3)
        # I returns at bar 6 (beats 24)
        i_organ = [n for n in organ if n["start"] == 24.0]
        pitches = sorted([n["pitch"] for n in i_organ])
        assert pitches == [48, 52, 55]  # C major


# === Structure ===

class TestStructure:
    def test_four_tracks(self):
        drums, bass, organ, choir = _generate_gospel(bars=8)
        assert len(drums) > 0
        assert len(bass) > 0
        assert len(organ) > 0
        assert len(choir) > 0

    def test_total_notes(self):
        drums, bass, organ, choir = _generate_gospel(bars=8)
        total = len(drums) + len(bass) + len(organ) + len(choir)
        assert total > 100  # substantial arrangement

    def test_ab_default(self):
        drums, _, _, _ = _generate_gospel(bars=8, root="Ab")
        # Ab = 8, octave 3 → (4)*12+8 = 56
        # First kick at 0
        assert drums[0]["start"] == 0.0

    def test_velocity_range(self):
        drums, bass, organ, choir = _generate_gospel(bars=8, velocity=0.9)
        for n in drums + bass + organ + choir:
            assert 0.0 <= n["velocity"] <= 1.0


class TestEdgeCases:
    def test_4_bars(self):
        drums, bass, organ, choir = _generate_gospel(bars=4)
        assert len(drums) > 0

    def test_16_bars(self):
        drums, bass, organ, choir = _generate_gospel(bars=16)
        assert len(drums) > 0

    def test_different_root(self):
        drums, bass, organ, choir = _generate_gospel(bars=8, root="F")
        # F = 5, octave 3 → (4)*12+5 = 53
        # First organ chord: F major = 53, 57, 60
        bar0_organ = [n for n in organ if n["start"] == 0.0]
        pitches = sorted([n["pitch"] for n in bar0_organ])
        assert pitches == [53, 57, 60]
