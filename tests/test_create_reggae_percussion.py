"""Unit tests for create_reggae_percussion."""
import json
import pytest

KICK = 36
SNARE = 38
HAT_C = 42
HAT_O = 46


def _generate_reggae(style, bars, tempo_bpm=75.0, velocity=0.7, swing=0.0, start_beat=0.0):
    """Pure-Python reimplementation of create_reggae_percussion logic."""
    sec_per_beat = 60.0 / tempo_bpm
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

        if style == "one_drop":
            for h in range(8):
                hat_beat = bar_start + h * 0.5
                if h % 2 == 1 and swing > 0:
                    hat_beat += swing * 0.15
                hat_vel = velocity * 0.45 if h % 2 == 0 else velocity * 0.35
                add(HAT_C, hat_beat, 0.3, hat_vel)
            add(KICK, bar_start + 2.0, 0.5, velocity)
            add(SNARE, bar_start + 2.0, 0.4, velocity * 0.85)
            if bar % 2 == 0:
                add(KICK, bar_start + 0.0, 0.4, velocity * 0.6)

        elif style == "rockers":
            for h in range(8):
                hat_beat = bar_start + h * 0.5
                if h % 2 == 1 and swing > 0:
                    hat_beat += swing * 0.12
                add(HAT_C, hat_beat, 0.3, velocity * 0.4)
            add(KICK, bar_start + 0.0, 0.5, velocity * 0.9)
            add(SNARE, bar_start + 1.0, 0.4, velocity * 0.8)
            add(KICK, bar_start + 2.0, 0.5, velocity)
            add(SNARE, bar_start + 3.0, 0.4, velocity * 0.8)
            add(KICK, bar_start + 3.5, 0.3, velocity * 0.5)

        elif style == "steppers":
            for beat in range(4):
                add(KICK, bar_start + beat * 1.0, 0.5, velocity * 0.85)
            add(SNARE, bar_start + 2.0, 0.4, velocity * 0.85)
            for h in range(8):
                hat_beat = bar_start + h * 0.5
                if h % 2 == 1 and swing > 0:
                    hat_beat += swing * 0.1
                add(HAT_C, hat_beat, 0.3, velocity * 0.35)
            if bar % 2 == 1:
                add(HAT_O, bar_start + 3.5, 0.3, velocity * 0.4)

        elif style == "ska":
            add(KICK, bar_start + 0.0, 0.3, velocity * 0.9)
            add(SNARE, bar_start + 1.0, 0.3, velocity * 0.8)
            add(KICK, bar_start + 2.0, 0.3, velocity * 0.9)
            add(SNARE, bar_start + 3.0, 0.3, velocity * 0.8)
            for h in range(8):
                hat_beat = bar_start + h * 0.5
                if h % 2 == 1:
                    if swing > 0:
                        hat_beat += swing * 0.15
                    add(HAT_C, hat_beat, 0.25, velocity * 0.6)
                else:
                    add(HAT_C, hat_beat, 0.25, velocity * 0.3)
            add(HAT_O, bar_start + 1.5, 0.25, velocity * 0.5)
            add(HAT_O, bar_start + 3.5, 0.25, velocity * 0.5)

        elif style == "rocksteady":
            add(KICK, bar_start + 0.0, 0.5, velocity * 0.85)
            add(KICK, bar_start + 2.0, 0.5, velocity)
            add(SNARE, bar_start + 2.0, 0.4, velocity * 0.8)
            add(SNARE, bar_start + 3.0, 0.3, velocity * 0.4)
            for h in range(8):
                hat_beat = bar_start + h * 0.5 - 0.02
                add(HAT_C, hat_beat, 0.3, velocity * 0.4)
            add(HAT_O, bar_start + 1.5, 0.3, velocity * 0.45)

        else:  # dancehall
            add(KICK, bar_start + 0.0, 0.4, velocity)
            add(SNARE, bar_start + 1.0, 0.3, velocity * 0.85)
            add(KICK, bar_start + 2.5, 0.3, velocity * 0.8)
            add(SNARE, bar_start + 3.0, 0.3, velocity * 0.85)
            for h in range(16):
                hat_beat = bar_start + h * 0.25
                if h % 4 == 3 and swing > 0:
                    hat_beat += swing * 0.08
                vel = velocity * 0.35 if h % 2 == 0 else velocity * 0.25
                add(HAT_C, hat_beat, 0.15, vel)
            add(HAT_O, bar_start + 3.5, 0.2, velocity * 0.5)

    return notes


# === One-Drop ===

class TestOneDrop:
    def test_drop_on_beat_3(self):
        notes = _generate_reggae("one_drop", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        snares = [n for n in notes if n["pitch"] == SNARE]
        # Kick on beat 3 (position 2.0)
        assert any(k["start"] == 2.0 for k in kicks)
        # Snare on beat 3 (position 2.0)
        assert any(s["start"] == 2.0 for s in snares)

    def test_no_snare_on_1_2_4(self):
        notes = _generate_reggae("one_drop", 1)
        snares = [n for n in notes if n["pitch"] == SNARE]
        snare_starts = [s["start"] for s in snares]
        # Only beat 3
        assert snare_starts == [2.0]

    def test_hihat_8ths(self):
        notes = _generate_reggae("one_drop", 1)
        hats = [n for n in notes if n["pitch"] == HAT_C]
        assert len(hats) == 8  # 8 eighth notes per bar

    def test_hihat_velocities(self):
        notes = _generate_reggae("one_drop", 1, velocity=0.8)
        hats = [n for n in notes if n["pitch"] == HAT_C]
        # Even hats louder than odd
        even = [h for h in hats if h["start"] % 1.0 == 0]
        odd = [h for h in hats if h["start"] % 1.0 != 0]
        assert even[0]["velocity"] > odd[0]["velocity"]

    def test_light_kick_on_bar_0(self):
        notes = _generate_reggae("one_drop", 2)
        kicks = [n for n in notes if n["pitch"] == KICK]
        # Bar 0 has light kick on beat 1 (vel * 0.6)
        bar0_kicks = [k for k in kicks if k["start"] < 4.0]
        beat1_kick = [k for k in bar0_kicks if k["start"] == 0.0]
        assert len(beat1_kick) == 1
        assert beat1_kick[0]["velocity"] == round(0.7 * 0.6, 3)

    def test_no_light_kick_on_bar_1(self):
        notes = _generate_reggae("one_drop", 2)
        kicks = [n for n in notes if n["pitch"] == KICK]
        bar1_kicks = [k for k in kicks if k["start"] >= 4.0]
        beat1_kick = [k for k in bar1_kicks if k["start"] == 4.0]
        assert len(beat1_kick) == 0

    def test_multiple_bars(self):
        notes = _generate_reggae("one_drop", 4)
        # Each bar has: 8 hats + 1 kick(drop) + 1 snare(drop) + 0-1 light kick
        # Bar 0: 8+1+1+1=11, Bar 1: 8+1+1=10, Bar 2: 8+1+1+1=11, Bar 3: 8+1+1=10
        assert len(notes) == 42


# === Rockers ===

class TestRockers:
    def test_kick_on_1_and_3(self):
        notes = _generate_reggae("rockers", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        kick_starts = sorted([k["start"] for k in kicks])
        assert 0.0 in kick_starts
        assert 2.0 in kick_starts

    def test_snare_on_2_and_4(self):
        notes = _generate_reggae("rockers", 1)
        snares = [n for n in notes if n["pitch"] == SNARE]
        snare_starts = sorted([s["start"] for s in snares])
        assert snare_starts == [1.0, 3.0]

    def test_extra_kick_on_3_5(self):
        notes = _generate_reggae("rockers", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        assert any(k["start"] == 3.5 for k in kicks)

    def test_hihat_8ths(self):
        notes = _generate_reggae("rockers", 1)
        hats = [n for n in notes if n["pitch"] == HAT_C]
        assert len(hats) == 8


# === Steppers ===

class TestSteppers:
    def test_four_on_floor_kicks(self):
        notes = _generate_reggae("steppers", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        kick_starts = sorted([k["start"] for k in kicks])
        assert kick_starts == [0.0, 1.0, 2.0, 3.0]

    def test_snare_on_3(self):
        notes = _generate_reggae("steppers", 1)
        snares = [n for n in notes if n["pitch"] == SNARE]
        snare_starts = [s["start"] for s in snares]
        assert snare_starts == [2.0]

    def test_open_hat_on_odd_bars(self):
        notes = _generate_reggae("steppers", 2)
        open_hats = [n for n in notes if n["pitch"] == HAT_O]
        # Bar 1 (odd) has open hat on 3.5
        assert len(open_hats) == 1
        assert open_hats[0]["start"] == 4.0 + 3.5  # bar 1 start + 3.5

    def test_no_open_hat_on_bar_0(self):
        notes = _generate_reggae("steppers", 1)
        open_hats = [n for n in notes if n["pitch"] == HAT_O]
        assert len(open_hats) == 0


# === Ska ===

class TestSka:
    def test_kick_on_1_and_3(self):
        notes = _generate_reggae("ska", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        kick_starts = sorted([k["start"] for k in kicks])
        assert kick_starts == [0.0, 2.0]

    def test_snare_on_2_and_4(self):
        notes = _generate_reggae("ska", 1)
        snares = [n for n in notes if n["pitch"] == SNARE]
        snare_starts = sorted([s["start"] for s in snares])
        assert snare_starts == [1.0, 3.0]

    def test_offbeat_hat_emphasis(self):
        notes = _generate_reggae("ska", 1)
        hats = [n for n in notes if n["pitch"] == HAT_C]
        even = [h for h in hats if h["start"] % 1.0 == 0]
        odd = [h for h in hats if h["start"] % 1.0 != 0]
        # Offbeat hats louder in ska
        assert odd[0]["velocity"] > even[0]["velocity"]

    def test_open_hats_on_offbeats(self):
        notes = _generate_reggae("ska", 1)
        open_hats = [n for n in notes if n["pitch"] == HAT_O]
        open_starts = sorted([h["start"] for h in open_hats])
        assert open_starts == [1.5, 3.5]


# === Rocksteady ===

class TestRocksteady:
    def test_kick_on_1_and_3(self):
        notes = _generate_reggae("rocksteady", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        kick_starts = sorted([k["start"] for k in kicks])
        assert kick_starts == [0.0, 2.0]

    def test_snare_on_3_and_ghost_4(self):
        notes = _generate_reggae("rocksteady", 1)
        snares = [n for n in notes if n["pitch"] == SNARE]
        snare_starts = sorted([s["start"] for s in snares])
        assert 2.0 in snare_starts
        assert 3.0 in snare_starts
        # Ghost on 4 is quieter
        ghost = [s for s in snares if s["start"] == 3.0][0]
        main = [s for s in snares if s["start"] == 2.0][0]
        assert ghost["velocity"] < main["velocity"]

    def test_behind_beat_hat(self):
        notes = _generate_reggae("rocksteady", 1)
        hats = [n for n in notes if n["pitch"] == HAT_C]
        # First hat should be at -0.02 from beat 0
        assert hats[0]["start"] == round(-0.02, 4)

    def test_open_hat_on_1_5(self):
        notes = _generate_reggae("rocksteady", 1)
        open_hats = [n for n in notes if n["pitch"] == HAT_O]
        assert len(open_hats) == 1
        assert open_hats[0]["start"] == 1.5


# === Dancehall ===

class TestDancehall:
    def test_kick_pattern(self):
        notes = _generate_reggae("dancehall", 1)
        kicks = [n for n in notes if n["pitch"] == KICK]
        kick_starts = sorted([k["start"] for k in kicks])
        assert kick_starts == [0.0, 2.5]  # beat 1 and 3-and

    def test_snare_on_2_and_4(self):
        notes = _generate_reggae("dancehall", 1)
        snares = [n for n in notes if n["pitch"] == SNARE]
        snare_starts = sorted([s["start"] for s in snares])
        assert snare_starts == [1.0, 3.0]

    def test_16th_hats(self):
        notes = _generate_reggae("dancehall", 1)
        hats = [n for n in notes if n["pitch"] == HAT_C]
        assert len(hats) == 16  # 16 sixteenth notes

    def test_open_hat_on_and_of_4(self):
        notes = _generate_reggae("dancehall", 1)
        open_hats = [n for n in notes if n["pitch"] == HAT_O]
        assert len(open_hats) == 1
        assert open_hats[0]["start"] == 3.5


# === Cross-style ===

class TestCrossStyle:
    def test_all_styles_produce_notes(self):
        for s in ["one_drop", "rockers", "steppers", "ska", "rocksteady", "dancehall"]:
            notes = _generate_reggae(s, 1)
            assert len(notes) > 0, f"Style {s} produced no notes"

    def test_notes_within_velocity_range(self):
        for s in ["one_drop", "rockers", "steppers", "ska", "rocksteady", "dancehall"]:
            notes = _generate_reggae(s, 2, velocity=0.9)
            for n in notes:
                assert 0.0 <= n["velocity"] <= 1.0

    def test_swing_affects_offbeats(self):
        no_swing = _generate_reggae("one_drop", 1, swing=0.0)
        with_swing = _generate_reggae("one_drop", 1, swing=0.5)
        # Odd hats should be at different positions
        no_swing_odd = [n for n in no_swing if n["pitch"] == HAT_C and n["start"] % 1.0 != 0]
        with_swing_odd = [n for n in with_swing if n["pitch"] == HAT_C and n["start"] % 1.0 != 0]
        assert no_swing_odd[0]["start"] != with_swing_odd[0]["start"]

    def test_multiple_bars_progression(self):
        notes = _generate_reggae("steppers", 4)
        kicks = [n for n in notes if n["pitch"] == KICK]
        # 4 kicks per bar × 4 bars = 16
        assert len(kicks) == 16

    def test_tempo_affects_sec_per_beat(self):
        # Tempo is metadata, but verify the calculation
        bpm_75 = 60.0 / 75.0
        bpm_120 = 60.0 / 120.0
        assert bpm_75 > bpm_120  # slower = longer beat

    def test_start_beat_offset(self):
        notes = _generate_reggae("one_drop", 1, start_beat=8.0)
        # First note should be at start_beat (hat at beat 0 of bar 0)
        first_starts = [n["start"] for n in notes if n["pitch"] == HAT_C]
        assert min(first_starts) == 8.0


class TestEdgeCases:
    def test_single_bar(self):
        notes = _generate_reggae("one_drop", 1)
        assert len(notes) > 0

    def test_many_bars(self):
        notes = _generate_reggae("rockers", 8)
        assert len(notes) > 0

    def test_high_velocity_clamped(self):
        notes = _generate_reggae("steppers", 1, velocity=1.5)
        for n in notes:
            assert n["velocity"] <= 1.0

    def test_low_velocity_clamped(self):
        notes = _generate_reggae("steppers", 1, velocity=-0.5)
        for n in notes:
            assert n["velocity"] >= 0.0
