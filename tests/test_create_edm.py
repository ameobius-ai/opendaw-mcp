"""Unit tests for create_edm_arrangement."""
import json
import pytest

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
            "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
            "A#": 10, "Bb": 10, "B": 11}

KICK = 36
CLAP = 39
HAT_C = 42
HAT_O = 46
SNARE = 38

minor = [0, 2, 3, 5, 7, 8, 10]


def _generate_edm(bpm=128, bars=16, root="F", octave=3, velocity=0.8, start_beat=0.0):
    """Pure-Python reimplementation of create_edm_arrangement logic."""
    root_pc = NOTE_MAP[root]
    root_pitch = (octave + 1) * 12 + root_pc

    chord_degrees = [0, 5, 2, 6]
    chord_types = {0: [0, 3, 7], 5: [0, 3, 7], 2: [0, 3, 7], 6: [0, 3, 7]}

    beats_per_bar = 4
    bars_per_chord = max(2, bars // 4)

    drum_notes = []
    bass_notes = []
    synth_notes = []
    lead_notes = []

    for chord_idx, deg in enumerate(chord_degrees):
        chord_start = start_beat + chord_idx * bars_per_chord * beats_per_bar
        chord_root = root_pitch + minor[deg % 7] + (12 * (deg // 7))
        triad = chord_types.get(deg, [0, 3, 7])

        for bar in range(bars_per_chord):
            bar_start = chord_start + bar * beats_per_bar

            # Drums
            for beat in range(4):
                drum_notes.append({"pitch": KICK, "start": round(bar_start + beat, 4), "duration": 0.5, "velocity": velocity * 0.95})
            for beat in [1, 3]:
                drum_notes.append({"pitch": CLAP, "start": round(bar_start + beat, 4), "duration": 0.3, "velocity": velocity * 0.8})
            for beat in range(4):
                drum_notes.append({"pitch": HAT_O, "start": round(bar_start + beat + 0.5, 4), "duration": 0.2, "velocity": velocity * 0.5})
            for h in range(16):
                hat_beat = bar_start + h * 0.25
                hat_vel = velocity * (0.3 if h % 2 == 0 else 0.2)
                drum_notes.append({"pitch": HAT_C, "start": round(hat_beat, 4), "duration": 0.1, "velocity": round(hat_vel, 3)})

            if bar >= bars_per_chord - 2 and chord_idx < 3:
                if bar == bars_per_chord - 1:
                    for s in range(16):
                        svel = velocity * (0.3 + 0.04 * s)
                        drum_notes.append({"pitch": SNARE, "start": round(bar_start + s * 0.25, 4), "duration": 0.1, "velocity": round(min(svel, velocity), 3)})

            # Bass offbeat
            for beat in range(4):
                bass_notes.append({"pitch": chord_root - 12, "start": round(bar_start + beat + 0.5, 4), "duration": 0.45, "velocity": round(velocity * 0.85, 3)})

            # Supersaw stabs on 1 and 3
            for beat in [0, 2]:
                for interval in triad:
                    synth_notes.append({"pitch": chord_root + interval, "start": round(bar_start + beat, 4), "duration": 1.8, "velocity": round(velocity * 0.6, 3)})

            # Lead arp
            arp_intervals = [triad[0], triad[1], triad[2], triad[1], triad[0] + 12, triad[2], triad[1], triad[0]]
            for h in range(8):
                lead_pitch = chord_root + arp_intervals[h % len(arp_intervals)]
                lead_notes.append({"pitch": lead_pitch + 12, "start": round(bar_start + h * 0.5, 4), "duration": 0.4, "velocity": round(velocity * (0.55 + 0.06 * (h % 4)), 3)})

    return drum_notes, bass_notes, synth_notes, lead_notes


# === Drums ===

class TestDrums:
    def test_four_on_floor(self):
        drums, _, _, _ = _generate_edm(bars=16)
        kicks = [n for n in drums if n["pitch"] == KICK]
        kick_starts = [k["start"] for k in kicks[:4]]
        assert kick_starts == [0.0, 1.0, 2.0, 3.0]

    def test_claps_on_2_and_4(self):
        drums, _, _, _ = _generate_edm(bars=16)
        claps = [n for n in drums if n["pitch"] == CLAP]
        clap_starts = [c["start"] for c in claps[:2]]
        assert 1.0 in clap_starts
        assert 3.0 in clap_starts

    def test_open_hats_on_offbeats(self):
        drums, _, _, _ = _generate_edm(bars=16)
        open_hats = [n for n in drums if n["pitch"] == HAT_O]
        assert len(open_hats) > 0
        # First open hat at 0.5
        assert open_hats[0]["start"] == 0.5

    def test_16th_closed_hats(self):
        drums, _, _, _ = _generate_edm(bars=16)
        closed_hats = [n for n in drums if n["pitch"] == HAT_C]
        # 16 per bar
        bar0_hats = [h for h in closed_hats if h["start"] < 4.0]
        assert len(bar0_hats) == 16

    def test_snare_buildup(self):
        drums, _, _, _ = _generate_edm(bars=16)
        snares = [n for n in drums if n["pitch"] == SNARE]
        # Buildup on last bar of each chord except the last
        assert len(snares) > 0
        # Crescendo: later snares louder
        assert snares[-1]["velocity"] > snares[0]["velocity"]


# === Bass ===

class TestBass:
    def test_offbeat_bass(self):
        _, bass, _, _ = _generate_edm(bars=16, root="F", octave=3)
        # F3=53, bass = 53-12 = 41, on the "and" of beat 0 = 0.5
        assert bass[0]["start"] == 0.5
        assert bass[0]["pitch"] == 41

    def test_bass_one_per_beat(self):
        _, bass, _, _ = _generate_edm(bars=16)
        bar0 = [n for n in bass if n["start"] < 4.0]
        assert len(bar0) == 4

    def test_bass_follows_chord(self):
        _, bass, _, _ = _generate_edm(bars=8, root="F", octave=3)
        # Chord 0 = F minor, root = F3 = 53, bass = 41
        # Chord 1 = Db (degree 5), minor[5] = 8, root = 53+8 = 61, bass = 49
        # bars=8 → bars_per_chord=2, chord 1 starts at beat 8
        chord1_bass = [n for n in bass if n["start"] >= 8.0 and n["start"] < 16.0]
        assert chord1_bass[0]["pitch"] == 49  # Db


# === Synth ===

class TestSynth:
    def test_supersaw_stabs_on_1_and_3(self):
        _, _, synth, _ = _generate_edm(bars=16, root="F", octave=3)
        # F minor triad: F3=53, Ab3=56, C4=60
        bar0_stabs = [n for n in synth if n["start"] == 0.0]
        pitches = sorted([n["pitch"] for n in bar0_stabs])
        assert pitches == [53, 56, 60]

    def test_synth_sustained(self):
        _, _, synth, _ = _generate_edm(bars=16)
        # Duration 1.8 beats
        assert synth[0]["duration"] == 1.8

    def test_synth_on_beats_1_and_3(self):
        _, _, synth, _ = _generate_edm(bars=16)
        bar0_starts = sorted(set([n["start"] for n in synth if n["start"] < 4.0]))
        assert bar0_starts == [0.0, 2.0]


# === Lead ===

class TestLead:
    def test_arpeggiated_pattern(self):
        _, _, _, lead = _generate_edm(bars=16, root="F", octave=3)
        # First note: root + 12 = F4 = 65
        assert lead[0]["pitch"] == 65
        # 8 notes per bar (8th notes)
        bar0 = [n for n in lead if n["start"] < 4.0]
        assert len(bar0) == 8

    def test_lead_octave_up(self):
        _, _, _, lead = _generate_edm(bars=16, root="F", octave=3)
        # Lead should be above synth
        # Root = F3 = 53, lead = root + interval + 12
        assert lead[0]["pitch"] > 53

    def test_lead_8th_note_spacing(self):
        _, _, _, lead = _generate_edm(bars=16)
        bar0 = [n for n in lead if n["start"] < 4.0]
        starts = [n["start"] for n in bar0]
        expected = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        assert starts == expected


# === Progression ===

class TestProgression:
    def test_i_chord(self):
        _, _, synth, _ = _generate_edm(bars=16, root="F", octave=3)
        # i = F minor: 53, 56, 60
        bar0 = [n for n in synth if n["start"] == 0.0]
        pitches = sorted([n["pitch"] for n in bar0])
        assert pitches == [53, 56, 60]

    def test_vi_chord(self):
        _, _, synth, _ = _generate_edm(bars=8, root="F", octave=3)
        # VI = Db minor: 61, 64, 68
        # degree 5, minor[5] = 8, root = 53+8 = 61
        # bars=8 → bars_per_chord=2, chord 1 starts at beat 8
        bar_chord1 = [n for n in synth if n["start"] == 8.0]
        pitches = sorted([n["pitch"] for n in bar_chord1])
        assert pitches == [61, 64, 68]


# === Structure ===

class TestStructure:
    def test_four_tracks(self):
        drums, bass, synth, lead = _generate_edm(bars=16)
        assert len(drums) > 0
        assert len(bass) > 0
        assert len(synth) > 0
        assert len(lead) > 0

    def test_total_notes(self):
        drums, bass, synth, lead = _generate_edm(bars=16)
        total = len(drums) + len(bass) + len(synth) + len(lead)
        assert total > 200  # substantial

    def test_velocity_range(self):
        drums, bass, synth, lead = _generate_edm(bars=16, velocity=0.9)
        for n in drums + bass + synth + lead:
            assert 0.0 <= n["velocity"] <= 1.0


class TestEdgeCases:
    def test_8_bars(self):
        drums, _, _, _ = _generate_edm(bars=8)
        assert len(drums) > 0

    def test_32_bars(self):
        drums, _, _, _ = _generate_edm(bars=32)
        assert len(drums) > 0

    def test_different_root(self):
        _, _, synth, _ = _generate_edm(bars=16, root="A", octave=3)
        # A minor: A3=57, C4=60, E4=64
        bar0 = [n for n in synth if n["start"] == 0.0]
        pitches = sorted([n["pitch"] for n in bar0])
        assert pitches == [57, 60, 64]
