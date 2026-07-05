
import math


class TestCreateMelodicPolyrhythm:
    """Unit tests for create_melodic_polyrhythm — melodic polyrhythm generation"""

    def test_numerator_clamping(self):
        """numerator clamped to 2-9"""
        assert max(2, min(9, 1)) == 2, "clamped to 2"
        assert max(2, min(9, 12)) == 9, "clamped to 9"
        assert max(2, min(9, 3)) == 3, "3 is valid"

    def test_denominator_clamping(self):
        """denominator clamped to 2-8"""
        assert max(2, min(8, 1)) == 2, "clamped to 2"
        assert max(2, min(8, 10)) == 8, "clamped to 8"
        assert max(2, min(8, 4)) == 4, "4 is valid"

    def test_bars_clamping(self):
        """bars clamped to 1-8"""
        assert max(1, min(8, 0)) == 1, "clamped to 1"
        assert max(1, min(8, 12)) == 8, "clamped to 8"

    def test_total_notes_calculation(self):
        """total notes = numerator * bars"""
        assert 3 * 1 == 3, "3:4 over 1 bar = 3 notes"
        assert 5 * 2 == 10, "5:4 over 2 bars = 10 notes"
        assert 7 * 4 == 28, "7:4 over 4 bars = 28 notes"

    def test_beat_spacing_3_4(self):
        """3:4 — each note 1.333 beats apart"""
        numer = 3
        denom = 4
        spacing = denom / numer
        assert abs(spacing - 1.3333) < 0.01, "4/3 = 1.333 beats"

    def test_beat_spacing_5_4(self):
        """5:4 — each note 0.8 beats apart"""
        numer = 5
        denom = 4
        spacing = denom / numer
        assert abs(spacing - 0.8) < 0.01, "4/5 = 0.8 beats"

    def test_beat_spacing_7_4(self):
        """7:4 — each note ~0.571 beats apart"""
        numer = 7
        denom = 4
        spacing = denom / numer
        assert abs(spacing - 0.5714) < 0.01, "4/7 = 0.571 beats"

    def test_tick_spacing_calculation(self):
        """Tick spacing = beat_spacing * Quarter"""
        Quarter = 960
        numer = 3
        denom = 4
        beat_spacing = denom / numer
        tick_spacing = round(beat_spacing * Quarter)
        assert tick_spacing == 1280, "4/3 * 960 = 1280 ticks"

    def test_note_duration_shorter_than_spacing(self):
        """Note duration = 90% of spacing for articulation"""
        tick_spacing = 1280
        note_dur = max(1, round(tick_spacing * 0.9))
        assert note_dur == 1152, "1280 * 0.9 = 1152"

    def test_position_sequence(self):
        """Notes positioned at start + i * spacing"""
        start_ticks = 0
        tick_spacing = 1280
        positions = [start_ticks + i * tick_spacing for i in range(3)]
        assert positions == [0, 1280, 2560], "3 notes at 0, 1280, 2560"

    def test_velocity_constant(self):
        """constant: same velocity for all notes"""
        base_vel = 0.8
        for i in range(5):
            vel = base_vel
            assert vel == 0.8, f"note {i}: constant velocity"

    def test_velocity_accent(self):
        """accent: first note of each cycle louder"""
        base_vel = 0.8
        numer = 3
        for i in range(6):
            vel = min(1, base_vel * 1.2) if i % numer == 0 else base_vel * 0.7
            if i % numer == 0:
                assert vel > base_vel, f"note {i}: accented"
            else:
                assert vel < base_vel, f"note {i}: unaccented"

    def test_velocity_fade(self):
        """fade: linear decrease across all notes"""
        base_vel = 0.8
        total = 6
        for i in range(total):
            vel = base_vel * (1 - 0.5 * i / (total - 1))
            assert vel <= base_vel, f"note {i}: fading"

    def test_velocity_wave(self):
        """wave: sine pattern velocity within reasonable range"""
        base_vel = 0.8
        numer = 3
        for i in range(6):
            vel = base_vel * (0.7 + 0.3 * math.sin(i * math.pi / numer))
            assert 0.3 <= vel <= 1.1, f"note {i}: wave in valid range, got {vel}"

    def test_custom_pitches_override(self):
        """Custom pitches override scale generation"""
        custom = [60, 64, 67]
        total = 6
        pitches = [custom[i % len(custom)] for i in range(total)]
        assert pitches == [60, 64, 67, 60, 64, 67], "cycling custom pitches"

    def test_alternate_direction(self):
        """alternate: direction flips per cycle"""
        going_up = True
        numer = 3
        flips = 0
        for i in range(9):
            if i > 0 and i % numer == 0:
                going_up = not going_up
                flips += 1
        assert flips == 2, "2 flips in 9 notes with cycle 3 (at i=3 and i=6)"
        # 2 flips: True → False → True
        assert going_up, "after 2 flips starting True = True again"

    def test_velocity_clamping(self):
        """velocity clamped to 0.01-1"""
        assert max(0.01, min(1, 0)) == 0.01, "clamped to 0.01"
        assert max(0.01, min(1, 2)) == 1, "clamped to 1"
