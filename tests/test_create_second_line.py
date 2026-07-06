"""Unit tests for New Orleans second line percussion tool."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _generate_second_line_notes(bars, style, velocity=0.78, start_beat=0,
                                 bass_pitch=36, snare_pitch=38, hi_hat_pitch=42,
                                 tom_pitch=45, cymbal_pitch=49):
    """Replicate the note-generation logic from create_second_line."""
    STYLES = {
        "traditional": {
            "bass": [
                (0.0, 0.9, 0.25), (1.5, 0.7, 0.2), (2.0, 0.85, 0.25), (3.5, 0.65, 0.15),
                (4.0, 0.9, 0.25), (5.5, 0.7, 0.2), (6.0, 0.85, 0.25), (7.5, 0.65, 0.15),
            ],
            "snare": [
                (1.0, 0.85, 0.1), (3.0, 0.9, 0.1), (5.0, 0.85, 0.1), (7.0, 0.9, 0.1),
                (0.75, 0.3, 0.05), (2.75, 0.3, 0.05), (4.75, 0.3, 0.05), (6.75, 0.35, 0.05),
            ],
            "hi_hat": [
                (0.0, 0.5, 0.08), (1.5, 0.6, 0.1), (2.0, 0.5, 0.08), (3.5, 0.6, 0.1),
                (4.0, 0.5, 0.08), (5.5, 0.6, 0.1), (6.0, 0.5, 0.08), (7.5, 0.6, 0.1),
            ],
            "tom": [
                (7.25, 0.5, 0.1), (7.5, 0.6, 0.1), (7.75, 0.7, 0.08),
            ],
            "cymbal": [
                (0.0, 0.6, 0.15),
            ],
        },
        "brass_band": {
            "bass": [
                (0.0, 0.9, 0.2), (1.5, 0.75, 0.18), (2.0, 0.85, 0.2), (2.5, 0.65, 0.12),
                (3.5, 0.7, 0.15), (4.0, 0.9, 0.2), (5.5, 0.75, 0.18), (6.0, 0.85, 0.2),
                (6.5, 0.65, 0.12), (7.5, 0.7, 0.15),
            ],
            "snare": [
                (1.0, 0.85, 0.1), (1.75, 0.35, 0.04), (3.0, 0.9, 0.1), (3.25, 0.35, 0.04),
                (3.75, 0.4, 0.05), (5.0, 0.85, 0.1), (5.75, 0.35, 0.04), (7.0, 0.9, 0.1),
                (7.25, 0.35, 0.04), (7.75, 0.45, 0.06),
            ],
            "hi_hat": [
                (i * 0.5, 0.5 if i % 2 == 0 else 0.4, 0.06 if i % 2 == 0 else 0.05)
                for i in range(16)
            ],
            "tom": [
                (6.5, 0.5, 0.08), (6.75, 0.55, 0.08), (7.0, 0.6, 0.08),
                (7.25, 0.65, 0.06), (7.5, 0.7, 0.06), (7.75, 0.75, 0.05),
            ],
            "cymbal": [
                (0.0, 0.65, 0.2), (4.0, 0.55, 0.15),
            ],
        },
        "mardi_gras_indian": {
            "bass": [
                (0.0, 0.85, 0.3), (3.0, 0.7, 0.2), (3.5, 0.65, 0.15),
                (4.0, 0.8, 0.25), (7.0, 0.75, 0.2), (7.5, 0.6, 0.12),
            ],
            "snare": [
                (1.0, 0.7, 0.1), (2.0, 0.75, 0.1), (3.5, 0.8, 0.12),
                (5.0, 0.7, 0.1), (6.0, 0.75, 0.1), (7.5, 0.8, 0.12),
            ],
            "hi_hat": [
                (0.5, 0.5, 0.06), (1.5, 0.5, 0.06), (2.5, 0.5, 0.06), (3.5, 0.55, 0.08),
                (4.5, 0.5, 0.06), (5.5, 0.5, 0.06), (6.5, 0.5, 0.06), (7.5, 0.55, 0.08),
            ],
            "tom": [
                (0.0, 0.6, 0.15), (2.0, 0.55, 0.12), (4.0, 0.6, 0.15), (6.0, 0.55, 0.12),
            ],
            "cymbal": [
                (0.0, 0.7, 0.2),
            ],
        },
        "jazz_funeral": {
            "bass": [
                (0.0, 0.8, 0.4), (2.0, 0.65, 0.3),
                (4.0, 0.9, 0.2), (5.5, 0.75, 0.18), (6.0, 0.85, 0.2), (7.5, 0.7, 0.15),
            ],
            "snare": [
                (3.0, 0.6, 0.15),
                (5.0, 0.85, 0.1), (7.0, 0.9, 0.1), (7.75, 0.4, 0.05),
            ],
            "hi_hat": [
                (0.0, 0.5, 0.1), (2.0, 0.45, 0.08),
                (4.0, 0.5, 0.06), (4.5, 0.4, 0.05), (5.0, 0.5, 0.06), (5.5, 0.4, 0.05),
                (6.0, 0.5, 0.06), (6.5, 0.4, 0.05), (7.0, 0.5, 0.06), (7.5, 0.4, 0.05),
            ],
            "tom": [
                (3.0, 0.5, 0.12), (3.5, 0.45, 0.1),
            ],
            "cymbal": [
                (0.0, 0.7, 0.3), (4.0, 0.6, 0.2),
            ],
        },
        "bounce": {
            "bass": [
                (0.0, 0.9, 0.15), (0.5, 0.8, 0.12), (2.0, 0.9, 0.15), (2.5, 0.8, 0.12),
                (4.0, 0.9, 0.15), (4.5, 0.8, 0.12), (6.0, 0.9, 0.15), (6.5, 0.8, 0.12),
            ],
            "snare": [
                (1.0, 0.85, 0.08), (3.0, 0.9, 0.08), (5.0, 0.85, 0.08), (7.0, 0.9, 0.08),
            ],
            "hi_hat": [
                (i * 0.25, 0.45 if i % 2 == 0 else 0.3, 0.03 if i % 2 == 0 else 0.025)
                for i in range(32)
            ],
            "tom": [],
            "cymbal": [
                (0.0, 0.6, 0.15),
            ],
        },
    }

    pitch_map = {
        "bass": bass_pitch, "snare": snare_pitch,
        "hi_hat": hi_hat_pitch, "tom": tom_pitch, "cymbal": cymbal_pitch,
    }

    style_data = STYLES[style]
    cycle_len = 8.0
    cycles = bars // 2

    all_notes = []
    inst_counts = {}

    for inst in style_data:
        inst_counts[inst] = 0
        for c in range(cycles):
            offset = c * cycle_len
            for beat, vel_mult, dur in style_data[inst]:
                pos = round(start_beat + offset + beat, 4)
                vel = round(max(0.0, min(1.0, velocity * vel_mult)), 3)
                all_notes.append({
                    "pitch": pitch_map[inst],
                    "start": pos,
                    "duration": dur,
                    "velocity": vel,
                })
                inst_counts[inst] += 1

    all_notes.sort(key=lambda n: (n["start"], n["pitch"]))
    return all_notes, inst_counts


class TestCreateSecondLineValidation:
    """Test input validation."""

    def test_bars_too_small(self):
        from server import mcp_opendaw_create_second_line
        import asyncio
        result = asyncio.run(mcp_opendaw_create_second_line(bars=2))
        assert "Error" in result

    def test_bars_too_large(self):
        from server import mcp_opendaw_create_second_line
        import asyncio
        result = asyncio.run(mcp_opendaw_create_second_line(bars=20))
        assert "Error" in result

    def test_bars_odd(self):
        from server import mcp_opendaw_create_second_line
        import asyncio
        result = asyncio.run(mcp_opendaw_create_second_line(bars=5))
        assert "Error" in result

    def test_invalid_style(self):
        from server import mcp_opendaw_create_second_line
        import asyncio
        result = asyncio.run(mcp_opendaw_create_second_line(style="invalid"))
        assert "Error" in result

    def test_velocity_negative(self):
        from server import mcp_opendaw_create_second_line
        import asyncio
        result = asyncio.run(mcp_opendaw_create_second_line(velocity=-0.1))
        assert "Error" in result

    def test_velocity_over_one(self):
        from server import mcp_opendaw_create_second_line
        import asyncio
        result = asyncio.run(mcp_opendaw_create_second_line(velocity=1.5))
        assert "Error" in result


class TestCreateSecondLineNotes:
    """Test note generation logic."""

    def test_traditional_basic(self):
        notes, counts = _generate_second_line_notes(4, "traditional")
        assert len(notes) > 0
        # 4 bars = 2 cycles (cycle_len=8, cycles=bars//2)
        assert counts["bass"] == 16  # 8 per cycle × 2
        assert counts["snare"] == 16  # 8 per cycle × 2
        assert counts["hi_hat"] == 16  # 8 per cycle × 2
        assert counts["tom"] == 6  # 3 per cycle × 2
        assert counts["cymbal"] == 2  # 1 per cycle × 2

    def test_bass_backbeat_positions(self):
        notes, counts = _generate_second_line_notes(4, "traditional")
        bass_notes = [n for n in notes if n["pitch"] == 36]
        positions = [n["start"] for n in bass_notes]
        assert 0.0 in positions
        assert 1.5 in positions
        assert 2.0 in positions
        assert 3.5 in positions

    def test_snare_on_2_and_4(self):
        notes, counts = _generate_second_line_notes(4, "traditional")
        snare_notes = [n for n in notes if n["pitch"] == 38]
        accented = [n for n in snare_notes if n["velocity"] > 0.5]
        positions = [n["start"] for n in accented]
        assert 1.0 in positions
        assert 3.0 in positions
        assert 5.0 in positions
        assert 7.0 in positions

    def test_ghost_notes_lower_velocity(self):
        notes, counts = _generate_second_line_notes(4, "traditional")
        snare_notes = [n for n in notes if n["pitch"] == 38]
        ghosts = [n for n in snare_notes if n["velocity"] < 0.5]
        # 4 ghost notes per cycle × 2 cycles
        assert len(ghosts) == 8
        for g in ghosts:
            assert g["velocity"] < 0.35

    def test_charleston_hihat_pattern(self):
        notes, counts = _generate_second_line_notes(4, "traditional")
        hh_notes = [n for n in notes if n["pitch"] == 42]
        positions = [n["start"] for n in hh_notes]
        assert 0.0 in positions
        assert 1.5 in positions
        assert 2.0 in positions
        assert 3.5 in positions

    def test_all_pitches_present(self):
        notes, counts = _generate_second_line_notes(4, "traditional")
        pitches = set(n["pitch"] for n in notes)
        assert 36 in pitches
        assert 38 in pitches
        assert 42 in pitches
        assert 45 in pitches
        assert 49 in pitches

    def test_bars_8_doubles_notes(self):
        notes4, counts4 = _generate_second_line_notes(4, "traditional")
        notes8, counts8 = _generate_second_line_notes(8, "traditional")
        assert len(notes8) == len(notes4) * 2

    def test_bars_16_quadruples(self):
        notes4, _ = _generate_second_line_notes(4, "traditional")
        notes16, _ = _generate_second_line_notes(16, "traditional")
        assert len(notes16) == len(notes4) * 4

    def test_start_beat_offset(self):
        notes, counts = _generate_second_line_notes(4, "traditional", start_beat=10.0)
        assert notes[0]["start"] >= 10.0

    def test_velocity_scaling(self):
        notes_low, _ = _generate_second_line_notes(4, "traditional", velocity=0.5)
        notes_high, _ = _generate_second_line_notes(4, "traditional", velocity=1.0)
        low_vels = [n["velocity"] for n in notes_low]
        high_vels = [n["velocity"] for n in notes_high]
        assert max(low_vels) < max(high_vels)

    def test_custom_pitches(self):
        notes, counts = _generate_second_line_notes(
            4, "traditional",
            bass_pitch=35, snare_pitch=40, hi_hat_pitch=44, tom_pitch=50, cymbal_pitch=57
        )
        pitches = set(n["pitch"] for n in notes)
        assert 35 in pitches
        assert 40 in pitches
        assert 44 in pitches
        assert 50 in pitches
        assert 57 in pitches


class TestCreateSecondLineStyles:
    """Test style-specific characteristics."""

    def test_brass_band_denser_than_traditional(self):
        notes_t, _ = _generate_second_line_notes(4, "traditional")
        notes_b, _ = _generate_second_line_notes(4, "brass_band")
        assert len(notes_b) > len(notes_t)

    def test_brass_band_8th_hihat(self):
        notes, counts = _generate_second_line_notes(4, "brass_band")
        assert counts["hi_hat"] == 32

    def test_brass_band_ghost_notes_present(self):
        notes, counts = _generate_second_line_notes(4, "brass_band")
        snare_notes = [n for n in notes if n["pitch"] == 38]
        ghosts = [n for n in snare_notes if n["velocity"] < 0.5]
        assert len(ghosts) >= 4

    def test_brass_band_tom_roll_at_end(self):
        notes, counts = _generate_second_line_notes(4, "brass_band")
        tom_notes = [n for n in notes if n["pitch"] == 45]
        positions = [n["start"] for n in tom_notes]
        assert any(p > 6.0 for p in positions)

    def test_mardi_gras_indian_tom_driven(self):
        notes, counts = _generate_second_line_notes(4, "mardi_gras_indian")
        assert counts["tom"] >= 4

    def test_mardi_gras_indian_sparse_bass(self):
        notes_t, counts_t = _generate_second_line_notes(4, "traditional")
        notes_m, counts_m = _generate_second_line_notes(4, "mardi_gras_indian")
        assert counts_m["bass"] < counts_t["bass"]

    def test_mardi_gras_indian_call_response(self):
        notes, counts = _generate_second_line_notes(4, "mardi_gras_indian")
        tom_notes = [n for n in notes if n["pitch"] == 45]
        snare_notes = [n for n in notes if n["pitch"] == 38]
        tom_starts = set(n["start"] for n in tom_notes)
        snare_starts = set(n["start"] for n in snare_notes)
        assert tom_starts != snare_starts
        assert len(tom_starts) > 0
        assert len(snare_starts) > 0

    def test_jazz_funeral_dirge_phase_sparse(self):
        notes, counts = _generate_second_line_notes(4, "jazz_funeral")
        bass_notes = [n for n in notes if n["pitch"] == 36]
        dirge_bass = [n for n in bass_notes if n["start"] < 4.0]
        assert len(dirge_bass) <= 2

    def test_jazz_funeral_celebration_phase_dense(self):
        notes, counts = _generate_second_line_notes(4, "jazz_funeral")
        bass_notes = [n for n in notes if n["pitch"] == 36]
        celebration_bass = [n for n in bass_notes if n["start"] >= 4.0]
        assert len(celebration_bass) >= 3

    def test_jazz_funeral_dirge_longer_durations(self):
        notes, counts = _generate_second_line_notes(4, "jazz_funeral")
        bass_notes = [n for n in notes if n["pitch"] == 36]
        dirge_bass = [n for n in bass_notes if n["start"] < 4.0]
        if dirge_bass:
            assert dirge_bass[0]["duration"] >= 0.3

    def test_jazz_funeral_snare_sparse_in_dirge(self):
        notes, counts = _generate_second_line_notes(4, "jazz_funeral")
        snare_notes = [n for n in notes if n["pitch"] == 38]
        dirge_snare = [n for n in snare_notes if n["start"] < 4.0]
        assert len(dirge_snare) <= 1

    def test_bounce_double_time_bass(self):
        notes, counts = _generate_second_line_notes(4, "bounce")
        bass_notes = [n for n in notes if n["pitch"] == 36]
        positions = [n["start"] for n in bass_notes]
        assert 0.0 in positions
        assert 0.5 in positions

    def test_bounce_16th_hihat(self):
        notes, counts = _generate_second_line_notes(4, "bounce")
        assert counts["hi_hat"] == 64

    def test_bounce_no_tom(self):
        notes, counts = _generate_second_line_notes(4, "bounce")
        assert counts["tom"] == 0

    def test_bounce_backbeat_snare(self):
        notes, counts = _generate_second_line_notes(4, "bounce")
        snare_notes = [n for n in notes if n["pitch"] == 38]
        positions = [n["start"] for n in snare_notes]
        assert 1.0 in positions
        assert 3.0 in positions
        assert 5.0 in positions
        assert 7.0 in positions


class TestCreateSecondLineStructure:
    """Test structural properties."""

    def test_notes_sorted_by_start(self):
        notes, _ = _generate_second_line_notes(8, "brass_band")
        starts = [n["start"] for n in notes]
        assert starts == sorted(starts)

    def test_velocity_range(self):
        notes, _ = _generate_second_line_notes(4, "traditional")
        for n in notes:
            assert 0.0 <= n["velocity"] <= 1.0

    def test_duration_positive(self):
        notes, _ = _generate_second_line_notes(4, "traditional")
        for n in notes:
            assert n["duration"] > 0

    def test_cycle_length_8(self):
        notes, counts = _generate_second_line_notes(8, "traditional")
        # 8 bars = 4 cycles, cycle_len=8 → max start < 32
        max_start = max(n["start"] for n in notes)
        assert max_start < 32.0

    def test_all_notes_have_required_fields(self):
        notes, _ = _generate_second_line_notes(4, "traditional")
        for n in notes:
            assert "pitch" in n
            assert "start" in n
            assert "duration" in n
            assert "velocity" in n
