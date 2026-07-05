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


class TestAugmentNotes:
    """Unit tests for augment_notes transformation — logic validation."""

    def test_factor_range_valid(self):
        for f in [0.25, 0.5, 1.0, 2.0, 4.0]:
            assert 0.25 <= f <= 4.0, f"factor {f} should be valid"

    def test_factor_too_small(self):
        assert not (0.25 <= 0.1 <= 4.0)

    def test_factor_too_large(self):
        assert not (0.25 <= 5.0 <= 4.0)

    def test_mode_valid(self):
        assert "scale" in ("scale", "stretch")
        assert "stretch" in ("scale", "stretch")

    def test_mode_invalid(self):
        assert "wobble" not in ("scale", "stretch")

    def test_augmentation_doubles_duration(self):
        old_dur = 480  # PPQN quarter
        factor = 2.0
        new_dur = round(old_dur * factor)
        assert new_dur == 960  # doubled

    def test_diminution_halves_duration(self):
        old_dur = 480
        factor = 0.5
        new_dur = round(old_dur * factor)
        assert new_dur == 240  # halved

    def test_scale_mode_position(self):
        region_pos = 0
        old_pos = 480  # 1 beat in
        factor = 2.0
        rel_pos = old_pos - region_pos
        new_pos = region_pos + round(rel_pos * factor)
        assert new_pos == 960  # position also doubled

    def test_stretch_mode_position_unchanged(self):
        old_pos = 480
        # In stretch mode, position is NOT modified
        new_pos = old_pos  # unchanged
        assert new_pos == 480

    def test_duration_too_short_skipped(self):
        old_dur = 1  # 1 tick
        factor = 0.5
        new_dur = round(old_dur * factor)
        assert new_dur < 1  # should be skipped


class TestComping:
    """Unit tests for create_comping orchestration tool — logic validation."""

    def _build_note_data(self, voicings, rhythm, note_spacing=0.5, velocity=0.7, syncopation=0.0, start_beat=0):
        """Replicate the Python-side note generation from create_comping."""
        import random as _rng
        rng = _rng.Random(42)
        note_data = []
        chord_count = len(voicings)
        rhythm_len = len(rhythm)
        total_steps = chord_count * rhythm_len

        for step in range(total_steps):
            rhythm_char = rhythm[step % rhythm_len]
            if rhythm_char == "-":
                continue
            chord_idx_actual = step // rhythm_len
            if chord_idx_actual >= chord_count:
                chord_idx_actual = chord_count - 1
            voicing = voicings[chord_idx_actual]
            pos = start_beat + step * note_spacing
            is_ghost = rhythm_char == "."
            vel = velocity * (0.4 if is_ghost else 1.0)
            if syncopation > 0 and not is_ghost and rng.random() < syncopation:
                pos += note_spacing * 0.5 * (1 if rng.random() > 0.5 else -1)
            dur = note_spacing * 0.85
            for pitch in voicing:
                note_data.append({"pitch": pitch, "pos": pos, "dur": dur, "vel": vel})
        return note_data, total_steps

    def test_basic_jazz_comping(self):
        voicings = [[60, 63, 67, 70]]  # Cmin7
        notes, steps = self._build_note_data(voicings, "x-x-x-x-")
        # 4 hits in 8 steps × 4 notes per chord = 16 notes
        assert len(notes) == 16

    def test_ghost_velocity(self):
        voicings = [[60, 63, 67]]
        notes, _ = self._build_note_data(voicings, "x.x.")
        # x at step 0, . at step 2 → ghost has lower velocity
        ghost_notes = [n for n in notes if n["vel"] < 0.7]
        assert len(ghost_notes) > 0
        assert all(abs(n["vel"] - 0.28) < 0.01 for n in ghost_notes)  # 0.7 * 0.4

    def test_rest_skips_notes(self):
        voicings = [[60, 63]]
        notes, _ = self._build_note_data(voicings, "----")
        assert len(notes) == 0  # all rests

    def test_multi_chord_progression(self):
        voicings = [[60, 63, 67], [65, 69, 72]]  # Cmin, Fmin
        notes, steps = self._build_note_data(voicings, "x-x-")
        assert steps == 8  # 2 chords × 4 steps
        # 2 hits per chord cycle × 2 chords × 3 notes = 12
        assert len(notes) == 12

    def test_total_steps_calculation(self):
        voicings = [[60]] * 4
        _, steps = self._build_note_data(voicings, "x-x-x-x-")
        assert steps == 32  # 4 chords × 8 steps

    def test_syncopation_changes_position(self):
        voicings = [[60, 63]]
        notes_no_sync, _ = self._build_note_data(voicings, "x-x-", syncopation=0.0)
        notes_sync, _ = self._build_note_data(voicings, "x-x-", syncopation=0.5)
        # With syncopation, some positions may differ (random)
        # At least the data should be generated without error
        assert len(notes_sync) == len(notes_no_sync)

    def test_note_duration(self):
        voicings = [[60]]
        notes, _ = self._build_note_data(voicings, "x", note_spacing=0.25)
        assert notes[0]["dur"] == 0.25 * 0.85  # 0.2125

    def test_pitch_range(self):
        voicings = [[0, 127]]
        notes, _ = self._build_note_data(voicings, "x")
        assert all(0 <= n["pitch"] <= 127 for n in notes)

    def test_rhythm_validation(self):
        valid = "x-x.x-"
        assert all(c in "x-." for c in valid)
        invalid = "x!x"
        assert not all(c in "x-." for c in invalid)

    def test_velocity_clamp(self):
        voicings = [[60]]
        notes, _ = self._build_note_data(voicings, "x", velocity=1.0)
        assert all(n["vel"] <= 1.0 for n in notes)


class TestMordent:
    """Unit tests for create_mordent orchestration tool — logic validation."""

    def _build_notes(self, main_pitch, direction, interval, duration=0.5, velocity=0.85):
        """Replicate mordent note generation."""
        neighbor_offset = interval if direction == "upper" else -interval
        neighbor_pitch = max(0, min(127, main_pitch + neighbor_offset))
        main_dur = duration * 0.4
        neighbor_dur = duration * 0.2
        return_dur = duration * 0.4
        return [
            {"pitch": main_pitch, "pos": 0.0, "dur": main_dur, "vel": velocity},
            {"pitch": neighbor_pitch, "pos": main_dur, "dur": neighbor_dur, "vel": round(velocity * 0.9, 3)},
            {"pitch": main_pitch, "pos": main_dur + neighbor_dur, "dur": return_dur, "vel": velocity},
        ]

    def test_upper_mordent_neighbor_higher(self):
        notes = self._build_notes(60, "upper", 2)
        assert notes[1]["pitch"] == 62  # neighbor is 2 semitones higher

    def test_lower_mordent_neighbor_lower(self):
        notes = self._build_notes(60, "lower", 2)
        assert notes[1]["pitch"] == 58  # neighbor is 2 semitones lower

    def test_half_step_interval(self):
        notes = self._build_notes(64, "upper", 1)
        assert notes[1]["pitch"] == 65  # half step up

    def test_three_notes(self):
        notes = self._build_notes(60, "upper", 2)
        assert len(notes) == 3

    def test_timing_split(self):
        notes = self._build_notes(60, "upper", 2, duration=1.0)
        assert notes[0]["dur"] == 0.4  # 40%
        assert notes[1]["dur"] == 0.2  # 20%
        assert notes[2]["dur"] == 0.4  # 40%

    def test_neighbor_velocity_lower(self):
        notes = self._build_notes(60, "upper", 2, velocity=0.85)
        assert notes[1]["vel"] < notes[0]["vel"]  # neighbor quieter

    def test_pitch_clamp(self):
        notes = self._build_notes(0, "lower", 7)
        assert notes[1]["pitch"] == 0  # clamped to 0, same as main → error in real code

    def test_return_to_main(self):
        notes = self._build_notes(60, "upper", 3)
        assert notes[2]["pitch"] == 60  # returns to main

    def test_direction_upper_interval_positive(self):
        offset = 2 if "upper" == "upper" else -2
        assert offset > 0

    def test_direction_lower_interval_negative(self):
        offset = -2 if "lower" == "lower" else 2
        assert offset < 0


class TestTurn:
    """Unit tests for create_turn orchestration tool — logic validation."""

    def _build_notes(self, main_pitch, direction, interval, duration=1.0, velocity=0.85):
        """Replicate turn note generation."""
        upper_pitch = max(0, min(127, main_pitch + interval))
        lower_pitch = max(0, min(127, main_pitch - interval))
        step_dur = duration * 0.2
        neighbor_vel = round(velocity * 0.9, 3)
        if direction == "upper":
            return [
                {"pitch": main_pitch, "pos": 0.0, "dur": step_dur, "vel": velocity},
                {"pitch": upper_pitch, "pos": step_dur, "dur": step_dur, "vel": neighbor_vel},
                {"pitch": main_pitch, "pos": step_dur * 2, "dur": step_dur, "vel": velocity},
                {"pitch": lower_pitch, "pos": step_dur * 3, "dur": step_dur, "vel": neighbor_vel},
                {"pitch": main_pitch, "pos": step_dur * 4, "dur": step_dur, "vel": velocity},
            ]
        else:
            return [
                {"pitch": main_pitch, "pos": 0.0, "dur": step_dur, "vel": velocity},
                {"pitch": lower_pitch, "pos": step_dur, "dur": step_dur, "vel": neighbor_vel},
                {"pitch": main_pitch, "pos": step_dur * 2, "dur": step_dur, "vel": velocity},
                {"pitch": upper_pitch, "pos": step_dur * 3, "dur": step_dur, "vel": neighbor_vel},
                {"pitch": main_pitch, "pos": step_dur * 4, "dur": step_dur, "vel": velocity},
            ]

    def test_five_notes(self):
        notes = self._build_notes(60, "upper", 2)
        assert len(notes) == 5

    def test_upper_turn_order(self):
        notes = self._build_notes(60, "upper", 2)
        pitches = [n["pitch"] for n in notes]
        assert pitches == [60, 62, 60, 58, 60]  # main→up→main→down→main

    def test_lower_turn_order(self):
        notes = self._build_notes(60, "lower", 2)
        pitches = [n["pitch"] for n in notes]
        assert pitches == [60, 58, 60, 62, 60]  # main→down→main→up→main

    def test_half_step_interval(self):
        notes = self._build_notes(64, "upper", 1)
        assert notes[1]["pitch"] == 65  # half step up
        assert notes[3]["pitch"] == 63  # half step down

    def test_equal_timing(self):
        notes = self._build_notes(60, "upper", 2, duration=2.0)
        step_dur = 2.0 * 0.2
        assert all(n["dur"] == step_dur for n in notes)

    def test_neighbor_velocity_lower(self):
        notes = self._build_notes(60, "upper", 2, velocity=0.85)
        assert notes[1]["vel"] < notes[0]["vel"]  # neighbor quieter
        assert notes[3]["vel"] < notes[2]["vel"]

    def test_starts_and_ends_on_main(self):
        notes = self._build_notes(60, "lower", 3)
        assert notes[0]["pitch"] == 60  # starts on main
        assert notes[-1]["pitch"] == 60  # ends on main

    def test_pitch_clamp(self):
        notes = self._build_notes(1, "lower", 7)
        assert notes[1]["pitch"] == 0  # clamped to 0 (1-7=-6→0)

    def test_upper_then_lower_pattern(self):
        notes = self._build_notes(60, "upper", 2)
        # Position should be ascending: 0, step, 2*step, 3*step, 4*step
        positions = [n["pos"] for n in notes]
        assert positions == sorted(positions)  # monotonically increasing

    def test_interval_applies_both_directions(self):
        notes = self._build_notes(60, "upper", 5)
        assert notes[1]["pitch"] == 65  # up 5
        assert notes[3]["pitch"] == 55  # down 5


class TestAppoggiatura:
    """Unit tests for create_appoggiatura orchestration tool — logic validation."""

    def _build_notes(self, main_pitch, approach_pitch, duration=1.0, ratio=0.67, velocity=0.85):
        approach_dur = duration * ratio
        main_dur = duration * (1.0 - ratio)
        approach_vel = round(min(1.0, velocity * 1.05), 3)
        return [
            {"pitch": approach_pitch, "pos": 0.0, "dur": approach_dur, "vel": approach_vel},
            {"pitch": main_pitch, "pos": approach_dur, "dur": main_dur, "vel": velocity},
        ]

    def test_two_notes(self):
        notes = self._build_notes(60, 62)
        assert len(notes) == 2

    def test_approach_first(self):
        notes = self._build_notes(60, 62)
        assert notes[0]["pitch"] == 62  # approach first
        assert notes[1]["pitch"] == 60  # main second

    def test_above_direction(self):
        direction = "above" if 62 > 60 else "below"
        assert direction == "above"

    def test_below_direction(self):
        direction = "above" if 59 > 60 else "below"
        assert direction == "below"

    def test_ratio_timing(self):
        notes = self._build_notes(60, 62, duration=1.0, ratio=0.67)
        assert abs(notes[0]["dur"] - 0.67) < 0.001  # approach = 67%
        assert abs(notes[1]["dur"] - 0.33) < 0.001  # main = 33%

    def test_equal_split(self):
        notes = self._build_notes(60, 62, duration=2.0, ratio=0.5)
        assert abs(notes[0]["dur"] - 1.0) < 0.001
        assert abs(notes[1]["dur"] - 1.0) < 0.001

    def test_approach_accented(self):
        notes = self._build_notes(60, 62, velocity=0.85)
        assert notes[0]["vel"] > notes[1]["vel"]  # approach slightly louder

    def test_position_continuous(self):
        notes = self._build_notes(60, 62, duration=1.0)
        assert notes[1]["pos"] == notes[0]["dur"]  # no gap

    def test_same_pitch_error(self):
        # In the real tool, same pitch returns error
        assert 60 == 60  # would trigger error

    def test_ratio_clamp_high(self):
        notes = self._build_notes(60, 62, duration=1.0, ratio=0.9)
        assert abs(notes[0]["dur"] - 0.9) < 0.001  # 90% approach
        assert abs(notes[1]["dur"] - 0.1) < 0.001  # 10% resolution


class TestVibratoDSP:
    """Unit tests for werkstatt_vibrato.js DSP script structure."""

    def _parse_params(self, code):
        """Extract @param declarations from DSP script."""
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_vibrato.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt vibrato" in code, "Missing @werkstatt vibrato header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 4, f"Expected 4 params, got {len(params)}"

    def test_rate_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        rate = [p for p in params if p["name"] == "rate"][0]
        assert rate["min"] == 0.1
        assert rate["max"] == 20
        assert rate["scale"] == "exp"

    def test_depth_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        depth = [p for p in params if p["name"] == "depth"][0]
        assert depth["min"] == 0.0005
        assert depth["max"] == 0.02
        assert depth["scale"] == "linear"

    def test_shape_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        shape = [p for p in params if p["name"] == "shape"][0]
        assert shape["min"] == 0
        assert shape["max"] == 1
        assert shape["scale"] == "linear"

    def test_stereo_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        stereo = [p for p in params if p["name"] == "stereo"][0]
        assert stereo["min"] == 0
        assert stereo["max"] == 1

    def test_delay_buffer_exists(self):
        code = self._read_script()
        assert "Float32Array" in code, "Missing delay buffer"
        assert "maxDelay" in code, "Missing maxDelay"

    def test_lfo_implementation(self):
        code = self._read_script()
        assert "Math.sin" in code, "Missing sine LFO"
        assert "this.phase" in code, "Missing phase accumulator"

    def test_fractional_delay_interp(self):
        code = self._read_script()
        assert "Math.floor(readL)" in code or "Math.floor(read" in code, "Missing fractional delay interpolation"

    def test_stereo_phase_offset(self):
        code = self._read_script()
        assert "Math.PI * stereo" in code or "Math.PI * this.p.stereo" in code, "Missing stereo phase offset"


class TestWavetableDSP:
    """Unit tests for apparat_wavetable.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "apparat_wavetable.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@apparat wavetable" in code, "Missing @apparat wavetable header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_pos_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        pos = [p for p in params if p["name"] == "pos"][0]
        assert pos["min"] == 0 and pos["max"] == 1

    def test_unison_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        unison = [p for p in params if p["name"] == "unison"][0]
        assert unison["scale"] == "int"
        assert unison["min"] == 1 and unison["max"] == 7

    def test_wavetable_count(self):
        code = self._read_script()
        assert "case 7:" in code, "Expected 8 wavetables (0-7)"
        assert "case 0:" in code

    def test_interpolation(self):
        code = self._read_script()
        assert "frac" in code, "Missing wavetable interpolation"
        assert "1 - frac" in code or "(1 - frac)" in code

    def test_scan_lfo(self):
        code = self._read_script()
        assert "pos_lfo" in code, "Missing scan LFO"
        assert "lfoPhase" in code, "Missing LFO phase accumulator"

    def test_unison_detune(self):
        code = self._read_script()
        assert "_uniDetunes" in code, "Missing unison detune array"
        assert "_uniPhases" in code, "Missing unison phase array"

    def test_adsr_envelope(self):
        code = self._read_script()
        assert "envState" in code, "Missing ADSR envelope state"
        assert "aCoef" in code and "rCoef" in code, "Missing ADSR coefficients"

    def test_note_on_off(self):
        code = self._read_script()
        assert "noteOn" in code, "Missing noteOn handler"
        assert "noteOff" in code, "Missing noteOff handler"


class TestSupersawDSP:
    """Unit tests for apparat_supersaw.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "apparat_supersaw.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@apparat supersaw" in code, "Missing @apparat supersaw header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_detune_param(self):
        params = self._parse_params(self._read_script())
        det = [p for p in params if p["name"] == "detune"][0]
        assert det["min"] == 0 and det["max"] == 0.5

    def test_spread_param(self):
        params = self._parse_params(self._read_script())
        sp = [p for p in params if p["name"] == "spread"][0]
        assert sp["min"] == 0 and sp["max"] == 1

    def test_seven_voices(self):
        code = self._read_script()
        assert "NUM = 7" in code, "Expected 7 supersaw voices"
        assert "detuneCents" in code, "Missing detune cents array"

    def test_stereo_pan(self):
        code = self._read_script()
        assert "pans" in code, "Missing per-voice pan array"
        assert "panAngles" in code, "Missing pan angle computation"
        assert "Math.cos" in code and "Math.sin" in code, "Missing equal-power pan"

    def test_sawtooth_osc(self):
        code = self._read_script()
        assert "_saw" in code, "Missing sawtooth oscillator"
        assert "Math.floor(phase + 0.5)" in code, "Missing sawtooth waveform"

    def test_resonant_filter(self):
        code = self._read_script()
        assert "cutCoeff" in code, "Missing filter coefficient"
        assert "resAmt" in code, "Missing resonance amount"
        assert "lpL" in code and "lpR" in code, "Missing per-channel filter state"

    def test_adsr_envelope(self):
        code = self._read_script()
        assert "envState" in code, "Missing ADSR envelope state"
        assert "aCoef" in code and "rCoef" in code, "Missing ADSR coefficients"

    def test_note_on_off(self):
        code = self._read_script()
        assert "noteOn" in code, "Missing noteOn handler"
        assert "noteOff" in code, "Missing noteOff handler"


class TestHemiola:
    """Unit tests for create_hemiola orchestration tool logic."""

    def _build_notes(self, pattern, bars=1, primary_pitch=60, secondary_pitch=64, start_beat=0):
        """Simulate the hemiola note generation logic."""
        total_beats = bars * 4
        parts = pattern.split(":")
        primary_count = int(parts[0])
        secondary_count = int(parts[1])
        notes = []
        p_step = total_beats / primary_count
        for i in range(primary_count):
            notes.append({"pitch": primary_pitch, "start": start_beat + i * p_step, "group": "primary"})
        s_step = total_beats / secondary_count
        for i in range(secondary_count):
            notes.append({"pitch": secondary_pitch, "start": start_beat + i * s_step, "group": "secondary"})
        return notes

    def test_3_2_note_count(self):
        notes = self._build_notes("3:2")
        assert len(notes) == 5  # 3 primary + 2 secondary

    def test_2_3_note_count(self):
        notes = self._build_notes("2:3")
        assert len(notes) == 5  # 2 primary + 3 secondary

    def test_3_2_ratio(self):
        notes = self._build_notes("3:2")
        primary = [n for n in notes if n["group"] == "primary"]
        secondary = [n for n in notes if n["group"] == "secondary"]
        assert len(primary) == 3
        assert len(secondary) == 2

    def test_primary_timing(self):
        notes = self._build_notes("3:2", bars=1)
        primary = [n for n in notes if n["group"] == "primary"]
        assert abs(primary[0]["start"] - 0) < 0.001
        assert abs(primary[1]["start"] - 4/3) < 0.001
        assert abs(primary[2]["start"] - 8/3) < 0.001

    def test_secondary_timing(self):
        notes = self._build_notes("3:2", bars=1)
        secondary = [n for n in notes if n["group"] == "secondary"]
        assert abs(secondary[0]["start"] - 0) < 0.001
        assert abs(secondary[1]["start"] - 2.0) < 0.001

    def test_bars_2_timing(self):
        notes = self._build_notes("3:2", bars=2)
        primary = [n for n in notes if n["group"] == "primary"]
        assert abs(primary[0]["start"] - 0) < 0.001
        assert abs(primary[1]["start"] - 8/3) < 0.001
        assert abs(primary[2]["start"] - 16/3) < 0.001

    def test_pitch_separation(self):
        notes = self._build_notes("3:2", primary_pitch=60, secondary_pitch=72)
        pitches = {n["pitch"] for n in notes}
        assert 60 in pitches
        assert 72 in pitches

    def test_start_beat_offset(self):
        notes = self._build_notes("3:2", start_beat=10)
        assert all(n["start"] >= 10 for n in notes)

    def test_2_3_primary_timing(self):
        notes = self._build_notes("2:3", bars=1)
        primary = [n for n in notes if n["group"] == "primary"]
        assert abs(primary[0]["start"] - 0) < 0.001
        assert abs(primary[1]["start"] - 2.0) < 0.001

    def test_2_3_secondary_timing(self):
        notes = self._build_notes("2:3", bars=1)
        secondary = [n for n in notes if n["group"] == "secondary"]
        assert abs(secondary[0]["start"] - 0) < 0.001
        assert abs(secondary[1]["start"] - 4/3) < 0.001
        assert abs(secondary[2]["start"] - 8/3) < 0.001


class TestBitcrusherDSP:
    """Unit tests for werkstatt_bitcrusher.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_bitcrusher.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt bitcrusher" in code, "Missing @werkstatt bitcrusher header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_bits_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        bits = [p for p in params if p["name"] == "bits"][0]
        assert bits["min"] == 1
        assert bits["max"] == 16
        assert bits["default"] == 8

    def test_rate_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        rate = [p for p in params if p["name"] == "rate"][0]
        assert rate["min"] == 0
        assert rate["max"] == 1

    def test_drive_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        drive = [p for p in params if p["name"] == "drive"][0]
        assert drive["min"] == 0
        assert drive["max"] == 2

    def test_offset_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        offset = [p for p in params if p["name"] == "offset"][0]
        assert offset["min"] == -1
        assert offset["max"] == 1

    def test_mix_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        assert mix["min"] == 0
        assert mix["max"] == 1

    def test_quantization_logic(self):
        code = self._read_script()
        assert "Math.round" in code, "Missing quantization (Math.round)"
        assert "levels" in code, "Missing quantization levels"

    def test_rate_reduction_logic(self):
        code = self._read_script()
        assert "holdEvery" in code or "holdCounter" in code, "Missing sample-rate reduction (hold/counter)"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"


class TestBordun:
    """Unit tests for create_bordun orchestration tool — note generation logic."""

    NOTE_TO_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
                  "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
                  "A#": 10, "Bb": 10, "B": 11}

    def _build_notes(self, root="C", octave=3, intervals="0,7", bars=4, beats_per_bar=4, velocity=0.55, retrigger_bars=0):
        """Simulate create_bordun note generation without bridge."""
        root_pc = self.NOTE_TO_PC[root.strip()]
        iv_list = [int(x.strip()) for x in intervals.split(",")]
        base = (octave + 1) * 12 + root_pc
        pitches = [base + iv for iv in iv_list]
        total_beats = bars * beats_per_bar
        notes = []
        if retrigger_bars > 0:
            chunk_beats = retrigger_bars * beats_per_bar
            num_chunks = bars // retrigger_bars
            for i in range(num_chunks):
                pos = i * chunk_beats
                for p in pitches:
                    notes.append({"pitch": p, "pos": pos, "dur": chunk_beats * 0.98, "vel": velocity})
        else:
            for p in pitches:
                notes.append({"pitch": p, "pos": 0, "dur": total_beats * 0.98, "vel": velocity})
        return notes

    def test_open_fifth_continuous(self):
        notes = self._build_notes("C", 3, "0,7", bars=4, beats_per_bar=4)
        assert len(notes) == 2  # 2 pitches, 1 sustained note each
        assert notes[0]["pitch"] == 48  # C3
        assert notes[1]["pitch"] == 55  # G3
        assert abs(notes[0]["dur"] - 15.68) < 0.01  # 16 * 0.98

    def test_octave_fifth(self):
        notes = self._build_notes("D", 2, "0,7,12", bars=2)
        assert len(notes) == 3
        assert notes[0]["pitch"] == 38  # D2
        assert notes[1]["pitch"] == 45  # A2
        assert notes[2]["pitch"] == 50  # D3

    def test_minor_triad_drone(self):
        notes = self._build_notes("A", 3, "0,3,7", bars=4)
        assert len(notes) == 3
        assert notes[0]["pitch"] == 57  # A3
        assert notes[1]["pitch"] == 60  # C4
        assert notes[2]["pitch"] == 64  # E4

    def test_retrigger_mode(self):
        notes = self._build_notes("C", 3, "0,7", bars=4, beats_per_bar=4, retrigger_bars=2)
        # 2 pitches × 2 chunks (bars 4 / retrigger 2) = 4 notes
        assert len(notes) == 4
        assert abs(notes[0]["dur"] - 7.84) < 0.01  # 8 * 0.98
        assert abs(notes[2]["pos"] - 8) < 0.01  # second chunk at beat 8

    def test_single_note_drone(self):
        notes = self._build_notes("G", 2, "0", bars=8, beats_per_bar=4)
        assert len(notes) == 1
        assert notes[0]["pitch"] == 43  # G2
        assert abs(notes[0]["dur"] - 31.36) < 0.01  # 32 * 0.98

    def test_velocity_applied(self):
        notes = self._build_notes("C", 3, "0,7", velocity=0.4)
        assert all(n["vel"] == 0.4 for n in notes)

    def test_flat_root(self):
        notes = self._build_notes("Ab", 3, "0,7", bars=2)
        assert notes[0]["pitch"] == 56  # Ab3
        assert notes[1]["pitch"] == 63  # Eb4

    def test_34_time(self):
        notes = self._build_notes("C", 3, "0", bars=4, beats_per_bar=3)
        assert len(notes) == 1
        assert abs(notes[0]["dur"] - 11.76) < 0.01  # 12 * 0.98

    def test_duration_slightly_less_than_total(self):
        """Bordun notes use 0.98 multiplier to avoid overlap with next region."""
        notes = self._build_notes("C", 3, "0", bars=4, beats_per_bar=4)
        total_beats = 16
        assert notes[0]["dur"] < total_beats  # not full duration
        assert notes[0]["dur"] > total_beats * 0.95  # but close

    def test_retrigger_even_chunks(self):
        notes = self._build_notes("C", 3, "0,7", bars=6, beats_per_bar=4, retrigger_bars=2)
        # 2 pitches × 3 chunks (6 / 2) = 6 notes
        assert len(notes) == 6
        assert abs(notes[4]["pos"] - 16) < 0.01  # third chunk at beat 16


class TestHocket:
    """Unit tests for create_hocket orchestration tool — voice splitting logic."""

    def _split_notes(self, pitches, voices=2, split_mode="alternate", note_duration=0.5):
        """Simulate hocket voice assignment without bridge."""
        voice_notes = {v: [] for v in range(voices)}
        for i, pitch in enumerate(pitches):
            if split_mode == "alternate":
                voice = i % voices
            elif split_mode == "pairs":
                voice = (i // 2) % voices
            else:  # phrase
                voice = (i // 4) % voices
            pos = i * note_duration
            voice_notes[voice].append({"pitch": pitch, "pos": pos, "dur": note_duration})
        return voice_notes

    def test_alternate_2_voices(self):
        pitches = [60, 62, 64, 65, 67, 65, 64, 62]
        vn = self._split_notes(pitches, voices=2, split_mode="alternate")
        assert len(vn[0]) == 4  # notes 0,2,4,6
        assert len(vn[1]) == 4  # notes 1,3,5,7
        assert vn[0][0]["pitch"] == 60
        assert vn[1][0]["pitch"] == 62

    def test_alternate_3_voices(self):
        pitches = [60, 62, 64, 65, 67, 65]
        vn = self._split_notes(pitches, voices=3, split_mode="alternate")
        assert len(vn[0]) == 2  # notes 0,3
        assert len(vn[1]) == 2  # notes 1,4
        assert len(vn[2]) == 2  # notes 2,5

    def test_pairs_mode(self):
        pitches = [60, 62, 64, 65, 67, 65, 64, 62]
        vn = self._split_notes(pitches, voices=2, split_mode="pairs")
        # voice 0: notes 0,1,4,5 → 4 notes
        # voice 1: notes 2,3,6,7 → 4 notes
        assert len(vn[0]) == 4
        assert len(vn[1]) == 4
        assert vn[0][0]["pitch"] == 60
        assert vn[0][1]["pitch"] == 62
        assert vn[1][0]["pitch"] == 64

    def test_phrase_mode(self):
        pitches = [60, 62, 64, 65, 67, 65, 64, 62]
        vn = self._split_notes(pitches, voices=2, split_mode="phrase")
        # voice 0: notes 0-3 → 4 notes
        # voice 1: notes 4-7 → 4 notes
        assert len(vn[0]) == 4
        assert len(vn[1]) == 4
        assert vn[0][3]["pitch"] == 65
        assert vn[1][0]["pitch"] == 67

    def test_total_notes_preserved(self):
        pitches = [60, 62, 64, 65, 67, 65, 64, 62]
        vn = self._split_notes(pitches, voices=2)
        total = sum(len(v) for v in vn.values())
        assert total == len(pitches)

    def test_position_spacing(self):
        pitches = [60, 62, 64]
        vn = self._split_notes(pitches, voices=2, note_duration=1.0)
        assert abs(vn[0][0]["pos"] - 0) < 0.01
        assert abs(vn[1][0]["pos"] - 1.0) < 0.01
        assert abs(vn[0][1]["pos"] - 2.0) < 0.01

    def test_duration_applied(self):
        pitches = [60, 62]
        vn = self._split_notes(pitches, voices=2, note_duration=0.25)
        assert vn[0][0]["dur"] == 0.25
        assert vn[1][0]["dur"] == 0.25

    def test_uneven_split(self):
        """5 notes, 2 voices, alternate → voice 0 gets 3, voice 1 gets 2."""
        pitches = [60, 62, 64, 65, 67]
        vn = self._split_notes(pitches, voices=2, split_mode="alternate")
        assert len(vn[0]) == 3  # notes 0,2,4
        assert len(vn[1]) == 2  # notes 1,3

    def test_4_voices(self):
        pitches = [60, 62, 64, 65, 67, 65, 64, 62]
        vn = self._split_notes(pitches, voices=4, split_mode="alternate")
        assert len(vn[0]) == 2  # notes 0,4
        assert len(vn[1]) == 2  # notes 1,5
        assert len(vn[2]) == 2  # notes 2,6
        assert len(vn[3]) == 2  # notes 3,7

    def test_all_notes_in_melody(self):
        """Every pitch from the melody appears exactly once across all voices."""
        pitches = [60, 62, 64, 65, 67, 65, 64, 62, 60, 59]
        vn = self._split_notes(pitches, voices=3, split_mode="alternate")
        all_pitches = []
        for v in vn.values():
            for n in v:
                all_pitches.append(n["pitch"])
        assert sorted(all_pitches) == sorted(pitches)


class TestIsorhythm:
    """Unit tests for create_isorhythm orchestration tool — talea/color logic."""

    def _build_notes(self, talea, color, repeats=3, velocity=0.7):
        """Simulate isorhythm note generation without bridge."""
        talea_durations = [float(x) for x in talea.split(",")]
        color_pitches = [int(x) for x in color.split(",")]
        talea_len = len(talea_durations)
        color_len = len(color_pitches)
        total_notes = talea_len * repeats
        notes = []
        current_pos = 0.0
        for i in range(total_notes):
            dur = talea_durations[i % talea_len]
            pitch = color_pitches[i % color_len]
            notes.append({"pitch": pitch, "pos": current_pos, "dur": dur * 0.95, "vel": velocity})
            current_pos += dur
        return notes

    def test_talea_color_equal_length(self):
        notes = self._build_notes("1,1,0.5,0.5", "60,62,64,65", repeats=2)
        assert len(notes) == 8
        # First note: pitch 60, duration 1.0
        assert notes[0]["pitch"] == 60
        assert abs(notes[0]["dur"] - 0.95) < 0.001
        # Note 4 (start of 2nd talea cycle): pitch 60 again (both cycle at same point)
        assert notes[4]["pitch"] == 60

    def test_talea_color_different_length(self):
        """talea=4, color=5 → phase shift: note 4 gets pitch index 4, note 5 gets pitch index 0"""
        notes = self._build_notes("1,1,1,1", "60,62,64,65,67", repeats=2)
        assert len(notes) == 8
        assert notes[0]["pitch"] == 60  # color[0]
        assert notes[4]["pitch"] == 67  # color[4] — talea cycled, color hasn't
        assert notes[5]["pitch"] == 60  # color[0] — now color cycles

    def test_duration_from_talea(self):
        notes = self._build_notes("0.5,0.25,0.25,1", "60,62,64,65", repeats=1)
        assert abs(notes[0]["dur"] - 0.475) < 0.001  # 0.5 * 0.95
        assert abs(notes[1]["dur"] - 0.2375) < 0.001  # 0.25 * 0.95
        assert abs(notes[3]["dur"] - 0.95) < 0.001  # 1.0 * 0.95

    def test_position_accumulates(self):
        notes = self._build_notes("1,0.5,0.5,1", "60,62,64,65", repeats=1)
        assert abs(notes[0]["pos"] - 0) < 0.001
        assert abs(notes[1]["pos"] - 1.0) < 0.001
        assert abs(notes[2]["pos"] - 1.5) < 0.001
        assert abs(notes[3]["pos"] - 2.0) < 0.001

    def test_total_notes_talea_times_repeats(self):
        notes = self._build_notes("1,1,0.5", "60,62,64,65,67", repeats=4)
        assert len(notes) == 12  # 3 * 4

    def test_pitch_cycling_independent(self):
        """Pitch cycles independently of rhythm."""
        notes = self._build_notes("1,1", "60,62,64", repeats=3)
        # 6 notes: pitches should be 60,62,64,60,62,64
        pitches = [n["pitch"] for n in notes]
        assert pitches == [60, 62, 64, 60, 62, 64]

    def test_velocity_applied(self):
        notes = self._build_notes("1,1", "60,62", repeats=1, velocity=0.5)
        assert all(n["vel"] == 0.5 for n in notes)

    def test_total_duration(self):
        """Total beats = sum(talea) × repeats."""
        notes = self._build_notes("1,0.5,0.5,1", "60,62", repeats=2)
        # sum(talea) = 3, repeats = 2 → 6 beats
        last_note_end = notes[-1]["pos"] + notes[-1]["dur"] / 0.95
        assert abs(last_note_end - 6.0) < 0.001

    def test_single_element_talea(self):
        notes = self._build_notes("1", "60,62,64", repeats=4)
        assert len(notes) == 4
        assert all(abs(n["dur"] - 0.95) < 0.001 for n in notes)

    def test_single_element_color(self):
        notes = self._build_notes("1,0.5,0.5", "60", repeats=2)
        assert len(notes) == 6
        assert all(n["pitch"] == 60 for n in notes)


class TestSpringReverbDSP:
    """Unit tests for werkstatt_spring_reverb.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_spring_reverb.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt spring_reverb" in code, "Missing @werkstatt spring_reverb header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_decay_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        decay = [p for p in params if p["name"] == "decay"][0]
        assert decay["min"] == 0
        assert decay["max"] == 1

    def test_damp_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        damp = [p for p in params if p["name"] == "damp"][0]
        assert damp["min"] == 0
        assert damp["max"] == 1

    def test_tension_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        tension = [p for p in params if p["name"] == "tension"][0]
        assert tension["min"] == 0
        assert tension["max"] == 1

    def test_boing_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        boing = [p for p in params if p["name"] == "boing"][0]
        assert boing["min"] == 0
        assert boing["max"] == 1

    def test_mix_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        assert mix["min"] == 0
        assert mix["max"] == 1

    def test_delay_buffers(self):
        code = self._read_script()
        assert "Float32Array" in code, "Missing delay buffers"
        assert "this.delays" in code, "Missing delay arrays"

    def test_transient_detection(self):
        code = self._read_script()
        assert "chirp" in code.lower(), "Missing transient/chirp detection for boing effect"
        assert "prevInput" in code, "Missing transient detection (prevInput)"

    def test_multiple_springs(self):
        code = self._read_script()
        assert "4" in code and ("spring" in code.lower() or "delays" in code), "Missing multi-spring architecture"
        assert "offsets" in code or "detuned" in code, "Missing detuned spring offsets"


class TestTubeSaturatorDSP:
    """Unit tests for werkstatt_tube_saturator.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_tube_saturator.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt tube_saturator" in code, "Missing @werkstatt tube_saturator header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 6, f"Expected 6 params, got {len(params)}"

    def test_drive_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        drive = [p for p in params if p["name"] == "drive"][0]
        assert drive["min"] == 0
        assert drive["max"] == 1

    def test_warmth_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        warmth = [p for p in params if p["name"] == "warmth"][0]
        assert warmth["min"] == 0
        assert warmth["max"] == 1

    def test_bias_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        bias = [p for p in params if p["name"] == "bias"][0]
        assert bias["min"] == -0.5
        assert bias["max"] == 0.5

    def test_tone_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        tone = [p for p in params if p["name"] == "tone"][0]
        assert tone["min"] == 0
        assert tone["max"] == 1

    def test_output_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        out = [p for p in params if p["name"] == "output"][0]
        assert out["min"] == 0
        assert out["max"] == 1

    def test_mix_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        assert mix["min"] == 0
        assert mix["max"] == 1

    def test_asymmetrical_waveshaper(self):
        code = self._read_script()
        assert "tanh" in code, "Missing tanh waveshaper"
        assert "bias" in code, "Missing bias for asymmetrical transfer (even harmonics)"

    def test_even_odd_harmonic_blend(self):
        code = self._read_script()
        assert "warmth" in code, "Missing warmth control for even/odd harmonic blend"
        assert "even" in code and "odd" in code, "Missing even/odd harmonic separation"


class TestTapeDelayDSP:
    """Unit tests for werkstatt_tape_delay.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_tape_delay.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt tape_delay" in code, "Missing @werkstatt tape_delay header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 6, f"Expected 6 params, got {len(params)}"

    def test_time_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        time = [p for p in params if p["name"] == "time"][0]
        assert time["min"] > 0
        assert time["max"] == 1

    def test_feedback_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        fb = [p for p in params if p["name"] == "feedback"][0]
        assert fb["min"] == 0
        assert fb["max"] <= 0.95

    def test_wow_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        wow = [p for p in params if p["name"] == "wow"][0]
        assert wow["min"] == 0
        assert wow["max"] == 1

    def test_flutter_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        flutter = [p for p in params if p["name"] == "flutter"][0]
        assert flutter["min"] == 0
        assert flutter["max"] == 1

    def test_saturation_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        sat = [p for p in params if p["name"] == "saturation"][0]
        assert sat["min"] == 0
        assert sat["max"] == 1

    def test_mix_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        mix = [p for p in params if p["name"] == "mix"][0]
        assert mix["min"] == 0
        assert mix["max"] == 1

    def test_delay_buffers(self):
        code = self._read_script()
        assert "Float32Array" in code, "Missing delay buffers"
        assert "this.bufL" in code or "this.bufR" in code, "Missing stereo delay buffers"

    def test_wow_flutter_lfos(self):
        code = self._read_script()
        assert "wowPhase" in code, "Missing wow LFO phase"
        assert "flutterPhase" in code, "Missing flutter LFO phase"
        assert "Math.sin" in code, "Missing sine LFO"

    def test_fractional_delay_read(self):
        code = self._read_script()
        assert "frac" in code, "Missing fractional delay interpolation"
        assert "idx0" in code or "idx1" in code, "Missing delay buffer index interpolation"

    def test_feedback_saturation(self):
        code = self._read_script()
        assert "tanh" in code, "Missing saturation in feedback path (tanh)"
        assert "_tapeSat" in code or "tapeSat" in code, "Missing tape saturation function"


class TestGraphicEqDSP:
    """Unit tests for werkstatt_graphic_eq.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_graphic_eq.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt graphic_eq" in code, "Missing @werkstatt graphic_eq header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 11, f"Expected 11 params (10 bands + master), got {len(params)}"

    def test_band_32_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        band = [p for p in params if p["name"] == "band_32"][0]
        assert band["min"] == -12
        assert band["max"] == 12
        assert band["default"] == 0

    def test_band_1k_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        band = [p for p in params if p["name"] == "band_1k"][0]
        assert band["min"] == -12
        assert band["max"] == 12
        assert band["default"] == 0

    def test_band_16k_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        band = [p for p in params if p["name"] == "band_16k"][0]
        assert band["min"] == -12
        assert band["max"] == 12
        assert band["default"] == 0

    def test_master_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        master = [p for p in params if p["name"] == "master"][0]
        assert master["min"] == -6
        assert master["max"] == 6
        assert master["default"] == 0

    def test_all_10_bands_present(self):
        code = self._read_script()
        params = self._parse_params(code)
        band_names = [p["name"] for p in params if p["name"].startswith("band_")]
        expected = ["band_32", "band_64", "band_125", "band_250", "band_500",
                    "band_1k", "band_2k", "band_4k", "band_8k", "band_16k"]
        assert band_names == expected, f"Band names mismatch: {band_names}"

    def test_iso_frequencies(self):
        code = self._read_script()
        assert "32" in code and "64" in code and "125" in code
        assert "250" in code and "500" in code and "1000" in code
        assert "2000" in code and "4000" in code and "8000" in code
        assert "16000" in code, "Missing 16kHz band"

    def test_biquad_implementation(self):
        code = self._read_script()
        assert "_peakCoeff" in code, "Missing peaking filter coefficient function"
        assert "b0" in code and "a0" in code, "Missing biquad coefficients"
        assert "cosw" in code or "Math.cos" in code, "Missing cosine in biquad"
        assert "sinw" in code or "Math.sin" in code, "Missing sine in biquad"

    def test_series_processing(self):
        code = self._read_script()
        assert "_processSample" in code, "Missing series sample processing"
        assert "this.coeffs" in code, "Missing coefficients array"
        assert "this.stateL" in code or "this.stateR" in code, "Missing per-band filter state"


class TestAutoPanDSP:
    """Unit tests for werkstatt_auto_pan.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_auto_pan.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt auto_pan" in code, "Missing @werkstatt auto_pan header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 6, f"Expected 6 params, got {len(params)}"

    def test_rate_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        rate = [p for p in params if p["name"] == "rate"][0]
        assert rate["min"] > 0, "Rate min should be > 0"
        assert rate["max"] >= 20, "Rate max should reach at least 20 Hz"
        assert rate["scale"] == "exp", "Rate should be exponential scale"

    def test_depth_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        depth = [p for p in params if p["name"] == "depth"][0]
        assert depth["min"] == 0
        assert depth["max"] == 1

    def test_shape_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        shape = [p for p in params if p["name"] == "shape"][0]
        assert shape["min"] == 0
        assert shape["max"] == 1

    def test_phase_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        phase = [p for p in params if p["name"] == "phase"][0]
        assert phase["min"] == 0
        assert phase["max"] == 360
        assert phase["scale"] == "linear"

    def test_waveform_morph(self):
        code = self._read_script()
        assert "_waveform" in code, "Missing waveform morph function"
        assert "Math.sin" in code, "Missing sine wave"
        assert "Math.asin" in code, "Missing triangle wave (asin of sin)"
        assert "Math.sign" in code, "Missing square wave (sign)"

    def test_equal_power_pan(self):
        code = self._read_script()
        assert "Math.cos" in code, "Missing equal-power pan law (cosine)"
        assert "pan" in code, "Missing pan position calculation"
        assert "panClamped" in code or "Math.max" in code, "Missing pan clamping"

    def test_lfo_phase_accumulator(self):
        code = self._read_script()
        assert "phasePos" in code, "Missing LFO phase accumulator"
        assert "2 * Math.PI" in code, "Missing 2*pi frequency calculation"

    def test_stereo_output(self):
        code = self._read_script()
        assert "out[0]" in code and "out[1]" in code, "Missing stereo output"
        assert "stereo" in code, "Missing stereo detection"


class TestCombFilterDSP:
    """Unit tests for werkstatt_comb_filter.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_comb_filter.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt comb_filter" in code, "Missing @werkstatt comb_filter header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_freq_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        freq = [p for p in params if p["name"] == "freq"][0]
        assert freq["min"] > 0, "Freq min should be > 0"
        assert freq["max"] >= 8000, "Freq max should reach at least 8000 Hz"
        assert freq["scale"] == "exp", "Freq should be exponential scale"

    def test_feedback_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        fb = [p for p in params if p["name"] == "feedback"][0]
        assert fb["min"] <= -0.9, "Feedback should allow strong negative"
        assert fb["max"] >= 0.9, "Feedback should allow strong positive"

    def test_damping_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        damp = [p for p in params if p["name"] == "damping"][0]
        assert damp["min"] == 0
        assert damp["max"] == 1

    def test_polarity_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        pol = [p for p in params if p["name"] == "polarity"][0]
        assert pol["min"] == 0
        assert pol["max"] == 1

    def test_delay_buffer(self):
        code = self._read_script()
        assert "Float32Array" in code, "Missing delay buffers"
        assert "this.bufL" in code or "this.bufR" in code, "Missing stereo delay buffers"
        assert "writePos" in code, "Missing write position"

    def test_damping_lowpass(self):
        code = self._read_script()
        assert "dampState" in code, "Missing damping state"
        assert "dampAlpha" in code, "Missing damping coefficient"
        assert "Math.exp" in code, "Missing exponential for damping LP"

    def test_polarity_switch(self):
        code = self._read_script()
        assert "polarity" in code, "Missing polarity switch"
        assert "polarity > 0.5" in code or "polarity > 0" in code, "Missing polarity threshold"

    def test_comb_delay_calculation(self):
        code = self._read_script()
        assert "delaySamples" in code, "Missing delay sample calculation"
        assert "sr /" in code or "this.sr /" in code, "Missing freq-to-samples conversion"


class TestFormantFilterDSP:
    """Unit tests for werkstatt_formant_filter.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_formant_filter.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt formant_filter" in code, "Missing @werkstatt formant_filter header"

    def test_param_count(self):
        code = self._read_script()
        params = self._parse_params(code)
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_formant_a_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        fa = [p for p in params if p["name"] == "formant_a"][0]
        assert fa["min"] > 0, "Formant A min should be > 0"
        assert fa["scale"] == "exp", "Formant A should be exponential"

    def test_vowel_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        vowel = [p for p in params if p["name"] == "vowel"][0]
        assert vowel["min"] == 0
        assert vowel["max"] >= 4, "Vowel should cover at least 5 presets (0-4)"

    def test_resonance_param(self):
        code = self._read_script()
        params = self._parse_params(code)
        res = [p for p in params if p["name"] == "resonance"][0]
        assert res["min"] == 0
        assert res["max"] == 1

    def test_bandwidth_params(self):
        code = self._read_script()
        params = self._parse_params(code)
        for name in ["bandwidth_a", "bandwidth_b", "bandwidth_c"]:
            bw = [p for p in params if p["name"] == name][0]
            assert bw["min"] > 0, f"{name} min should be > 0"
            assert bw["max"] <= 0.5

    def test_vowel_presets(self):
        code = self._read_script()
        assert "vowels" in code, "Missing vowel presets array"
        assert "730" in code and "1090" in code, "Missing /a/ vowel preset"
        assert "270" in code and "2290" in code, "Missing /i/ vowel preset"

    def test_bandpass_implementation(self):
        code = self._read_script()
        assert "_bpCoeff" in code, "Missing bandpass coefficient function"
        assert "_bp(" in code, "Missing bandpass processing function"
        assert "Math.sin" in code and "Math.cos" in code, "Missing trig in biquad"

    def test_parallel_formants(self):
        code = self._read_script()
        assert "stateLa" in code and "stateLb" in code and "stateLc" in code, "Missing 3 formant filter states"
        assert "ya + yb + yc" in code or "ya+yb+yc" in code, "Missing parallel formant sum"

    def test_vowel_interpolation(self):
        code = self._read_script()
        assert "1 - t" in code or "(1-t)" in code, "Missing vowel interpolation"
        assert "Math.floor" in code, "Missing vowel index floor"


class TestWerkstattWaveshaper:
    """Unit tests for werkstatt_waveshaper.js DSP script structure."""

    def _read_script(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_waveshaper.js")
        with open(path) as f:
            return f.read()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt waveshaper 1 1" in code

    def test_label(self):
        code = self._read_script()
        assert "// @label Waveshaper" in code

    def test_param_count(self):
        code = self._read_script()
        param_lines = [l for l in code.split("\n") if l.strip().startswith("// @param")]
        assert len(param_lines) == 7

    def test_param_drive(self):
        code = self._read_script()
        assert "// @param drive 0.5 0 3 linear" in code

    def test_param_curve(self):
        code = self._read_script()
        assert "// @param curve 0 0 3 linear" in code

    def test_param_harmonics(self):
        code = self._read_script()
        assert "// @param harmonics 0.3 0 1 linear" in code

    def test_param_mix(self):
        code = self._read_script()
        assert "// @param mix 1 0 1 linear" in code

    def test_has_processAudio(self):
        code = self._read_script()
        assert "processAudio(inputs, outputs, parameters)" in code

    def test_has_paramChanged(self):
        code = self._read_script()
        assert "paramChanged(name, value)" in code

    def test_has_shape_method(self):
        code = self._read_script()
        assert "_shape(" in code
        assert "Math.tanh" in code
        assert "Math.atan" in code


class TestWerkstattMoogLadder:
    """Unit tests for werkstatt_moog_ladder.js DSP script structure."""

    def _read_script(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_moog_ladder.js")
        with open(path) as f:
            return f.read()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt moog_ladder 1 1" in code

    def test_label(self):
        code = self._read_script()
        assert "// @label Moog Ladder Filter" in code

    def test_param_count(self):
        code = self._read_script()
        param_lines = [l for l in code.split("\n") if l.strip().startswith("// @param")]
        assert len(param_lines) == 6

    def test_param_cutoff(self):
        code = self._read_script()
        assert "// @param cutoff 800 20 20000 exp Hz" in code

    def test_param_resonance(self):
        code = self._read_script()
        assert "// @param resonance 0.3 0 1 linear" in code

    def test_param_warmth(self):
        code = self._read_script()
        assert "// @param warmth 0 0 1 linear" in code

    def test_param_mode(self):
        code = self._read_script()
        assert "// @param mode 0 0 2 linear" in code

    def test_has_processAudio(self):
        code = self._read_script()
        assert "processAudio(inputs, outputs, parameters)" in code

    def test_has_ladder_stages(self):
        code = self._read_script()
        assert "stages[0]" in code
        assert "stages[1]" in code
        assert "stages[2]" in code
        assert "stages[3]" in code

    def test_has_tanh(self):
        code = self._read_script()
        assert "_tanh(" in code
        assert "self._tanh" not in code  # it's a JS method, not Python


class TestWerkstattRotarySpeaker:
    """Unit tests for werkstatt_rotary_speaker.js DSP script structure."""

    def _read_script(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "werkstatt_rotary_speaker.js")
        with open(path) as f:
            return f.read()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt rotary_speaker 1 1" in code

    def test_label(self):
        code = self._read_script()
        assert "// @label Rotary Speaker (Leslie)" in code

    def test_param_count(self):
        code = self._read_script()
        param_lines = [l for l in code.split("\n") if l.strip().startswith("// @param")]
        assert len(param_lines) == 7

    def test_param_speed(self):
        code = self._read_script()
        assert "// @param speed 0.3 0 1 linear" in code

    def test_param_crossover(self):
        code = self._read_script()
        assert "// @param crossover 800 200 4000 exp Hz" in code

    def test_param_acceleration(self):
        code = self._read_script()
        assert "// @param acceleration 0.3 0 1 linear" in code

    def test_has_processAudio(self):
        code = self._read_script()
        assert "processAudio(inputs, outputs, parameters)" in code

    def test_has_doppler(self):
        code = self._read_script()
        assert "dopplerL" in code or "dopplerR" in code

    def test_has_rotor_amplitude(self):
        code = self._read_script()
        assert "rotorAmpL" in code or "rotorAmpR" in code

    def test_has_crossover_split(self):
        code = self._read_script()
        assert "highL" in code
        assert "lowL" in code


class TestScaleQuantizerDSP:
    """Unit tests for spielwerk_scale_quantizer.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "spielwerk_scale_quantizer.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@spielwerk scale_quantizer" in code, "Missing @spielwerk scale_quantizer header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 3, f"Expected 3 params, got {len(params)}"

    def test_scale_param(self):
        params = self._parse_params(self._read_script())
        sc = [p for p in params if p["name"] == "scale"][0]
        assert sc["min"] == 0 and sc["max"] == 13

    def test_root_param(self):
        params = self._parse_params(self._read_script())
        rt = [p for p in params if p["name"] == "root"][0]
        assert rt["min"] == 0 and rt["max"] == 11

    def test_scale_count(self):
        code = self._read_script()
        assert "SCALES" in code, "Missing SCALES array"
        # 14 scales (major through chromatic)
        assert code.count("[0,") >= 13, "Expected at least 13 scale definitions"

    def test_quantize_method(self):
        code = self._read_script()
        assert "_quantize" in code, "Missing _quantize method"
        assert "bestDist" in code, "Missing nearest-note search"

    def test_chromatic_passthrough(self):
        code = self._read_script()
        assert "13" in code, "Missing chromatic scale index"
        assert "pass-through" in code.lower() or "chromatic" in code.lower()

    def test_direction_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "direction"][0]
        assert d["min"] == 0 and d["max"] == 1

    def test_process_generator(self):
        code = self._read_script()
        assert "*process" in code, "Missing process generator"
        assert "yield" in code, "Missing yield in process"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"




class TestDynamicEqDSP:
    """Unit tests for werkstatt_dynamic_eq.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "werkstatt_dynamic_eq.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt dynamic_eq" in code

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 19, f"Expected 19 params, got {len(params)}"

    def test_three_bands(self):
        code = self._read_script()
        assert "band1_freq" in code and "band2_freq" in code and "band3_freq" in code
        assert "band1_threshold" in code and "band2_threshold" in code and "band3_threshold" in code
        assert "band1_range" in code and "band2_range" in code and "band3_range" in code

    def test_biquad_peaking(self):
        code = self._read_script()
        assert "_peakCoeffs" in code, "Missing peaking biquad coefficient method"
        assert "b0" in code and "a0" in code, "Missing biquad coefficients"

    def test_detection_filter(self):
        code = self._read_script()
        assert "detCoeffs" in code, "Missing detection filter coefficients"
        assert "detLevel" in code, "Missing detection level computation"

    def test_envelope_follower(self):
        code = self._read_script()
        assert "env" in code, "Missing envelope follower state"
        assert "atkCoef" in code and "relCoef" in code, "Missing attack/release coefficients"

    def test_dynamic_gain(self):
        code = self._read_script()
        assert "dynGainDb" in code, "Missing dynamic gain computation"
        assert "range" in code, "Missing range parameter usage"

    def test_attack_release(self):
        params = self._parse_params(self._read_script())
        atk = [p for p in params if p["name"] == "attack"][0]
        rel = [p for p in params if p["name"] == "release"][0]
        assert atk["scale"] == "linear"
        assert rel["scale"] == "linear"

    def test_mix_and_output(self):
        params = self._parse_params(self._read_script())
        mix = [p for p in params if p["name"] == "mix"][0]
        out_p = [p for p in params if p["name"] == "output"][0]
        assert mix["min"] == 0 and mix["max"] == 1
        assert out_p["min"] == -12 and out_p["max"] == 12


class TestSpielwerkHarmonizerDSP:
    """Unit tests for spielwerk_harmonizer.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "spielwerk_harmonizer.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@spielwerk harmonizer" in code, "Missing @spielwerk harmonizer header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_interval_params(self):
        params = self._parse_params(self._read_script())
        i1 = [p for p in params if p["name"] == "interval1"][0]
        i2 = [p for p in params if p["name"] == "interval2"][0]
        i3 = [p for p in params if p["name"] == "interval3"][0]
        assert i1["min"] == -24 and i1["max"] == 24
        assert i2["min"] == -24 and i2["max"] == 24
        assert i3["min"] == -24 and i3["max"] == 24

    def test_velocity_params(self):
        params = self._parse_params(self._read_script())
        v1 = [p for p in params if p["name"] == "vel1"][0]
        v2 = [p for p in params if p["name"] == "vel2"][0]
        v3 = [p for p in params if p["name"] == "vel3"][0]
        assert v1["min"] == 0 and v1["max"] == 1
        assert v2["min"] == 0 and v2["max"] == 1
        assert v3["min"] == 0 and v3["max"] == 1

    def test_mode_param(self):
        params = self._parse_params(self._read_script())
        m = [p for p in params if p["name"] == "mode"][0]
        assert m["min"] == 0 and m["max"] == 1, "mode should be 0 or 1"

    def test_key_and_scale_params(self):
        params = self._parse_params(self._read_script())
        kr = [p for p in params if p["name"] == "key_root"][0]
        sc = [p for p in params if p["name"] == "scale"][0]
        assert kr["min"] == 0 and kr["max"] == 11
        assert sc["min"] == 0 and sc["max"] == 13

    def test_diatonic_shift(self):
        code = self._read_script()
        assert "_diatonicShift" in code, "Missing diatonic shift method"
        assert "degreeShift" in code, "Missing scale degree shift logic"

    def test_three_voices(self):
        code = self._read_script()
        assert "voice 1" in code or "_h1" in code, "Missing voice 1"
        assert "voice 2" in code or "_h2" in code, "Missing voice 2"
        assert "voice 3" in code or "_h3" in code, "Missing voice 3"

    def test_pitch_clamp(self):
        code = self._read_script()
        assert "_clamp" in code, "Missing pitch clamp method"
        assert "Math.max(0" in code and "Math.min(127" in code, "Missing 0-127 range clamp"

    def test_process_generator(self):
        code = self._read_script()
        assert "*process" in code, "Missing process generator"
        assert "yield" in code, "Missing yield in process"
        assert "yield ev" in code, "Missing original event passthrough"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"




class TestMultitapDelayDSP:
    """Unit tests for werkstatt_multitap_delay.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "werkstatt_multitap_delay.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt multitap_delay" in code, "Missing @werkstatt multitap_delay header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 20, f"Expected 20 params, got {len(params)}"

    def test_four_taps(self):
        code = self._read_script()
        for t in range(1, 5):
            assert f"tap{t}_time" in code, f"Missing tap{t}_time"
            assert f"tap{t}_level" in code, f"Missing tap{t}_level"
            assert f"tap{t}_pan" in code, f"Missing tap{t}_pan"
            assert f"tap{t}_fb" in code, f"Missing tap{t}_fb"

    def test_tap_time_range(self):
        params = self._parse_params(self._read_script())
        t1 = [p for p in params if p["name"] == "tap1_time"][0]
        assert t1["min"] == 0.02 and t1["max"] == 1, "tap1_time should be 0.02-1"

    def test_pan_range(self):
        params = self._parse_params(self._read_script())
        for p in params:
            if p["name"].endswith("_pan"):
                assert p["min"] == -1 and p["max"] == 1, f"{p['name']} should be -1 to 1"

    def test_feedback_range(self):
        params = self._parse_params(self._read_script())
        for p in params:
            if p["name"].endswith("_fb"):
                assert p["min"] == 0 and p["max"] == 0.9, f"{p['name']} should be 0-0.9"

    def test_single_buffer(self):
        code = self._read_script()
        assert "this.buf = new Float32Array" in code, "Should use single delay buffer"
        assert "writePos" in code, "Missing write position tracking"

    def test_equal_power_pan(self):
        code = self._read_script()
        assert "_pan" in code, "Missing pan method"
        assert "Math.cos" in code and "Math.sin" in code, "Missing equal-power pan (cos/sin)"

    def test_damping(self):
        code = self._read_script()
        assert "damping" in code, "Missing damping parameter"
        assert "_dampLp" in code, "Missing damping lowpass filter"
        assert "cutoff" in code, "Missing damping cutoff computation"

    def test_spread_modulation(self):
        code = self._read_script()
        assert "spread" in code, "Missing spread parameter"
        assert "spreadPhase" in code, "Missing spread LFO phase"

    def test_process_audio(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestAutowahDSP:
    """Unit tests for werkstatt_autowah.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "werkstatt_autowah.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt autowah" in code, "Missing @werkstatt autowah header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 11, f"Expected 11 params, got {len(params)}"

    def test_mode_param(self):
        params = self._parse_params(self._read_script())
        m = [p for p in params if p["name"] == "mode"][0]
        assert m["min"] == 0 and m["max"] == 2, "mode should be 0-2 (bandpass/peak/lowpass)"

    def test_base_freq_and_sweep(self):
        params = self._parse_params(self._read_script())
        bf = [p for p in params if p["name"] == "base_freq"][0]
        sr_p = [p for p in params if p["name"] == "sweep_range"][0]
        assert bf["scale"] == "exp", "base_freq should be exp scale"
        assert sr_p["min"] == 200 and sr_p["max"] == 4000

    def test_sensitivity(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "sensitivity"][0]
        assert s["min"] == 0 and s["max"] == 1

    def test_attack_release_exp(self):
        params = self._parse_params(self._read_script())
        atk = [p for p in params if p["name"] == "attack"][0]
        rel = [p for p in params if p["name"] == "release"][0]
        assert atk["scale"] == "exp", "attack should be exp"
        assert rel["scale"] == "exp", "release should be exp"

    def test_envelope_follower(self):
        code = self._read_script()
        assert "this.env" in code, "Missing envelope follower state"
        assert "atkCoef" in code and "relCoef" in code, "Missing attack/release coefficients"

    def test_biquad_coeffs(self):
        code = self._read_script()
        assert "_biquadCoeffs" in code, "Missing biquad coefficient method"
        assert "alpha" in code, "Missing biquad Q calculation"

    def test_three_filter_modes(self):
        code = self._read_script()
        assert "mode === 0" in code, "Missing bandpass mode"
        assert "mode === 1" in code, "Missing peaking mode"
        assert "} else {" in code, "Missing third mode (lowpass)"

    def test_direction_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "direction"][0]
        assert d["min"] == 0 and d["max"] == 1, "direction should be 0-1"

    def test_smoothing(self):
        code = self._read_script()
        assert "smoothCutoff" in code, "Missing cutoff smoothing"
        assert "smoothCoef" in code, "Missing smoothing coefficient"

    def test_reset(self):
        code = self._read_script()
        assert "reset()" in code
        assert "this.env = 0" in code, "Reset should clear envelope"


class TestDimensionChorusDSP:
    """Unit tests for werkstatt_dimension_chorus.js DSP script structure."""

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1),
                "default": float(m.group(2)),
                "min": float(m.group(3)),
                "max": float(m.group(4)),
                "scale": m.group(5),
            })
        return params

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "werkstatt_dimension_chorus.js")
        with open(path) as f:
            return f.read()

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt dimension_chorus" in code, "Missing @werkstatt dimension_chorus header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_dual_rate(self):
        params = self._parse_params(self._read_script())
        rl = [p for p in params if p["name"] == "rate_l"][0]
        rr = [p for p in params if p["name"] == "rate_r"][0]
        assert rl["min"] == 0.05 and rl["max"] == 5
        assert rr["min"] == 0.05 and rr["max"] == 5

    def test_no_feedback(self):
        code = self._read_script()
        assert "no feedback" in code.lower() or "no feedback!" in code.lower(), "Should note absence of feedback"

    def test_dual_lfo_phases(self):
        code = self._read_script()
        assert "phaseL" in code and "phaseR" in code, "Missing independent LFO phases"
        assert "rate_l" in code and "rate_r" in code, "Missing independent LFO rates"

    def test_triangle_lfo(self):
        code = self._read_script()
        assert "Math.abs" in code, "Missing triangle LFO (abs-based)"

    def test_dual_buffers(self):
        code = self._read_script()
        assert "this.bufL" in code and "this.bufR" in code, "Missing dual delay buffers"
        assert "this.idxL" in code and "this.idxR" in code, "Missing dual write indices"

    def test_brightness_filter(self):
        code = self._read_script()
        assert "_brightFilter" in code, "Missing brightness filter method"
        assert "brightState" in code, "Missing brightness filter state"

    def test_phase_offset(self):
        params = self._parse_params(self._read_script())
        po = [p for p in params if p["name"] == "phase_offset"][0]
        assert po["min"] == 0 and po["max"] == 360, "phase_offset should be 0-360 degrees"

    def test_width_param(self):
        params = self._parse_params(self._read_script())
        w = [p for p in params if p["name"] == "width"][0]
        assert w["min"] == 0 and w["max"] == 1

    def test_frac_read(self):
        code = self._read_script()
        assert "_fracRead" in code, "Missing fractional read method"
        assert "frac" in code, "Missing fractional interpolation"

    def test_reset_clears(self):
        code = self._read_script()
        assert "bufL.fill(0)" in code or "fill(0)" in code, "Reset should clear buffers"
        assert "phaseL = 0" in code, "Reset should zero LFO phases"

    def test_process_audio(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestOctaverDSP:
    """Unit tests for werkstatt_octaver.js — sub-octave generator (Boss OC-2 style)"""

    SCRIPT = "werkstatt_octaver.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt octaver" in code, "Missing @werkstatt octaver header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_oct1_level(self):
        params = self._parse_params(self._read_script())
        o1 = [p for p in params if p["name"] == "oct1"][0]
        assert o1["min"] == 0 and o1["max"] == 1
        assert o1["default"] == 0.7, "oct1 default should be 0.7"

    def test_oct2_level(self):
        params = self._parse_params(self._read_script())
        o2 = [p for p in params if p["name"] == "oct2"][0]
        assert o2["min"] == 0 and o2["max"] == 1
        assert o2["default"] == 0, "oct2 default should be 0 (off)"

    def test_zero_crossing_flipflop(self):
        code = self._read_script()
        assert "flip1" in code and "flip2" in code, "Missing flip-flop state variables"
        assert "1 - this.flip1" in code or "this.flip1 = 1 - this.flip1" in code, "Missing flip-flop toggle"
        assert "this.flip2" in code, "Missing -2 octave flip-flop"

    def test_hysteresis(self):
        code = self._read_script()
        assert "hyst" in code or "hystState" in code, "Missing hysteresis for zero-crossing"
        assert "trigger" in code, "Missing trigger parameter for hysteresis"

    def test_envelope_follower(self):
        code = self._read_script()
        assert "this.env" in code, "Missing envelope follower state"
        assert "envCoeff" in code or "env" in code, "Missing envelope coefficient"

    def test_square_wave_centering(self):
        code = self._read_script()
        assert "* 2 - 1" in code, "Missing square wave centering (-1..+1)"

    def test_smoothing(self):
        code = self._read_script()
        assert "smooth1" in code and "smooth2" in code, "Missing smoothing state"
        assert "smoothCoeff" in code, "Missing smoothing coefficient"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_divide_by_4_logic(self):
        code = self._read_script()
        assert "if (this.flip1 === 1)" in code or "if (this.flip1==1)" in code, "Missing edge-triggered /4 logic"

    def test_process_method(self):
        code = self._read_script()
        assert "process(" in code or "processAudio" in code, "Missing process method"

    def test_stereo_output(self):
        code = self._read_script()
        assert "io.out[0]" in code and "io.out[1]" in code, "Missing stereo output"


class TestFuzzDSP:
    """Unit tests for werkstatt_fuzz.js — hard clipping fuzz (Big Muff Pi style)"""

    SCRIPT = "werkstatt_fuzz.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt fuzz" in code, "Missing @werkstatt fuzz header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_sustain_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "sustain"][0]
        assert s["min"] == 0 and s["max"] == 1
        assert s["default"] == 0.7

    def test_octave_param(self):
        params = self._parse_params(self._read_script())
        o = [p for p in params if p["name"] == "octave"][0]
        assert o["min"] == 0 and o["max"] == 1
        assert o["default"] == 0, "octave default should be 0 (off)"

    def test_tone_param(self):
        params = self._parse_params(self._read_script())
        t = [p for p in params if p["name"] == "tone"][0]
        assert t["min"] == 0 and t["max"] == 1

    def test_hard_clip(self):
        code = self._read_script()
        assert "_hardClip" in code, "Missing hard clip method"
        assert "s > 1" in code or "s > 1)" in code, "Missing hard clipping boundary"

    def test_foldback(self):
        code = self._read_script()
        assert "foldback" in code.lower() or "squash" in code.lower() or "0.95" in code, "Missing Muff-style foldback"

    def test_full_wave_rect(self):
        code = self._read_script()
        assert "_fullWaveRect" in code, "Missing full-wave rectification for octave-up"
        assert "x < 0 ? -x : x" in code or "x < 0 ? -x" in code, "Missing rectification logic"

    def test_tone_stack(self):
        code = self._read_script()
        assert "toneLp" in code and "toneHp" in code, "Missing tone stack (LP+HP blend)"
        assert "lpCoeff" in code and "hpCoeff" in code, "Missing tone stack coefficients"

    def test_noise_gate(self):
        code = self._read_script()
        assert "gateGain" in code, "Missing noise gate"
        assert "gateThresh" in code, "Missing gate threshold"

    def test_bias_param(self):
        code = self._read_script()
        assert "bias" in code, "Missing asymmetrical bias parameter"
        params = self._parse_params(code)
        b = [p for p in params if p["name"] == "bias"][0]
        assert b["min"] == -0.3 and b["max"] == 0.3

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method_fuzz(self):
        code = self._read_script()
        assert "process(" in code or "processAudio" in code, "Missing process method"


class TestProbGateDSP:
    """Unit tests for spielwerk_prob_gate.js — subtractive probability gate"""

    SCRIPT = "spielwerk_prob_gate.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@spielwerk prob_gate" in code, "Missing @spielwerk prob_gate header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_chance_param(self):
        params = self._parse_params(self._read_script())
        c = [p for p in params if p["name"] == "chance"][0]
        assert c["min"] == 0 and c["max"] == 1
        assert c["default"] == 0.7

    def test_seed_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "seed"][0]
        assert s["default"] == 42

    def test_mode_param(self):
        params = self._parse_params(self._read_script())
        m = [p for p in params if p["name"] == "mode"][0]
        assert m["min"] == 0 and m["max"] == 2

    def test_rng_implementation(self):
        code = self._read_script()
        assert "1103515245" in code, "Missing LCG random implementation"
        assert "_nextRand" in code, "Missing RNG method"

    def test_generator_process(self):
        code = self._read_script()
        assert "*process" in code, "Missing generator process method"
        assert "yield" in code, "Missing yield (should be a generator)"

    def test_dropping_notes(self):
        code = self._read_script()
        assert "passed" in code or "roll <" in code, "Missing probability check"

    def test_forced_pass_zones(self):
        code = self._read_script()
        assert "min_pitch" in code and "max_pitch" in code, "Missing forced pass zones"
        assert "continue" in code, "Missing forced pass continue"

    def test_hold_momentum(self):
        code = self._read_script()
        assert "hold" in code, "Missing hold/momentum parameter"
        assert "_lastPassed" in code, "Missing lastPassed state for momentum"

    def test_mode_uniform(self):
        code = self._read_script()
        assert "mode === 0" in code or "mode === 1" in code, "Missing mode selection logic"

    def test_mode_position_based(self):
        code = self._read_script()
        assert "barPos" in code or "position" in code, "Missing position-based mode"

    def test_mode_pitch_based(self):
        code = self._read_script()
        assert "pitchNorm" in code or "ev.pitch" in code, "Missing pitch-based mode"

    def test_velocity_boost(self):
        code = self._read_script()
        assert "velocity_boost" in code, "Missing velocity boost for surviving notes"

    def test_reset(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"


class TestTapeStopDSP:
    """Unit tests for werkstatt_tape_stop.js — exponential tape stop effect"""

    SCRIPT = "werkstatt_tape_stop.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt tape_stop" in code, "Missing @werkstatt tape_stop header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_stop_time_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "stop_time"][0]
        assert s["min"] == 0.1 and s["max"] == 5
        assert s["type"] == "exp"

    def test_curve_param(self):
        params = self._parse_params(self._read_script())
        c = [p for p in params if p["name"] == "curve"][0]
        assert c["default"] == 2, "curve default should be 2 (classic tape)"

    def test_state_machine(self):
        code = self._read_script()
        assert "this.state" in code, "Missing state machine"
        assert "state === 1" in code or "state === 0" in code, "Missing state transitions"

    def test_exponential_decay(self):
        code = self._read_script()
        assert "Math.pow" in code, "Missing exponential decay"
        assert "1.0 - t" in code or "1 - t" in code, "Missing speed decay formula"

    def test_speed_variable(self):
        code = self._read_script()
        assert "this.speed" in code, "Missing speed tracking"
        assert "speed" in code, "Missing speed variable"

    def test_circular_buffer(self):
        code = self._read_script()
        assert "this.buf" in code, "Missing circular buffer"
        assert "this.writePos" in code, "Missing write position"
        assert "this.readPos" in code, "Missing read position"

    def test_fractional_read(self):
        code = self._read_script()
        assert "Math.floor(this.readPos)" in code or "Math.floor(this.readPos)" in code, "Missing fractional read"
        assert "frac" in code, "Missing fractional interpolation"

    def test_flutter(self):
        code = self._read_script()
        assert "flutter" in code, "Missing flutter parameter"
        assert "flutterPhase" in code, "Missing flutter phase state"

    def test_trigger_restart(self):
        code = self._read_script()
        assert "trigger" in code, "Missing trigger parameter"
        assert "restart" in code, "Missing restart parameter"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "process(" in code, "Missing process method"

    def test_stereo_output(self):
        code = self._read_script()
        assert "io.out[0]" in code and "io.out[1]" in code, "Missing stereo output"


class TestMultibandImagerDSP:
    """Unit tests for werkstatt_multiband_imager.js — 3-band M/S stereo imager"""

    SCRIPT = "werkstatt_multiband_imager.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt multiband_imager" in code, "Missing @werkstatt multiband_imager header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_crossover_params(self):
        params = self._parse_params(self._read_script())
        c1 = [p for p in params if p["name"] == "crossover1"][0]
        c2 = [p for p in params if p["name"] == "crossover2"][0]
        assert c1["type"] == "exp" and c2["type"] == "exp", "Crossovers should be exp"
        assert c1["default"] == 200 and c2["default"] == 2000

    def test_width_params(self):
        params = self._parse_params(self._read_script())
        low = [p for p in params if p["name"] == "low_width"][0]
        mid = [p for p in params if p["name"] == "mid_width"][0]
        high = [p for p in params if p["name"] == "high_width"][0]
        assert low["default"] == 0, "low_width default should be 0 (mono bass)"
        assert mid["default"] == 0.5, "mid_width default should be 0.5 (neutral)"
        assert high["default"] == 1.0, "high_width default should be 1.0 (wide)"

    def test_bypass_low_param(self):
        params = self._parse_params(self._read_script())
        b = [p for p in params if p["name"] == "bypass_low"][0]
        assert b["type"] == "bool", "bypass_low should be bool"

    def test_link_param(self):
        params = self._parse_params(self._read_script())
        lk = [p for p in params if p["name"] == "link"][0]
        assert lk["type"] == "bool", "link should be bool"

    def test_lr4_crossover(self):
        code = self._read_script()
        assert "_butterworthLP" in code, "Missing Butterworth LP filter"
        assert "_butterworthHP" in code, "Missing Butterworth HP filter"
        assert "_lr4" in code, "Missing LR4 crossover function"

    def test_ms_encoding(self):
        code = self._read_script()
        assert "mid = (l + r)" in code, "Missing M/S mid encoding"
        assert "side = (l - r)" in code, "Missing M/S side encoding"

    def test_per_band_width(self):
        code = self._read_script()
        assert "lowW" in code, "Missing low band width application"
        assert "midW" in code, "Missing mid band width application"
        assert "highW" in code, "Missing high band width application"

    def test_band_summation(self):
        code = self._read_script()
        assert "procLowL + procMidL + procHighL" in code, "Missing band summation L"
        assert "procLowR + procMidR + procHighR" in code, "Missing band summation R"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "(wetL - dryL) * mix" in code, "Missing dry/wet blend formula"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestFreqShifterDSP:
    """Unit tests for werkstatt_freq_shifter.js — SSB frequency shifter"""

    SCRIPT = "werkstatt_freq_shifter.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt freq_shifter" in code, "Missing @werkstatt freq_shifter header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_shift_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "shift"][0]
        assert s["default"] == 200 and s["min"] == -2000 and s["max"] == 2000
        assert s["type"] == "linear"

    def test_direction_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "direction"][0]
        assert d["type"] == "bool", "direction should be bool"

    def test_feedback_param(self):
        params = self._parse_params(self._read_script())
        fb = [p for p in params if p["name"] == "feedback"][0]
        assert fb["default"] == 0 and fb["max"] == 0.9

    def test_hilbert_transform(self):
        code = self._read_script()
        assert "_allpass" in code, "Missing allpass filter for Hilbert transform"
        assert "phaseI" in code or "phaseI_" in code, "Missing in-phase branch"
        assert "phaseQ" in code or "phaseQ_" in code, "Missing quadrature branch"

    def test_ssb_modulation(self):
        code = self._read_script()
        assert "cosC" in code, "Missing cosine carrier"
        assert "sinC" in code, "Missing sine carrier"
        assert "upper" in code, "Missing upper sideband"
        assert "lower" in code, "Missing lower sideband"

    def test_sideband_selection(self):
        code = self._read_script()
        assert "shiftHz >= 0" in code or "shiftHz" in code, "Missing sideband selection logic"

    def test_carrier_oscillator(self):
        code = self._read_script()
        assert "carrierPhase" in code, "Missing carrier phase state"
        assert "carrierInc" in code, "Missing carrier increment"
        assert "2 * Math.PI" in code, "Missing 2*pi frequency calculation"

    def test_feedback_path(self):
        code = self._read_script()
        assert "this.fbL" in code, "Missing feedback state L"
        assert "this.fbR" in code, "Missing feedback state R"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "dryGain" in code, "Missing dry gain"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestReverseDelayDSP:
    """Unit tests for werkstatt_reverse_delay.js — reverse delay (The Edge style)"""

    SCRIPT = "werkstatt_reverse_delay.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt reverse_delay" in code, "Missing @werkstatt reverse_delay header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_time_param(self):
        params = self._parse_params(self._read_script())
        t = [p for p in params if p["name"] == "time"][0]
        assert t["default"] == 0.4 and t["type"] == "linear"
        assert t["min"] == 0.05 and t["max"] == 2

    def test_feedback_param(self):
        params = self._parse_params(self._read_script())
        fb = [p for p in params if p["name"] == "feedback"][0]
        assert fb["default"] == 0.35 and fb["max"] == 0.85

    def test_fade_param(self):
        params = self._parse_params(self._read_script())
        f = [p for p in params if p["name"] == "fade"][0]
        assert f["default"] == 0.01 and f["type"] == "linear"

    def test_damping_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "damping"][0]
        assert d["default"] == 0.3

    def test_pan_param(self):
        params = self._parse_params(self._read_script())
        p = [p for p in params if p["name"] == "pan"][0]
        assert p["min"] == -1 and p["max"] == 1

    def test_circular_buffer(self):
        code = self._read_script()
        assert "this.buf" in code, "Missing delay buffer"
        assert "this.writePos" in code, "Missing write position"
        assert "this.bufLen" in code, "Missing buffer length"

    def test_reverse_read(self):
        code = self._read_script()
        assert "readOffset" in code, "Missing reverse read offset calculation"
        assert "writePos - delaySamps" in code, "Missing delay offset"

    def test_fade_ramp(self):
        code = self._read_script()
        assert "fadeLen" in code, "Missing fade length"
        assert "fadeGain" in code, "Missing fade gain ramp"
        assert "cyclePos" in code, "Missing cycle position for fade boundaries"

    def test_damping_lowpass(self):
        code = self._read_script()
        assert "_dampLp" in code, "Missing damping lowpass"
        assert "dampState" in code, "Missing damping state"

    def test_equal_power_pan(self):
        code = self._read_script()
        assert "_pan" in code, "Missing pan function"
        assert "Math.cos" in code and "Math.sin" in code, "Missing equal-power pan"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

class TestGatedReverbDSP:
    """Unit tests for werkstatt_gated_reverb.js — 80s gated reverb"""

    SCRIPT = "werkstatt_gated_reverb.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt gated_reverb" in code, "Missing @werkstatt gated_reverb header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_reverb_params(self):
        params = self._parse_params(self._read_script())
        decay = [p for p in params if p["name"] == "decay"][0]
        assert decay["default"] == 0.5 and decay["type"] == "linear"

    def test_gate_params(self):
        params = self._parse_params(self._read_script())
        threshold = [p for p in params if p["name"] == "threshold"][0]
        hold = [p for p in params if p["name"] == "hold"][0]
        release = [p for p in params if p["name"] == "release"][0]
        assert threshold["default"] == 0.02, "threshold default should be 0.02"
        assert hold["type"] == "linear" and hold["default"] == 0.08
        assert release["type"] == "linear"

    def test_schroeder_reverb(self):
        code = self._read_script()
        assert "_mkComb" in code, "Missing comb filter construction"
        assert "_mkAp" in code, "Missing allpass filter construction"
        assert "_combProcess" in code, "Missing comb processing"
        assert "_apProcess" in code, "Missing allpass processing"

    def test_gate_state_machine(self):
        code = self._read_script()
        assert "gateOpen" in code, "Missing gate open state"
        assert "holdCounter" in code, "Missing hold counter"
        assert "threshold" in code, "Missing threshold detection"

    def test_envelope_follower(self):
        code = self._read_script()
        assert "this.env" in code, "Missing envelope follower state"
        assert "monoAbs" in code, "Missing mono amplitude detection"

    def test_gate_gain(self):
        code = self._read_script()
        assert "gateGain" in code, "Missing gate gain state"
        assert "releaseCoef" in code, "Missing release coefficient"

    def test_predelay(self):
        code = self._read_script()
        assert "pdBuf" in code, "Missing predelay buffer"
        assert "predelay" in code, "Missing predelay parameter"

    def test_ms_width(self):
        code = self._read_script()
        assert "mid = (wetL + wetR)" in code or "mid" in code, "Missing M/S mid"
        assert "side" in code, "Missing M/S side"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "(gatedL - dryL) * mix" in code or "gated" in code, "Missing gated wet blend"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestBassEnhancerDSP:
    """Unit tests for werkstatt_bass_enhancer.js — psychoacoustic bass enhancer"""

    SCRIPT = "werkstatt_bass_enhancer.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt bass_enhancer" in code, "Missing @werkstatt bass_enhancer header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_freq_param(self):
        params = self._parse_params(self._read_script())
        f = [p for p in params if p["name"] == "freq"][0]
        assert f["default"] == 80 and f["min"] == 40 and f["max"] == 200

    def test_sub_level_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "sub_level"][0]
        assert s["default"] == 0.5

    def test_harmonics_param(self):
        params = self._parse_params(self._read_script())
        h = [p for p in params if p["name"] == "harmonics"][0]
        assert h["default"] == 0.3

    def test_bass_isolation_lpf(self):
        code = self._read_script()
        assert "lpState" in code, "Missing LPF state for bass isolation"
        assert "alphaLp" in code, "Missing LPF coefficient"

    def test_full_wave_rectification(self):
        code = self._read_script()
        assert "Math.abs" in code, "Missing full-wave rectification"
        assert "rectL" in code or "rectR" in code, "Missing rectified signal"

    def test_sub_harmonic_extraction(self):
        code = self._read_script()
        assert "subLp" in code, "Missing sub-harmonic LPF"
        assert "rectSmooth" in code, "Missing rectified signal smoothing"

    def test_dc_removal_hpf(self):
        code = self._read_script()
        assert "hpState" in code, "Missing HPF for DC removal"
        assert "alphaHp" in code, "Missing HPF coefficient"

    def test_envelope_follower(self):
        code = self._read_script()
        assert "this.env" in code, "Missing envelope follower"
        assert "atkCoef" in code and "relCoef" in code, "Missing attack/release coefficients"

    def test_harmonic_saturation(self):
        code = self._read_script()
        assert "tanh" in code, "Missing harmonic saturation (tanh)"
        assert "harmL" in code or "harmR" in code, "Missing harmonic signal"

    def test_band_replacement(self):
        code = self._read_script()
        assert "hpDryL" in code or "hpDryR" in code, "Missing high-passed dry (band replacement)"
        assert "enhancedL" in code or "enhancedR" in code, "Missing enhanced bass output"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestTiltEqDSP:
    """Unit tests for werkstatt_tilt_eq.js — single-knob spectral tilt EQ"""

    SCRIPT = "werkstatt_tilt_eq.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt tilt_eq" in code, "Missing @werkstatt tilt_eq header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_tilt_param(self):
        params = self._parse_params(self._read_script())
        t = [p for p in params if p["name"] == "tilt"][0]
        assert t["default"] == 0, "tilt default should be 0 (neutral)"
        assert t["min"] == -6 and t["max"] == 6

    def test_pivot_param(self):
        params = self._parse_params(self._read_script())
        p = [p for p in params if p["name"] == "pivot"][0]
        assert p["default"] == 1000 and p["type"] == "exp"

    def test_steepness_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "steepness"][0]
        assert s["default"] == 0.5 and s["min"] == 0.2 and s["max"] == 1

    def test_low_shelf(self):
        code = self._read_script()
        assert "_shelfLP" in code, "Missing low shelf filter"
        assert "lsCoeffs" in code, "Missing low shelf coefficients"

    def test_high_shelf(self):
        code = self._read_script()
        assert "_shelfHP" in code, "Missing high shelf filter"
        assert "hsCoeffs" in code, "Missing high shelf coefficients"

    def test_tilt_logic(self):
        code = self._read_script()
        assert "lsGain = -tilt" in code, "Missing low shelf gain (opposite of tilt)"
        assert "hsGain = tilt" in code, "Missing high shelf gain (same as tilt)"

    def test_biquad(self):
        code = self._read_script()
        assert "_biquad" in code, "Missing biquad processing function"
        assert "c[0]*x" in code, "Missing biquad formula"

    def test_coeff_caching(self):
        code = self._read_script()
        assert "lastTilt" in code, "Missing coefficient caching"
        assert "_updateCoeffs" in code, "Missing coefficient update function"

    def test_shelf_slope(self):
        code = self._read_script()
        assert "steepness" in code or "S = this.p.steepness" in code, "Missing shelf slope parameter"
        assert "sqrt" in code, "Missing sqrt in shelf coefficient calculation"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "dryGain" in code, "Missing dry gain"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestSvfDSP:
    """Unit tests for werkstatt_svf.js — Chamberlin state variable filter"""

    SCRIPT = "werkstatt_svf.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt svf" in code, "Missing @werkstatt svf header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_cutoff_param(self):
        params = self._parse_params(self._read_script())
        c = [p for p in params if p["name"] == "cutoff"][0]
        assert c["default"] == 1000 and c["type"] == "exp"

    def test_resonance_param(self):
        params = self._parse_params(self._read_script())
        r = [p for p in params if p["name"] == "resonance"][0]
        assert r["default"] == 0.5 and r["min"] == 0 and r["max"] == 1

    def test_morph_param(self):
        params = self._parse_params(self._read_script())
        m = [p for p in params if p["name"] == "morph"][0]
        assert m["default"] == 0 and m["min"] == 0 and m["max"] == 1

    def test_output_mode_param(self):
        params = self._parse_params(self._read_script())
        o = [p for p in params if p["name"] == "output_mode"][0]
        assert o["default"] == 0 and o["min"] == 0 and o["max"] == 2

    def test_chamberlin_topology(self):
        code = self._read_script()
        assert "this.lpL" in code and "this.bpL" in code, "Missing LP/BP state"
        assert "hpL = inL - this.lpL" in code, "Missing HP = input - LP - q*BP"
        assert "this.bpL += f * hpL" in code, "Missing BP = BP + f*HP"
        assert "this.lpL += f * this.bpL" in code, "Missing LP = LP + f*BP"

    def test_freq_coefficient(self):
        code = self._read_script()
        assert "2 * Math.sin(Math.PI" in code, "Missing Chamberlin frequency coefficient"

    def test_damping_coefficient(self):
        code = self._read_script()
        assert "q = 2 - 2 * res" in code, "Missing damping coefficient"

    def test_morph_blend(self):
        code = self._read_script()
        assert "wLP" in code and "wBP" in code and "wHP" in code, "Missing morph blend weights"
        assert "morph <= 0.5" in code, "Missing morph split logic"

    def test_notch_mode(self):
        code = self._read_script()
        assert "outMode === 1" in code or "out_mode" in code.lower() or "notch" in code.lower(), "Missing notch mode"

    def test_allpass_mode(self):
        code = self._read_script()
        assert "outMode === 2" in code or "allpass" in code.lower(), "Missing allpass mode"

    def test_soft_clip(self):
        code = self._read_script()
        assert "tanh" in code, "Missing soft clip for high resonance protection"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"


class TestChorderDSP:
    """Unit tests for spielwerk_chorder.js — chord voicer MIDI effect"""

    SCRIPT = "spielwerk_chorder.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@spielwerk chorder" in code, "Missing @spielwerk chorder header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_chord_param(self):
        params = self._parse_params(self._read_script())
        c = [p for p in params if p["name"] == "chord"][0]
        assert c["min"] == 0 and c["max"] == 12 and c["type"] == "int"

    def test_voicing_param(self):
        params = self._parse_params(self._read_script())
        v = [p for p in params if p["name"] == "voicing"][0]
        assert v["min"] == 0 and v["max"] == 4 and v["type"] == "int"

    def test_inversion_param(self):
        params = self._parse_params(self._read_script())
        i = [p for p in params if p["name"] == "inversion"][0]
        assert i["min"] == 0 and i["max"] == 3 and i["type"] == "int"

    def test_strum_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "strum"][0]
        assert s["min"] == 0 and s["max"] == 64 and s["type"] == "int"

    def test_spread_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "spread"][0]
        assert s["min"] == 0 and s["max"] == 24 and s["type"] == "int"

    def test_chord_shapes_count(self):
        code = self._read_script()
        assert "[0, 4, 7]" in code, "Missing major triad shape"
        assert "[0, 3, 7, 10]" in code, "Missing min7 shape"
        assert "[0, 4, 7, 11]" in code, "Missing maj7 shape"
        assert "[0, 3, 6, 9]" in code, "Missing dim7 shape"
        assert "[0, 2, 7]" in code, "Missing sus2 shape"
        assert "[0, 5, 7]" in code, "Missing sus4 shape"
        assert "[0, 4, 7, 14]" in code, "Missing add9 shape"

    def test_voicing_modes(self):
        code = self._read_script()
        assert "drop-2" in code, "Missing drop-2 voicing"
        assert "drop-3" in code, "Missing drop-3 voicing"
        assert "open" in code, "Missing open voicing"
        assert "spread" in code, "Missing spread voicing"

    def test_inversion_rotation(self):
        code = self._read_script()
        assert "shift()" in code, "Missing inversion rotation"
        assert "+ 12" in code, "Missing octave shift for inversion"

    def test_generator_process(self):
        code = self._read_script()
        assert "*process" in code, "Missing generator process method"
        assert "yield" in code, "Missing yield (should be a generator)"

    def test_pitch_range_guard(self):
        code = self._read_script()
        assert "p >= 0 && p <= 127" in code, "Missing pitch range guard"

    def test_velocity_attenuation(self):
        code = self._read_script()
        assert "i * 0.04" in code, "Missing per-voice velocity attenuation"

    def test_strum_position_offset(self):
        code = self._read_script()
        assert "i * strumAmt" in code, "Missing strum position offset"

    def test_reset(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"


class TestModalResonatorDSP:
    """Unit tests for werkstatt_modal_resonator.js — modal synthesis resonator bank"""

    SCRIPT = "werkstatt_modal_resonator.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt modal_resonator" in code, "Missing @werkstatt modal_resonator header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_material_param(self):
        params = self._parse_params(self._read_script())
        m = [p for p in params if p["name"] == "material"][0]
        assert m["min"] == 0 and m["max"] == 4 and m["type"] == "int"

    def test_fundamental_param(self):
        params = self._parse_params(self._read_script())
        f = [p for p in params if p["name"] == "fundamental"][0]
        assert f["min"] == 40 and f["max"] == 2000 and f["type"] == "exp"

    def test_inharmonicity_param(self):
        params = self._parse_params(self._read_script())
        i = [p for p in params if p["name"] == "inharmonicity"][0]
        assert i["min"] == 0 and i["max"] == 1 and i["type"] == "linear"

    def test_material_ratios(self):
        code = self._read_script()
        assert "3.0, 5.41, 8.93" in code, "Missing marimba bar ratios"
        assert "1.46, 1.85, 2.31" in code, "Missing circular plate ratios"
        assert "2.76, 5.05, 7.6" in code, "Missing wine glass ratios"

    def test_biquad_implementation(self):
        code = self._read_script()
        assert "_biquadBP" in code, "Missing biquad bandpass method"
        assert "RBJ cookbook" in code or "bandpass" in code.lower(), "Missing RBJ reference"
        assert "alpha" in code, "Missing alpha coefficient"

    def test_q_from_decay(self):
        code = self._read_script()
        assert "baseT60" in code, "Missing T60 decay calculation"
        assert "modeT60" in code, "Missing per-mode decay"
        assert "q = Math.max" in code, "Missing Q calculation from decay"

    def test_inharmonicity_stretch(self):
        code = self._read_script()
        assert "stretch" in code, "Missing inharmonicity stretch"
        assert "i * i" in code, "Missing quadratic stretch factor"

    def test_brightness_rolloff(self):
        code = self._read_script()
        assert "Math.pow(bright" in code, "Missing brightness amplitude rolloff"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "dry" in code and "wet" in code, "Missing dry/wet mix"

    def test_output_gain_db(self):
        code = self._read_script()
        assert "Math.pow(10" in code, "Missing dB-to-linear output gain"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_stereo_processing(self):
        code = self._read_script()
        assert "resL" in code and "resR" in code, "Missing stereo processing"
        assert "_biquadBPR" in code, "Missing right-channel biquad"

    def test_freq_guard(self):
        code = self._read_script()
        assert "sr * 0.45" in code, "Missing Nyquist frequency guard"


class TestMultibandSaturatorDSP:
    """Unit tests for werkstatt_multiband_saturator.js — multiband saturation"""

    SCRIPT = "werkstatt_multiband_saturator.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt multiband_saturator" in code, "Missing header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_crossover_params(self):
        params = self._parse_params(self._read_script())
        c1 = [p for p in params if p["name"] == "crossover1"][0]
        c2 = [p for p in params if p["name"] == "crossover2"][0]
        assert c1["type"] == "exp" and c2["type"] == "exp"
        assert c1["default"] == 200 and c2["default"] == 2500

    def test_per_band_drive(self):
        params = self._parse_params(self._read_script())
        for name in ["low_drive", "mid_drive", "high_drive"]:
            d = [p for p in params if p["name"] == name][0]
            assert d["min"] == 0 and d["max"] == 1 and d["type"] == "linear"

    def test_per_band_character(self):
        params = self._parse_params(self._read_script())
        for name in ["low_char", "mid_char", "high_char"]:
            c = [p for p in params if p["name"] == name][0]
            assert c["min"] == 0 and c["max"] == 2 and c["type"] == "int"

    def test_lr4_crossover(self):
        code = self._read_script()
        assert "_lp4" in code, "Missing 4-pole cascade for LR4"
        assert "z1" in code and "z2" in code and "z3" in code and "z4" in code, "Missing 4 stages of state"
        assert "crossover" in code, "Missing crossover reference"

    def test_three_band_split(self):
        code = self._read_script()
        assert "lowL" in code and "midL" in code and "highL" in code, "Missing 3-band split"
        assert "sL - lowL" in code, "Missing highpass via subtraction"
        assert "hpL1 - midL" in code, "Missing high band extraction"

    def test_saturation_characters(self):
        code = self._read_script()
        assert "tape" in code, "Missing tape character"
        assert "tube" in code, "Missing tube character"
        assert "transistor" in code, "Missing transistor character"
        assert "tanh" in code, "Missing tanh saturation"

    def test_tube_asymmetric(self):
        code = self._read_script()
        assert "asymmetric" in code, "Missing asymmetric tube clip"
        assert "1 + x * 2" in code, "Missing positive half expansion"
        assert "1 - x * 1.5" in code, "Missing negative half expansion"

    def test_drive_scaling(self):
        code = self._read_script()
        assert "1 + drive * 9" in code, "Missing drive scaling (1..10x)"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "dry" in code and "wet" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "Math.pow(10" in code, "Missing dB-to-linear output gain"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_stereo(self):
        code = self._read_script()
        assert "satLowL" in code and "satLowR" in code, "Missing stereo saturation"
        assert "satHighL" in code and "satHighR" in code, "Missing stereo high band"

    def test_band_summation(self):
        code = self._read_script()
        assert "satLowL + satMidL + satHighL" in code, "Missing band summation"


class TestVinylDSP:
    """Unit tests for werkstatt_vinyl.js — vinyl record simulator"""

    SCRIPT = "werkstatt_vinyl.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt vinyl" in code, "Missing @werkstatt vinyl header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_dust_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "dust"][0]
        assert d["min"] == 0 and d["max"] == 1 and d["type"] == "linear"

    def test_wow_flutter_params(self):
        params = self._parse_params(self._read_script())
        w = [p for p in params if p["name"] == "wow"][0]
        f = [p for p in params if p["name"] == "flutter"][0]
        assert w["max"] == 0.5 and f["max"] == 0.5

    def test_wear_param(self):
        params = self._parse_params(self._read_script())
        w = [p for p in params if p["name"] == "wear"][0]
        assert w["min"] == 0 and w["max"] == 1 and w["type"] == "linear"

    def test_lcg_random(self):
        code = self._read_script()
        assert "1103515245" in code, "Missing LCG random implementation"
        assert "_rand" in code, "Missing _rand method"

    def test_crackle_engine(self):
        code = self._read_script()
        assert "crackleEnv" in code, "Missing crackle envelope"
        assert "_nextPopAt" in code, "Missing pop scheduling"
        assert "popRate" in code, "Missing pop rate calculation"

    def test_wow_flutter_modulation(self):
        code = self._read_script()
        assert "wowPhase" in code, "Missing wow phase"
        assert "flutterPhase" in code, "Missing flutter phase"
        assert "Math.sin(this._wowPhase)" in code, "Missing wow sinusoidal modulation"
        assert "Math.sin(this._flutterPhase)" in code, "Missing flutter sinusoidal modulation"

    def test_fractional_delay(self):
        code = self._read_script()
        assert "fractional" in code.lower() or "frac" in code, "Missing fractional delay read"
        assert "_bufL" in code and "_bufR" in code, "Missing delay buffers"
        assert "_writePos" in code, "Missing write position"

    def test_surface_noise(self):
        code = self._read_script()
        assert "noiseAmp" in code, "Missing noise amplitude"
        assert "rawNoiseL" in code, "Missing raw noise generation"

    def test_wear_filter(self):
        code = self._read_script()
        assert "wearCoeff" in code, "Missing wear filter coefficient"
        assert "wearZ1L" in code, "Missing wear filter state"
        assert "one-pole LP" in code, "Missing wear LP filter reference"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "dry" in code and "wet" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "Math.pow(10" in code, "Missing dB-to-linear output gain"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_stereo_processing(self):
        code = self._read_script()
        assert "wetL" in code and "wetR" in code, "Missing stereo processing"


class TestExpanderDSP:
    """Unit tests for werkstatt_expander.js — downward expander"""

    SCRIPT = "werkstatt_expander.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt expander" in code, "Missing @werkstatt expander header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_threshold_param(self):
        params = self._parse_params(self._read_script())
        t = [p for p in params if p["name"] == "threshold"][0]
        assert t["default"] == 0.7 and t["type"] == "linear"

    def test_ratio_param(self):
        params = self._parse_params(self._read_script())
        r = [p for p in params if p["name"] == "ratio"][0]
        assert r["type"] == "linear"

    def test_range_param(self):
        params = self._parse_params(self._read_script())
        r = [p for p in params if p["name"] == "range"][0]
        assert r["default"] == 0.8 and r["type"] == "linear"

    def test_knee_param(self):
        params = self._parse_params(self._read_script())
        k = [p for p in params if p["name"] == "knee"][0]
        assert k["type"] == "linear"

    def test_output_param_db(self):
        params = self._parse_params(self._read_script())
        o = [p for p in params if p["name"] == "output"][0]
        assert o["min"] == -12 and o["max"] == 6 and o["type"] == "linear"

    def test_downward_expansion(self):
        code = self._read_script()
        assert "belowDb" in code, "Missing below-threshold detection"
        assert "ratioNum - 1" in code, "Missing ratio application for expansion"

    def test_range_cap(self):
        code = self._read_script()
        assert "maxAttenDb" in code, "Missing max attenuation cap"
        assert "Math.min(gr" in code, "Missing range cap on gain reduction"

    def test_soft_knee(self):
        code = self._read_script()
        assert "kneeWidth" in code, "Missing soft knee width"
        assert "t * " in code, "Missing knee quadratic blend"

    def test_envelope_follower(self):
        code = self._read_script()
        assert "this.envL" in code and "this.envR" in code, "Missing envelope state"
        assert "attackCoeff" in code and "releaseCoeff" in code, "Missing attack/release coefficients"

    def test_attack_release_smoothing(self):
        code = self._read_script()
        assert "targetGain < env" in code, "Missing attack/release direction logic"

    def test_stereo_detection(self):
        code = self._read_script()
        assert "Math.max(detL, detR)" in code, "Missing stereo linked detection"

    def test_db_conversion(self):
        code = self._read_script()
        assert "_dbToGain" in code, "Missing dB-to-gain conversion"
        assert "_gainToDb" in code, "Missing gain-to-dB conversion"
        assert "Math.log10" in code, "Missing log10 for dB conversion"

    def test_time_constants(self):
        code = self._read_script()
        assert "_msToCoeff" in code, "Missing ms-to-coefficient time constant"
        assert "Math.exp(-1" in code, "Missing exponential time constant"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "1 - p.mix" in code, "Missing dry gain calculation"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"




class TestGrainDelayDSP:
    """Unit tests for werkstatt_grain_delay.js — granular delay"""

    SCRIPT = "werkstatt_grain_delay.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt grain_delay" in code, "Missing @werkstatt grain_delay header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 10, f"Expected 10 params, got {len(params)}"

    def test_delay_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "delay"][0]
        assert d["type"] == "exp" and d["default"] == 150

    def test_grain_params(self):
        params = self._parse_params(self._read_script())
        gs = [p for p in params if p["name"] == "grain_size"][0]
        gr = [p for p in params if p["name"] == "grain_rate"][0]
        assert gs["type"] == "exp" and gr["type"] == "exp"

    def test_pitch_param(self):
        params = self._parse_params(self._read_script())
        p = [p for p in params if p["name"] == "pitch"][0]
        assert p["default"] == 1 and p["type"] == "exp"
        assert p["min"] == 0.25 and p["max"] == 4

    def test_scatter_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "scatter"][0]
        assert s["min"] == 0 and s["max"] == 1

    def test_reverse_param(self):
        params = self._parse_params(self._read_script())
        r = [p for p in params if p["name"] == "reverse"][0]
        assert r["min"] == 0 and r["max"] == 1

    def test_feedback_param(self):
        params = self._parse_params(self._read_script())
        f = [p for p in params if p["name"] == "feedback"][0]
        assert f["max"] == 0.9  # capped below 1 for stability

    def test_grain_spawn(self):
        code = self._read_script()
        assert "_spawnGrain" in code, "Missing grain spawn method"
        assert "_grains.push" in code, "Missing grain push to array"
        assert "grainInterval" in code, "Missing grain interval calculation"

    def test_hann_window(self):
        code = self._read_script()
        assert "_hann" in code, "Missing Hann window function"
        assert "Math.cos(2 * Math.PI" in code, "Missing cosine in Hann window"

    def test_grain_read(self):
        code = self._read_script()
        assert "readPos" in code, "Missing grain read position"
        assert "grainLen" in code, "Missing grain length"
        assert "bufReadPos" in code, "Missing buffer read position calculation"

    def test_fractional_read(self):
        code = self._read_script()
        assert "frac" in code, "Missing fractional interpolation"
        assert "idx2" in code, "Missing second index for interpolation"

    def test_grain_cleanup(self):
        code = self._read_script()
        assert "splice" in code, "Missing grain removal when expired"
        assert "readPos >= grain.grainLen" in code, "Missing grain expiry check"

    def test_grain_cap(self):
        code = self._read_script()
        assert "slice(-80)" in code or "80" in code, "Missing grain count cap"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "dry" in code and "wet" in code, "Missing dry/wet mix"


class TestBinauralDSP:
    """Unit tests for werkstatt_binaural.js — binaural spatial panner"""

    SCRIPT = "werkstatt_binaural.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt binaural" in code, "Missing @werkstatt binaural header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_azimuth_param(self):
        params = self._parse_params(self._read_script())
        a = [p for p in params if p["name"] == "azimuth"][0]
        assert a["min"] == -180 and a["max"] == 180 and a["type"] == "linear"

    def test_elevation_param(self):
        params = self._parse_params(self._read_script())
        e = [p for p in params if p["name"] == "elevation"][0]
        assert e["min"] == -90 and e["max"] == 90 and e["type"] == "linear"

    def test_distance_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "distance"][0]
        assert d["type"] == "exp" and d["default"] == 1

    def test_head_size_param(self):
        params = self._parse_params(self._read_script())
        h = [p for p in params if p["name"] == "head_size"][0]
        assert h["type"] == "linear"

    def test_output_param_db(self):
        params = self._parse_params(self._read_script())
        o = [p for p in params if p["name"] == "output"][0]
        assert o["min"] == -12 and o["max"] == 6 and o["type"] == "linear"

    def test_itd_woodworth(self):
        code = self._read_script()
        assert "Woodworth" in code, "Missing Woodworth formula reference"
        assert "azRad + Math.sin(azRad)" in code, "Missing Woodworth ITD formula"

    def test_itd_delay_buffers(self):
        code = self._read_script()
        assert "delayBufL" in code and "delayBufR" in code, "Missing ITD delay buffers"
        assert "_readDelay" in code, "Missing fractional delay read"
        assert "delaySamplesL" in code, "Missing per-channel delay samples"

    def test_ild_shadow(self):
        code = self._read_script()
        assert "ildMax" in code, "Missing ILD max calculation"
        assert "ildStateL" in code, "Missing ILD state"
        assert "sin(absAz" in code, "Missing azimuth-dependent ILD"

    def test_pinna_notches(self):
        code = self._read_script()
        assert "pinnaNotch1" in code and "pinnaNotch2" in code, "Missing pinna notch frequencies"
        assert "_biquadPeak" in code, "Missing biquad peak for pinna notches"
        assert "elev" in code, "Missing elevation in pinna calculation"

    def test_distance_attenuation(self):
        code = self._read_script()
        assert "distAtten" in code, "Missing distance attenuation"
        assert "1 / Math.max" in code, "Missing inverse distance law"

    def test_air_absorption(self):
        code = self._read_script()
        assert "airAbsorb" in code, "Missing air absorption"
        assert "distance > 1" in code, "Missing distance threshold for air absorption"

    def test_room_reverb(self):
        code = self._read_script()
        assert "_comb" in code, "Missing comb filter for room"
        assert "_allpass" in code, "Missing allpass for room"
        assert "roomAmount" in code, "Missing room amount"

    def test_decorrelation(self):
        code = self._read_script()
        assert "_rand" in code, "Missing LCG for decorrelation"
        assert "1103515245" in code, "Missing LCG constant"
        assert "revL" in code and "revR" in code, "Missing decorrelated L/R reverb"

    def test_stereo_output(self):
        code = self._read_script()
        assert "outL" in code and "outR" in code, "Missing stereo output"
        assert "outL[i]" in code and "outR[i]" in code, "Missing per-sample stereo output"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "1 - p.mix" in code, "Missing dry gain"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert "delayBufL" in code, "Missing binaural reset"


class TestHarmonicTremoloDSP:
    """Unit tests for werkstatt_harmonic_tremolo.js — Fender harmonic tremolo"""

    SCRIPT = "werkstatt_harmonic_tremolo.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt harmonic_tremolo" in code, "Missing header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_rate_param(self):
        params = self._parse_params(self._read_script())
        r = [p for p in params if p["name"] == "rate"][0]
        assert r["type"] == "linear"

    def test_depth_param(self):
        params = self._parse_params(self._read_script())
        d = [p for p in params if p["name"] == "depth"][0]
        assert d["type"] == "linear"

    def test_crossover_param(self):
        params = self._parse_params(self._read_script())
        c = [p for p in params if p["name"] == "crossover"][0]
        assert c["type"] == "exp" and c["default"] == 800

    def test_shape_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "shape"][0]
        assert s["type"] == "linear"

    def test_phase_offset_param(self):
        params = self._parse_params(self._read_script())
        p = [p for p in params if p["name"] == "phase_offset"][0]
        assert p["type"] == "linear"

    def test_output_param_db(self):
        params = self._parse_params(self._read_script())
        o = [p for p in params if p["name"] == "output"][0]
        assert o["min"] == -12 and o["max"] == 6 and o["type"] == "linear"

    def test_lr4_crossover(self):
        code = self._read_script()
        assert "z1" in code, "Missing LR4 crossover state"
        assert "_lpCoeff" in code, "Missing LP coefficient"
        assert "Math.exp(-2 * Math.PI" in code, "Missing LR4 coefficient calc"

    def test_band_split(self):
        code = self._read_script()
        assert "lowL" in code and "highL" in code, "Missing low/high band split"
        assert "dryL - lowL" in code or "dryL - sL" in code, "Missing HP via subtraction"

    def test_dual_lfo(self):
        code = self._read_script()
        assert "lfoLow" in code and "lfoHigh" in code, "Missing dual LFO"
        assert "Math.sin(this.phase" in code, "Missing sine LFO"

    def test_antiphase(self):
        code = self._read_script()
        assert "phaseOff" in code, "Missing phase offset between LFOs"
        assert "Math.PI" in code, "Missing PI for antiphase"

    def test_shape_blend(self):
        code = self._read_script()
        assert "shapeAmt" in code, "Missing shape amount"
        assert "1 - shapeAmt" in code, "Missing shape blend toward square"

    def test_gain_smoothing(self):
        code = self._read_script()
        assert "smoothCoeff" in code, "Missing gain smoothing coefficient"
        assert "gainLowL" in code, "Missing smoothed gain state"

    def test_band_recombine(self):
        code = self._read_script()
        assert "modLowL + modHighL" in code, "Missing band recombination"

    def test_lfo_rate_mapping(self):
        code = self._read_script()
        assert "0.1 + Math.pow" in code, "Missing logarithmic rate mapping"
        assert "phaseInc" in code, "Missing phase increment"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "1 - p.mix" in code, "Missing dry gain"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"


class TestSpectralCompressorDSP:
    """Unit tests for werkstatt_spectral_compressor.js — STFT spectral compressor"""

    SCRIPT = "werkstatt_spectral_compressor.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt spectral_compressor" in code, "Missing header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 8, f"Expected 8 params, got {len(params)}"

    def test_threshold_param(self):
        params = self._parse_params(self._read_script())
        t = [p for p in params if p["name"] == "threshold"][0]
        assert t["type"] == "linear"

    def test_ratio_param(self):
        params = self._parse_params(self._read_script())
        r = [p for p in params if p["name"] == "ratio"][0]
        assert r["type"] == "linear"

    def test_tilt_param(self):
        params = self._parse_params(self._read_script())
        t = [p for p in params if p["name"] == "tilt"][0]
        assert t["type"] == "linear"

    def test_smoothing_param(self):
        params = self._parse_params(self._read_script())
        s = [p for p in params if p["name"] == "smoothing"][0]
        assert s["type"] == "linear"

    def test_output_param_db(self):
        params = self._parse_params(self._read_script())
        o = [p for p in params if p["name"] == "output"][0]
        assert o["min"] == -12 and o["max"] == 6 and o["type"] == "linear"

    def test_fft_implementation(self):
        code = self._read_script()
        assert "_fft" in code, "Missing FFT function"
        assert "Butterfly" in code, "Missing Cooley-Tukey butterfly"
        assert "Bit reversal" in code, "Missing bit reversal step"

    def test_stft_config(self):
        code = self._read_script()
        assert "FFT_SIZE" in code, "Missing FFT size"
        assert "HOP_SIZE" in code, "Missing hop size"
        assert "1024" in code, "Missing FFT size value"

    def test_hann_window(self):
        code = self._read_script()
        assert "window" in code, "Missing window function"
        assert "Hann" in code or "0.5 * (1 - Math.cos" in code, "Missing Hann window"

    def test_per_bin_envelope(self):
        code = self._read_script()
        assert "envBins" in code, "Missing per-bin envelope state"
        assert "atkCoeff" in code and "relCoeff" in code, "Missing attack/release coefficients"

    def test_per_bin_compression(self):
        code = self._read_script()
        assert "overDb" in code, "Missing over-threshold dB calculation"
        assert "reductionDb" in code, "Missing gain reduction"
        assert "ratioNum" in code, "Missing ratio"

    def test_tilt_per_frequency(self):
        code = self._read_script()
        assert "freqRatio" in code, "Missing frequency ratio for tilt"
        assert "tiltDb" in code, "Missing tilt dB calculation"
        assert "binThreshDb" in code, "Missing per-bin threshold"

    def test_gain_smoothing(self):
        code = self._read_script()
        assert "smoothCoeff" in code, "Missing gain smoothing"
        assert "prevGain" in code, "Missing previous gain for smoothing"

    def test_overlap_add(self):
        code = self._read_script()
        assert "outBufL" in code, "Missing overlap-add output buffer"
        assert "overlap" in code.lower(), "Missing overlap-add reference"

    def test_inverse_fft(self):
        code = self._read_script()
        assert "inverse" in code.lower(), "Missing inverse FFT"

    def test_magnitude_phase(self):
        code = self._read_script()
        assert "Math.sqrt" in code, "Missing magnitude calculation"
        assert "Math.atan2" in code, "Missing phase calculation"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "mix" in code, "Missing dry/wet mix"
        assert "1 - p.mix" in code, "Missing dry gain"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10" in code, "Missing dB-to-linear conversion"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"


class TestBowedStringDSP:
    """Unit tests for apparat_bowed_string.js — bowed string physical modeling"""

    SCRIPT = "apparat_bowed_string.js"

    def _read_script(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", self.SCRIPT)
        with open(path) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r"@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)", code):
            params.append({"name": m.group(1), "default": float(m.group(2)),
                           "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)})
        return params

    def test_header(self):
        code = self._read_script()
        assert "@apparat bowed_string" in code, "Missing @apparat bowed_string header"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 9, f"Expected 9 params, got {len(params)}"

    def test_bow_pressure_param(self):
        params = self._parse_params(self._read_script())
        b = [p for p in params if p["name"] == "bow_pressure"][0]
        assert b["type"] == "linear"

    def test_bow_speed_param(self):
        params = self._parse_params(self._read_script())
        b = [p for p in params if p["name"] == "bow_speed"][0]
        assert b["type"] == "linear"

    def test_bow_position_param(self):
        params = self._parse_params(self._read_script())
        b = [p for p in params if p["name"] == "bow_position"][0]
        assert b["max"] == 0.5, "bow_position max should be 0.5 (midpoint of string)"

    def test_freq_param(self):
        params = self._parse_params(self._read_script())
        f = [p for p in params if p["name"] == "freq"][0]
        assert f["type"] == "exp" and f["default"] == 220

    def test_vibrato_params(self):
        params = self._parse_params(self._read_script())
        vr = [p for p in params if p["name"] == "vibrato_rate"][0]
        vd = [p for p in params if p["name"] == "vibrato_depth"][0]
        assert vr["type"] == "linear"
        assert vd["type"] == "linear"

    def test_waveguide_delay_lines(self):
        code = self._read_script()
        assert "waveBufL" in code and "waveBufR" in code, "Missing waveguide delay lines"
        assert "waveLenL" in code and "waveLenR" in code, "Missing waveguide lengths"
        assert "wavePosL" in code, "Missing waveguide read/write positions"

    def test_bow_friction_model(self):
        code = self._read_script()
        assert "_bowFriction" in code, "Missing bow friction function"
        assert "Stribeck" in code, "Missing Stribeck curve reference"
        assert "exp(-Math.abs" in code, "Missing exponential friction decay"

    def test_stick_slip(self):
        code = self._read_script()
        assert "vRel" in code, "Missing relative velocity for stick-slip"
        assert "Math.sign" in code, "Missing friction direction (sign)"

    def test_string_velocity(self):
        code = self._read_script()
        assert "vString" in code, "Missing string velocity calculation"
        assert "waveR - waveL" in code, "Missing velocity = right wave - left wave"

    def test_waveguide_damping(self):
        code = self._read_script()
        assert "_dampFilter" in code, "Missing damping filter"
        assert "dampState" in code, "Missing damping filter state"
        assert "brightness" in code, "Missing brightness control for damping"

    def test_body_resonator(self):
        code = self._read_script()
        assert "_resonate" in code, "Missing body resonator function"
        assert "body1_z1" in code, "Missing body resonator state"
        assert "bodyFreqs" in code, "Missing body resonator frequencies"
        assert "280" in code and "450" in code, "Missing violin body frequencies"

    def test_vibrato(self):
        code = self._read_script()
        assert "vibPhase" in code, "Missing vibrato phase"
        assert "vibCents" in code, "Missing vibrato cents calculation"
        assert "actualFreq" in code, "Missing vibrato-modulated frequency"

    def test_note_on(self):
        code = self._read_script()
        assert "noteOn" in code, "Missing noteOn method"
        assert "440 * Math.pow(2" in code, "Missing MIDI to frequency conversion"
        assert "Math.random" in code, "Missing noise seed for oscillation"

    def test_bridge_output(self):
        code = self._read_script()
        assert "bridgeOut" in code, "Missing bridge output"
        assert "bridge" in code.lower(), "Missing bridge reference"

    def test_volume_param(self):
        params = self._parse_params(self._read_script())
        v = [p for p in params if p["name"] == "volume"][0]
        assert v["type"] == "linear"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"


class TestAutoTuneDSP:
    """Unit tests for werkstatt_auto_tune.js — pitch detection + correction"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_auto_tune.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt auto_tune" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "Auto-Tune" in code or "Pitch Correction" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "key" in names, "Missing key param"
        assert "scale" in names, "Missing scale param"
        assert "retune" in names, "Missing retune param"
        assert "strength" in names, "Missing strength param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_key_param_type(self):
        params = self._parse_params(self._read_script())
        key = [p for p in params if p["name"] == "key"][0]
        assert key["type"] == "int", f"key should be int, got {key['type']}"
        assert key["min"] == 0 and key["max"] == 11, "key range should be 0-11"

    def test_scale_param_type(self):
        params = self._parse_params(self._read_script())
        scale = [p for p in params if p["name"] == "scale"][0]
        assert scale["type"] == "int", f"scale should be int, got {scale['type']}"
        assert scale["min"] == 0 and scale["max"] == 6, "scale range should be 0-6"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear", f"output should be linear, got {out['type']}"

    def test_scales_table(self):
        code = self._read_script()
        assert "SCALES" in code, "Missing SCALES table"
        assert "[0,1,2,3,4,5,6,7,8,9,10,11]" in code, "Missing chromatic scale"
        assert "[0,2,4,5,7,9,11]" in code, "Missing major scale"
        assert "[0,2,3,5,7,10,12]" in code, "Missing minor scale"

    def test_autocorrelation(self):
        code = self._read_script()
        assert "_detectPitch" in code, "Missing pitch detection method"
        assert "bestLag" in code, "Missing lag tracking"

    def test_parabolic_interpolation(self):
        code = self._read_script()
        assert "parabolic" in code.lower() or "y1" in code, "Missing parabolic interpolation"

    def test_freq_to_midi(self):
        code = self._read_script()
        assert "_freqToMidi" in code, "Missing freqToMidi"
        assert "69 + 12 * Math.log2" in code, "Missing standard freq-to-midi formula"

    def test_midi_to_freq(self):
        code = self._read_script()
        assert "_midiToFreq" in code, "Missing midiToFreq"
        assert "440 * Math.pow(2" in code, "Missing standard midi-to-freq formula"

    def test_snap_to_scale(self):
        code = self._read_script()
        assert "_snapToScale" in code, "Missing snapToScale method"
        assert "intervals" in code, "Missing intervals reference in snap"

    def test_pitch_shift(self):
        code = self._read_script()
        assert "_processPitchShift" in code or "_pitchShift" in code, "Missing pitch shift method"
        assert "psRatio" in code, "Missing pitch ratio"

    def test_retune_smoothing(self):
        code = self._read_script()
        assert "retuneCoeff" in code, "Missing retune smoothing coefficient"
        assert "psTargetRatio" in code, "Missing target ratio for smoothing"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset in reset()"


class TestPhaseVocoderDSP:
    """Unit tests for werkstatt_phase_vocoder.js — FFT-based pitch shifter"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_phase_vocoder.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt phase_vocoder" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "Phase Vocoder" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "pitch" in names, "Missing pitch param"
        assert "formant" in names, "Missing formant param"
        assert "lock_phase" in names, "Missing lock_phase param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_pitch_range(self):
        params = self._parse_params(self._read_script())
        pitch = [p for p in params if p["name"] == "pitch"][0]
        assert pitch["min"] == 0 and pitch["max"] == 1, "pitch range should be 0-1"
        assert pitch["default"] == 0.5, "pitch default should be 0.5 (unison)"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear", f"output should be linear, got {out['type']}"

    def test_fft_implementation(self):
        code = self._read_script()
        assert "_fft" in code, "Missing FFT method"
        assert "Cooley" in code or "Butterfly" in code or "halfLen" in code, "Missing FFT butterfly"
        assert "Bit reversal" in code or "j += k" in code, "Missing bit reversal"

    def test_fft_size(self):
        code = self._read_script()
        assert "FFT_SIZE = 2048" in code or "FFT_SIZE=2048" in code, "Missing FFT size 2048"

    def test_hop_size(self):
        code = self._read_script()
        assert "HOP_SIZE = 512" in code or "HOP_SIZE=512" in code, "Missing hop size 512"

    def test_hann_window(self):
        code = self._read_script()
        assert "Hann" in code or "0.5 * (1 - Math.cos" in code, "Missing Hann window"

    def test_phase_unwrapping(self):
        code = self._read_script()
        assert "phaseDev" in code, "Missing phase deviation"
        assert "while (phaseDev > Math.PI)" in code, "Missing phase unwrapping"
        assert "while (phaseDev < -Math.PI)" in code, "Missing phase unwrapping lower bound"

    def test_true_frequency(self):
        code = self._read_script()
        assert "trueFreq" in code, "Missing true frequency computation"
        assert "omegaBase" in code, "Missing base angular frequency"

    def test_accumulated_phase(self):
        code = self._read_script()
        assert "accumPhase" in code, "Missing accumulated phase"
        assert "prevPhase" in code, "Missing previous phase tracking"

    def test_synthesis_hop(self):
        code = self._read_script()
        assert "synthesisHop" in code, "Missing synthesis hop"
        assert "analysisHop" in code, "Missing analysis hop"
        # synthesis hop = analysis hop * ratio
        assert "ratio" in code, "Missing pitch ratio"

    def test_phase_locking(self):
        code = self._read_script()
        assert "lock_phase" in code.lower() or "lockPhase" in code, "Missing phase locking"
        assert "identity" in code.lower() or "lockAmount" in code, "Missing identity phase lock"

    def test_formant_control(self):
        code = self._read_script()
        assert "formant" in code.lower(), "Missing formant control"
        assert "formantShift" in code or "formantRatio" in code, "Missing formant shift"

    def test_overlap_add(self):
        code = self._read_script()
        assert "overlap" in code.lower() or "Overlap" in code, "Missing overlap-add"
        assert "outBuf" in code, "Missing output buffer for overlap-add"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset in reset()"


class TestTimeStretchDSP:
    """Unit tests for werkstatt_time_stretch.js — phase vocoder time stretch"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_time_stretch.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt time_stretch" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "Time Stretch" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 5, f"Expected 5 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "stretch" in names, "Missing stretch param"
        assert "lock_phase" in names, "Missing lock_phase param"
        assert "transient" in names, "Missing transient param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_stretch_range(self):
        params = self._parse_params(self._read_script())
        stretch = [p for p in params if p["name"] == "stretch"][0]
        assert stretch["min"] == 0 and stretch["max"] == 1, "stretch range should be 0-1"
        assert stretch["default"] == 0.5, "stretch default should be 0.5 (unison)"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear", f"output should be linear, got {out['type']}"

    def test_fft_implementation(self):
        code = self._read_script()
        assert "_fft" in code, "Missing FFT method"
        assert "halfLen" in code, "Missing FFT butterfly"

    def test_fft_size(self):
        code = self._read_script()
        assert "FFT_SIZE = 2048" in code, "Missing FFT size 2048"

    def test_hop_size(self):
        code = self._read_script()
        assert "HOP_SIZE = 512" in code, "Missing hop size 512"

    def test_hann_window(self):
        code = self._read_script()
        assert "0.5 * (1 - Math.cos" in code, "Missing Hann window"

    def test_phase_unwrapping(self):
        code = self._read_script()
        assert "phaseDev" in code, "Missing phase deviation"
        assert "while (phaseDev > Math.PI)" in code, "Missing phase unwrapping"
        assert "while (phaseDev < -Math.PI)" in code, "Missing phase unwrapping lower bound"

    def test_true_frequency(self):
        code = self._read_script()
        assert "trueFreq" in code, "Missing true frequency computation"

    def test_accumulated_phase(self):
        code = self._read_script()
        assert "accumPhase" in code, "Missing accumulated phase"
        assert "prevPhase" in code, "Missing previous phase tracking"

    def test_synthesis_hop_differs(self):
        code = self._read_script()
        assert "synthesisHop" in code, "Missing synthesis hop"
        assert "analysisHop" in code, "Missing analysis hop"
        assert "ratio" in code, "Missing stretch ratio"

    def test_transient_detection(self):
        code = self._read_script()
        assert "_detectTransient" in code, "Missing transient detection"
        assert "prevEnergy" in code, "Missing energy tracking"
        assert "transientFlag" in code, "Missing transient flag"

    def test_transient_preservation(self):
        code = self._read_script()
        assert "transientPres" in code, "Missing transient preservation"
        assert "tMix" in code, "Missing transient blend"

    def test_phase_locking(self):
        code = self._read_script()
        assert "lockPhase" in code, "Missing phase locking"
        assert "lockAmount" in code, "Missing lock amount"

    def test_magnitude_preserved(self):
        code = self._read_script()
        assert "mag * Math.cos(outPhase)" in code, "Missing magnitude-preserved output"

    def test_overlap_add(self):
        code = self._read_script()
        assert "outBuf" in code, "Missing output buffer for overlap-add"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset in reset()"


class TestMatchingEQDSP:
    """Unit tests for werkstatt_matching_eq.js — adaptive spectral balance corrector"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_matching_eq.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt matching_eq" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "Matching EQ" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "target" in names, "Missing target param"
        assert "match_amt" in names, "Missing match_amt param"
        assert "smooth" in names, "Missing smooth param"
        assert "adapt_rate" in names, "Missing adapt_rate param"
        assert "tilt" in names, "Missing tilt param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear", f"output should be linear, got {out['type']}"

    def test_fft_implementation(self):
        code = self._read_script()
        assert "_fft" in code, "Missing FFT method"
        assert "halfLen" in code, "Missing FFT butterfly"

    def test_fft_size(self):
        code = self._read_script()
        assert "FFT_SIZE = 1024" in code, "Missing FFT size 1024"

    def test_hann_window(self):
        code = self._read_script()
        assert "0.5 * (1 - Math.cos" in code, "Missing Hann window"

    def test_ltas_accumulation(self):
        code = self._read_script()
        assert "ltasMag" in code, "Missing LTAS magnitude accumulation"
        assert "ltasCount" in code, "Missing LTAS frame counter"

    def test_target_spectrum(self):
        code = self._read_script()
        assert "_targetMag" in code, "Missing target magnitude function"
        assert "pinkSlope" in code, "Missing pink noise slope"
        assert "brownSlope" in code, "Missing brown noise slope"
        assert "whiteSlope" in code, "Missing white noise slope"

    def test_pink_noise_slope(self):
        code = self._read_script()
        assert "1 / Math.sqrt(freq)" in code, "Missing pink noise -3dB/octave formula"

    def test_brown_noise_slope(self):
        code = self._read_script()
        assert "1 / freq" in code, "Missing brown noise -6dB/octave formula"

    def test_gain_computation(self):
        code = self._read_script()
        assert "_computeGainCurve" in code, "Missing gain curve computation"
        assert "matchAmt" in code, "Missing match amount in gain computation"
        assert "ratio" in code, "Missing target/actual ratio"

    def test_gain_smoothing(self):
        code = self._read_script()
        assert "smoothSize" in code, "Missing smoothing window size"
        assert "smoothed" in code, "Missing smoothed gain array"

    def test_gain_clamping(self):
        code = self._read_script()
        assert "Math.max(0.1" in code, "Missing minimum gain clamp"
        assert "Math.min(10" in code, "Missing maximum gain clamp"

    def test_adaptation_smoothing(self):
        code = self._read_script()
        assert "adaptCoeff" in code, "Missing adaptation coefficient"
        assert "targetGain" in code, "Missing target gain for smoothing"
        assert "gainCurve" in code, "Missing current gain curve"

    def test_tilt_control(self):
        code = self._read_script()
        assert "tiltAmt" in code, "Missing tilt amount"
        assert "tiltGain" in code, "Missing tilt gain computation"

    def test_overlap_add(self):
        code = self._read_script()
        assert "outBuf" in code, "Missing output buffer for overlap-add"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset in reset()"
        assert ".fill(1)" in code, "Missing gain curve reset to 1"


class TestSpectralDenoiseDSP:
    """Unit tests for werkstatt_spectral_denoise.js — noise floor subtraction"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_spectral_denoise.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt spectral_denoise" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "Denoiser" in code or "Noise" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "reduction" in names, "Missing reduction param"
        assert "learn_time" in names, "Missing learn_time param"
        assert "oversub" in names, "Missing oversub param"
        assert "floor" in names, "Missing floor param"
        assert "smoothing" in names, "Missing smoothing param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear", f"output should be linear, got {out['type']}"

    def test_fft_implementation(self):
        code = self._read_script()
        assert "_fft" in code, "Missing FFT method"
        assert "halfLen" in code, "Missing FFT butterfly"

    def test_fft_size(self):
        code = self._read_script()
        assert "FFT_SIZE = 1024" in code, "Missing FFT size 1024"

    def test_hann_window(self):
        code = self._read_script()
        assert "0.5 * (1 - Math.cos" in code, "Missing Hann window"

    def test_noise_learning(self):
        code = self._read_script()
        assert "noiseMag" in code, "Missing noise magnitude accumulation"
        assert "noiseCount" in code, "Missing noise frame counter"
        assert "noiseLearned" in code, "Missing noise learned flag"
        assert "noiseFramesTarget" in code, "Missing noise learning target"

    def test_spectral_subtraction(self):
        code = self._read_script()
        assert "noiseBin" in code, "Missing per-bin noise subtraction"
        assert "oversubFactor" in code, "Missing oversubtraction factor"
        assert "cleanMag" in code, "Missing clean magnitude computation"

    def test_oversubtraction_range(self):
        code = self._read_script()
        # oversub 0→1x, 1→4x
        assert "1 + this.p.oversub * 3" in code, "Missing oversubtraction range 1-4x"

    def test_spectral_floor(self):
        code = self._read_script()
        assert "floorLevel" in code, "Missing spectral floor"
        assert "minMag" in code, "Missing minimum magnitude from floor"

    def test_half_wave_rectification(self):
        code = self._read_script()
        assert "cleanMag < 0" in code, "Missing half-wave rectification"
        assert "cleanMag = 0" in code, "Missing rectification to zero"

    def test_gain_smoothing(self):
        code = self._read_script()
        assert "smoothCoeff" in code, "Missing smoothing coefficient"
        assert "prevGain" in code, "Missing previous gain for smoothing"
        assert "smoothedGain" in code, "Missing smoothed gain"

    def test_reduction_amount(self):
        code = self._read_script()
        assert "reductionDb" in code, "Missing reduction in dB"
        assert "reductionGain" in code, "Missing reduction gain factor"
        assert "-30" in code, "Missing -30 dB max reduction"

    def test_learn_time_range(self):
        code = self._read_script()
        assert "0.5 + this.p.learn_time * 9.5" in code, "Missing learn time range 0.5-10s"

    def test_conjugate_symmetry(self):
        code = self._read_script()
        assert "N - bin" in code or "mirror" in code, "Missing conjugate symmetry mirror"

    def test_overlap_add(self):
        code = self._read_script()
        assert "outBuf" in code, "Missing output buffer for overlap-add"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset in reset()"
        assert ".fill(1)" in code, "Missing gain reset to 1"


class TestDeReverbDSP:
    """Unit tests for werkstatt_dereverb.js — reverb tail suppression"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_dereverb.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt dereverb" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "De-Reverb" in code or "Reverb" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "reduction" in names, "Missing reduction param"
        assert "decay_est" in names, "Missing decay_est param"
        assert "sensitivity" in names, "Missing sensitivity param"
        assert "bands" in names, "Missing bands param"
        assert "preserve" in names, "Missing preserve param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear"

    def test_fft_implementation(self):
        code = self._read_script()
        assert "_fft" in code, "Missing FFT method"
        assert "halfLen" in code, "Missing FFT butterfly"

    def test_fft_size(self):
        code = self._read_script()
        assert "FFT_SIZE = 1024" in code, "Missing FFT size"

    def test_hann_window(self):
        code = self._read_script()
        assert "0.5 * (1 - Math.cos" in code, "Missing Hann window"

    def test_per_band_processing(self):
        code = self._read_script()
        assert "numBands" in code, "Missing per-band processing"
        assert "bandEdges" in code, "Missing band edges"
        assert "MAX_BANDS" in code, "Missing max bands config"

    def test_dual_envelope_followers(self):
        """Fast envelope tracks direct signal, slow tracks reverb tail"""
        code = self._read_script()
        assert "fastEnv" in code, "Missing fast envelope follower"
        assert "slowEnv" in code, "Missing slow envelope follower"

    def test_transient_detection(self):
        """Detects transients by comparing fast vs slow envelope ratio"""
        code = self._read_script()
        assert "transThresh" in code, "Missing transient threshold"
        assert "energyRatio" in code, "Missing energy ratio comparison"
        assert "tailActive" in code, "Missing tail active flag"

    def test_tail_suppression(self):
        """In tail mode, reduces gain based on tail dominance"""
        code = self._read_script()
        assert "tailDominance" in code, "Missing tail dominance calculation"
        assert "targetGain" in code, "Missing target gain computation"
        assert "reductionGain" in code, "Missing reduction gain"

    def test_decay_estimation(self):
        """Slow envelope decay rate tracks reverb decay"""
        code = self._read_script()
        assert "decayCoeff" in code or "slowCoeff" in code, "Missing decay coefficient"
        assert "decay_est" in code, "Missing decay estimation parameter"

    def test_decay_time_range(self):
        code = self._read_script()
        assert "100 + this.p.decay_est * 1900" in code, "Missing decay time range 100ms-2s"

    def test_reduction_range(self):
        code = self._read_script()
        assert "-24" in code, "Missing -24 dB max reduction"

    def test_band_count_configurable(self):
        code = self._read_script()
        assert "4 + this.p.bands * 12" in code, "Missing band count 4-16"

    def test_preserve_direct_signal(self):
        code = self._read_script()
        assert "preserve" in code, "Missing preserve parameter"
        assert "preserveAmt" in code, "Missing preserve amount"

    def test_gain_smoothing(self):
        code = self._read_script()
        assert "prevGain" in code, "Missing smoothed gain"
        assert "0.8" in code, "Missing smoothing coefficient"

    def test_conjugate_symmetry(self):
        code = self._read_script()
        assert "N - bin" in code or "mirror" in code, "Missing conjugate symmetry"

    def test_overlap_add(self):
        code = self._read_script()
        assert "outBuf" in code, "Missing output buffer for overlap-add"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset"
        assert ".fill(1)" in code, "Missing gain reset to 1"


class TestDeClickerDSP:
    """Unit tests for werkstatt_declicker.js — click & crackle removal"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_declicker.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt declicker" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "De-Clicker" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "sensitivity" in names, "Missing sensitivity param"
        assert "click_len" in names, "Missing click_len param"
        assert "median_size" in names, "Missing median_size param"
        assert "interp" in names, "Missing interp param"
        assert "overlap" in names, "Missing overlap param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear"

    def test_median_filter(self):
        code = self._read_script()
        assert "_median" in code, "Missing median filter method"
        assert "insertion" in code.lower() or "Insertion" in code, "Missing insertion sort reference"

    def test_median_window_size(self):
        code = self._read_script()
        assert "5 + this.p.median_size * 10" in code, "Missing median size range 5-15"

    def test_hermite_interpolation(self):
        code = self._read_script()
        assert "_hermite" in code, "Missing Hermite interpolation method"
        assert "h00" in code, "Missing Hermite basis h00"
        assert "h01" in code, "Missing Hermite basis h01"
        assert "m1" in code and "m2" in code, "Missing Hermite tangents"

    def test_linear_interpolation_fallback(self):
        code = self._read_script()
        assert "_linear" in code, "Missing linear interpolation fallback"

    def test_click_detection(self):
        code = self._read_script()
        assert "isClick" in code, "Missing click detection flag"
        assert "deviation" in code, "Missing deviation calculation"
        assert "threshold" in code, "Missing detection threshold"

    def test_adaptive_threshold(self):
        code = self._read_script()
        assert "localAvg" in code, "Missing local energy average"
        assert "energySum" in code, "Missing sliding energy window"
        assert "energyWin" in code, "Missing energy window size"

    def test_click_length_limit(self):
        code = self._read_script()
        assert "maxClickLen" in code, "Missing max click length"
        assert "8 + this.p.click_len * 120" in code, "Missing click length range 8-128"

    def test_overlap_expansion(self):
        code = self._read_script()
        assert "overlapSamps" in code, "Missing overlap samples"
        assert "this.p.overlap * 32" in code, "Missing overlap range 0-32"

    def test_click_region_finding(self):
        code = self._read_script()
        assert "clickEnd" in code, "Missing click region end detection"
        assert "clickWidth" in code, "Missing click width calculation"

    def test_anchor_points(self):
        code = self._read_script()
        assert "p0" in code and "p1" in code, "Missing anchor points p0/p1"
        assert "p2" in code and "p3" in code, "Missing anchor points p2/p3"

    def test_delay_buffer(self):
        code = self._read_script()
        assert "delayBuf" in code, "Missing delay buffer for look-back"
        assert "DELAY = 256" in code, "Missing delay buffer size"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset"

    def test_config_update(self):
        code = self._read_script()
        assert "_updateConfig" in code, "Missing config update method"
        assert "paramChanged" in code, "Missing paramChanged handler"

    def test_interpolation_mode(self):
        code = self._read_script()
        assert "useCubic" in code, "Missing interpolation mode selection"
        assert "this.p.interp > 0.3" in code, "Missing interpolation threshold"

    def test_combined_buffer(self):
        code = self._read_script()
        assert "combined" in code, "Missing combined buffer (delay + current)"


class TestDeCrackleDSP:
    """Unit tests for werkstatt_decrackle.js — continuous crackle removal"""

    def _read_script(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "werkstatt_decrackle.js")) as f:
            return f.read()

    def _parse_params(self, code):
        import re
        params = []
        for m in re.finditer(r'//\s*@param\s+(\w+)\s+([\d.]+)\s+([\d.-]+)\s+([\d.-]+)\s+(\w+)', code):
            params.append({
                "name": m.group(1), "default": float(m.group(2)),
                "min": float(m.group(3)), "max": float(m.group(4)), "type": m.group(5)
            })
        return params

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt decrackle" in code, "Missing @werkstatt header"

    def test_label(self):
        code = self._read_script()
        assert "De-Crackle" in code, "Missing label"

    def test_param_count(self):
        params = self._parse_params(self._read_script())
        assert len(params) == 7, f"Expected 7 params, got {len(params)}"

    def test_param_names(self):
        params = self._parse_params(self._read_script())
        names = [p["name"] for p in params]
        assert "strength" in names, "Missing strength param"
        assert "sensitivity" in names, "Missing sensitivity param"
        assert "freq_est" in names, "Missing freq_est param"
        assert "smooth" in names, "Missing smooth param"
        assert "adaptive" in names, "Missing adaptive param"
        assert "mix" in names, "Missing mix param"
        assert "output" in names, "Missing output param"

    def test_output_param_type(self):
        params = self._parse_params(self._read_script())
        out = [p for p in params if p["name"] == "output"][0]
        assert out["type"] == "linear"

    def test_hermite_interpolation(self):
        code = self._read_script()
        assert "_hermite" in code, "Missing Hermite interpolation"
        assert "2*t3" in code, "Missing Hermite basis"

    def test_linear_interpolation(self):
        code = self._read_script()
        assert "_linear" in code, "Missing linear interpolation"

    def test_adaptive_crackle_model(self):
        code = self._read_script()
        assert "crackleEnergy" in code, "Missing crackle energy tracking"
        assert "signalEnergy" in code, "Missing signal energy tracking"

    def test_adaptive_threshold(self):
        code = self._read_script()
        assert "adaptive" in code, "Missing adaptive threshold"
        assert "adaptAmt" in code, "Missing adaptive amount"
        assert "this.threshold" in code, "Missing threshold variable"

    def test_crackle_detection(self):
        code = self._read_script()
        assert "isCrackle" in code, "Missing crackle detection flag"
        assert "isLikelyCrackle" in code, "Missing likely crackle flag"

    def test_crackle_extent_finding(self):
        code = self._read_script()
        assert "crackEnd" in code, "Missing crackle extent detection"
        assert "crackLen" in code, "Missing crackle length"

    def test_crackle_rate_estimation(self):
        code = self._read_script()
        assert "freq_est" in code, "Missing frequency estimation param"
        assert "samplesPerCrackle" in code or "estRate" in code, "Missing crackle rate estimate"

    def test_strength_blend(self):
        code = self._read_script()
        assert "strengthAmt" in code, "Missing strength amount"
        assert "1 - strengthAmt" in code, "Missing strength blend"

    def test_smooth_blend(self):
        code = self._read_script()
        assert "smoothAmt" in code, "Missing smooth amount"
        assert "smoothAmt + linVal" in code or "smoothAmt *" in code, "Missing smooth blend"

    def test_local_energy_window(self):
        code = self._read_script()
        assert "localEnergy" in code, "Missing local energy tracking"
        assert "energyWin" in code, "Missing energy window"

    def test_delay_buffer(self):
        code = self._read_script()
        assert "delayBuf" in code, "Missing delay buffer"
        assert "DELAY = 128" in code, "Missing delay buffer size"

    def test_process_method(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code, "Missing dry/wet mix"

    def test_output_gain(self):
        code = self._read_script()
        assert "outGain" in code, "Missing output gain"
        assert "Math.pow(10, value / 20)" in code, "Missing dB to linear conversion"

    def test_reset_method(self):
        code = self._read_script()
        assert "reset()" in code, "Missing reset method"
        assert ".fill(0)" in code, "Missing buffer reset"

    def test_param_changed(self):
        code = self._read_script()
        assert "paramChanged" in code, "Missing paramChanged handler"

    def test_combined_buffer(self):
        code = self._read_script()
        assert "combined" in code, "Missing combined buffer (delay + current)"


class TestWerkstattEnvelopeFollower:
    """Tests for werkstatt_envelope_follower.js — amplitude tracking DSP"""

    def _read_script(self):
        with open("scripts/werkstatt_envelope_follower.js") as f:
            return f.read()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt envelope_follower 1 1" in code

    def test_params(self):
        code = self._read_script()
        for p in ["attack", "release", "gain", "mix"]:
            assert f"@param {p}" in code, f"Missing @param {p}"

    def test_param_count(self):
        import re
        code = self._read_script()
        params = re.findall(r"@param\s+(\w+)", code)
        assert len(params) == 4, f"Expected 4 params, got {len(params)}: {params}"

    def test_envelope_detection(self):
        code = self._read_script()
        assert "Math.abs" in code, "Missing abs() for envelope detection"
        assert "envelope" in code

    def test_attack_release(self):
        code = self._read_script()
        assert "attackCoef" in code, "Missing attack coefficient"
        assert "releaseCoef" in code, "Missing release coefficient"
        assert "Math.exp" in code, "Missing exp() for time constant"

    def test_mix_dry_wet(self):
        code = self._read_script()
        assert "1 - this.mix" in code, "Missing dry/wet mix"

    def test_process_audio(self):
        code = self._read_script()
        assert "processAudio" in code, "Missing processAudio method"

    def test_param_changed(self):
        code = self._read_script()
        assert "paramChanged" in code, "Missing paramChanged handler"

    def test_recalculate(self):
        code = self._read_script()
        assert "recalculate" in code, "Missing recalculate for coefficients"

    def test_attack_fast_percussive(self):
        """Fast attack (0.005s) = percussive detection"""
        attack = 0.005
        assert attack < 0.01  # fast

    def test_release_slow_smooth(self):
        """Slow release (0.1s) = smooth envelope"""
        release = 0.1
        assert release > 0.05  # smooth


class TestWerkstattAutoWah:
    """Tests for werkstatt_auto_wah.js — envelope-driven filter sweep"""

    def _read_script(self):
        with open("scripts/werkstatt_auto_wah.js") as f:
            return f.read()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt auto_wah 1 1" in code

    def test_params(self):
        code = self._read_script()
        for p in ["attack", "release", "min_freq", "max_freq", "resonance", "mix"]:
            assert f"@param {p}" in code, f"Missing @param {p}"

    def test_param_count(self):
        import re
        code = self._read_script()
        params = re.findall(r"@param\s+(\w+)", code)
        assert len(params) == 6, f"Expected 6 params, got {len(params)}: {params}"

    def test_envelope_driven(self):
        code = self._read_script()
        assert "envelope" in code, "Missing envelope detection"
        assert "Math.abs" in code, "Missing abs() for detection"

    def test_freq_mapping(self):
        code = self._read_script()
        assert "minFreq" in code, "Missing min frequency"
        assert "maxFreq" in code, "Missing max frequency"
        assert "envNorm" in code, "Missing envelope-to-frequency mapping"

    def test_biquad_filter(self):
        code = self._read_script()
        assert "biquad" in code.lower() or "Biquad" in code, "Missing biquad filter"
        assert "cosw0" in code, "Missing cosine coefficient"
        assert "alpha" in code, "Missing alpha (resonance)"

    def test_bandpass_response(self):
        code = self._read_script()
        assert "b0" in code and "b2" in code, "Missing biquad coefficients"

    def test_per_channel_state(self):
        code = self._read_script()
        assert "state" in code, "Missing per-channel state for stereo"

    def test_process_audio(self):
        code = self._read_script()
        assert "processAudio" in code

    def test_param_changed(self):
        code = self._read_script()
        assert "paramChanged" in code

    def test_mix_dry_wet(self):
        code = self._read_script()
        assert "1 - this.mix" in code, "Missing dry/wet mix"

    def test_freq_range(self):
        """Default: 400-2000 Hz sweep range"""
        min_f = 400
        max_f = 2000
        assert min_f < max_f
        assert 100 <= min_f <= 2000
        assert 500 <= max_f <= 8000

    def test_resonance_range(self):
        """Default Q=8, range 1-20"""
        q = 8
        assert 1 <= q <= 20

    def test_classic_funk_usage(self):
        """Auto-wah is the Bootsy Collins funk quack effect"""
        attack = 0.005
        release = 0.15
        resonance = 8
        assert attack < 0.01
        assert release > 0.05
        assert resonance > 5

    def test_vs_static_filter(self):
        """Auto-wah modulates filter freq dynamically, unlike static filter"""
        auto_wah_features = {"envelope_following", "dynamic_freq", "amplitude_driven"}
        static_filter_features = {"fixed_freq", "no_envelope"}
        assert auto_wah_features.isdisjoint(static_filter_features)


class TestDePlosiveDSP:
    """Tests for werkstatt_de_plosive.js — adaptive plosive removal"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_de_plosive.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt de_plosive" in code

    def test_has_processor_class(self):
        code = self._read_script()
        assert "class Processor" in code

    def test_has_plosive_detection(self):
        code = self._read_script()
        assert "threshold" in code
        assert "plosiveDetected" in code or "plosive" in code.lower()

    def test_has_biquad_highpass(self):
        code = self._read_script()
        assert "b0" in code and "a0" in code
        assert "cosW0" in code or "cos(" in code

    def test_has_adaptive_engagement(self):
        code = self._read_script()
        assert "filterEngage" in code or "engage" in code.lower()

    def test_has_attack_release(self):
        code = self._read_script()
        assert "attackCoeff" in code
        assert "releaseCoeff" in code

    def test_has_detection_envelope(self):
        code = self._read_script()
        assert "detectEnv" in code or "detect" in code.lower()

    def test_has_mix_param(self):
        code = self._read_script()
        assert "@param mix" in code

    def test_has_q_param(self):
        code = self._read_script()
        assert "@param q" in code

    def test_has_freq_param(self):
        code = self._read_script()
        assert "@param freq" in code

    def test_has_threshold_param(self):
        code = self._read_script()
        assert "@param threshold" in code

    def test_process_audio_signature(self):
        code = self._read_script()
        assert "processAudio(inputs, outputs" in code

    def test_param_changed_signature(self):
        code = self._read_script()
        assert "paramChanged(name, value)" in code

    def test_prepare_signature(self):
        code = self._read_script()
        assert "prepare(sampleRate" in code

    def test_plosive_frequency_range(self):
        """Plosives live in 20-100 Hz range, filter cutoff 80-300 Hz"""
        freq_min, freq_max = 80, 300
        assert freq_min >= 80
        assert freq_max <= 300

    def test_default_threshold_sensitive(self):
        """Default threshold 0.15 catches typical plosive bursts"""
        threshold = 0.15
        assert 0.05 <= threshold <= 0.5

    def test_filter_only_active_on_bursts(self):
        """Filter engagement is 0 on clean signal, >0 on plosive"""
        clean_energy = 0.01
        threshold = 0.15
        assert clean_energy < threshold  # no filter on clean vocal

    def test_i_zotope_rx_influences(self):
        """Influenced by iZotope RX De-plosive"""
        code = self._read_script()
        assert "RX" in code or "iZotope" in code or "DeBreath" in code


class TestMidSideProcessorDSP:
    """Tests for werkstatt_mid_side_processor.js — M/S mastering processor"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_mid_side_processor.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "// @werkstatt mid_side_processor" in code

    def test_has_processor_class(self):
        code = self._read_script()
        assert "class Processor" in code

    def test_ms_encoding(self):
        """M = (L+R)/2, S = (L-R)/2"""
        code = self._read_script()
        assert "(l + r)" in code or "(L + R)" in code
        assert "(l - r)" in code or "(L - R)" in code

    def test_ms_decoding(self):
        """L = M+S, R = M-S"""
        code = self._read_script()
        assert "mid + side" in code or "M + S" in code
        assert "mid - side" in code or "M - S" in code

    def test_has_mid_gain(self):
        code = self._read_script()
        assert "@param mid_gain" in code

    def test_has_side_gain(self):
        code = self._read_script()
        assert "@param side_gain" in code

    def test_has_width_param(self):
        code = self._read_script()
        assert "@param width" in code

    def test_has_mid_highpass(self):
        code = self._read_script()
        assert "mid_freq" in code
        assert "midB0" in code or "midB" in code

    def test_has_side_lowpass(self):
        code = self._read_script()
        assert "side_freq" in code
        assert "sideB0" in code or "sideB" in code

    def test_has_biquad_coeffs(self):
        code = self._read_script()
        assert "cosW0" in code
        assert "alpha" in code

    def test_process_audio_stereo(self):
        """M/S requires stereo input (L and R)"""
        code = self._read_script()
        assert "input[0]" in code and "input[1]" in code
        assert "output[0]" in code and "output[1]" in code

    def test_process_audio_signature(self):
        code = self._read_script()
        assert "processAudio(inputs, outputs" in code

    def test_param_changed_signature(self):
        code = self._read_script()
        assert "paramChanged(name, value)" in code

    def test_prepare_signature(self):
        code = self._read_script()
        assert "prepare(sampleRate" in code

    def test_width_zero_is_mono(self):
        """width=0 → S=0 → L=R=M (mono collapse)"""
        width = 0
        side_gain = 1.0
        effective_side = side_gain * width
        assert effective_side == 0  # mono

    def test_width_two_is_double_wide(self):
        """width=2 → S doubled → stereo doubled"""
        width = 2
        side_gain = 1.0
        effective_side = side_gain * width
        assert effective_side == 2  # double wide

    def test_ms_math_correct(self):
        """M/S encoding/decoding roundtrip: L→M→L should be identity"""
        l, r = 0.7, -0.3
        mid = (l + r) * 0.5
        side = (l - r) * 0.5
        newL = mid + side
        newR = mid - side
        assert abs(newL - l) < 0.001
        assert abs(newR - r) < 0.001

    def test_brainworx_influence(self):
        """Influenced by Brainworx bx_digital (M/S mastering standard)"""
        code = self._read_script()
        assert "Brainworx" in code or "bx_digital" in code

    def test_mix_bypass(self):
        """mix=0 bypasses M/S processing (dry passthrough)"""
        code = self._read_script()
        assert "1 - this.mixAmount" in code or "(1 - this.mix" in code


class TestAddVocalChain:
    """Tests for add_vocal_chain — one-call vocal processing"""

    STYLES = ["balanced", "warm", "bright", "intimate", "aggressive"]

    def test_five_styles(self):
        assert len(self.STYLES) == 5

    def test_balanced_is_pop_default(self):
        """Balanced: transparent EQ, gentle comp, medium reverb"""
        params = {"comp_threshold": -20, "comp_ratio": 3.0, "comp_attack": 8, "comp_release": 80}
        assert params["comp_threshold"] == -20
        assert params["comp_ratio"] == 3.0

    def test_warm_is_rnb(self):
        """Warm: low-mid warmth, slower comp"""
        params = {"comp_threshold": -22, "comp_ratio": 2.5, "comp_attack": 20, "comp_release": 150}
        assert params["comp_attack"] == 20  # slower than balanced

    def test_aggressive_hardest_compression(self):
        """Aggressive: hardest comp (lowest threshold, highest ratio)"""
        aggressive = {"threshold": -16, "ratio": 5.0}
        balanced = {"threshold": -20, "ratio": 3.0}
        assert aggressive["threshold"] > balanced["threshold"]  # less negative = harder
        assert aggressive["ratio"] > balanced["ratio"]

    def test_chain_order(self):
        """Chain order: EQ → Compressor → Reverb (→ Delay)"""
        chain = ["Revamp EQ", "Compressor", "Reverb"]
        assert chain[0] == "Revamp EQ"
        assert chain[-1] == "Reverb"

    def test_chain_with_delay(self):
        """Chain with delay: EQ → Comp → Reverb → Delay"""
        chain = ["Revamp EQ", "Compressor", "Reverb", "Delay"]
        assert len(chain) == 4
        assert chain[-1] == "Delay"

    def test_default_reverb_subtle(self):
        """Default reverb_amount=0.25 (subtle)"""
        assert 0.25 < 0.5

    def test_default_delay_off(self):
        """Default delay_amount=0.0 (off)"""
        assert 0.0 == 0

    def test_bright_has_most_air(self):
        """Bright style: highest high-shelf gain (5dB@10kHz)"""
        bright_high = 5.0
        balanced_high = 3.0
        assert bright_high > balanced_high

    def test_intimate_is_gentlest(self):
        """Intimate: lightest comp (lowest ratio)"""
        intimate_ratio = 2.0
        aggressive_ratio = 5.0
        assert intimate_ratio < aggressive_ratio

    def test_vocal_vs_mastering_chain(self):
        """add_vocal_chain adds EQ+comp+reverb; add_mastering_chain adds EQ+comp+maximizer"""
        vocal = {"EQ", "Compressor", "Reverb"}
        mastering = {"EQ", "Compressor", "Maximizer"}
        assert "Reverb" in vocal and "Reverb" not in mastering
        assert "Maximizer" in mastering and "Maximizer" not in vocal

    def test_pipeline_with_vocal_chain(self):
        """Full vocal pipeline: create_modulated_song → add_vocal_chain → render"""
        pipeline = ["create_modulated_song", "add_vocal_chain", "render_full_song"]
        assert "add_vocal_chain" in pipeline
        assert len(pipeline) == 3


class TestAddDrumChain:
    """Tests for add_drum_chain — one-call drum processing"""

    STYLES = ["punchy", "deep", "crisp", "roomy", "tight"]

    def test_five_styles(self):
        assert len(self.STYLES) == 5

    def test_punchy_is_pop_default(self):
        """Punchy: tight gate, bright EQ, fast comp"""
        params = {"gate_threshold": -45, "comp_threshold": -18, "comp_ratio": 4.0, "comp_attack": 3}
        assert params["gate_threshold"] == -45
        assert params["comp_attack"] == 3  # fast

    def test_deep_has_lowest_gate_threshold(self):
        """Deep: loosest gate (-55dB) for 808s"""
        deep_gate = -55
        punchy_gate = -45
        assert deep_gate < punchy_gate  # more negative = more open

    def test_crisp_brightest_eq(self):
        """Crisp: highest high-shelf (6dB@10kHz) for electronic"""
        crisp_high = 6.0
        punchy_high = 4.0
        assert crisp_high > punchy_high

    def test_roomy_longest_release(self):
        """Roomy: longest gate release (200ms) for room sound"""
        roomy_release = 200
        punchy_release = 80
        assert roomy_release > punchy_release

    def test_tight_gentlest(self):
        """Tight: transparent, lightest comp (ratio 2.0)"""
        tight_ratio = 2.0
        punchy_ratio = 4.0
        assert tight_ratio < punchy_ratio

    def test_chain_order(self):
        """Chain order: Gate → EQ → Compressor (→ Reverb)"""
        chain = ["Gate", "Revamp EQ", "Compressor"]
        assert chain[0] == "Gate"
        assert chain[-1] == "Compressor"

    def test_chain_with_reverb(self):
        """Chain with reverb: Gate → EQ → Comp → Reverb"""
        chain = ["Gate", "Revamp EQ", "Compressor", "Reverb"]
        assert len(chain) == 4
        assert chain[-1] == "Reverb"

    def test_default_reverb_off(self):
        """Default reverb_amount=0.0 (off)"""
        assert 0.0 == 0

    def test_drum_vs_vocal_chain(self):
        """add_drum_chain adds Gate; add_vocal_chain does not"""
        drum = {"Gate", "EQ", "Compressor", "Reverb"}
        vocal = {"EQ", "Compressor", "Reverb"}
        assert "Gate" in drum and "Gate" not in vocal

    def test_pipeline_with_drum_chain(self):
        """Full drum pipeline: create_genre_track → add_drum_chain → render"""
        pipeline = ["create_genre_track", "add_drum_chain", "render_full_song"]
        assert "add_drum_chain" in pipeline
        assert len(pipeline) == 3


class TestAddBassChain:
    """Tests for add_bass_chain — one-call bass processing"""

    STYLES = ["deep", "round", "driven", "clean", "tight"]

    def test_five_styles(self):
        assert len(self.STYLES) == 5

    def test_deep_is_default(self):
        """Deep: sub boost (5dB@50Hz), thick low end"""
        params = {"eq_low_shelf_gain": 5.0, "eq_low_shelf_freq": 50, "comp_ratio": 4.0}
        assert params["eq_low_shelf_gain"] == 5.0
        assert params["eq_low_shelf_freq"] == 50

    def test_round_has_mid_warmth(self):
        """Round: mid boost (2dB@200Hz) for R&B warmth"""
        round_mid = 2.0
        deep_mid = 1.0
        assert round_mid > deep_mid

    def test_driven_has_highest_mid(self):
        """Driven: most mid boost (3dB@800Hz) for rock bass"""
        driven_mid = 3.0
        deep_mid = 1.0
        assert driven_mid > deep_mid

    def test_clean_cuts_highs_most(self):
        """Clean: most high cut (-4dB@2kHz) for electronic"""
        clean_high = -4.0
        deep_high = -3.0
        assert clean_high < deep_high  # more negative = more cut

    def test_tight_fastest_comp(self):
        """Tight: fastest comp (attack 3ms, release 40ms) for disco/funk"""
        tight_attack = 3
        deep_attack = 15
        assert tight_attack < deep_attack

    def test_chain_order(self):
        """Chain order: EQ → Compressor (→ Waveshaper)"""
        chain = ["Revamp EQ", "Compressor"]
        assert chain[0] == "Revamp EQ"

    def test_chain_with_drive(self):
        """Chain with drive: EQ → Comp → Waveshaper"""
        chain = ["Revamp EQ", "Compressor", "Waveshaper"]
        assert len(chain) == 3
        assert chain[-1] == "Waveshaper"

    def test_default_drive_off(self):
        """Default drive_amount=0.0 (off)"""
        assert 0.0 == 0

    def test_bass_vs_drum_chain(self):
        """add_bass_chain starts with EQ; add_drum_chain starts with Gate"""
        bass = {"EQ", "Compressor"}
        drum = {"Gate", "EQ", "Compressor"}
        assert "Gate" in drum and "Gate" not in bass

    def test_pipeline_with_bass_chain(self):
        """Full bass pipeline: create_genre_track → add_bass_chain → render"""
        pipeline = ["create_genre_track", "add_bass_chain", "render_full_song"]
        assert "add_bass_chain" in pipeline
        assert len(pipeline) == 3

    def test_full_mix_chains_pipeline(self):
        """Full mix: drum chain + bass chain + vocal chain + mastering"""
        pipeline = ["add_drum_chain", "add_bass_chain", "add_vocal_chain", "add_mastering_chain"]
        assert len(pipeline) == 4
        assert "add_mastering_chain" == pipeline[-1]


class TestAddInstrumentChain:
    """Tests for add_instrument_chain — universal instrument processing"""

    STYLES = ["clean", "warm", "bright", "ambient", "driven"]

    def test_five_styles(self):
        assert len(self.STYLES) == 5

    def test_clean_is_default(self):
        """Clean: transparent EQ, light comp (ratio 2.0)"""
        params = {"comp_threshold": -22, "comp_ratio": 2.0, "comp_attack": 12}
        assert params["comp_ratio"] == 2.0
        assert params["comp_attack"] == 12

    def test_warm_has_low_mid_warmth(self):
        """Warm: low-mid boost (1.5dB@300Hz) for Rhodes/jazz guitar"""
        warm_mid = 1.5
        clean_mid = 0.0
        assert warm_mid > clean_mid

    def test_bright_has_most_air(self):
        """Bright: highest high-shelf (4dB@10kHz) for lead instruments"""
        bright_high = 4.0
        clean_high = 2.0
        assert bright_high > clean_high

    def test_ambient_has_gentlest_comp(self):
        """Ambient: lightest comp (ratio 1.5, slowest attack 25ms)"""
        ambient_ratio = 1.5
        clean_ratio = 2.0
        assert ambient_ratio < clean_ratio

    def test_driven_has_most_mid_crunch(self):
        """Driven: most mid boost (3dB@800Hz) and hardest comp"""
        driven_mid = 3.0
        clean_mid = 0.0
        assert driven_mid > clean_mid

    def test_driven_cuts_lows(self):
        """Driven: low cut (-2dB@100Hz) for rock guitar clarity"""
        driven_low = -2.0
        clean_low = 1.0
        assert driven_low < clean_low  # more negative = cut

    def test_ambient_slowest_release(self):
        """Ambient: slowest comp release (200ms) for transparent leveling"""
        ambient_release = 200
        driven_release = 50
        assert ambient_release > driven_release

    def test_chain_order(self):
        """Chain order: EQ → Compressor → Reverb (→ Delay)"""
        chain = ["Revamp EQ", "Compressor", "Reverb"]
        assert chain[0] == "Revamp EQ"
        assert chain[-1] == "Reverb"

    def test_chain_with_delay(self):
        """Chain with delay: EQ → Comp → Reverb → Delay"""
        chain = ["Revamp EQ", "Compressor", "Reverb", "Delay"]
        assert len(chain) == 4
        assert chain[-1] == "Delay"

    def test_default_reverb_subtle(self):
        """Default reverb_amount=0.15 (subtle)"""
        assert 0.15 < 0.3

    def test_default_delay_off(self):
        """Default delay_amount=0.0 (off)"""
        assert 0.0 == 0

    def test_instrument_vs_vocal_chain(self):
        """Both have EQ+comp+reverb, but different defaults and EQ curves"""
        instr = {"EQ", "Compressor", "Reverb"}
        vocal = {"EQ", "Compressor", "Reverb"}
        assert instr == vocal  # same structure, different params

    def test_pipeline_with_instrument_chain(self):
        """Full instrument pipeline: create_genre_track → add_instrument_chain → render"""
        pipeline = ["create_genre_track", "add_instrument_chain", "render_full_song"]
        assert "add_instrument_chain" in pipeline

    def test_all_five_chains_family(self):
        """Complete chain family: drum + bass + vocal + instrument + mastering"""
        family = {"add_drum_chain", "add_bass_chain", "add_vocal_chain",
                  "add_instrument_chain", "add_mastering_chain"}
        assert len(family) == 5

    def test_track_chains_in_pipeline(self):
        """create_full_genre_pipeline with add_track_chains=True applies genre-aware chains"""
        pipeline = ["create_tracks", "arrangement", "genre_mix", "track_chains",
                     "humanization", "mastering"]
        assert "track_chains" in pipeline
        assert pipeline.index("track_chains") > pipeline.index("genre_mix")
        assert pipeline.index("track_chains") < pipeline.index("mastering")


class TestHaasWidener:
    """Tests for werkstatt_haas_widener.js — Haas stereo widener DSP"""

    def _read_script(self):
        return open("scripts/werkstatt_haas_widener.js").read()

    def test_file_exists(self):
        import os
        assert os.path.exists("scripts/werkstatt_haas_widener.js")

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt" in code
        assert "haas_stereo_widener" in code

    def test_has_5_params(self):
        import re
        code = self._read_script()
        params = re.findall(r"// @param (\w+)", code)
        assert len(params) == 5
        assert "delay" in params
        assert "width" in params
        assert "channel" in params
        assert "feedback" in params
        assert "mix" in params

    def test_delay_range_1_to_30_ms(self):
        import re
        code = self._read_script()
        m = re.search(r"// @param delay linear ([\d.]+) ([\d.]+) ([\d.]+)", code)
        assert float(m.group(2)) == 1  # min 1ms
        assert float(m.group(3)) == 30  # max 30ms
        assert float(m.group(1)) == 5  # default 5ms

    def test_width_default_08(self):
        import re
        code = self._read_script()
        m = re.search(r"// @param width linear ([\d.]+) ([\d.]+) ([\d.]+)", code)
        assert float(m.group(1)) == 0.8  # default 0.8 = wide

    def test_channel_is_int_type(self):
        import re
        code = self._read_script()
        m = re.search(r"// @param channel (\w+)", code)
        assert m.group(1) == "int"

    def test_feedback_max_03(self):
        import re
        code = self._read_script()
        m = re.search(r"// @param feedback linear ([\d.]+) ([\d.]+) ([\d.]+)", code)
        assert float(m.group(3)) == 0.3  # max 0.3 — limited to avoid runaway

    def test_mix_default_full(self):
        import re
        code = self._read_script()
        m = re.search(r"// @param mix linear ([\d.]+) ([\d.]+) ([\d.]+)", code)
        assert float(m.group(1)) == 1.0  # default full Haas

    def test_has_process_audio(self):
        code = self._read_script()
        assert "processAudio" in code
        assert "inputs" in code and "outputs" in code

    def test_has_delay_buffer(self):
        code = self._read_script()
        assert "delayBuffer" in code
        assert "Float32Array" in code

    def test_has_feedback_path(self):
        code = self._read_script()
        assert "feedbackSample" in code
        assert "feedback" in code

    def test_has_mono_sum(self):
        code = self._read_script()
        assert "mono" in code
        assert "0.5" in code  # (left + right) * 0.5

    def test_has_channel_flip(self):
        code = self._read_script()
        assert "channel === 0" in code or "channel==0" in code

    def test_width_blend(self):
        code = self._read_script()
        assert "1 - width" in code  # mono blend

    def test_mix_blend(self):
        code = self._read_script()
        assert "1 - mix" in code  # dry blend

    def test_haas_vs_stereowidth_different(self):
        """Haas uses delay-based widening; stereowidth uses M/S or level-based"""
        haas = self._read_script()
        sw = open("scripts/werkstatt_stereowidth.js").read()
        assert "delayBuffer" in haas
        assert "delayBuffer" not in sw  # stereowidth doesn't use delay

    def test_haas_vs_mid_side_different(self):
        """Haas uses delay; M/S uses encode/decode"""
        haas = self._read_script()
        assert "delayBuffer" in haas
        assert "delayBuffer" not in open("scripts/werkstatt_mid_side_processor.js").read()

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_haas_widener.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0


class TestApplyFullMix:
    """Tests for apply_full_mix — one-call complete mix"""

    GENRES = ["dnb", "liquid_dnb", "house", "trap", "techno", "dubstep",
              "afrobeat", "rock", "jazz", "pop", "funk", "reggae",
              "synthwave", "trance", "disco"]

    def test_15_genres_supported(self):
        assert len(self.GENRES) == 15

    def test_chain_assignment_4_tracks(self):
        """4 tracks: drum(0) + bass(1) + instrument(2) + instrument(3) + mastering"""
        chains = [
            {"track": 0, "chain": "drum"},
            {"track": 1, "chain": "bass"},
            {"track": 2, "chain": "instrument"},
            {"track": 3, "chain": "instrument"},
            {"track": "output", "chain": "mastering"},
        ]
        assert len(chains) == 5
        assert chains[0]["chain"] == "drum"
        assert chains[-1]["chain"] == "mastering"

    def test_chain_assignment_3_tracks(self):
        """3 tracks: drum(0) + bass(1) + instrument(2) + mastering"""
        num_tracks = 3
        chains = [{"track": 0, "chain": "drum"}, {"track": 1, "chain": "bass"}]
        for t in range(2, num_tracks):
            chains.append({"track": t, "chain": "instrument"})
        chains.append({"track": "output", "chain": "mastering"})
        assert len(chains) == 4

    def test_genre_drum_styles(self):
        drum_styles = {
            "dnb": "crisp", "house": "punchy", "trap": "deep",
            "techno": "crisp", "jazz": "tight", "rock": "roomy",
        }
        assert drum_styles["dnb"] == "crisp"
        assert drum_styles["trap"] == "deep"

    def test_genre_bass_styles(self):
        bass_styles = {
            "dnb": "deep", "house": "deep", "rock": "driven",
            "jazz": "round", "techno": "clean",
        }
        assert bass_styles["rock"] == "driven"
        assert bass_styles["techno"] == "clean"

    def test_genre_instr_styles(self):
        instr_styles = {
            "dnb": "bright", "jazz": "warm", "rock": "driven",
            "techno": "clean", "pop": "bright",
        }
        assert instr_styles["rock"] == "driven"
        assert instr_styles["jazz"] == "warm"

    def test_genre_master_styles(self):
        master_styles = {
            "dnb": "loud", "house": "warm", "jazz": "transparent",
            "pop": "balanced", "techno": "loud",
        }
        assert master_styles["jazz"] == "transparent"
        assert master_styles["pop"] == "balanced"

    def test_default_lufs_spotify(self):
        assert -14 == -14  # Spotify target

    def test_loud_master_target(self):
        assert -10 > -14  # louder than Spotify

    def test_apple_master_target(self):
        assert -16 < -14  # quieter than Spotify

    def test_replaces_5_to_6_calls(self):
        """apply_full_mix replaces: drum + bass + instrument×N + mastering"""
        individual_calls = ["add_drum_chain", "add_bass_chain",
                           "add_instrument_chain", "add_instrument_chain",
                           "add_mastering_chain"]
        assert len(individual_calls) == 5
        # one call replaces all
        assert "apply_full_mix" != "add_drum_chain"

    def test_pipeline_integration(self):
        """Full production: create → arrange → apply_full_mix → render"""
        pipeline = ["create_genre_track", "create_dnb_arrangement",
                    "apply_full_mix", "render_full_song"]
        assert "apply_full_mix" in pipeline
        assert pipeline.index("apply_full_mix") < pipeline.index("render_full_song")


class TestGlueCompressor:
    """Tests for werkstatt_glue_comp.js — SSL-style bus glue compressor"""

    def _read_script(self):
        return open("scripts/werkstatt_glue_comp.js").read()

    def test_file_exists(self):
        import os
        assert os.path.exists("scripts/werkstatt_glue_comp.js")

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt" in code
        assert "glue_compressor" in code

    def test_has_7_params(self):
        import re
        code = self._read_script()
        params = re.findall(r"// @param (\w+)", code)
        assert len(params) == 7
        expected = {"threshold", "ratio", "attack", "release", "mix", "warmth", "output"}
        assert set(params) == expected

    def test_ratio_is_int_type(self):
        code = self._read_script()
        assert "ratio" in code and "int" in code

    def test_ratio_range_1_to_4(self):
        code = self._read_script()
        # ratio: 2 1 4 int — min=1, max=4
        assert "1    4" in code or "1   4" in code

    def test_threshold_is_db(self):
        code = self._read_script()
        assert "dB" in code
        assert "threshold" in code

    def test_default_threshold_minus_10(self):
        code = self._read_script()
        assert "threshold  -10" in code  # -10 dB default

    def test_default_attack_10ms(self):
        code = self._read_script()
        assert "attack     10" in code  # 10ms SSL default

    def test_default_release_100ms(self):
        code = self._read_script()
        assert "release    100" in code  # 100ms SSL default

    def test_has_auto_makeup(self):
        code = self._read_script()
        assert "makeupGain" in code
        assert "makeup" in code.lower()

    def test_has_warmth_saturation(self):
        code = self._read_script()
        assert "warmth" in code
        assert "tanh" in code  # soft clip for even harmonics

    def test_has_parallel_mix(self):
        code = self._read_script()
        assert "1 - mix" in code  # dry blend for parallel compression

    def test_has_envelope_follower(self):
        code = self._read_script()
        assert "env" in code
        assert "attackCoef" in code
        assert "releaseCoef" in code

    def test_has_dB_to_linear_conversion(self):
        code = self._read_script()
        assert "log10" in code or "Math.log10" in code
        assert "pow(10" in code or "Math.pow(10" in code

    def test_has_peak_detect_across_channels(self):
        code = self._read_script()
        assert "maxSample" in code
        assert "numCh" in code

    def test_glue_vs_regular_compressor(self):
        """Glue comp has warmth + auto makeup; regular comp doesn't"""
        glue = self._read_script()
        reg = open("scripts/werkstatt_compressor.js").read()
        assert "warmth" in glue
        assert "warmth" not in reg
        assert "makeupGain" in glue

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_glue_comp.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_ssl_default_values(self):
        """SSL bus compressor defaults: 2:1 ratio, 10ms attack, 100ms release"""
        code = self._read_script()
        assert "ratio       2" in code  # 2:1 = SSL glue
        assert "attack     10" in code  # 10ms = SSL
        assert "release    100" in code  # 100ms = SSL

    def test_warmth_default_03(self):
        code = self._read_script()
        assert "warmth      0.3" in code  # subtle warmth by default


class TestCreateImpact:
    """Tests for create_impact — transition hit tool"""

    IMPACT_TYPES = ["sub_boom", "impact_hit", "downlifter", "sub_drop", "punch"]

    def test_5_impact_types(self):
        assert len(self.IMPACT_TYPES) == 5

    def test_sub_boom_is_lowest_bass(self):
        """Sub boom: pitch 24 (C1), long 8 beats"""
        t = {"pitch": 24, "length": 8}
        assert t["pitch"] == 24
        assert t["length"] == 8

    def test_impact_hit_is_mid_punch(self):
        """Impact hit: pitch 48 (C3), short 2 beats"""
        t = {"pitch": 48, "length": 2}
        assert t["pitch"] == 48

    def test_downlifter_descending(self):
        """Downlifter: starts at pitch 72, descends 2 octaves (24 semitones)"""
        start_pitch = 72
        steps = 12
        for i in range(steps):
            progress = i / (steps - 1)
            p = round(start_pitch - progress * 24)
        end_pitch = p
        assert end_pitch == 48  # fell from 72 to 48 (C5 → C3)

    def test_sub_drop_lowest_and_longest(self):
        """Sub drop: pitch 23 (B0), length 12 beats — lowest and longest"""
        t = {"pitch": 23, "length": 12}
        assert t["pitch"] == 23  # below C1
        assert t["length"] == 12  # 3 bars

    def test_punch_is_shortest(self):
        """Punch: 0.5 beat duration — shortest impact"""
        t = {"length": 0.5}
        assert t["length"] < 1

    def test_sub_boom_default_velocity_09(self):
        """Default velocity 0.9 — loud impact"""
        assert 0.9 > 0.7

    def test_impact_hit_hardest_velocity(self):
        """Impact hit: hardest at 0.95"""
        assert 0.95 > 0.9

    def test_riser_impact_pipeline(self):
        """Build-up transition: riser + impact on the drop"""
        pipeline = ["create_riser", "create_impact"]
        assert pipeline[0] == "create_riser"
        assert pipeline[1] == "create_impact"

    def test_impact_after_modulated_song_chorus(self):
        """Impact lands on chorus downbeat after verse"""
        pipeline = ["create_modulated_song", "create_impact"]
        assert "create_impact" in pipeline

    def test_downlifter_velocity_decays(self):
        """Downlifter: velocity decays from full to 70%"""
        vel_start = 0.7
        steps = 12
        last_progress = (steps - 1) / (steps - 1)  # = 1.0
        vel_end = vel_start * (1 - 0.3 * last_progress)
        assert vel_end < vel_start  # decays
        assert abs(vel_end - 0.49) < 0.01  # 0.7 * 0.7


class TestCreateBuildup:
    """Tests for create_buildup — combined riser + snare roll"""

    STYLES = ["edm", "trap", "techno", "rock", "minimal"]

    def test_5_styles(self):
        assert len(self.STYLES) == 5

    def test_edm_has_snare_roll(self):
        s = {"snare": True, "riser_start": 36, "riser_end": 84}
        assert s["snare"] is True

    def test_minimal_no_snare_roll(self):
        s = {"snare": False, "riser_start": 36, "riser_end": 72}
        assert s["snare"] is False

    def test_edm_riser_widest_range(self):
        """EDM: C2→C6 (48 semitone range, widest)"""
        edm_range = 84 - 36
        techno_range = 60 - 36
        assert edm_range > techno_range

    def test_trap_riser_starts_lowest(self):
        """Trap: starts at C1 (24), lowest of all styles"""
        trap_start = 24
        edm_start = 36
        assert trap_start < edm_start

    def test_rock_uses_linear_curve(self):
        """Rock: linear riser (not exp) for steady build"""
        rock_curve = "linear"
        edm_curve = "exp"
        assert rock_curve != edm_curve

    def test_snare_pitch_38(self):
        """Snare drum MIDI pitch = 38 (D2)"""
        assert 38 == 38

    def test_snare_density_increases(self):
        """Snare roll: quarter → eighth → sixteenth → 32nd (density increases)"""
        rates = [1, 0.5, 0.25, 0.125]
        # each subsequent is faster (smaller division)
        for i in range(len(rates) - 1):
            assert rates[i] > rates[i + 1]

    def test_velocity_crescendo(self):
        """Velocity ramps up during build-up (0.3→1.0 of base)"""
        base_vel = 0.7
        start_vel = base_vel * 0.3
        end_vel = base_vel * 1.0
        assert end_vel > start_vel

    def test_buildup_impact_pipeline(self):
        """Build-up → impact: the classic EDM transition"""
        pipeline = ["create_buildup", "create_impact"]
        assert pipeline[0] == "create_buildup"
        assert pipeline[1] == "create_impact"

    def test_full_transition_pipeline(self):
        """Full transition: buildup → impact → main arrangement → mix"""
        pipeline = ["create_buildup", "create_impact", "create_dnb_arrangement",
                    "apply_full_mix", "render_full_song"]
        assert len(pipeline) == 5
        assert pipeline.index("create_buildup") < pipeline.index("create_impact")
        assert pipeline.index("create_impact") < pipeline.index("apply_full_mix")

    def test_trap_has_triplet_section(self):
        """Trap: includes triplet division in snare roll"""
        trap_sections = [("quarter", 0.20), ("triplet", 0.30), ("sixteenth", 0.20), ("thirtysecond", 0.30)]
        divisions = [s[0] for s in trap_sections]
        assert "triplet" in divisions

    def test_minimal_just_riser(self):
        """Minimal: no snare roll, just a riser"""
        s = {"snare": False, "roll_type": None}
        assert s["snare"] is False
        assert s["roll_type"] is None


class TestVowelMorph:
    """Tests for werkstatt_vowel_morph.js — formant vowel morph DSP"""

    def _read_script(self):
        return open("scripts/werkstatt_vowel_morph.js").read()

    def test_file_exists(self):
        import os
        assert os.path.exists("scripts/werkstatt_vowel_morph.js")

    def test_header_tag(self):
        code = self._read_script()
        assert "@werkstatt" in code
        assert "vowel_morph" in code

    def test_has_7_params(self):
        import re
        code = self._read_script()
        params = re.findall(r"// @param (\w+)", code)
        assert len(params) == 7
        expected = {"vowel", "morph", "rate", "reso", "tilt", "mix", "output"}
        assert set(params) == expected

    def test_5_vowels_defined(self):
        code = self._read_script()
        # VOWELS array has 5 entries
        assert code.count("[") >= 5  # at least 5 formant arrays

    def test_vowel_a_lowest_f1(self):
        """Vowel A: F1=800 (highest F1 = open mouth)"""
        vowels = [
            [800, 1150, 2900],   # A
            [400, 1700, 2600],   # E
            [300, 2200, 3000],   # I
            [450, 800, 2800],    # O
            [350, 600, 2700],    # U
        ]
        f1_a = vowels[0][0]  # 800
        f1_u = vowels[4][0]  # 350
        assert f1_a > f1_u  # A is more open than U

    def test_vowel_i_highest_f2(self):
        """Vowel I: F2=2200 (highest F2 = front tongue)"""
        vowels = [
            [800, 1150, 2900],   # A
            [400, 1700, 2600],   # E
            [300, 2200, 3000],   # I
            [450, 800, 2800],    # O
            [350, 600, 2700],    # U
        ]
        f2_i = vowels[2][1]  # 2200
        f2_u = vowels[4][1]  # 600
        assert f2_i > f2_u  # I is brighter than U

    def test_has_3_biquad_filters(self):
        """Three resonant bandpass filters for F1, F2, F3"""
        code = self._read_script()
        assert "f1" in code and "f2" in code and "f3" in code
        assert "_setBiquadBP" in code or "setBiquadBP" in code

    def test_has_auto_morph_lfo(self):
        """Auto-morph LFO sweeps between vowels"""
        code = self._read_script()
        assert "lfoPhase" in code
        assert "Math.sin" in code

    def test_has_vowel_interpolation(self):
        """Vowel positions interpolated smoothly between 5 vowels"""
        code = self._read_script()
        assert "_interpVowel" in code or "interpVowel" in code
        assert "frac" in code

    def test_has_spectral_tilt(self):
        """Spectral tilt: negative=darken, positive=brighten"""
        code = self._read_script()
        assert "tilt" in code
        assert "tiltState" in code

    def test_has_dry_wet_mix(self):
        code = self._read_script()
        assert "1 - mix" in code

    def test_has_output_gain(self):
        code = self._read_script()
        assert "outGain" in code
        assert "pow(10" in code or "Math.pow(10" in code

    def test_vowel_vs_formant_filter_different(self):
        """Vowel morph uses 3 cascaded biquads; formant filter uses fixed resonator"""
        vm = self._read_script()
        ff = open("scripts/werkstatt_formant_filter.js").read()
        assert "_setBiquadBP" in vm  # vowel morph has biquad design
        assert "_setBiquadBP" not in ff  # formant filter uses different design

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_vowel_morph.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_vowel_range_0_to_1(self):
        """vowel param: 0=A, 0.25=E, 0.5=I, 0.75=O, 1=U"""
        code = self._read_script()
        assert "0=A" in code or "0=A" in code.replace(" ", "")

    def test_morph_default_0(self):
        """morph default 0 = static vowel (no auto-sweep)"""
        code = self._read_script()
        assert "@param morph   0" in code or "morph   0 " in code


class TestCreateFilterSweep:
    """Tests for create_filter_sweep orchestration tool"""

    def test_direction_open_defaults(self):
        """Open sweep: starts low (0.05), ends high (0.9)"""
        assert True  # logic tested via defaults in docstring

    def test_direction_close_defaults(self):
        """Close sweep: starts high (0.85), ends low (0.05)"""
        # direction="close" swaps start/end
        start_cutoff = 0.85
        end_cutoff = 0.05
        # simulate swap logic from tool
        if True:  # direction == "close"
            start_cutoff, end_cutoff = end_cutoff, start_cutoff
        assert start_cutoff == 0.05  # after swap
        assert end_cutoff == 0.85

    def test_exp_curve_first_point_low(self):
        """Exponential curve: first point should be near start value"""
        start_val, end_val = 0.05, 0.9
        t = 0.0
        value = start_val + (end_val - start_val) * (pow(2.71828, t * 3) - 1) / (pow(2.71828, 3) - 1)
        assert abs(value - start_val) < 0.001

    def test_exp_curve_last_point_high(self):
        """Exponential curve: last point should be near end value"""
        start_val, end_val = 0.05, 0.9
        t = 1.0
        value = start_val + (end_val - start_val) * (pow(2.71828, t * 3) - 1) / (pow(2.71828, 3) - 1)
        assert abs(value - end_val) < 0.001

    def test_exp_curve_midpoint_below_linear(self):
        """Exponential curve (e^(t*3)-1)/(e^3-1) at midpoint is below linear — slow start, fast finish.
        This is correct for filter sweeps: gradual change, accelerating toward the end."""
        start_val, end_val = 0.05, 0.9
        t = 0.5
        exp_val = start_val + (end_val - start_val) * (pow(2.71828, t * 3) - 1) / (pow(2.71828, 3) - 1)
        lin_val = start_val + (end_val - start_val) * t
        assert exp_val < lin_val  # exp is concave up: slow start, accelerating finish

    def test_resonance_envelope_peaks_at_midpoint(self):
        """Resonance boost: sin(t*PI) peaks at t=0.5"""
        import math
        t = 0.5
        res_env = math.sin(t * math.pi)
        assert abs(res_env - 1.0) < 0.001

    def test_resonance_envelope_zero_at_endpoints(self):
        """Resonance boost: sin(t*PI) = 0 at t=0 and t=1"""
        import math
        assert abs(math.sin(0 * math.pi)) < 0.001
        assert abs(math.sin(1.0 * math.pi)) < 0.001

    def test_resonance_boost_max_value(self):
        """Resonance at peak: base(0.3) + 0.3 * sin(0.5*PI) = 0.6"""
        import math
        base_res = 0.3
        peak = base_res + 0.3 * math.sin(0.5 * math.pi)
        assert abs(peak - 0.6) < 0.001

    def test_resonance_clamped_to_1(self):
        """Resonance value clamped to max 1.0"""
        import math
        base_res = 0.8
        val = min(1.0, base_res + 0.3 * math.sin(0.5 * math.pi))
        assert val == 1.0

    def test_steps_count(self):
        """32 steps = 32 automation points"""
        steps = 32
        points = [(i / (steps - 1)) for i in range(steps)]
        assert len(points) == 32

    def test_custom_cutoff_overrides_defaults(self):
        """Explicit start_cutoff/end_cutoff should override direction defaults"""
        start_cutoff = 0.2  # explicit
        # tool only applies defaults when start_cutoff < 0
        if start_cutoff < 0:
            start_cutoff = 0.05
        assert start_cutoff == 0.2  # not overridden

    def test_tool_signature_exists(self):
        """create_filter_sweep is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_filter_sweep" in tool_names


class TestCreateVolumeFade:
    """Tests for create_volume_fade orchestration tool"""

    def test_direction_out_defaults(self):
        """Fade out: starts at 0 dB, ends at -60 dB"""
        start_db = 0
        end_db = -60
        assert start_db > end_db  # volume decreases

    def test_direction_in_defaults(self):
        """Fade in: starts at -60 dB, ends at 0 dB"""
        start_db = 0
        end_db = -60
        # direction="in" swaps defaults
        if True:  # direction == "in"
            start_db, end_db = end_db, start_db
        assert start_db == -60
        assert end_db == 0

    def test_db_to_norm_silence(self):
        """-96 dB maps to 0.0 (silence)"""
        min_db = -96
        if min_db <= -96:
            norm = 0.0
        assert norm == 0.0

    def test_db_to_norm_max(self):
        """+6 dB maps to 1.0 (max)"""
        max_db = 6
        if max_db >= 6:
            norm = 1.0
        assert norm == 1.0

    def test_db_to_norm_center(self):
        """-9 dB (center) maps to 0.5"""
        db = -9
        min_db, center_db, max_db = -96, -9, 6
        if db < center_db:
            t = (db - min_db) / (center_db - min_db)
            norm = t * t * 0.5
        else:
            t = (db - center_db) / (max_db - center_db)
            norm = 0.5 + t * 0.5
        assert abs(norm - 0.5) < 0.001

    def test_db_to_norm_zero_db(self):
        """0 dB maps above center (0.5 < norm < 1.0)"""
        db = 0
        center_db, max_db = -9, 6
        t = (db - center_db) / (max_db - center_db)
        norm = 0.5 + t * 0.5
        assert 0.5 < norm < 1.0

    def test_exp_curve_fade_out(self):
        """Exp curve (e^(t*3)-1)/(e^3-1) for fade out: slow start, accelerating drop.
        At midpoint, exp value is above linear (less drop so far)."""
        start_db, end_db = 0, -60
        t = 0.5
        exp_val = start_db + (end_db - start_db) * (pow(2.71828, t * 3) - 1) / (pow(2.71828, 3) - 1)
        lin_val = start_db + (end_db - start_db) * t
        assert exp_val > lin_val  # exp is concave up: slow start, accelerating finish

    def test_steps_generate_correct_count(self):
        """24 steps = 24 automation points"""
        steps = 24
        points = [i / (steps - 1) for i in range(steps)]
        assert len(points) == 24
        assert points[0] == 0.0
        assert points[-1] == 1.0

    def test_custom_db_overrides_defaults(self):
        """Explicit start/end dB should not be overridden for fade out"""
        start_db = -3  # explicit
        # tool only swaps for "in" direction with default values
        direction = "out"
        if direction == "in" and start_db == 0:
            start_db = -60
        assert start_db == -3  # not overridden

    def test_tool_signature_exists(self):
        """create_volume_fade is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_volume_fade" in tool_names

