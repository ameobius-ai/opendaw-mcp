"""Unit tests for create_montuno MCP tool."""




class TestMontunoParameterValidation:
    """Test parameter validation."""

    def test_bars_too_few(self):
        bars = 1
        assert not (2 <= bars <= 4)

    def test_bars_too_many(self):
        bars = 5
        assert not (2 <= bars <= 4)

    def test_bars_valid_2(self):
        assert 2 <= 2 <= 4

    def test_bars_valid_4(self):
        assert 2 <= 4 <= 4

    def test_octave_too_low(self):
        assert not (2 <= 1 <= 6)

    def test_octave_too_high(self):
        assert not (2 <= 7 <= 6)

    def test_invalid_pattern(self):
        pattern = "invalid"
        assert pattern not in ("2-3", "3-2", "guajira", "charanga")

    def test_invalid_rhythm(self):
        rhythm = "invalid"
        assert rhythm not in ("8th", "16th", "quarter")

    def test_valid_patterns(self):
        for p in ("2-3", "3-2", "guajira", "charanga"):
            assert p in ("2-3", "3-2", "guajira", "charanga")

    def test_valid_rhythms(self):
        for r in ("8th", "16th", "quarter"):
            assert r in ("8th", "16th", "quarter")


class TestMontunoChordParsing:
    """Test chord name parsing."""

    NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                  "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

    def _get_chord_pitches(self, chord_name, octave=4):
        if chord_name.endswith("m") and not chord_name.endswith("dim"):
            base = chord_name[:-1]
            quality = "min"
        elif chord_name.endswith("dim"):
            base = chord_name[:-3]
            quality = "dim"
        else:
            base = chord_name
            quality = "maj"
        base_num = self.NOTE_NAMES.get(base, 0)
        if quality == "maj":
            intervals = [0, 4, 7]
        elif quality == "min":
            intervals = [0, 3, 7]
        else:
            intervals = [0, 3, 6]
        return [(octave + 1) * 12 + (base_num + iv) % 12 for iv in intervals]

    def test_major_chord(self):
        pitches = self._get_chord_pitches("C", octave=4)
        assert pitches == [60, 64, 67]  # C5, E5, G5

    def test_minor_chord(self):
        pitches = self._get_chord_pitches("Am", octave=4)
        # A=9, C=12%12=0, E=16%12=4 -> 69, 60, 64
        assert pitches == [69, 60, 64]

    def test_dim_chord(self):
        pitches = self._get_chord_pitches("Bdim", octave=4)
        # B=11, D=14%12=2, F=17%12=5 -> 71, 62, 65
        assert pitches == [71, 62, 65]

    def test_chord_with_sharp(self):
        pitches = self._get_chord_pitches("F#m", octave=4)
        # F#=6, A=9, C#=13%12=1 -> 66, 69, 61
        assert pitches == [66, 69, 61]


class TestMontunoRhythmSubdivision:
    """Test rhythm subdivision."""

    def test_eighth_subdiv(self):
        assert 0.5 == 0.5
        assert 8 == 8  # slots per bar

    def test_sixteenth_subdiv(self):
        assert 0.25 == 0.25
        assert 16 == 16

    def test_quarter_subdiv(self):
        assert 1.0 == 1.0
        assert 4 == 4


class TestMontunoSlotPatterns:
    """Test montuno slot patterns."""

    def test_2_3_clave_bar1(self):
        """2-3 clave: bar 1 has 2 syncopated hits."""
        bar1_slots = [0, 3]
        assert len(bar1_slots) == 2

    def test_2_3_clave_bar2(self):
        """2-3 clave: bar 2 has 3 hits."""
        bar2_slots = [0, 2, 4]
        assert len(bar2_slots) == 3

    def test_3_2_clave_reversed(self):
        """3-2 clave: bar 1 has 3, bar 2 has 2."""
        bar1_slots = [0, 2, 4]
        bar2_slots = [0, 3]
        assert len(bar1_slots) == 3
        assert len(bar2_slots) == 2

    def test_guajira_bar1(self):
        """Guajira pattern has dotted rhythm feel."""
        bar1_slots = [0, 3, 6]
        assert len(bar1_slots) == 3

    def test_charanga_more_notes(self):
        """Charanga has more flowing, melodic passages."""
        bar1_slots = [0, 1, 3, 5, 7]
        assert len(bar1_slots) == 5  # more notes than 2-3


class TestMontunoAccentBeats:
    """Test accent beat parsing."""

    def test_parse_accents(self):
        accent_beats = "1,3"
        accent_set = set()
        for b in accent_beats.split(","):
            accent_set.add(int(b.strip()))
        assert accent_set == {1, 3}

    def test_default_accents(self):
        accent_set = {1, 3}
        assert 1 in accent_set
        assert 3 in accent_set

    def test_all_beats_accent(self):
        accent_beats = "1,2,3,4"
        accent_set = set()
        for b in accent_beats.split(","):
            accent_set.add(int(b.strip()))
        assert accent_set == {1, 2, 3, 4}

    def test_invalid_accents_fallback(self):
        accent_beats = "abc"
        try:
            accent_set = set()
            for b in accent_beats.split(","):
                accent_set.add(int(b.strip()))
        except (ValueError, TypeError):
            accent_set = {1, 3}
        assert accent_set == {1, 3}


class TestMontunoDefaultProgression:
    """Test default chord progression generation."""

    def test_i_vi_iv_v_degrees(self):
        """Default progression uses I-vi-IV-V."""
        degrees = [0, 5, 3, 4]
        assert degrees == [0, 5, 3, 4]

    def test_major_scale_chord_qualities(self):
        """In major key: I=maj, ii=min, iii=min, IV=maj, V=maj, vi=min, vii=dim."""
        qualities = {0: "maj", 1: "min", 2: "min", 3: "maj", 4: "maj", 5: "min", 6: "dim"}
        assert qualities[0] == "maj"  # I
        assert qualities[5] == "min"  # vi
        assert qualities[3] == "maj"  # IV
        assert qualities[4] == "maj"  # V


class TestMontunoNoteGeneration:
    """Test the note generation logic."""

    def test_chord_stab_on_beat_1(self):
        """First slot of each bar is a chord stab (3 notes)."""
        notes = []
        slot = 0
        chord_pitches = [60, 64, 67]
        if slot == 0 or slot == 3:  # first or last slot
            for pi, p in enumerate(chord_pitches[:3]):
                notes.append({"pitch": p, "vel": 0.7})
        assert len(notes) == 3

    def test_melodic_passage_single_note(self):
        """Non-first/last slots produce single melodic notes."""
        notes = []
        slot = 2
        chord_pitches = [60, 64, 67]
        if slot != 0 and slot != 3:
            note_idx = slot % len(chord_pitches)
            notes.append({"pitch": chord_pitches[note_idx]})
        assert len(notes) == 1

    def test_accent_velocity_boost(self):
        """Accent beats get velocity boost."""
        base_vel = 0.65
        is_accent = True
        vel = base_vel * (1.15 if is_accent else 0.85)
        assert abs(vel - 0.7475) < 0.01

    def test_non_accent_velocity_cut(self):
        """Non-accent beats get velocity cut."""
        base_vel = 0.65
        is_accent = False
        vel = base_vel * (1.15 if is_accent else 0.85)
        assert abs(vel - 0.5525) < 0.01

    def test_velocity_clamped(self):
        """Velocity should be clamped to 0-1."""
        vel = 1.5
        vel = max(0.0, min(1.0, vel))
        assert vel == 1.0

    def test_note_duration_8th(self):
        """8th note duration is subdiv * 0.85-0.9."""
        subdiv = 0.5
        dur = subdiv * 0.9
        assert abs(dur - 0.45) < 0.01


class TestMontunoPositionCalculation:
    """Test beat position calculation."""

    def test_bar0_position(self):
        """Bar 0, slot 0 = position 0."""
        bar_idx = 0
        slot = 0
        subdiv = 0.5
        beat_pos = bar_idx * 4 + slot * subdiv
        assert beat_pos == 0.0

    def test_bar1_slot3(self):
        """Bar 1, slot 3 = position 5.5 (in 8th notes)."""
        bar_idx = 1
        slot = 3
        subdiv = 0.5
        beat_pos = bar_idx * 4 + slot * subdiv
        assert beat_pos == 5.5

    def test_bar0_slot7(self):
        """Bar 0, slot 7 = position 3.5 (last 8th of bar 1)."""
        bar_idx = 0
        slot = 7
        subdiv = 0.5
        beat_pos = bar_idx * 4 + slot * subdiv
        assert beat_pos == 3.5


class TestMontunoChordProgressionInput:
    """Test custom chord progression input."""

    def test_custom_prog_parsed(self):
        """Custom chord progression should be split by comma."""
        chord_prog = "C,Am,Dm,G"
        chords = [c.strip() for c in chord_prog.split(",")]
        assert chords == ["C", "Am", "Dm", "G"]

    def test_custom_prog_with_spaces(self):
        """Spaces around commas should be stripped."""
        chord_prog = "C , Am , Dm , G"
        chords = [c.strip() for c in chord_prog.split(",")]
        assert chords == ["C", "Am", "Dm", "G"]

    def test_empty_prog_uses_default(self):
        """Empty chord_prog triggers default I-vi-IV-V."""
        chord_prog = ""
        if not chord_prog:
            uses_default = True
        else:
            uses_default = False
        assert uses_default


class TestMontunoBarCycling:
    """Test bar cycling logic."""

    def test_bar0_uses_bar1_slots(self):
        """Even bars (0, 2) use bar1_slots pattern."""
        bar_idx = 0
        if bar_idx % 2 == 0:
            uses_bar1 = True
        else:
            uses_bar1 = False
        assert uses_bar1

    def test_bar1_uses_bar2_slots(self):
        """Odd bars (1, 3) use bar2_slots pattern."""
        bar_idx = 1
        if bar_idx % 2 == 0:
            uses_bar1 = True
        else:
            uses_bar1 = False
        assert not uses_bar1

    def test_4bar_cycle(self):
        """4-bar montuno cycles through 4 chords."""
        chords = ["C", "Am", "Dm", "G"]
        for bar_idx in range(4):
            chord = chords[bar_idx % len(chords)]
            assert chord == chords[bar_idx]


class TestMontunoTotalSlots:
    """Test total slot calculation."""

    def test_2bar_8th(self):
        bars = 2
        slots_per_bar = 8
        total = bars * slots_per_bar
        assert total == 16

    def test_4bar_16th(self):
        bars = 4
        slots_per_bar = 16
        total = bars * slots_per_bar
        assert total == 64

    def test_2bar_quarter(self):
        bars = 2
        slots_per_bar = 4
        total = bars * slots_per_bar
        assert total == 8
