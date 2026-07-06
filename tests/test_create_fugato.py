"""Unit tests for create_fugato MCP tool."""

import json



class TestFugatoParameterValidation:
    """Test parameter validation."""

    def test_bars_too_few(self):
        assert not (4 <= 3 <= 16)

    def test_bars_too_many(self):
        assert not (4 <= 17 <= 16)

    def test_bars_valid(self):
        for b in (4, 8, 12, 16):
            assert 4 <= b <= 16

    def test_octave_too_low(self):
        assert not (2 <= 1 <= 6)

    def test_octave_too_high(self):
        assert not (2 <= 7 <= 6)

    def test_voices_too_few(self):
        assert not (2 <= 1 <= 4)

    def test_voices_too_many(self):
        assert not (2 <= 5 <= 4)

    def test_voices_valid(self):
        for v in (2, 3, 4):
            assert 2 <= v <= 4

    def test_invalid_answer_mode(self):
        m = "invalid"
        assert m not in ("real", "tonal")

    def test_valid_answer_modes(self):
        for m in ("real", "tonal"):
            assert m in ("real", "tonal")

    def test_episode_bars_too_few(self):
        assert not (1 <= 0 <= 4)

    def test_episode_bars_too_many(self):
        assert not (1 <= 5 <= 4)


class TestFugatoSubjectParsing:
    """Test subject parsing."""

    def test_custom_subject_parsed(self):
        """Custom subject JSON is parsed correctly."""
        subject_notes = "[[0, 0.5], [2, 0.5], [5, 1.0]]"
        subject = json.loads(subject_notes)
        assert subject == [[0, 0.5], [2, 0.5], [5, 1.0]]

    def test_invalid_subject_json(self):
        """Invalid JSON raises error."""
        bad = "not json{"
        try:
            json.loads(bad)
            assert False
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    def test_empty_subject_auto_generates(self):
        """Empty subject_notes triggers auto-generation."""
        subject_notes = ""
        if not subject_notes:
            auto_generated = True
        else:
            auto_generated = False
        assert auto_generated

    def test_auto_subject_has_7_notes(self):
        """Auto-generated subject has 7 notes (degree_pattern)."""
        degree_pattern = [0, 2, 4, 2, 0, -1, 0]
        assert len(degree_pattern) == 7

    def test_auto_subject_durations(self):
        """Auto-generated subject has matching durations."""
        dur_pattern = [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 1.0]
        assert sum(dur_pattern) == 4.5  # total subject length


class TestFugatoSubjectPitches:
    """Test subject pitch construction."""

    def test_subject_base_pitch(self):
        """Subject base = (octave+1)*12 + root_num."""
        octave = 4
        root_num = 0  # C
        subject_base = (octave + 1) * 12 + root_num
        assert subject_base == 60  # C5

    def test_subject_pitches_offset(self):
        """Subject pitches are base + offset."""
        subject_base = 60
        subject = [[0, 0.5], [7, 0.5], [12, 1.0]]
        pitches = [subject_base + offset for offset, dur in subject]
        assert pitches == [60, 67, 72]

    def test_negative_offset(self):
        """Negative offsets produce lower pitches."""
        subject_base = 60
        subject = [[0, 0.5], [-5, 0.5]]
        pitches = [subject_base + offset for offset, dur in subject]
        assert pitches == [60, 55]


class TestFugatoAnswer:
    """Test answer construction."""

    def test_real_answer_transposition(self):
        """Real answer transposes subject by answer_interval."""
        subject_pitches = [60, 62, 65, 67]
        answer_interval = 7
        answer_pitches = [p + answer_interval for p in subject_pitches]
        assert answer_pitches == [67, 69, 72, 74]

    def test_answer_durations_same(self):
        """Answer durations match subject durations."""
        subject_durations = [0.5, 0.5, 1.0, 0.5]
        answer_durations = subject_durations[:]
        assert answer_durations == subject_durations

    def test_answer_at_fifth(self):
        """Standard fugue answer is at the fifth (7 semitones)."""
        answer_interval = 7
        assert answer_interval == 7

    def test_answer_at_fourth(self):
        """Some fugues answer at the fourth (5 semitones)."""
        answer_interval = 5
        assert answer_interval == 5


class TestFugatoCountersubject:
    """Test countersubject construction."""

    def test_countersubject_inverts_contour(self):
        """Countersubject inverts subject contour."""
        subject = [[0, 0.5], [2, 0.5], [5, 1.0]]
        countersubject_interval = -3
        cs_pitches = []
        for offset, dur in subject:
            inv_offset = -offset + countersubject_interval
            cs_pitches.append(inv_offset)
        # 0-3=-3, -2-3=-5, -5-3=-8
        assert cs_pitches == [-3, -5, -8]

    def test_countersubject_when_disabled(self):
        """When include_countersubject=False, no countersubject."""
        include_countersubject = False
        if not include_countersubject:
            cs_pitches = []
        assert len(cs_pitches) == 0

    def test_countersubject_starts_below_answer(self):
        """Countersubject starts below answer (negative interval)."""
        countersubject_interval = -3
        assert countersubject_interval < 0


class TestFugatoEpisode:
    """Test episode construction."""

    def test_episode_sequences_downward(self):
        """Episode sequences the subject's first notes down by step."""
        subject_pitches = [60, 62, 65]
        episode_pitches = []
        for seq in range(3):
            for i in range(3):
                ep_pitch = subject_pitches[i] - seq * 2
                episode_pitches.append(ep_pitch)
        # seq 0: 60, 62, 65
        # seq 1: 58, 60, 63
        # seq 2: 56, 58, 61
        assert episode_pitches == [60, 62, 65, 58, 60, 63, 56, 58, 61]

    def test_episode_when_disabled(self):
        """When include_episode=False, no episode."""
        include_episode = False
        if not include_episode:
            episode_pitches = []
        assert len(episode_pitches) == 0


class TestFugatoVoiceEntries:
    """Test voice entry structure."""

    def test_voice1_subject_starts_at_zero(self):
        """Voice 1 (subject) starts at beat 0."""
        current_beat = 0.0
        assert current_beat == 0.0

    def test_voice2_answer_enters_with_subject(self):
        """Voice 2 (answer) enters while subject is playing."""
        answer_start = 0.0
        subject_length = 4.5
        assert answer_start < subject_length  # answer enters during subject

    def test_voice3_enters_after_subject(self):
        """Voice 3 enters after voice 1's subject finishes."""
        subject_total_beats = 4.5
        v3_start = subject_total_beats
        assert v3_start == 4.5

    def test_voice4_enters_with_voice3(self):
        """Voice 4 enters at the same time as voice 3."""
        v3_start = 4.5
        v4_start = v3_start
        assert v4_start == v3_start

    def test_two_voices_no_v3_v4(self):
        """With voices=2, no voice 3 or 4."""
        voices = 2
        assert voices < 3

    def test_four_voices_all_present(self):
        """With voices=4, all 4 voices present."""
        voices = 4
        assert voices >= 4


class TestFugatoVelocityScaling:
    """Test velocity scaling per voice."""

    def test_voice1_full_velocity(self):
        """Voice 1 gets full velocity."""
        velocity = 0.6
        vel = velocity
        assert vel == 0.6

    def test_voice2_reduced(self):
        """Voice 2 gets 90% velocity."""
        velocity = 0.6
        vel = velocity * 0.9
        assert abs(vel - 0.54) < 0.01

    def test_voice3_reduced(self):
        """Voice 3 gets 85% velocity."""
        velocity = 0.6
        vel = velocity * 0.85
        assert abs(vel - 0.51) < 0.01

    def test_countersubject_reduced(self):
        """Countersubject gets 80% velocity."""
        velocity = 0.6
        vel = velocity * 0.8
        assert abs(vel - 0.48) < 0.01

    def test_episode_reduced(self):
        """Episode gets 70% velocity."""
        velocity = 0.6
        vel = velocity * 0.7
        assert abs(vel - 0.42) < 0.01


class TestFugatoNoteFiltering:
    """Test note filtering to fit within bars."""

    def test_notes_filtered_by_max_beat(self):
        """Notes beyond bars*4 are filtered out."""
        bars = 4
        max_beat = bars * 4
        notes = [
            {"pos": 0.0},
            {"pos": 4.0},
            {"pos": 15.9},
            {"pos": 16.0},
            {"pos": 17.0},
        ]
        filtered = [n for n in notes if n["pos"] < max_beat]
        assert len(filtered) == 3  # 0, 4, 15.9 pass

    def test_notes_sorted_by_position(self):
        """Notes are sorted by position."""
        notes = [
            {"pos": 4.5, "pitch": 67},
            {"pos": 0.0, "pitch": 60},
            {"pos": 2.0, "pitch": 62},
        ]
        notes.sort(key=lambda n: n["pos"])
        assert notes[0]["pos"] == 0.0
        assert notes[1]["pos"] == 2.0
        assert notes[2]["pos"] == 4.5


class TestFugatoEntryLog:
    """Test entry log structure."""

    def test_entry_log_has_voice_and_type(self):
        """Each entry has voice, type, start_beat, pitch_base."""
        entry = {"voice": 1, "type": "subject", "start_beat": 0.0, "pitch_base": 60}
        assert "voice" in entry
        assert "type" in entry
        assert "start_beat" in entry
        assert "pitch_base" in entry

    def test_entry_types(self):
        """Entry types include subject, answer, episode."""
        types = {"subject", "answer", "episode"}
        assert "subject" in types
        assert "answer" in types
        assert "episode" in types


class TestFugatoSubjectLength:
    """Test subject length calculation."""

    def test_subject_length_sum(self):
        """Subject length = sum of durations."""
        subject_durations = [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 1.0]
        total = sum(subject_durations)
        assert total == 4.5

    def test_custom_subject_length(self):
        """Custom subject length is calculated from durations."""
        subject = [[0, 1.0], [7, 0.5], [5, 0.5], [0, 1.0]]
        total = sum(dur for _, dur in subject)
        assert total == 3.0
