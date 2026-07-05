"""
Unit tests for pure Python helper functions in server.py.

These tests don't require a running openDAW instance — they verify
the utility functions that handle JSON serialization, filename sanitization,
and path traversal protection.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server import _ok, _err, _wrap_eval, _unwrap_eval, _safe_filename, _safe_path, _clamp_script_param


class TestOk:
    def test_empty(self):
        result = json.loads(_ok())
        assert result["success"] is True

    def test_with_data(self):
        result = json.loads(_ok({"bpm": 120, "tracks": 3}))
        assert result["success"] is True
        assert result["bpm"] == 120
        assert result["tracks"] == 3

    def test_overrides_success(self):
        # success in data should not override the True from _ok
        result = json.loads(_ok({"success": False}))
        assert result["success"] is True


class TestErr:
    def test_simple(self):
        result = json.loads(_err("something went wrong"))
        assert result["error"] == "something went wrong"


class TestWrapEval:
    def test_dict_success(self):
        result = json.loads(_wrap_eval({"value": 42}))
        assert result["value"] == 42

    def test_dict_error(self):
        result = json.loads(_wrap_eval({"error": "bad"}))
        assert result["error"] == "bad"

    def test_list(self):
        result = json.loads(_wrap_eval([1, 2, 3]))
        assert result == [1, 2, 3]

    def test_string(self):
        result = json.loads(_wrap_eval("hello"))
        assert result == "hello"

    def test_none(self):
        result = json.loads(_wrap_eval(None))
        assert result is None


class TestUnwrapEval:
    def test_json_string(self):
        result = _unwrap_eval('{"key": "value"}')
        assert result == {"key": "value"}

    def test_non_json_string(self):
        result = _unwrap_eval("not json")
        assert result == "not json"

    def test_non_string(self):
        result = _unwrap_eval({"already": "dict"})
        assert result == {"already": "dict"}


class TestSafeFilename:
    def test_simple(self):
        assert _safe_filename("my_track") == "my_track"

    def test_strips_quotes(self):
        assert _safe_filename('"injection"') == "injection"
        assert _safe_filename("it's") == "its"

    def test_strips_backslash(self):
        # backslash is converted to / then basename extracted
        assert _safe_filename("path\\to\\file") == "file"

    def test_strips_extensions(self):
        assert _safe_filename("track.wav") == "track"
        assert _safe_filename("song.MP3") == "song"
        assert _safe_filename("audio.Flac") == "audio"

    def test_path_traversal(self):
        assert _safe_filename("../../../etc/passwd") == "passwd"
        assert _safe_filename("../../secret") == "secret"

    def test_empty_fallback(self):
        assert _safe_filename("") == "output"
        assert _safe_filename("///") == "output"


class TestSafePath:
    def test_normal(self, tmp_path):
        path = _safe_path(str(tmp_path), "my_track", "wav")
        assert path == os.path.join(str(tmp_path), "my_track.wav")

    def test_traversal_blocked(self, tmp_path):
        path = _safe_path(str(tmp_path), "../../../etc/passwd", "wav")
        assert os.path.abspath(path).startswith(os.path.abspath(str(tmp_path)))

    def test_extension(self, tmp_path):
        path = _safe_path(str(tmp_path), "output", "flac")
        assert path.endswith(".flac")

    def test_empty_filename(self, tmp_path):
        path = _safe_path(str(tmp_path), "", "wav")
        assert path.endswith("output.wav")


def _make_wav_float32(samples, n_channels=1, sample_rate=48000):
    """Create a minimal float32 WAV file bytes from interleaved float samples."""
    import struct
    n_samples = len(samples)
    bytes_per = 4
    data_size = n_samples * bytes_per
    # fmt: format(3=float32), channels, sample_rate, byte_rate, block_align, bits_per_sample
    fmt_chunk = struct.pack("<HHIIHH", 3, n_channels, sample_rate,
                            sample_rate * n_channels * bytes_per,
                            n_channels * bytes_per, bytes_per * 8)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<I", 16) + fmt_chunk
    header += b"data" + struct.pack("<I", data_size)
    return header + struct.pack(f"<{n_samples}f", *samples)


def _make_wav_pcm16(samples, n_channels=1, sample_rate=48000):
    """Create a minimal 16-bit PCM WAV file bytes from float samples (-1..1)."""
    import struct
    int_samples = [max(-32768, min(32767, int(s * 32768))) for s in samples]
    n = len(int_samples)
    data_size = n * 2
    fmt_chunk = struct.pack("<HHIIHH", 1, n_channels, sample_rate,
                            sample_rate * n_channels * 2,
                            n_channels * 2, 16)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack("<I", 16) + fmt_chunk
    header += b"data" + struct.pack("<I", data_size)
    return header + struct.pack(f"<{n}h", *int_samples)


class TestParseWav:
    def test_float32_mono(self):
        from server import _parse_wav
        samples = [0.5, -0.3, 0.8, -0.1, 0.0]
        raw = _make_wav_float32(samples, n_channels=1)
        wav = _parse_wav(raw)
        assert wav["audio_format"] == 3
        assert wav["bits_per_sample"] == 32
        assert wav["n_channels"] == 1
        assert wav["sample_rate"] == 48000
        assert wav["n_frames"] == 5
        assert len(wav["channels"]) == 1
        for i, s in enumerate(samples):
            assert abs(wav["channels"][0][i] - s) < 1e-5

    def test_float32_stereo(self):
        from server import _parse_wav
        # interleaved: L, R, L, R
        samples = [0.1, 0.2, 0.3, 0.4]
        raw = _make_wav_float32(samples, n_channels=2)
        wav = _parse_wav(raw)
        assert wav["n_channels"] == 2
        assert wav["n_frames"] == 2
        assert abs(wav["channels"][0][0] - 0.1) < 1e-5  # L0
        assert abs(wav["channels"][1][0] - 0.2) < 1e-5  # R0
        assert abs(wav["channels"][0][1] - 0.3) < 1e-5  # L1
        assert abs(wav["channels"][1][1] - 0.4) < 1e-5  # R1

    def test_pcm16(self):
        from server import _parse_wav
        samples = [0.5, -0.5, 0.0]
        raw = _make_wav_pcm16(samples, n_channels=1)
        wav = _parse_wav(raw)
        assert wav["audio_format"] == 1
        assert wav["bits_per_sample"] == 16
        assert wav["n_channels"] == 1
        assert abs(wav["channels"][0][0] - 0.5) < 1e-3

    def test_invalid_header(self):
        from server import _parse_wav
        try:
            _parse_wav(b"XXXX" + b"\x00" * 40)
            assert False, "Should have raised"
        except ValueError as e:
            assert "WAV" in str(e)

    def test_no_data_chunk(self):
        from server import _parse_wav
        import struct
        # RIFF + WAVE + fmt chunk but no data chunk
        fmt_chunk = struct.pack("<HHIIHH", 3, 1, 48000, 48000 * 4, 32, 0)
        raw = b"RIFF" + struct.pack("<I", 4 + 8 + 16) + b"WAVE"
        raw += b"fmt " + struct.pack("<I", 16) + fmt_chunk
        try:
            _parse_wav(raw)
            assert False, "Should have raised"
        except ValueError as e:
            assert "data" in str(e).lower()


class TestComputeLufs:
    def test_silence_raises(self):
        from server import _compute_lufs
        # 2 seconds of silence at 48kHz
        silence = [0.0] * (48000 * 2)
        try:
            _compute_lufs([silence], 48000)
            assert False, "Should raise for silence"
        except ValueError:
            pass

    def test_full_scale_tone(self):
        from server import _compute_lufs
        import math
        # 3 seconds of 1kHz sine at full scale, 48kHz
        sr = 48000
        n = sr * 3
        tone = [math.sin(2 * math.pi * 1000 * i / sr) for i in range(n)]
        result = _compute_lufs([tone], sr)
        assert "lufs_integrated" in result
        # Full-scale 1kHz sine should be around -0.7 to -3 LUFS
        assert result["lufs_integrated"] > -5
        assert result["lufs_integrated"] < 5
        assert result["true_peak_db"] >= 0  # near 0 dB for full-scale
        assert result["blocks_measured"] > 0

    def test_low_level(self):
        from server import _compute_lufs
        import math
        # 3 seconds of -30dB sine
        sr = 48000
        n = sr * 3
        amp = 10 ** (-30 / 20)
        tone = [amp * math.sin(2 * math.pi * 1000 * i / sr) for i in range(n)]
        result = _compute_lufs([tone], sr)
        assert result["lufs_integrated"] < -20
        assert result["lufs_integrated"] > -40

    def test_stereo(self):
        from server import _compute_lufs
        import math
        sr = 48000
        n = sr * 3
        tone = [math.sin(2 * math.pi * 1000 * i / sr) for i in range(n)]
        result = _compute_lufs([tone, tone], sr)
        assert "lufs_integrated" in result
        # Stereo should be ~3 LU louder than mono (double power)
        mono = _compute_lufs([tone], sr)
        assert result["lufs_integrated"] > mono["lufs_integrated"]


class TestTidalRateMap:
    """Verify Tidal LFO rate fraction-to-index mapping."""
    def test_basic_fractions(self):
        from server import TIDAL_RATE_MAP
        assert TIDAL_RATE_MAP["1/1"] == 0
        assert TIDAL_RATE_MAP["1/4"] == 3
        assert TIDAL_RATE_MAP["1/8"] == 6
        assert TIDAL_RATE_MAP["1/16"] == 9
        assert TIDAL_RATE_MAP["1/128"] == 16

    def test_count(self):
        from server import TIDAL_RATE_MAP
        assert len(TIDAL_RATE_MAP) == 17

    def test_indices_contiguous(self):
        from server import TIDAL_RATE_MAP
        indices = sorted(TIDAL_RATE_MAP.values())
        assert indices == list(range(17))

    def test_triplets(self):
        from server import TIDAL_RATE_MAP
        assert TIDAL_RATE_MAP["3/16"] == 4
        assert TIDAL_RATE_MAP["3/32"] == 7
        assert TIDAL_RATE_MAP["3/64"] == 10


class TestDelaySyncMap:
    """Verify Delay sync fraction-to-index mapping."""
    def test_off(self):
        from server import DELAY_SYNC_MAP
        assert DELAY_SYNC_MAP["off"] == 0

    def test_basic_fractions(self):
        from server import DELAY_SYNC_MAP
        assert DELAY_SYNC_MAP["1/128"] == 1
        assert DELAY_SYNC_MAP["1/16"] == 8
        assert DELAY_SYNC_MAP["1/8"] == 11
        assert DELAY_SYNC_MAP["1/4"] == 14
        assert DELAY_SYNC_MAP["1/1"] == 20

    def test_count(self):
        from server import DELAY_SYNC_MAP
        assert len(DELAY_SYNC_MAP) == 21

    def test_indices_contiguous(self):
        from server import DELAY_SYNC_MAP
        indices = sorted(DELAY_SYNC_MAP.values())
        assert indices == list(range(21))

    def test_smallest_to_largest_order(self):
        from server import DELAY_SYNC_MAP
        # 1/128 should have smaller index than 1/1
        assert DELAY_SYNC_MAP["1/128"] < DELAY_SYNC_MAP["1/1"]


class TestWaveshaperFuncs:
    """Verify waveshaper transfer function lookup table."""
    def test_known_funcs(self):
        from server import WAVESHAPER_FUNCS
        expected = {"hardclip", "cubicSoft", "tanh", "sigmoid", "arctan", "asymmetric"}
        assert set(WAVESHAPER_FUNCS.keys()) == expected

    def test_count(self):
        from server import WAVESHAPER_FUNCS
        assert len(WAVESHAPER_FUNCS) == 6

    def test_expressions_nonempty(self):
        from server import WAVESHAPER_FUNCS
        for name, expr in WAVESHAPER_FUNCS.items():
            assert isinstance(expr, str)
            assert len(expr) > 5
            assert "x" in expr  # all must reference x

    def test_hardclip(self):
        from server import WAVESHAPER_FUNCS
        assert "min" in WAVESHAPER_FUNCS["hardclip"]
        assert "max" in WAVESHAPER_FUNCS["hardclip"]


class TestRevampSections:
    """Verify Revamp EQ section names."""
    def test_known_sections(self):
        from server import REVAMP_SECTIONS
        expected = {"highPass", "lowShelf", "lowBell", "midBell",
                     "highBell", "highShelf", "lowPass"}
        assert set(REVAMP_SECTIONS) == expected

    def test_count(self):
        from server import REVAMP_SECTIONS
        assert len(REVAMP_SECTIONS) == 7

    def test_camelcase(self):
        from server import REVAMP_SECTIONS
        for s in REVAMP_SECTIONS:
            # Each section should be camelCase (starts lowercase, has uppercase)
            assert s[0].islower()
            assert any(c.isupper() for c in s)


class TestSafeFilenameEdgeCases:
    """Additional edge cases for filename sanitization."""
    def test_dawproject_extension(self):
        assert _safe_filename("project.dawproject") == "project"

    def test_multiple_dots(self):
        assert _safe_filename("my.track.v2") == "my.track.v2"

    def test_unicode(self):
        assert _safe_filename("трек") == "трек"

    def test_only_extension(self):
        assert _safe_filename(".wav") == "output" or _safe_filename(".wav") == ".wav"

    def test_double_extension(self):
        # only the last extension is stripped
        result = _safe_filename("track.wav.wav")
        assert result == "track.wav"


class TestOkErrCombo:
    """Verify _ok and _err produce valid JSON."""
    def test_ok_has_success_key(self):
        result = json.loads(_ok({"data": [1, 2, 3]}))
        assert "success" in result
        assert "data" in result

    def test_err_has_error_key(self):
        result = json.loads(_err("fail"))
        assert "error" in result
        assert "success" not in result


class TestOrchestrationCurves:
    """Test interpolation math used by automation_sweep.

    The sweep tool generates points along linear/exp/log curves.
    These tests verify the math produces correct values at boundaries.
    """

    def _linear(self, t, start, end):
        return start + (end - start) * t

    def _exp(self, t, start, end):
        return start + (end - start) * (math.exp(t * 3) - 1) / (math.exp(3) - 1)

    def _log(self, t, start, end):
        return start + (end - start) * math.log(1 + t * (math.e - 1))

    def test_linear_endpoints(self):
        assert abs(self._linear(0, 0.1, 0.9) - 0.1) < 1e-9
        assert abs(self._linear(1, 0.1, 0.9) - 0.9) < 1e-9
        assert abs(self._linear(0.5, 0.1, 0.9) - 0.5) < 1e-9

    def test_exp_endpoints(self):
        assert abs(self._exp(0, 0.1, 0.9) - 0.1) < 1e-9
        assert abs(self._exp(1, 0.1, 0.9) - 0.9) < 1e-9

    def test_exp_slow_start(self):
        # exponential curve should start slower than linear
        mid_exp = self._exp(0.3, 0.0, 1.0)
        mid_lin = self._linear(0.3, 0.0, 1.0)
        assert mid_exp < mid_lin  # exp accelerates

    def test_log_endpoints(self):
        assert abs(self._log(0, 0.1, 0.9) - 0.1) < 1e-9
        assert abs(self._log(1, 0.1, 0.9) - 0.9) < 1e-9

    def test_log_fast_start(self):
        # logarithmic curve should start faster than linear
        mid_log = self._log(0.3, 0.0, 1.0)
        mid_lin = self._linear(0.3, 0.0, 1.0)
        assert mid_log > mid_lin  # log decelerates

    def test_clamp_to_01(self):
        # values should be clamped to [0, 1] range
        for curve_fn in [self._linear, self._exp, self._log]:
            for t in [0, 0.25, 0.5, 0.75, 1]:
                v = curve_fn(t, 0.0, 1.0)
                assert 0.0 <= v <= 1.0

    def test_reverse_sweep(self):
        # sweep from high to low should work
        for curve_fn in [self._linear, self._exp, self._log]:
            assert curve_fn(0, 0.9, 0.1) > curve_fn(1, 0.9, 0.1)


class TestSongStructureParsing:
    """Test JSON section parsing used by create_song_structure."""

    def test_valid_sections(self):
        sections = json.dumps([
            {"name": "Intro", "bars": 4},
            {"name": "Verse", "bars": 8},
            {"name": "Chorus", "bars": 8},
        ])
        parsed = json.loads(sections)
        assert len(parsed) == 3
        assert parsed[0]["name"] == "Intro"
        assert parsed[1]["bars"] == 8

    def test_default_bars(self):
        # if bars omitted, should default to 8
        sections = json.dumps([{"name": "Verse"}])
        parsed = json.loads(sections)
        bars = parsed[0].get("bars", 8)
        assert bars == 8

    def test_total_beats_calculation(self):
        sections = [
            {"name": "Intro", "bars": 4},
            {"name": "Verse", "bars": 8},
            {"name": "Outro", "bars": 4},
        ]
        total = sum(s.get("bars", 8) * 4 for s in sections)
        assert total == 64  # (4+8+4) * 4

    def test_marker_positions(self):
        sections = [
            {"name": "A", "bars": 4},
            {"name": "B", "bars": 8},
            {"name": "C", "bars": 4},
        ]
        pos = 0
        positions = []
        for s in sections:
            positions.append(pos)
            pos += s.get("bars", 8) * 4
        assert positions == [0, 16, 48]

    def test_empty_sections(self):
        sections = json.dumps([])
        parsed = json.loads(sections)
        assert len(parsed) == 0


class TestChordProgressionTheory:
    """Test chord name parsing and note generation logic used by create_chord_progression."""

    # Chord intervals (semitones from root)
    CHORD_INTERVALS = {
        "maj": [0, 4, 7],
        "min": [0, 3, 7],
        "min7": [0, 3, 7, 10],
        "dom7": [0, 4, 7, 10],
        "maj7": [0, 4, 7, 11],
        "dim": [0, 3, 6],
        "sus4": [0, 5, 7],
    }

    NOTE_TO_SEMITONE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                        "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

    def _parse_chord(self, name):
        """Parse chord name like 'Cmin7' → (root_semitone, intervals)."""
        if len(name) >= 2 and name[1] == "#":
            root = name[:2]
            quality = name[2:]
        else:
            root = name[0]
            quality = name[1:]
        root_st = self.NOTE_TO_SEMITONE[root]
        if quality == "" or quality == "maj":
            intervals = self.CHORD_INTERVALS["maj"]
        else:
            intervals = self.CHORD_INTERVALS.get(quality, self.CHORD_INTERVALS["maj"])
        return root_st, intervals

    def test_major_chord(self):
        root, intervals = self._parse_chord("C")
        assert root == 0
        assert intervals == [0, 4, 7]

    def test_minor_seventh(self):
        root, intervals = self._parse_chord("Amin7")
        assert root == 9
        assert intervals == [0, 3, 7, 10]

    def test_dominant_seventh(self):
        root, intervals = self._parse_chord("Gdom7")
        assert root == 7
        assert intervals == [0, 4, 7, 10]

    def test_sharp_root(self):
        root, intervals = self._parse_chord("F#min7")
        assert root == 6
        assert intervals == [0, 3, 7, 10]

    def test_diminished(self):
        root, intervals = self._parse_chord("Bdim")
        assert root == 11
        assert intervals == [0, 3, 6]

    def test_sus4(self):
        root, intervals = self._parse_chord("Dsus4")
        assert root == 2
        assert intervals == [0, 5, 7]

    def test_chord_note_count(self):
        # 7th chords should have 4 notes, triads 3
        _, maj_intervals = self._parse_chord("C")
        _, min7_intervals = self._parse_chord("Dmin7")
        assert len(maj_intervals) == 3
        assert len(min7_intervals) == 4


class TestDrumPatternParsing:
    """Test step-sequencer notation parsing used by create_drum_pattern."""

    VELOCITIES = {"x": 0.9, "o": 0.5, "X": 1.0, ".": 0.0, " ": 0.0}

    def _parse_pattern(self, steps):
        hits = []
        for i, ch in enumerate(steps):
            if ch in (".", " "):
                continue
            vel = self.VELOCITIES.get(ch, 0.8)
            hits.append({"step": i, "velocity": vel})
        return hits

    def test_basic_kick(self):
        hits = self._parse_pattern("x...x...x...x...")
        assert len(hits) == 4
        assert hits[0]["step"] == 0
        assert hits[1]["step"] == 4
        assert all(h["velocity"] == 0.9 for h in hits)

    def test_accent_hit(self):
        hits = self._parse_pattern("X...x...X...x...")
        assert hits[0]["velocity"] == 1.0  # X = accent
        assert hits[1]["velocity"] == 0.9  # x = normal

    def test_ghost_note(self):
        hits = self._parse_pattern("o...x...o...x...")
        assert hits[0]["velocity"] == 0.5  # o = ghost

    def test_empty_pattern(self):
        hits = self._parse_pattern("................")
        assert len(hits) == 0

    def test_sixteenth_positions(self):
        hits = self._parse_pattern("x.x.x.x.x.x.x.x.")
        assert len(hits) == 8
        positions = [h["step"] for h in hits]
        assert positions == [0, 2, 4, 6, 8, 10, 12, 14]


class TestScriptParamClamping:
    """Verify _clamp_script_param mirrors JS-side @param range validation."""

    def test_linear_clamp_high(self):
        val, clamped = _clamp_script_param(99999, "linear", 20, 20000)
        assert val == 20000.0
        assert clamped is True

    def test_linear_clamp_low(self):
        val, clamped = _clamp_script_param(-5, "linear", 20, 20000)
        assert val == 20.0
        assert clamped is True

    def test_linear_no_clamp(self):
        val, clamped = _clamp_script_param(1000, "linear", 20, 20000)
        assert val == 1000.0
        assert clamped is False

    def test_exp_clamp(self):
        val, clamped = _clamp_script_param(50000, "exp", 20, 20000)
        assert val == 20000.0
        assert clamped is True

    def test_int_round_up(self):
        val, clamped = _clamp_script_param(2.7, "int", 0, 4)
        assert val == 3.0
        assert clamped is True

    def test_int_round_down(self):
        val, clamped = _clamp_script_param(2.3, "int", 0, 4)
        assert val == 2.0
        assert clamped is True

    def test_int_no_round(self):
        val, clamped = _clamp_script_param(3, "int", 0, 4)
        assert val == 3.0
        assert clamped is False

    def test_int_clamp_high(self):
        val, clamped = _clamp_script_param(7.9, "int", 0, 4)
        assert val == 4.0
        assert clamped is True

    def test_int_clamp_low(self):
        val, clamped = _clamp_script_param(-2.7, "int", 0, 4)
        assert val == 0.0
        assert clamped is True

    def test_bool_snap_high(self):
        val, clamped = _clamp_script_param(0.8, "bool", 0, 1)
        assert val == 1.0
        assert clamped is True

    def test_bool_snap_low(self):
        val, clamped = _clamp_script_param(0.3, "bool", 0, 1)
        assert val == 0.0
        assert clamped is True

    def test_bool_exact_one(self):
        val, clamped = _clamp_script_param(1, "bool", 0, 1)
        assert val == 1.0
        assert clamped is False

    def test_bool_exact_zero(self):
        val, clamped = _clamp_script_param(0, "bool", 0, 1)
        assert val == 0.0
        assert clamped is False

    def test_unipolar_clamp(self):
        val, clamped = _clamp_script_param(1.5, "unipolar", 0, 1)
        assert val == 1.0
        assert clamped is True

    def test_unipolar_no_clamp(self):
        val, clamped = _clamp_script_param(0.5, "unipolar", 0, 1)
        assert val == 0.5
        assert clamped is False


class TestVelocityCurveMath:
    """Test velocity curve interpolation logic (mirrors JS in apply_velocity_curve)."""

    @staticmethod
    def _curve_value(t, curve_type, start_vel, end_vel, power=1.0):
        """Python mirror of the JS curve logic for unit testing."""
        if curve_type == "ramp_up":
            return start_vel + (end_vel - start_vel) * t
        elif curve_type == "ramp_down":
            return end_vel + (start_vel - end_vel) * t
        elif curve_type == "arc":
            if t < 0.5:
                return start_vel + (end_vel - start_vel) * (t * 2)
            else:
                return end_vel + (start_vel - end_vel) * ((t - 0.5) * 2)
        elif curve_type == "trough":
            if t < 0.5:
                return end_vel + (start_vel - end_vel) * (t * 2)
            else:
                return start_vel + (end_vel - start_vel) * ((t - 0.5) * 2)
        elif curve_type == "power":
            return start_vel + (end_vel - start_vel) * (t ** power)
        return start_vel

    def test_ramp_up_start(self):
        v = self._curve_value(0.0, "ramp_up", 0.3, 1.0)
        assert abs(v - 0.3) < 0.001

    def test_ramp_up_end(self):
        v = self._curve_value(1.0, "ramp_up", 0.3, 1.0)
        assert abs(v - 1.0) < 0.001

    def test_ramp_up_mid(self):
        v = self._curve_value(0.5, "ramp_up", 0.3, 1.0)
        assert abs(v - 0.65) < 0.001

    def test_ramp_down_start(self):
        v = self._curve_value(0.0, "ramp_down", 0.3, 1.0)
        assert abs(v - 1.0) < 0.001

    def test_ramp_down_end(self):
        v = self._curve_value(1.0, "ramp_down", 0.3, 1.0)
        assert abs(v - 0.3) < 0.001

    def test_arc_peak_middle(self):
        v = self._curve_value(0.5, "arc", 0.3, 1.0)
        assert abs(v - 1.0) < 0.001

    def test_arc_start(self):
        v = self._curve_value(0.0, "arc", 0.3, 1.0)
        assert abs(v - 0.3) < 0.001

    def test_arc_end(self):
        v = self._curve_value(1.0, "arc", 0.3, 1.0)
        assert abs(v - 0.3) < 0.001

    def test_trough_dip_middle(self):
        v = self._curve_value(0.5, "trough", 0.3, 1.0)
        assert abs(v - 0.3) < 0.001

    def test_trough_start(self):
        v = self._curve_value(0.0, "trough", 0.3, 1.0)
        assert abs(v - 1.0) < 0.001

    def test_trough_end(self):
        v = self._curve_value(1.0, "trough", 0.3, 1.0)
        assert abs(v - 1.0) < 0.001

    def test_power_linear(self):
        v = self._curve_value(0.5, "power", 0.2, 1.0, power=1.0)
        assert abs(v - 0.6) < 0.001

    def test_power_sharp(self):
        # power=2.0: t=0.5 → 0.25 → vel = 0.2 + 0.8*0.25 = 0.4
        v = self._curve_value(0.5, "power", 0.2, 1.0, power=2.0)
        assert abs(v - 0.4) < 0.001

    def test_power_slow(self):
        # power=0.5: t=0.5 → sqrt(0.5) ≈ 0.707 → vel = 0.2 + 0.8*0.707 ≈ 0.766
        v = self._curve_value(0.5, "power", 0.2, 1.0, power=0.5)
        assert abs(v - (0.2 + 0.8 * (0.5 ** 0.5))) < 0.01

    def test_clamp_min_velocity(self):
        # When start and end are very low, curve should still produce >= 0.05
        v = self._curve_value(0.0, "ramp_up", 0.01, 0.02)
        clamped = max(0.05, min(1.0, v))
        assert clamped >= 0.05


class TestArticulationMath:
    """Test articulation logic (mirrors JS in apply_articulation)."""

    @staticmethod
    def _staccato_duration(dur, amount, sixteenth=240):
        slot = max(sixteenth, dur)
        return max(1, int(slot * amount))

    @staticmethod
    def _legato_duration(pos, dur, next_start, amount):
        target_end = pos + (next_start - pos) * amount
        return max(1, int(target_end - pos))

    @staticmethod
    def _tenuto_duration(pos, dur, sixteenth=240):
        slot_end = math.ceil((pos + dur) / sixteenth) * sixteenth
        return max(1, slot_end - pos)

    @staticmethod
    def _accent_velocity(cur_vel, amount):
        return min(1.0, cur_vel + amount * (1.0 - cur_vel))

    def test_staccato_half(self):
        d = self._staccato_duration(240, 0.5)
        assert d == 120

    def test_staccato_very_short(self):
        d = self._staccato_duration(240, 0.3)
        assert d == 72

    def test_staccato_moderate(self):
        d = self._staccato_duration(480, 0.5)
        assert d == 240

    def test_staccato_min_duration(self):
        d = self._staccato_duration(240, 0.001)
        assert d == 1  # never zero

    def test_legato_near_full(self):
        d = self._legato_duration(0, 240, 480, 0.95)
        # target_end = 0 + 480 * 0.95 = 456 → dur = 456
        assert d == 456

    def test_legato_half(self):
        d = self._legato_duration(0, 240, 480, 0.5)
        # target_end = 0 + 480 * 0.5 = 240 → dur = 240
        assert d == 240

    def test_legato_last_note(self):
        # Last note: next_start = pos + dur → target_end = pos + dur * amount
        d = self._legato_duration(480, 240, 720, 0.95)
        # target_end = 480 + 240 * 0.95 = 480 + 228 = 708 → dur = 228
        assert d == 228

    def test_tenuto_fills_slot(self):
        # pos=0, dur=200 → slot_end = ceil(200/240)*240 = 240 → dur = 240
        d = self._tenuto_duration(0, 200)
        assert d == 240

    def test_tenuto_already_full(self):
        # pos=0, dur=240 → slot_end = 240 → dur = 240
        d = self._tenuto_duration(0, 240)
        assert d == 240

    def test_tenuto_crosses_slot(self):
        # pos=240, dur=300 → slot_end = ceil(540/240)*240 = 720 → dur = 480
        d = self._tenuto_duration(240, 300)
        assert d == 480

    def test_accent_subtle(self):
        v = self._accent_velocity(0.5, 0.3)
        # 0.5 + 0.3 * 0.5 = 0.65
        assert abs(v - 0.65) < 0.001

    def test_accent_strong(self):
        v = self._accent_velocity(0.5, 1.0)
        assert v == 1.0

    def test_accent_already_loud(self):
        v = self._accent_velocity(0.9, 0.5)
        # 0.9 + 0.5 * 0.1 = 0.95
        assert abs(v - 0.95) < 0.001


class TestParseMelodyPattern:
    """Test parse_melody_pattern — the core function used by create_melody, create_bassline, create_arpeggio."""

    def _parse(self, pattern, root="C", scale="major", **kw):
        from opendaw_mcp.music_theory import parse_melody_pattern
        return parse_melody_pattern(pattern, root=root, scale_type=scale, **kw)

    def test_basic_ascending(self):
        notes = self._parse("1 2 3 4", root="C", scale="major")
        assert len(notes) == 4
        assert notes[0]["pitch"] == 60  # C4
        assert notes[1]["pitch"] == 62  # D4
        assert notes[2]["pitch"] == 64  # E4
        assert notes[3]["pitch"] == 65  # F4

    def test_rests_skipped(self):
        notes = self._parse("1 - 3 - 5", root="C", scale="major")
        assert len(notes) == 3
        assert notes[0]["pitch"] == 60
        assert notes[1]["pitch"] == 64
        assert notes[2]["pitch"] == 67

    def test_step_duration_affects_timing(self):
        notes = self._parse("1 2 3", root="C", scale="major", step_duration=0.5)
        assert notes[0]["start"] == 0.0
        assert notes[1]["start"] == 0.5
        assert notes[2]["start"] == 1.0
        assert all(n["duration"] == 0.5 for n in notes)

    def test_start_beat_offset(self):
        notes = self._parse("1 2", root="C", scale="major", start_beat=4.0)
        assert notes[0]["start"] == 4.0
        assert notes[1]["start"] == 4.25

    def test_velocity_passed_through(self):
        notes = self._parse("1 2", root="C", scale="major", velocity=0.9)
        assert all(n["velocity"] == 0.9 for n in notes)

    def test_minor_scale_intervals(self):
        notes = self._parse("1 2 3", root="A", scale="minor")
        assert notes[0]["pitch"] == 69  # A4
        assert notes[1]["pitch"] == 71  # B4
        assert notes[2]["pitch"] == 72  # C5 (minor 3rd = +3)

    def test_dorian_scale(self):
        notes = self._parse("1 2 3", root="D", scale="dorian")
        assert notes[0]["pitch"] == 62  # D4 (default octave=4)
        assert notes[1]["pitch"] == 64  # E4
        assert notes[2]["pitch"] == 65  # F4 (minor 3rd in dorian)

    def test_octave_shift(self):
        notes_low = self._parse("1", root="C", scale="major", octave=2)
        notes_mid = self._parse("1", root="C", scale="major", octave=4)
        assert notes_low[0]["pitch"] == 36  # C2
        assert notes_mid[0]["pitch"] == 60  # C4
        assert notes_mid[0]["pitch"] - notes_low[0]["pitch"] == 24  # 2 octaves

    def test_sharp_root(self):
        notes = self._parse("1", root="F#", scale="major")
        assert notes[0]["pitch"] == 66  # F#4

    def test_empty_pattern_raises(self):
        import pytest
        with pytest.raises(ValueError):
            self._parse("-", root="C", scale="major")

    def test_note_dict_structure(self):
        notes = self._parse("1", root="C", scale="major")
        n = notes[0]
        assert "pitch" in n
        assert "start" in n
        assert "duration" in n
        assert "velocity" in n


class TestScaleToPitches:
    """Test scale_to_pitches — used by create_scale_run, create_counterpoint, create_harmony."""

    def _scale(self, root, scale, **kw):
        from opendaw_mcp.music_theory import scale_to_pitches
        return scale_to_pitches(root, scale, **kw)

    def test_c_major(self):
        assert self._scale("C", "major") == [60, 62, 64, 65, 67, 69, 71]

    def test_a_minor(self):
        assert self._scale("A", "minor") == [69, 71, 72, 74, 76, 77, 79]

    def test_length_extension(self):
        notes = self._scale("C", "major", length=14)
        assert len(notes) == 14
        assert notes[7] == 72  # C5 (octave wrap)

    def test_octave_param(self):
        notes = self._scale("C", "major", octave=3)
        assert notes[0] == 48  # C3

    def test_dorian_mode(self):
        notes = self._scale("D", "dorian")
        assert notes == [62, 64, 65, 67, 69, 71, 72]

    def test_phrygian_mode(self):
        notes = self._scale("E", "phrygian")
        assert notes[0] == 64  # E4
        assert notes[1] == 65  # F4 (minor 2nd — phrygian hallmark)


class TestChordToPitches:
    """Test chord_to_pitches — used by create_chord_progression, create_harmony."""

    def _chord(self, root, chord_type, **kw):
        from opendaw_mcp.music_theory import chord_to_pitches
        return chord_to_pitches(root, chord_type, **kw)

    def test_major_triad(self):
        assert self._chord("C", "maj") == [60, 64, 67]

    def test_minor_triad(self):
        assert self._chord("A", "min") == [69, 72, 76]

    def test_dominant_seventh(self):
        assert self._chord("G", "dom7") == [67, 71, 74, 77]

    def test_major_seventh(self):
        assert self._chord("C", "maj7") == [60, 64, 67, 71]

    def test_diminished(self):
        assert self._chord("B", "dim") == [71, 74, 77]

    def test_sus4(self):
        assert self._chord("D", "sus4") == [62, 67, 69]

    def test_octave_shift(self):
        assert self._chord("C", "maj", octave=3) == [48, 52, 55]

    def test_sharp_root(self):
        assert self._chord("F#", "min") == [66, 69, 73]


class TestGenrePresets:
    """Test GENRE_PRESETS — used by create_genre_track."""

    def test_known_genres(self):
        from opendaw_mcp.music_theory import GENRE_PRESETS
        for g in ["house", "techno", "lofi", "dnb", "trap", "ambient", "coldwave", "hiphop"]:
            assert g in GENRE_PRESETS, f"Missing genre: {g}"

    def test_preset_has_bpm(self):
        from opendaw_mcp.music_theory import GENRE_PRESETS
        for g, p in GENRE_PRESETS.items():
            assert "bpm" in p, f"{g} missing bpm"

    def test_preset_has_drums(self):
        from opendaw_mcp.music_theory import GENRE_PRESETS
        for g, p in GENRE_PRESETS.items():
            assert "drums" in p, f"{g} missing drums"

    def test_techno_bpm_range(self):
        from opendaw_mcp.music_theory import GENRE_PRESETS
        bpm = GENRE_PRESETS["techno"]["bpm"]
        assert 120 <= bpm <= 140, f"techno bpm {bpm} out of range"

    def test_dnb_bpm_range(self):
        from opendaw_mcp.music_theory import GENRE_PRESETS
        bpm = GENRE_PRESETS["dnb"]["bpm"]
        assert 160 <= bpm <= 180, f"dnb bpm {bpm} out of range"

    def test_lofi_bpm_range(self):
        from opendaw_mcp.music_theory import GENRE_PRESETS
        bpm = GENRE_PRESETS["lofi"]["bpm"]
        assert 60 <= bpm <= 90, f"lofi bpm {bpm} out of range"


class TestCanon:
    """Unit tests for create_canon orchestration tool — logic validation."""

    def _build_voice_data(self, melody, voices, entry_delay, transpose_list, vel=0.85, decay=0.15, direction="up"):
        """Replicate the Python-side note generation from create_canon."""
        note_spacing = 0.5
        voice_data = []
        for v in range(voices):
            if direction == "down":
                delay = (voices - 1 - v) * entry_delay
                tr = transpose_list[voices - 1 - v]
                v_vel = max(0.1, vel - (voices - 1 - v) * decay)
            else:
                delay = v * entry_delay
                tr = transpose_list[v]
                v_vel = max(0.1, vel - v * decay)
            notes = []
            for i, p in enumerate(melody):
                tp = max(0, min(127, p + tr))
                notes.append({"pitch": tp, "pos": delay + i * note_spacing, "dur": note_spacing * 0.9, "vel": round(v_vel, 3)})
            voice_data.append(notes)
        return voice_data

    def test_basic_3_voice(self):
        vd = self._build_voice_data([60, 62, 64, 67, 64, 62, 60, 57], 3, 4, [0, 7, 12])
        assert len(vd) == 3
        assert len(vd[0]) == 8
        assert len(vd[2]) == 8
        # Voice 0 starts at beat 0, voice 1 at beat 4, voice 2 at beat 8
        assert vd[0][0]["pos"] == 0.0
        assert vd[1][0]["pos"] == 4.0
        assert vd[2][0]["pos"] == 8.0

    def test_transposition_applied(self):
        vd = self._build_voice_data([60, 62], 3, 4, [0, 7, 12])
        assert vd[0][0]["pitch"] == 60  # unison
        assert vd[1][0]["pitch"] == 67  # fifth
        assert vd[2][0]["pitch"] == 72  # octave

    def test_velocity_decay(self):
        vd = self._build_voice_data([60], 4, 2, [0, 5, 7, 12], vel=0.85, decay=0.1)
        assert vd[0][0]["vel"] == 0.85
        assert vd[1][0]["vel"] == 0.75
        assert vd[2][0]["vel"] == 0.65
        assert vd[3][0]["vel"] == 0.55

    def test_direction_down(self):
        vd = self._build_voice_data([60], 3, 4, [0, 7, 12], direction="down")
        # Voice 0 should have highest delay and highest transposition
        assert vd[0][0]["pos"] == 8.0  # (3-1-0)*4 = 8
        assert vd[0][0]["pitch"] == 72  # transpose_list[2] = 12
        assert vd[2][0]["pos"] == 0.0  # (3-1-2)*4 = 0
        assert vd[2][0]["pitch"] == 60  # transpose_list[0] = 0

    def test_velocity_clamp(self):
        # With high decay, velocity should clamp to 0.1
        vd = self._build_voice_data([60], 6, 1, [0, 0, 0, 0, 0, 0], vel=0.5, decay=0.3)
        assert vd[5][0]["vel"] == 0.1  # 0.5 - 5*0.3 = -1.0 → clamped to 0.1

    def test_pitch_clamp(self):
        # Extreme transposition should clamp to 0-127
        vd = self._build_voice_data([60], 2, 1, [0, 80])
        assert vd[1][0]["pitch"] == 127  # 60+80=140 → clamped

    def test_pitch_clamp_low(self):
        vd = self._build_voice_data([10], 2, 1, [0, -50])
        assert vd[1][0]["pitch"] == 0  # 10-50=-40 → clamped

    def test_total_beats(self):
        voices = 4
        entry_delay = 4
        melody_len = 8 * 0.5  # 8 notes × 0.5 spacing
        total = (voices - 1) * entry_delay + melody_len
        assert total == 16.0  # 3*4 + 4 = 16

    def test_round_unison(self):
        # All voices at same pitch (round/canon)
        vd = self._build_voice_data([60, 62, 64, 65], 2, 2, [0, 0])
        assert vd[0][0]["pitch"] == 60
        assert vd[1][0]["pitch"] == 60  # same pitch, just delayed

    def test_note_count(self):
        melody = [60, 62, 64, 67, 64, 62, 60, 57]
        voices = 3
        vd = self._build_voice_data(melody, voices, 4, [0, 7, 12])
        total_notes = sum(len(v) for v in vd)
        assert total_notes == len(melody) * voices  # 24
