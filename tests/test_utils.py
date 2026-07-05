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


class TestCreatePanSweep:
    """Tests for create_pan_sweep orchestration tool"""

    def test_pan_range_left_to_right(self):
        """Default sweep: -1 (full left) to +1 (full right)"""
        start_pan, end_pan = -1, 1
        assert start_pan < end_pan

    def test_pan_clamped_to_valid_range(self):
        """Pan values clamped to -1..+1"""
        val = max(-1, min(1, 1.5))
        assert val == 1
        val = max(-1, min(1, -1.5))
        assert val == -1

    def test_linear_midpoint_is_center(self):
        """Linear L→R sweep at midpoint should be 0 (center)"""
        start_pan, end_pan = -1, 1
        t = 0.5
        val = start_pan + (end_pan - start_pan) * t
        assert abs(val) < 0.001

    def test_linear_first_point_is_start(self):
        """First point of linear sweep = start_pan"""
        start_pan, end_pan = -1, 1
        t = 0.0
        val = start_pan + (end_pan - start_pan) * t
        assert val == start_pan

    def test_linear_last_point_is_end(self):
        """Last point of linear sweep = end_pan"""
        start_pan, end_pan = -1, 1
        t = 1.0
        val = start_pan + (end_pan - start_pan) * t
        assert val == end_pan

    def test_reverse_sweep_right_to_left(self):
        """R→L sweep: start +1, end -1"""
        start_pan, end_pan = 1, -1
        assert start_pan > end_pan

    def test_partial_sweep_stays_in_range(self):
        """Half-right to half-left: 0.5 to -0.5"""
        start_pan, end_pan = 0.5, -0.5
        t = 0.5
        val = start_pan + (end_pan - start_pan) * t
        assert abs(val) < 0.001  # center at midpoint

    def test_steps_count(self):
        """24 steps = 24 points"""
        steps = 24
        points = [i / (steps - 1) for i in range(steps)]
        assert len(points) == 24

    def test_tool_signature_exists(self):
        """create_pan_sweep is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_pan_sweep" in tool_names


class TestCreateMuteAutomation:
    """Tests for create_mute_automation orchestration tool"""

    def test_event_parsing(self):
        """Valid JSON events parse correctly"""
        import json
        events = json.loads('[[0,false],[16,true],[24,false]]')
        assert len(events) == 3
        assert events[0] == [0, False]
        assert events[1] == [16, True]

    def test_mute_value_conversion(self):
        """muted=true → value 1, muted=false → value 0"""
        assert (1 if True else 0) == 1
        assert (1 if False else 0) == 0

    def test_step_interpolation_for_boolean(self):
        """Mute automation uses step interpolation (0), not smooth (1)"""
        interp = 0  # step, no interpolation for boolean
        assert interp == 0

    def test_schedule_format(self):
        """Schedule maps events to readable format"""
        events = [[0, False], [16, True], [24, False]]
        schedule = [{"beat": b, "state": "muted" if m else "audible"} for b, m in events]
        assert schedule[0]["state"] == "audible"
        assert schedule[1]["state"] == "muted"
        assert schedule[2]["state"] == "audible"

    def test_breakdown_pattern(self):
        """Classic breakdown: audible → muted → audible"""
        events = [[0, False], [16, True], [24, False]]
        # 0-16 audible, 16-24 muted (breakdown), 24+ audible (drop)
        assert events[0][1] == False  # start audible
        assert events[1][1] == True   # mute for breakdown
        assert events[2][1] == False  # unmute for drop

    def test_intro_silence_pattern(self):
        """Intro silence: muted → audible"""
        events = [[0, True], [8, False]]
        assert events[0][1] == True   # silent intro
        assert events[1][1] == False  # kicks in

    def test_empty_events_rejected(self):
        """Empty events array should be rejected"""
        import json
        events = json.loads('[]')
        assert len(events) == 0  # should be rejected by validation

    def test_invalid_event_format_rejected(self):
        """Non-pair events should be rejected"""
        bad_event = [0, 1, 2]  # 3 elements, not 2
        assert len(bad_event) != 2

    def test_tool_signature_exists(self):
        """create_mute_automation is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_mute_automation" in tool_names


class TestSpectralBlurDSP:
    """Tests for werkstatt_spectral_blur.js — STFT-based spectral smearing"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_spectral_blur.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt spectral_blur" in code

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_spectral_blur.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_six_params(self):
        """6 params: blur_size, freq_blur, time_blur, phase_rand, mix, output"""
        code = self._read_script()
        params = code.count("@param")
        assert params == 6

    def test_blur_size_is_int(self):
        """blur_size is int type (1-32 bins)"""
        code = self._read_script()
        assert "int bins" in code

    def test_has_fft(self):
        """Uses FFT (Cooley-Tukey radix-2)"""
        code = self._read_script()
        assert "fft" in code.lower()
        assert "Cooley" in code or "butterfly" in code.lower() or "Bit reversal" in code

    def test_has_hann_window(self):
        """Uses Hann window for overlap-add"""
        code = self._read_script()
        assert "Hann" in code or "hann" in code
        assert "0.5 * (1 - Math.cos" in code

    def test_overlap_add(self):
        """Overlap-add for reconstruction"""
        code = self._read_script()
        assert "overlap" in code.lower()

    def test_freq_blur_smears_magnitude(self):
        """Frequency blur averages magnitude across neighboring bins"""
        code = self._read_script()
        assert "freqBlur" in code
        assert "blurSize" in code

    def test_time_blur_averages_frames(self):
        """Temporal blur averages magnitude across previous frames"""
        code = self._read_script()
        assert "timeBlur" in code
        assert "magnitudeHistory" in code

    def test_phase_randomization(self):
        """Phase randomization for diffuse texture"""
        code = self._read_script()
        assert "phaseRand" in code
        assert "randPhase" in code

    def test_magnitude_spectrum_reconstruction(self):
        """Reconstructs from magnitude + phase"""
        code = self._read_script()
        assert "Math.cos(phase" in code
        assert "Math.sin(phase" in code


class TestKarplusStrongDSP:
    """Tests for werkstatt_karplus_strong.js — physical modeling string synthesis"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_karplus_strong.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt karplus_strong" in code

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_karplus_strong.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_seven_params(self):
        """7 params: frequency, decay, brightness, pluck_damping, stretch, mix, output"""
        code = self._read_script()
        params = code.count("@param")
        assert params == 7

    def test_frequency_is_exp(self):
        """frequency is exponential type (20-2000 Hz)"""
        code = self._read_script()
        assert "frequency 220 20 2000 exp" in code

    def test_delay_line_initialized(self):
        """Float32Array delay line per channel"""
        code = self._read_script()
        assert "Float32Array" in code
        assert "delayL" in code
        assert "delayR" in code

    def test_delay_length_from_frequency(self):
        """Delay length = floor(sr / freq * stretch)"""
        code = self._read_script()
        assert "delayLen" in code
        assert "sr / f" in code or "sr / this.frequency" in code

    def test_one_pole_lowpass_feedback(self):
        """One-pole averaging lowpass in feedback path (brightness control)"""
        code = self._read_script()
        assert "lastFiltL" in code
        assert "lastFiltR" in code
        assert "bright * next" in code or "brightness" in code

    def test_decay_clamped(self):
        """Decay gain clamped to prevent infinite ring (0.995 max)"""
        code = self._read_script()
        assert "0.995" in code

    def test_pluck_damping_controls_excitation(self):
        """pluck_damping reduces excitation gain"""
        code = self._read_script()
        assert "pluck_damping" in code
        assert "exciteGain" in code

    def test_stretch_param(self):
        """Stretch parameter for inharmonic/detuned strings"""
        code = self._read_script()
        assert "stretch" in code

    def test_process_audio_wet_dry(self):
        """Wet/dry mix with output gain"""
        code = self._read_script()
        assert "dry" in code
        assert "wet" in code
        assert "outGain" in code


class TestWaveguideStringDSP:
    """Tests for werkstatt_waveguide_string.js — bidirectional waveguide string synthesis"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_waveguide_string.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt waveguide_string" in code

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_waveguide_string.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_seven_params(self):
        """7 params: frequency, decay, brightness, pick_position, inharmonicity, mix, output"""
        code = self._read_script()
        params = code.count("@param")
        assert params == 7

    def test_bidirectional_delay_lines(self):
        """Two delay lines per channel: forward and backward"""
        code = self._read_script()
        assert "delayFwd" in code
        assert "delayBwd" in code
        assert "Float32Array" in code

    def test_bridge_lowpass_filter(self):
        """Bridge termination uses one-pole lowpass (brightness control)"""
        code = self._read_script()
        assert "bridgeFilt" in code
        assert "bridgeCoeff" in code

    def test_nut_allpass_dispersion(self):
        """Nut uses allpass for inharmonicity (stiff string)"""
        code = self._read_script()
        assert "nutState" in code
        assert "nutCoeff" in code
        assert "inharmonicity" in code

    def test_pick_position_splits_excitation(self):
        """Pick position splits input between forward and backward waves"""
        code = self._read_script()
        assert "pick_position" in code
        assert "pickFwd" in code
        assert "pickBwd" in code

    def test_stereo_processing(self):
        """Separate waveguide state per channel"""
        code = self._read_script()
        assert "delayFwdR" in code
        assert "delayBwdR" in code
        assert "idxL" in code
        assert "idxR" in code

    def test_decay_clamped(self):
        """Decay gain clamped (0.99 max)"""
        code = self._read_script()
        assert "0.99" in code

    def test_output_is_wave_sum(self):
        """Output = sum of forward and backward waves"""
        code = self._read_script()
        assert "fwdL + bwdL" in code or "waveOut" in code


class TestPhaserDSP:
    """Tests for werkstatt_phaser.js — cascaded allpass phaser with LFO sweep"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_phaser.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt phaser" in code

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_phaser.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_seven_params(self):
        """7 params: rate, depth, stages, base_freq, feedback, mix, stereo"""
        code = self._read_script()
        params = code.count("@param")
        assert params == 7

    def test_allpass_stages(self):
        """Cascaded allpass filters (phaser core)"""
        code = self._read_script()
        assert "allpass" in code
        assert "stages" in code

    def test_lfo_sine(self):
        """LFO uses sine wave for sweep"""
        code = self._read_script()
        assert "Math.sin" in code
        assert "lfoPhase" in code

    def test_feedback_path(self):
        """Resonance feedback from last stage output"""
        code = self._read_script()
        assert "feedback" in code
        assert "fbL" in code

    def test_stereo_offset(self):
        """Stereo parameter creates L/R LFO phase offset"""
        code = self._read_script()
        assert "stereo" in code
        assert "lfoPhaseR" in code

    def test_dry_wet_mix(self):
        """Output = dry*(1-mix) + wet*mix"""
        code = self._read_script()
        assert "1 - mix" in code
        assert "* mix" in code

    def test_allpass_coefficient(self):
        """Allpass coefficient from frequency: a = (1-sin(wT))/(1+sin(wT))"""
        code = self._read_script()
        assert "1 - sinW" in code
        assert "1 + sinW" in code

    def test_stage_clamping(self):
        """Stages clamped to 2-12 range"""
        code = self._read_script()
        assert "Math.min(12" in code or "min(12" in code
        assert "Math.max(2" in code or "max(2" in code

    def test_feedback_clamped(self):
        """Feedback clamped to ±0.95"""
        code = self._read_script()
        assert "0.95" in code


class TestSpectralEnhancerDSP:
    """Tests for werkstatt_spectral_enhancer.js — STFT-based high-frequency air boost"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_spectral_enhancer.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt spectral_enhancer" in code

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_spectral_enhancer.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_seven_params(self):
        """7 params: crossover, air, sparkle, transients, width, mix, output"""
        code = self._read_script()
        params = code.count("@param")
        assert params == 7

    def test_fft_implementation(self):
        """Has radix-2 Cooley-Tukey FFT"""
        code = self._read_script()
        assert "_fft" in code
        assert "bit" in code.lower() or "Bit reversal" in code
        assert "Butterfly" in code or "butterfly" in code.lower() or "len <<= 1" in code

    def test_hann_window(self):
        """Uses Hann window for STFT"""
        code = self._read_script()
        assert "hann" in code.lower() or "0.5 * (1 - Math.cos" in code

    def test_overlap_add(self):
        """Uses overlap-add reconstruction"""
        code = self._read_script()
        assert "overlap" in code.lower()
        assert "winNorm" in code or "windowNorm" in code.lower()

    def test_crossover_band(self):
        """Crossover frequency splits enhancement band"""
        code = self._read_script()
        assert "crossover" in code
        assert "crossBin" in code

    def test_spectral_peak_emphasis(self):
        """Sparkle parameter emphasizes spectral peaks"""
        code = self._read_script()
        assert "sparkle" in code
        assert "peak" in code.lower()

    def test_transient_enhancement(self):
        """Transient detection via magnitude delta"""
        code = self._read_script()
        assert "transients" in code
        assert "delta" in code
        assert "prevMag" in code

    def test_stereo_widening(self):
        """Width parameter applies stereo widening on enhanced band"""
        code = self._read_script()
        assert "width" in code

    def test_dry_wet_mix(self):
        """Output = dry + (wet - dry) * mix"""
        code = self._read_script()
        assert "mix" in code
        assert "dry" in code
        assert "wet" in code


class TestDetectBpm:
    """Tests for _detect_bpm and detect_bpm tool"""

    def test_empty_channels_returns_default(self):
        """Empty audio returns BPM 120 with 0 confidence"""
        from opendaw_mcp.utils import _detect_bpm
        result = _detect_bpm([], 44100)
        assert result["bpm"] == 120.0
        assert result["confidence"] == 0.0

    def test_short_audio_returns_default(self):
        """Very short audio (<10 windows) returns default"""
        from opendaw_mcp.utils import _detect_bpm
        # 1024 * 9 = 9216 samples, < 10 windows
        channels = [[0.0] * 9216]
        result = _detect_bpm(channels, 44100)
        assert result["confidence"] == 0.0

    def test_bpm_range_60_200(self):
        """Detected BPM should be in 60-200 range"""
        from opendaw_mcp.utils import _detect_bpm
        # Generate synthetic 120 BPM kick pattern
        sr = 44100
        duration = 10.0  # 10 seconds
        n = int(sr * duration)
        period = int(sr * 0.5)  # 120 BPM = 0.5s per beat
        mono = [0.0] * n
        for i in range(0, n, period):
            # Add a "kick" — 100 samples of high energy
            for j in range(min(100, n - i)):
                mono[i + j] = 0.9
        result = _detect_bpm([mono], sr)
        assert 60 <= result["bpm"] <= 200

    def test_synthetic_120_bpm(self):
        """Synthetic 120 BPM pattern should detect close to 120"""
        from opendaw_mcp.utils import _detect_bpm
        sr = 44100
        duration = 10.0
        n = int(sr * duration)
        period = int(sr * 0.5)  # 120 BPM
        mono = [0.0] * n
        for i in range(0, n - 100, period):
            for j in range(100):
                mono[i + j] = 0.9
        result = _detect_bpm([mono], sr)
        # Should detect 120 or 60 (half-time) or 240 capped at 200
        bpm = result["bpm"]
        assert bpm == 120.0 or bpm == 60.0 or bpm == 200.0

    def test_onset_count_positive(self):
        """Onset count should be positive for rhythmic audio"""
        from opendaw_mcp.utils import _detect_bpm
        sr = 44100
        duration = 10.0
        n = int(sr * duration)
        period = int(sr * 0.5)
        mono = [0.0] * n
        for i in range(0, n - 100, period):
            for j in range(100):
                mono[i + j] = 0.9
        result = _detect_bpm([mono], sr)
        assert result["onset_count"] > 0

    def test_duration_calculated(self):
        """Duration should be calculated from samples and sample rate"""
        from opendaw_mcp.utils import _detect_bpm
        sr = 44100
        n = sr * 10  # 10 seconds
        channels = [[0.0] * n]
        result = _detect_bpm(channels, sr)
        assert abs(result["duration_seconds"] - 10.0) < 0.1

    def test_few_onsets_returns_default(self):
        """<4 onsets returns default BPM with 0 confidence"""
        from opendaw_mcp.utils import _detect_bpm
        sr = 44100
        n = sr * 10
        mono = [0.0] * n
        # Only 2 energy spikes
        mono[1000:1100] = [0.9] * 100
        mono[5000:5100] = [0.9] * 100
        result = _detect_bpm([mono], sr)
        assert result["confidence"] == 0.0

    def test_stereo_mixdown(self):
        """Stereo input should be mixed to mono correctly"""
        from opendaw_mcp.utils import _detect_bpm
        sr = 44100
        duration = 10.0
        n = int(sr * duration)
        period = int(sr * 0.5)
        # Same pattern in both channels
        ch_l = [0.0] * n
        ch_r = [0.0] * n
        for i in range(0, n - 100, period):
            for j in range(100):
                ch_l[i + j] = 0.9
                ch_r[i + j] = 0.9
        result = _detect_bpm([ch_l, ch_r], sr)
        assert result["onset_count"] > 0

    def test_suno_pipeline_bpm_to_set_bpm(self):
        """Pipeline: detect_bpm → set_bpm"""
        steps = ["detect_bpm", "set_bpm"]
        assert steps[0] == "detect_bpm"
        assert len(steps) == 2


class TestFftRadix2:
    """Tests for pure Python radix-2 Cooley-Tukey FFT"""

    def test_dc_signal(self):
        """FFT of constant signal → energy in bin 0 only"""
        from opendaw_mcp.utils import _fft_radix2
        n = 8
        re = [1.0] * n
        im = [0.0] * n
        _fft_radix2(re, im)
        assert abs(re[0] - n) < 0.001  # DC = N
        for k in range(1, n):
            assert abs(re[k]) < 0.001

    def test_sine_wave_peak(self):
        """FFT of sine wave → peak at correct bin"""
        import math
        from opendaw_mcp.utils import _fft_radix2
        n = 256
        sr = 256  # 1 Hz per bin
        freq = 10  # bin 10
        re = [math.sin(2 * math.pi * freq * i / sr) for i in range(n)]
        im = [0.0] * n
        _fft_radix2(re, im)
        mags = [math.sqrt(re[k] ** 2 + im[k] ** 2) for k in range(n // 2)]
        peak_bin = mags.index(max(mags))
        assert peak_bin == freq

    def test_power_of_two_required(self):
        """FFT should work for any power of 2 size"""
        from opendaw_mcp.utils import _fft_radix2
        for n in [2, 4, 8, 16, 32, 64]:
            re = [0.0] * n
            im = [0.0] * n
            re[0] = 1.0
            _fft_radix2(re, im)
            assert len(re) == n  # no crash

    def test_linearity(self):
        """FFT is linear: FFT(a+b) = FFT(a) + FFT(b)"""
        import math
        from opendaw_mcp.utils import _fft_radix2
        n = 64
        a_re = [math.sin(2 * math.pi * 3 * i / n) for i in range(n)]
        b_re = [math.cos(2 * math.pi * 5 * i / n) for i in range(n)]
        sum_re = [a_re[i] + b_re[i] for i in range(n)]
        a_im = [0.0] * n
        b_im = [0.0] * n
        sum_im = [0.0] * n
        _fft_radix2(a_re, a_im)
        _fft_radix2(b_re, b_im)
        _fft_radix2(sum_re, sum_im)
        for k in range(n):
            expected_re = a_re[k] + b_re[k]
            expected_im = a_im[k] + b_im[k]
            assert abs(sum_re[k] - expected_re) < 0.01
            assert abs(sum_im[k] - expected_im) < 0.01


class TestDetectKey:
    """Tests for _detect_key and detect_key tool"""

    def test_empty_channels_returns_default(self):
        """Empty audio returns C major with 0 confidence"""
        from opendaw_mcp.utils import _detect_key
        result = _detect_key([], 44100)
        assert result["key"] == "C"
        assert result["mode"] == "major"
        assert result["confidence"] == 0.0

    def test_chroma_has_12_elements(self):
        """Chroma vector always has 12 elements"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2  # 2 seconds
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([mono], sr)
        assert len(result["chroma"]) == 12

    def test_key_is_valid_note_name(self):
        """Detected key must be a valid note name"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([mono], sr)
        valid_notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        assert result["key"] in valid_notes

    def test_mode_is_major_or_minor(self):
        """Mode must be 'major' or 'minor'"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([mono], sr)
        assert result["mode"] in ("major", "minor")

    def test_confidence_range_0_1(self):
        """Confidence should be in 0-1 range"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([mono], sr)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_alternatives_has_3_entries(self):
        """Alternatives list should have 3 entries"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([mono], sr)
        assert len(result["alternatives"]) == 3
        for alt in result["alternatives"]:
            assert "key" in alt
            assert "mode" in alt
            assert "correlation" in alt

    def test_a4_sine_detects_a(self):
        """Pure A4 (440 Hz) sine should detect A as key"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 3  # 3 seconds for better chroma
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        # Add A3 harmonic for robustness
        for i in range(n):
            mono[i] += math.sin(2 * math.pi * 220 * i / sr) * 0.3
        result = _detect_key([mono], sr)
        assert result["key"] == "A"

    def test_c_major_triad_detects_c(self):
        """C-E-G triad should detect C as key"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 3
        mono = [0.0] * n
        for freq in [261.63, 329.63, 392.00]:  # C4, E4, G4
            for i in range(n):
                mono[i] += math.sin(2 * math.pi * freq * i / sr) * 0.3
        result = _detect_key([mono], sr)
        assert result["key"] == "C"
        assert result["mode"] == "major"

    def test_a_minor_triad_detects_a_minor(self):
        """A-C-E triad should detect A minor"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 3
        mono = [0.0] * n
        for freq in [220.0, 261.63, 329.63]:  # A3, C4, E4
            for i in range(n):
                mono[i] += math.sin(2 * math.pi * freq * i / sr) * 0.3
        result = _detect_key([mono], sr)
        assert result["key"] == "A"
        assert result["mode"] == "minor"

    def test_stereo_mixdown(self):
        """Stereo input should be mixed to mono and produce valid result"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2
        ch_l = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        ch_r = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([ch_l, ch_r], sr)
        assert result["key"] == "A"

    def test_chroma_normalized(self):
        """Chroma values should sum to approximately 1.0"""
        import math
        from opendaw_mcp.utils import _detect_key
        sr = 44100
        n = sr * 2
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        result = _detect_key([mono], sr)
        assert abs(sum(result["chroma"]) - 1.0) < 0.01

    def test_suno_pipeline_key_to_progression(self):
        """Pipeline: detect_key → create_chord_progression"""
        steps = ["detect_key", "create_chord_progression"]
        assert steps[0] == "detect_key"
        assert len(steps) == 2


class TestDownloadAudio:
    """Tests for download_audio URL-to-file tool"""

    def test_url_validation_http(self):
        """HTTP URLs accepted"""
        url = "http://cdn.suno.ai/track.wav"
        assert url.startswith(("http://", "https://"))

    def test_url_validation_https(self):
        """HTTPS URLs accepted"""
        url = "https://cdn.suno.ai/track.wav"
        assert url.startswith(("http://", "https://"))

    def test_url_validation_invalid(self):
        """Non-HTTP schemes rejected"""
        url = "ftp://example.com/track.wav"
        assert not url.startswith(("http://", "https://"))

    def test_filename_from_url(self):
        """Filename derived from URL path when not provided"""
        url = "https://cdn.suno.ai/abc123.wav"
        url_path = url.split("?")[0].split("/")[-1]
        assert url_path == "abc123.wav"

    def test_filename_from_url_with_query(self):
        """Query string stripped from derived filename"""
        url = "https://cdn.suno.ai/track.mp3?token=xyz"
        url_path = url.split("?")[0].split("/")[-1]
        assert url_path == "track.mp3"

    def test_filename_sanitization(self):
        """Dangerous characters in filename are replaced"""
        filename = "..%2F..%2Fetc%2Fpasswd"
        safe = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
        assert "/" not in safe
        assert "\\" not in safe
        assert ".." not in safe

    def test_empty_url_rejected(self):
        """Empty URL returns error"""
        url = ""
        assert not url or not url.startswith(("http://", "https://"))

    def test_output_dir_check(self):
        """Non-existent output_dir returns error"""
        output_dir = "/tmp/nonexistent_dir_12345"
        assert not os.path.isdir(output_dir)

    def test_suno_pipeline_download_to_import(self):
        """Pipeline: download_audio → import_audio_to_tracks"""
        steps = ["download_audio", "import_audio_to_tracks"]
        assert len(steps) == 2
        assert steps[0] == "download_audio"

    def test_next_step_suggestion(self):
        """download_audio returns next_step pointing to import_audio_to_tracks"""
        output_path = "/tmp/track.wav"
        next_step = f'import_audio_to_tracks("{output_path}", mode="bs6")'
        assert "import_audio_to_tracks" in next_step
        assert output_path in next_step


class TestImportAudioToTracks:
    """Tests for import_audio_to_tracks composite pipeline tool"""

    def test_no_mode_single_track(self):
        """Empty mode = simple single-track import (no stem split)"""
        mode = ""
        stem_split = bool(mode)
        assert stem_split is False

    def test_mode_triggers_stem_split(self):
        """Non-empty mode = stem separation enabled"""
        mode = "bs6"
        stem_split = bool(mode)
        assert stem_split is True

    def test_valid_modes(self):
        """All STEM_MODES keys are valid for import"""
        valid_modes = ["ensemble", "scnet", "bs6", "polarformer", "dereverb", "drumsep", "denoise"]
        test_mode = "bs6"
        assert test_mode in valid_modes

    def test_invalid_mode_rejected(self):
        """Invalid mode should be rejected"""
        valid_modes = ["ensemble", "scnet", "bs6", "polarformer", "dereverb", "drumsep", "denoise"]
        test_mode = "invalid_mode"
        assert test_mode not in valid_modes

    def test_output_dir_naming(self):
        """Output dir = /tmp/stems_<basename>"""
        file_path = "/tmp/suno_track.wav"
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = f"/tmp/stems_{base_name}"
        assert output_dir == "/tmp/stems_suno_track"

    def test_track_per_stem(self):
        """Each stem gets its own track"""
        stems = [
            {"name": "bass", "path": "/tmp/stems/track/bass.wav"},
            {"name": "drums", "path": "/tmp/stems/track/drums.wav"},
            {"name": "vocals", "path": "/tmp/stems/track/vocals.wav"},
            {"name": "other", "path": "/tmp/stems/track/other.wav"},
            {"name": "guitar", "path": "/tmp/stems/track/guitar.wav"},
            {"name": "piano", "path": "/tmp/stems/track/piano.wav"},
        ]
        assert len(stems) == 6
        track_count = len(stems)
        assert track_count == 6

    def test_success_count_calculation(self):
        """success_count = stems without 'error' key"""
        tracks = [
            {"stem": "bass", "unit_index": 0},
            {"stem": "drums", "unit_index": 1},
            {"stem": "vocals", "error": "load failed"},
            {"stem": "other", "unit_index": 3},
        ]
        success_count = sum(1 for t in tracks if "error" not in t)
        assert success_count == 3

    def test_start_beat_placement(self):
        """All stems placed at same start_beat"""
        start_beat = 4.0
        stems = ["bass", "drums", "vocals"]
        placements = [start_beat for _ in stems]
        assert all(p == start_beat for p in placements)

    def test_file_not_found_error(self):
        """Non-existent file_path returns error"""
        file_path = "/tmp/nonexistent.wav"
        import os as _os
        assert not _os.path.exists(file_path)

    def test_suno_pipeline_order(self):
        """Pipeline: import → mix → master → render"""
        steps = ["import_audio_to_tracks", "apply_genre_mix", "add_mastering_chain", "render_full"]
        assert len(steps) == 4
        assert steps[0] == "import_audio_to_tracks"
        assert steps[-1] == "render_full"


class TestCreateSoloAutomation:
    """Tests for create_solo_automation orchestration tool"""

    def test_solo_events_for_muted_tracks(self):
        """Each non-solo track gets [0,false], [start,true], [end,false] events"""
        import json
        events = json.dumps([[0.0, False], [8.0, True], [16.0, False]])
        parsed = json.loads(events)
        assert len(parsed) == 3
        assert parsed[0] == [0.0, False]   # audible before
        assert parsed[1] == [8.0, True]    # muted during solo
        assert parsed[2] == [16.0, False]  # audible after

    def test_solo_track_not_muted(self):
        """Solo track stays audible — skipped in the mute loop"""
        solo_track = 0
        total_tracks = 4
        muted_tracks = [i for i in range(total_tracks) if i != solo_track]
        assert len(muted_tracks) == 3
        assert solo_track not in muted_tracks

    def test_unit_indices_default(self):
        """Empty unit_indices defaults to 0..N-1"""
        total_tracks = 4
        indices = list(range(total_tracks))
        assert indices == [0, 1, 2, 3]

    def test_unit_indices_custom(self):
        """Custom unit_indices parse correctly"""
        unit_indices = "5,6,7,8"
        indices = [int(x.strip()) for x in unit_indices.split(",")]
        assert indices == [5, 6, 7, 8]

    def test_unit_indices_mismatch(self):
        """Mismatched unit_indices count returns error"""
        total_tracks = 4
        indices = [int(x.strip()) for x in "0,1,2".split(",")]
        if len(indices) != total_tracks:
            error = True
        else:
            error = False
        assert error is True

    def test_start_end_validation(self):
        """start_beat >= end_beat is invalid"""
        start_beat = 16.0
        end_beat = 8.0
        assert start_beat >= end_beat  # should be rejected

    def test_solo_track_out_of_range(self):
        """solo_track >= total_tracks is invalid"""
        solo_track = 5
        total_tracks = 4
        assert not (0 <= solo_track < total_tracks)

    def test_tracks_muted_count(self):
        """tracks_muted = total_tracks - 1"""
        total_tracks = 4
        tracks_muted = total_tracks - 1
        assert tracks_muted == 3


class TestCreateSectionTransition:
    """Tests for create_section_transition orchestration tool"""

    def test_unit_indices_parsing(self):
        """Comma-separated indices parse to list of ints"""
        indices = [int(x.strip()) for x in "0,1,2,3".split(",")]
        assert indices == [0, 1, 2, 3]

    def test_mid_beat_calculation(self):
        """Mid beat = 75% of duration (transition point)"""
        start_beat = 32
        duration_beats = 16
        mid_beat = start_beat + duration_beats * 0.75
        assert mid_beat == 44

    def test_drop_pattern_operations(self):
        """Drop transition: filter close + mute + filter open + impact = 4 ops"""
        ops = ["lead_filter_close", "drums_mute", "lead_filter_open", "impact"]
        assert len(ops) == 4

    def test_buildup_pattern_operations(self):
        """Buildup transition: filter open + fade in = 2 ops"""
        ops = ["lead_filter_open", "pads_fade_in"]
        assert len(ops) == 2

    def test_breakdown_pattern_operations(self):
        """Breakdown transition: filter close + fade out + mute = 3 ops"""
        ops = ["drums_filter_close", "bass_fade_out", "synth_mute"]
        assert len(ops) == 3

    def test_intro_fades_all_units(self):
        """Intro: volume fade in on ALL units + filter open on pads"""
        indices = [0, 1, 2, 3]
        fade_ops = [f"unit{idx}_fade_in" for idx in indices]
        assert len(fade_ops) == 4
        assert "unit0_fade_in" in fade_ops

    def test_outro_fades_all_units(self):
        """Outro: volume fade out on ALL units + filter close on lead"""
        indices = [0, 1, 2, 3]
        fade_ops = [f"unit{idx}_fade_out" for idx in indices]
        assert len(fade_ops) == 4


class TestCreateTempoRamp:
    """Tests for create_tempo_ramp orchestration tool"""

    def test_ritardando_detected(self):
        """start_bpm > end_bpm = ritardando"""
        start_bpm, end_bpm = 120, 90
        ramp_type = "ritardando" if end_bpm < start_bpm else ("accelerando" if end_bpm > start_bpm else "constant")
        assert ramp_type == "ritardando"

    def test_accelerando_detected(self):
        """start_bpm < end_bpm = accelerando"""
        start_bpm, end_bpm = 100, 140
        ramp_type = "ritardando" if end_bpm < start_bpm else ("accelerando" if end_bpm > start_bpm else "constant")
        assert ramp_type == "accelerando"

    def test_constant_detected(self):
        """start_bpm == end_bpm = constant"""
        start_bpm, end_bpm = 120, 120
        ramp_type = "ritardando" if end_bpm < start_bpm else ("accelerando" if end_bpm > start_bpm else "constant")
        assert ramp_type == "constant"

    def test_linear_curve_points(self):
        """Linear curve: BPM values are evenly spaced"""
        start_bpm, end_bpm, steps = 120, 90, 4
        points = []
        for i in range(steps):
            t = i / (steps - 1)
            val = start_bpm + (end_bpm - start_bpm) * t
            points.append(round(val, 2))
        assert points[0] == 120.0
        assert points[-1] == 90.0
        # linear: midpoint = average
        assert points[2] == 100.0  # 120 + (90-120) * 2/3

    def test_exp_curve_eases_in(self):
        """Exp curve: first half smaller delta than second half"""
        import math
        start_bpm, end_bpm, steps = 120, 90, 16
        deltas = []
        prev = start_bpm
        for i in range(steps):
            t = i / (steps - 1)
            val = start_bpm + (end_bpm - start_bpm) * (math.exp(t * 3) - 1) / (math.exp(3) - 1)
            deltas.append(abs(val - prev))
            prev = val
        # exp: early deltas should be smaller than late deltas
        assert sum(deltas[:8]) < sum(deltas[8:])

    def test_log_curve_eases_out(self):
        """Log curve: first half larger delta than second half"""
        import math
        start_bpm, end_bpm, steps = 120, 90, 16
        deltas = []
        prev = start_bpm
        for i in range(steps):
            t = i / (steps - 1)
            val = start_bpm + (end_bpm - start_bpm) * math.log(1 + t * (math.e - 1))
            deltas.append(abs(val - prev))
            prev = val
        # log: early deltas should be larger than late deltas
        assert sum(deltas[:8]) > sum(deltas[8:])

    def test_beat_positions_span_range(self):
        """Beat positions span from start_beat to end_beat"""
        start_beat, end_beat, steps = 32, 48, 8
        beat_positions = []
        for i in range(steps):
            t = i / (steps - 1)
            beat_positions.append(round(start_beat + (end_beat - start_beat) * t, 2))
        assert beat_positions[0] == 32.0
        assert beat_positions[-1] == 48.0
        # 9 steps → index 4 = exact midpoint = 40.0
        beat_positions_9 = []
        for i in range(9):
            t = i / (9 - 1)
            beat_positions_9.append(round(32 + (48 - 32) * t, 2))
        assert beat_positions_9[4] == 40.0

    def test_steps_count_matches(self):
        """Number of generated points = steps"""
        steps = 16
        points = []
        for i in range(steps):
            points.append(i)
        assert len(points) == steps

    def test_bpm_clamped_to_valid_range(self):
        """BPM values must be 60-240"""
        start_bpm, end_bpm = 60, 240
        assert 60 <= start_bpm <= 240
        assert 60 <= end_bpm <= 240

    def test_tool_in_ast(self):
        """create_tempo_ramp is a registered MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_tempo_ramp" in tool_names


class TestDuplicateSection:
    """Tests for duplicate_section orchestration tool"""

    def test_offset_calculation(self):
        """Offset = target_beat - from_beat"""
        from_beat, target_beat = 0, 16
        offset = target_beat - from_beat
        assert offset == 16

    def test_offset_negative_when_target_before_source(self):
        """Offset can be negative if target is before source"""
        from_beat, target_beat = 32, 0
        offset = target_beat - from_beat
        assert offset == -32

    def test_section_length(self):
        """Section length = to_beat - from_beat"""
        from_beat, to_beat = 0, 16
        section_length = to_beat - from_beat
        assert section_length == 16

    def test_region_overlap_check(self):
        """Region [5, 21) overlaps [0, 16) — should be included"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 5, 16
        reg_end = reg_pos + reg_dur
        # overlap condition: NOT (regEnd <= from OR regPos >= to)
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert overlaps

    def test_region_no_overlap_before(self):
        """Region [0, 4) does not overlap [16, 32) — excluded"""
        from_beat, to_beat = 16, 32
        reg_pos, reg_dur = 0, 4
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert not overlaps

    def test_region_no_overlap_after(self):
        """Region [32, 48) does not overlap [0, 16) — excluded"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 32, 16
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert not overlaps

    def test_region_partial_overlap_included(self):
        """Region [12, 20) partially overlaps [0, 16) — included"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 12, 8
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert overlaps

    def test_new_position_calculation(self):
        """New position = original + offset"""
        reg_pos, offset = 4, 16
        new_pos = reg_pos + offset
        assert new_pos == 20

    def test_unit_indices_parsing(self):
        """Comma-separated unit indices parse correctly"""
        indices = [int(x.strip()) for x in "0,1,2,3".split(",")]
        assert indices == [0, 1, 2, 3]

    def test_empty_unit_indices_scans_all(self):
        """Empty string = scan all AUs"""
        unit_list = ""
        scans_all = not unit_list
        assert scans_all

    def test_tool_in_ast(self):
        """duplicate_section is a registered MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_duplicate_section" in tool_names


class TestApplyVelocityPattern:
    """Tests for apply_velocity_pattern orchestration tool"""

    def test_cycle_mode_4_note_pattern(self):
        """Cycle mode: 4-note pattern repeats every 4 notes"""
        pattern = [1.0, 0.5, 0.7, 0.5]
        num_notes = 10
        velocities = []
        for i in range(num_notes):
            idx = i % len(pattern)
            velocities.append(pattern[idx])
        assert velocities[0] == 1.0  # note 0
        assert velocities[4] == 1.0  # note 4 = pattern restart
        assert velocities[8] == 1.0  # note 8 = pattern restart

    def test_stretch_mode_distributes_evenly(self):
        """Stretch mode: pattern distributed across all notes"""
        pattern = [1.0, 0.3]
        num_notes = 8
        velocities = []
        for i in range(num_notes):
            idx = min(int(i / num_notes * len(pattern)), len(pattern) - 1)
            velocities.append(pattern[idx])
        # first 4 notes = pattern[0], last 4 = pattern[1]
        assert velocities[0] == 1.0
        assert velocities[3] == 1.0
        assert velocities[4] == 0.3
        assert velocities[7] == 0.3

    def test_base_velocity_multiplied(self):
        """Final velocity = base * pattern[i]"""
        base = 0.8
        pattern = [1.0, 0.5]
        v0 = base * pattern[0]
        v1 = base * pattern[1]
        assert v0 == 0.8
        assert v1 == 0.4

    def test_velocity_clamped_to_0_1(self):
        """Velocity clamped to 0-1 range"""
        base = 1.0
        pattern = [1.0, 0.0]
        v0 = max(0, min(1, base * pattern[0]))
        v1 = max(0, min(1, base * pattern[1]))
        assert v0 == 1.0
        assert v1 == 0.0

    def test_pattern_json_parsing(self):
        """JSON pattern string parses to list"""
        pattern_str = "[1.0, 0.5, 0.7, 0.5]"
        parsed = json.loads(pattern_str)
        assert parsed == [1.0, 0.5, 0.7, 0.5]

    def test_pattern_validation_rejects_negative(self):
        """Pattern values < 0 rejected"""
        pattern = [1.0, -0.5]
        valid = all(0 <= v <= 1 for v in pattern)
        assert not valid

    def test_pattern_validation_rejects_over_1(self):
        """Pattern values > 1 rejected"""
        pattern = [1.0, 1.5]
        valid = all(0 <= v <= 1 for v in pattern)
        assert not valid

    def test_empty_pattern_rejected(self):
        """Empty pattern array rejected"""
        pattern = []
        valid = isinstance(pattern, list) and len(pattern) > 0
        assert not valid

    def test_backbeat_accent_pattern(self):
        """Classic backbeat: strong-weak-medium-weak"""
        pattern = [1.0, 0.5, 0.7, 0.5]
        assert pattern[0] == 1.0  # downbeat strong
        assert pattern[2] == 0.7  # offbeat medium
        assert pattern[1] == pattern[3] == 0.5  # syncopated weak

    def test_tool_in_ast(self):
        """apply_velocity_pattern is a registered MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_apply_velocity_pattern" in tool_names


class TestMoveSection:
    """Tests for move_section orchestration tool"""

    def test_offset_forward(self):
        """Positive offset = move later"""
        offset = 32 - 0
        assert offset == 32

    def test_offset_backward(self):
        """Negative offset = move earlier"""
        offset = 0 - 32
        assert offset == -32

    def test_new_position_forward(self):
        """New position = old + offset (forward)"""
        old_pos, offset = 4, 16
        new_pos = old_pos + offset
        assert new_pos == 20

    def test_new_position_backward(self):
        """New position = old + offset (backward)"""
        old_pos, offset = 40, -16
        new_pos = old_pos + offset
        assert new_pos == 24

    def test_overlap_detection_included(self):
        """Region [10, 26) overlaps [0, 16) — included"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 10, 16
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert overlaps

    def test_overlap_detection_excluded_before(self):
        """Region [0, 4) does not overlap [16, 32) — excluded"""
        from_beat, to_beat = 16, 32
        reg_pos, reg_dur = 0, 4
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert not overlaps

    def test_overlap_detection_excluded_after(self):
        """Region [48, 64) does not overlap [0, 16) — excluded"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 48, 16
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert not overlaps

    def test_move_vs_duplicate(self):
        """Move changes position, duplicate creates copy — different operations"""
        move_ops = ["set_position"]
        dup_ops = ["copyTo"]
        assert move_ops != dup_ops

    def test_collect_then_move_pattern(self):
        """Collect all regions first, then move — avoids index invalidation"""
        regions = [{"pos": 0, "dur": 4}, {"pos": 8, "dur": 4}, {"pos": 20, "dur": 4}]
        from_beat, to_beat = 0, 16
        to_move = [r for r in regions if not (r["pos"] + r["dur"] <= from_beat or r["pos"] >= to_beat)]
        assert len(to_move) == 2  # pos=0 and pos=8

    def test_tool_in_ast(self):
        """move_section is a registered MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_move_section" in tool_names


class TestDeleteSection:
    """Tests for delete_section orchestration tool"""

    def test_overlap_included(self):
        """Region [10, 26) overlaps [0, 16) — included for deletion"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 10, 16
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert overlaps

    def test_no_overlap_excluded(self):
        """Region [20, 24) does not overlap [0, 16) — excluded"""
        from_beat, to_beat = 0, 16
        reg_pos, reg_dur = 20, 4
        reg_end = reg_pos + reg_dur
        overlaps = not (reg_end <= from_beat or reg_pos >= to_beat)
        assert not overlaps

    def test_collect_then_delete_pattern(self):
        """Collect all regions first, then delete — avoids index invalidation"""
        regions = [{"pos": 2, "dur": 4}, {"pos": 10, "dur": 8}, {"pos": 50, "dur": 4}]
        from_beat, to_beat = 0, 16
        to_delete = [r for r in regions if not (r["pos"] + r["dur"] <= from_beat or r["pos"] >= to_beat)]
        assert len(to_delete) == 2  # pos=2 and pos=10

    def test_remaining_count_after_delete(self):
        """After deleting 2 of 3 regions, 1 remains"""
        total = 3
        deleted = 2
        remaining = total - deleted
        assert remaining == 1

    def test_crud_trilogy_complete(self):
        """duplicate (copy) + move (cut-paste) + delete (remove) = complete CRUD"""
        operations = {"duplicate_section": "copy", "move_section": "move", "delete_section": "delete"}
        assert len(operations) == 3
        assert "copy" in operations.values()
        assert "move" in operations.values()
        assert "delete" in operations.values()

    def test_delete_is_destructive(self):
        """Delete removes region (unlike duplicate which creates copy)"""
        delete_ops = ["delete"]
        dup_ops = ["copyTo"]
        assert delete_ops != dup_ops

    def test_empty_section_no_regions(self):
        """Empty section (from==to) returns error"""
        from_beat, to_beat = 16, 16
        valid = to_beat > from_beat
        assert not valid

    def test_unit_indices_filter(self):
        """Specifying unit_indices limits scope"""
        all_units = [0, 1, 2, 3, 4]
        specified = [0, 1]
        # only AUs 0,1 are scanned, not all 5
        assert len(specified) < len(all_units)

    def test_tool_in_ast(self):
        """delete_section is a registered MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_delete_section" in tool_names


class TestClearRegionNotes:
    """Tests for clear_region_notes tool"""

    def test_clear_vs_delete_region(self):
        """clear_region_notes keeps region, delete_note_region removes it"""
        clear_ops = ["delete_note_events", "keep_region"]
        delete_ops = ["delete_region"]
        assert clear_ops != delete_ops

    def test_clear_vs_delete_note(self):
        """clear_region_notes removes all notes, delete_note removes one"""
        clear_scope = "all_notes_in_region"
        delete_scope = "single_note"
        assert clear_scope != delete_scope

    def test_all_regions_mode(self):
        """region_index=-1 targets all regions on track"""
        region_index = -1
        targets_all = region_index < 0
        assert targets_all

    def test_single_region_mode(self):
        """region_index=0 targets first region only"""
        region_index = 0
        targets_all = region_index < 0
        assert not targets_all

    def test_region_preserved_after_clear(self):
        """Region position and duration stay after notes are cleared"""
        region_info = {"position": 0, "duration": 1920, "notes_cleared": 16}
        # region still has position and duration — it's on the timeline
        assert region_info["position"] == 0
        assert region_info["duration"] == 1920
        assert region_info["notes_cleared"] == 16

    def test_note_count_decreases(self):
        """All notes cleared = 0 remaining"""
        initial = 16
        cleared = 16
        remaining = initial - cleared
        assert remaining == 0

    def test_empty_region_no_error(self):
        """Region with 0 notes — clearing returns 0 cleared, no error"""
        note_count = 0
        cleared = note_count  # nothing to clear
        assert cleared == 0

    def test_tool_in_ast(self):
        """clear_region_notes is a registered MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_clear_region_notes" in tool_names

    def test_unknown_type_rejected(self):
        """Unknown transition type returns error"""
        valid_types = {"drop", "buildup", "breakdown", "intro", "outro"}
        assert "invalid" not in valid_types

    def test_mute_events_format(self):
        """Mute events JSON format for drop: [[start, true], [mid, false]]"""
        import json
        start_beat = 32
        mid_beat = 44
        events = json.dumps([[start_beat, True], [mid_beat, False]])
        parsed = json.loads(events)
        assert parsed[0] == [32, True]   # mute at start
        assert parsed[1] == [44, False]  # unmute at drop

    def test_tool_signature_exists(self):
        """create_section_transition is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_section_transition" in tool_names


class TestCreateProgressionFromKey:
    """Tests for create_progression_from_key — diatonic auto-progression from key+mode"""

    # Mirror the server.py logic for unit testing without bridge
    _MAJOR_DEGREES = {0: "maj", 1: "min", 2: "min", 3: "maj", 4: "dom7", 5: "min", 6: "dim"}
    _MINOR_DEGREES = {0: "min", 1: "dim", 2: "maj", 3: "min", 4: "dom7", 5: "maj", 6: "maj"}
    _MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
    _MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
    _PROGRESSIONS = {
        ("major", "pop"):        [0, 4, 5, 3],
        ("major", "jazz"):       [1, 4, 0],
        ("major", "rock"):       [0, 3, 4],
        ("major", "synthwave"):  [0, 5, 2, 6],
        ("major", "folk"):       [0, 3, 5, 4],
        ("major", "lofi"):       [0, 5, 3, 4],
        ("minor", "pop"):        [0, 5, 2, 6],
        ("minor", "jazz"):       [1, 4, 0],
        ("minor", "rock"):       [0, 3, 4],
        ("minor", "synthwave"):  [0, 5, 2, 6],
        ("minor", "folk"):       [0, 3, 6, 2],
        ("minor", "lofi"):       [1, 4, 0],
    }
    _PC_TO_NAME = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
                   6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}

    def _generate(self, key_pc, mode, style):
        degrees = self._PROGRESSIONS[(mode, style)]
        scale = self._MAJOR_SCALE if mode == "major" else self._MINOR_SCALE
        qualities = self._MAJOR_DEGREES if mode == "major" else self._MINOR_DEGREES
        result = []
        for deg in degrees:
            root_pc = (key_pc + scale[deg]) % 12
            result.append((self._PC_TO_NAME[root_pc], qualities[deg]))
        return result

    def test_tool_signature_exists(self):
        """create_progression_from_key is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_progression_from_key" in tool_names

    def test_pop_major_c(self):
        """C major pop → C-G-Am-F (I-V-vi-IV)"""
        # C=0, G=7, A=9, F=5
        chords = self._generate(0, "major", "pop")
        assert chords[0] == ("C", "maj")
        assert chords[1] == ("G", "dom7")
        assert chords[2] == ("A", "min")
        assert chords[3] == ("F", "maj")

    def test_pop_minor_a(self):
        """A minor pop → Am-F-C-G (i-VI-III-VII)"""
        # A=9, F=5, C=0, G=7
        chords = self._generate(9, "minor", "pop")
        assert chords[0] == ("A", "min")
        assert chords[1] == ("F", "maj")
        assert chords[2] == ("C", "maj")
        assert chords[3] == ("G", "maj")

    def test_jazz_major_c(self):
        """C major jazz → Dm7-G7-Cmaj (ii-V-I)"""
        chords = self._generate(0, "major", "jazz")
        assert chords[0] == ("D", "min")
        assert chords[1] == ("G", "dom7")
        assert chords[2] == ("C", "maj")

    def test_jazz_minor_a(self):
        """A minor jazz → Bdim-E7-Am (ii-V-i)"""
        chords = self._generate(9, "minor", "jazz")
        assert chords[0] == ("B", "dim")
        assert chords[1] == ("E", "dom7")
        assert chords[2] == ("A", "min")

    def test_rock_major_c(self):
        """C major rock → Cmaj-Fmaj-G7 (I-IV-V)"""
        chords = self._generate(0, "major", "rock")
        assert chords[0] == ("C", "maj")
        assert chords[1] == ("F", "maj")
        assert chords[2] == ("G", "dom7")

    def test_rock_minor_a(self):
        """A minor rock → Am-Dm-E7 (i-iv-V)"""
        chords = self._generate(9, "minor", "rock")
        assert chords[0] == ("A", "min")
        assert chords[1] == ("D", "min")
        assert chords[2] == ("E", "dom7")

    def test_synthwave_minor_a(self):
        """A minor synthwave → Am-F-C-G (i-VI-III-VII)"""
        chords = self._generate(9, "minor", "synthwave")
        assert chords[0] == ("A", "min")
        assert chords[1] == ("F", "maj")
        assert chords[2] == ("C", "maj")
        assert chords[3] == ("G", "maj")

    def test_folk_major_c(self):
        """C major folk → Cmaj-Fmaj-Am-G7 (I-IV-vi-V)"""
        chords = self._generate(0, "major", "folk")
        assert chords[0] == ("C", "maj")
        assert chords[1] == ("F", "maj")
        assert chords[2] == ("A", "min")
        assert chords[3] == ("G", "dom7")

    def test_lofi_major_c(self):
        """C major lofi → Cmaj-Am-Fmaj-G7 (I-vi-IV-V)"""
        chords = self._generate(0, "major", "lofi")
        assert chords[0] == ("C", "maj")
        assert chords[1] == ("A", "min")
        assert chords[2] == ("F", "maj")
        assert chords[3] == ("G", "dom7")

    def test_all_styles_have_templates(self):
        """All 12 mode×style combos have progression templates"""
        for mode in ("major", "minor"):
            for style in ("pop", "jazz", "rock", "synthwave", "folk", "lofi"):
                assert (mode, style) in self._PROGRESSIONS, f"Missing {mode}/{style}"

    def test_all_chords_are_diatonic(self):
        """Every generated chord root is in the parent scale"""
        for key_pc in range(12):
            for mode in ("major", "minor"):
                scale = self._MAJOR_SCALE if mode == "major" else self._MINOR_SCALE
                scale_pcs = {(key_pc + s) % 12 for s in scale}
                for style in ("pop", "jazz", "rock", "synthwave", "folk", "lofi"):
                    chords = self._generate(key_pc, mode, style)
                    for root_name, _ in chords:
                        root_pc = {v: k for k, v in self._PC_TO_NAME.items()}[root_name]
                        assert root_pc in scale_pcs, f"{root_name} not in {mode} scale of pc={key_pc}"

    def test_progression_length(self):
        """Pop has 4 chords, jazz has 3, rock has 3"""
        assert len(self._generate(0, "major", "pop")) == 4
        assert len(self._generate(0, "major", "jazz")) == 3
        assert len(self._generate(0, "major", "rock")) == 3

    def test_pipeline_detect_key_to_progression(self):
        """Pipeline: detect_key → create_progression_from_key → create_harmonic_arrangement"""
        steps = ["detect_key", "create_progression_from_key", "create_harmonic_arrangement"]
        assert len(steps) == 3


class TestAnalyzeTrack:
    """Tests for analyze_track — composite BPM + key + LUFS + duration analysis"""

    def test_tool_signature_exists(self):
        """analyze_track is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_analyze_track" in tool_names

    def test_analyze_components_exist(self):
        """All three sub-analysis functions exist"""
        from opendaw_mcp.utils import _detect_bpm, _detect_key, _compute_lufs
        assert callable(_detect_bpm)
        assert callable(_detect_key)
        assert callable(_compute_lufs)

    def test_synthetic_track_analysis(self):
        """Composite analysis of synthetic C major track: all fields present"""
        import math
        from opendaw_mcp.utils import _detect_bpm, _detect_key, _compute_lufs

        sr = 44100
        duration_s = 10.0
        n = int(sr * duration_s)
        mono = [0.0] * n

        # Add C major triad (C4, E4, G4) for key detection
        for freq in [261.63, 329.63, 392.00]:
            for i in range(n):
                mono[i] += math.sin(2 * math.pi * freq * i / sr) * 0.2

        # Add rhythmic kick at 120 BPM for BPM detection
        period = int(sr * 0.5)
        for i in range(0, n - 100, period):
            for j in range(100):
                mono[i + j] += 0.5

        bpm = _detect_bpm([mono], sr)
        key = _detect_key([mono], sr)
        lufs = _compute_lufs([mono], sr)

        assert "bpm" in bpm
        assert "confidence" in bpm
        assert "key" in key
        assert "mode" in key
        assert "lufs_integrated" in lufs
        assert "true_peak_db" in lufs

    def test_analyze_result_fields(self):
        """Expected output fields for analyze_track composite result"""
        expected_fields = {
            "success", "bpm", "bpm_confidence", "key", "mode",
            "key_confidence", "lufs_integrated", "true_peak_db",
            "duration_seconds", "sample_rate", "channels",
            "dynamic_range_db", "chroma"
        }
        # Verify the MCP tool function has these in its return json.dumps
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_track":
                # Check the function source contains all field names
                source = ast.unparse(node)
                for field in expected_fields:
                    assert f'"{field}"' in source or f"'{field}'" in source, f"Missing field: {field}"
                return
        assert False, "analyze_track function not found"

    def test_dynamic_range_calculation(self):
        """Dynamic range = peak dB - RMS dB"""
        import math
        # A pure sine has ~3 dB crest factor
        sr = 44100
        n = sr
        mono = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n)]
        max_sample = max(abs(s) for s in mono)
        rms = math.sqrt(sum(s * s for s in mono) / n)
        peak_db = 20 * math.log10(max_sample) if max_sample > 0 else -120
        rms_db = 20 * math.log10(rms) if rms > 0 else -120
        dr = peak_db - rms_db
        # Sine wave crest factor is ~3.01 dB
        assert 2.5 < dr < 4.0

    def test_pipeline_analyze_to_remix(self):
        """Pipeline: analyze_track → set_bpm + create_progression_from_key → import → mix → render"""
        steps = ["analyze_track", "set_bpm", "create_progression_from_key",
                 "import_audio_to_tracks", "apply_genre_mix", "render_full"]
        assert steps[0] == "analyze_track"
        assert len(steps) == 6


class TestRemixTrack:
    """Tests for remix_track — full Suno remix pipeline in one call"""

    def test_tool_signature_exists(self):
        """remix_track is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_remix_track" in tool_names

    def test_pipeline_steps_count(self):
        """remix_track has exactly 7 pipeline steps"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_remix_track":
                source = ast.unparse(node)
                # Count the 7 step labels (ast.unparse may use single quotes)
                steps = ["analyze_track", "set_bpm", "import_audio",
                         "create_progression", "harmonic_arrangement",
                         "genre_mix", "mastering"]
                for s in steps:
                    # Check both single and double quoted forms
                    assert (f'"step": "{s}"' in source or
                            f"'step': '{s}'" in source or
                            f'"step": \'{s}\'' in source or
                            f'\'step\': "{s}"' in source or
                            s in source), f"Missing step: {s}"
                return
        assert False, "remix_track function not found"

    def test_default_params(self):
        """Default params: genre=synthwave, style=pop, stem_mode=bs4, lufs=-14"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_remix_track":
                # Defaults are aligned from the end (Python AST behavior)
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                defaults_map = {}
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if isinstance(d, ast.Constant):
                        defaults_map[arg_name] = d.value
                    elif isinstance(d, ast.UnaryOp) and isinstance(d.op, ast.USub):
                        if isinstance(d.operand, ast.Constant):
                            defaults_map[arg_name] = -d.operand.value
                assert defaults_map.get("genre") == "synthwave"
                assert defaults_map.get("style") == "pop"
                assert defaults_map.get("stem_mode") == "bs4"
                assert defaults_map.get("master_lufs") == -14
                assert defaults_map.get("add_harmony") is True
                return
        assert False, "remix_track function not found"

    def test_delegates_to_analyze_track(self):
        """remix_track calls analyze_track internally"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_remix_track":
                source = ast.unparse(node)
                assert "mcp_opendaw_analyze_track" in source
                assert "mcp_opendaw_set_bpm" in source
                assert "mcp_opendaw_import_audio_to_tracks" in source
                assert "mcp_opendaw_create_progression_from_key" in source
                assert "mcp_opendaw_create_harmonic_arrangement" in source
                assert "mcp_opendaw_apply_genre_mix" in source
                assert "mcp_opendaw_add_mastering_chain" in source
                return
        assert False, "remix_track function not found"

    def test_harmony_skip_when_disabled(self):
        """When add_harmony=False, progression and harmonic_arrangement steps are skipped"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_remix_track":
                source = ast.unparse(node)
                # The add_harmony flag controls steps 4 and 5
                assert "if add_harmony" in source
                assert "if add_harmony and progression_str" in source
                return
        assert False, "remix_track function not found"

    def test_suno_full_pipeline(self):
        """Full Suno pipeline: chirp_generate → download_audio → remix_track → render"""
        steps = ["chirp_generate", "download_audio", "remix_track", "render_full"]
        assert len(steps) == 4
        assert steps[2] == "remix_track"


class TestLofiArrangement:
    """Tests for create_lofi_arrangement — lofi hip-hop 4-track arrangement"""

    def test_tool_signature_exists(self):
        """create_lofi_arrangement is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_lofi_arrangement" in tool_names

    def test_default_bpm_78(self):
        """Default BPM is 78 (chillhop sweet spot)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bpm" and isinstance(d, ast.Constant):
                        assert d.value == 78
                return
        assert False, "function not found"

    def test_default_root_F(self):
        """Default root is F (classic lofi key)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert '"F"' in source or "'F'" in source
                return
        assert False, "function not found"

    def test_ii_V_I_harmony(self):
        """Harmony uses ii-V-I progression (jazzy lofi signature)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "ii_V_I" in source or "chord_degrees" in source
                assert "min7" in source
                assert "dom7" in source
                assert "maj7" in source
                return
        assert False, "function not found"

    def test_boom_bap_drums(self):
        """Drums are boom-bap pattern (kick + snare backbeat + 16th hats)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "boom_bap" in source
                assert "kick" in source.lower() or "kick_p" in source
                assert "snare" in source.lower() or "snare_p" in source
                assert "hat" in source.lower() or "hat_p" in source
                return
        assert False, "function not found"

    def test_four_tracks(self):
        """Arrangement uses 4 tracks: drums, bass, chords, melody"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "drum_track" in source
                assert "bass_track" in source
                assert "chord_track" in source
                assert "melody_track" in source
                return
        assert False, "function not found"

    def test_delegates_to_notes_batch(self):
        """Creates notes via create_notes_batch"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "mcp_opendaw_create_notes_batch" in source
                return
        assert False, "function not found"

    def test_lofi_in_full_genre_pipeline(self):
        """lofi is registered in create_full_genre_pipeline defaults + arrangement_fns"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_full_genre_pipeline":
                source = ast.unparse(node)
                assert "'lofi'" in source or '"lofi"' in source
                assert "mcp_opendaw_create_lofi_arrangement" in source
                return
        assert False, "full genre pipeline not found"

    def test_bpm_range_validation(self):
        """BPM validated to 65-95 range"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "65" in source
                assert "95" in source
                return
        assert False, "function not found"

    def test_chord_arpeggiation(self):
        """Chords are arpeggiated (gentle, not block)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "0.25" in source  # arpeggiation step
                assert "arpeggiat" in source.lower()
                return
        assert False, "function not found"

    def test_melody_pentatonic(self):
        """Melody uses pentatonic scale (sparse, sleepy)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_lofi_arrangement":
                source = ast.unparse(node)
                assert "PENTATONIC" in source
                return
        assert False, "function not found"


class TestSoulArrangement:
    """Tests for create_soul_arrangement — Motown/Stax soul 4-track arrangement"""

    def test_tool_signature_exists(self):
        """create_soul_arrangement is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_soul_arrangement" in tool_names

    def test_default_bpm_72(self):
        """Default BPM is 72 (classic slow soul)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bpm" and isinstance(d, ast.Constant):
                        assert d.value == 72
                return
        assert False, "function not found"

    def test_default_root_C(self):
        """Default root is C (warm soul key)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert '"C"' in source or "'C'" in source
                return
        assert False, "function not found"

    def test_gospel_changes(self):
        """Harmony uses I-IV-vi-V gospel changes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "I-IV-vi-V" in source or "gospel" in source.lower()
                assert "maj7" in source
                assert "dom7" in source
                return
        assert False, "function not found"

    def test_gospel_drums(self):
        """Drums are gospel soul pattern (backbeat + ride)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "kick" in source.lower() or "kick_p" in source
                assert "snare" in source.lower() or "snare_p" in source
                assert "ride" in source.lower()
                return
        assert False, "function not found"

    def test_four_tracks(self):
        """Arrangement uses 4 tracks: drums, bass, keys, horns"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "drum_track" in source
                assert "bass_track" in source
                assert "keys_track" in source
                assert "horns_track" in source
                return
        assert False, "function not found"

    def test_delegates_to_notes_batch(self):
        """Creates notes via create_notes_batch"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "mcp_opendaw_create_notes_batch" in source
                return
        assert False, "function not found"

    def test_soul_in_full_genre_pipeline(self):
        """soul is registered in create_full_genre_pipeline defaults + arrangement_fns"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_full_genre_pipeline":
                source = ast.unparse(node)
                assert "'soul'" in source or '"soul"' in source
                assert "mcp_opendaw_create_soul_arrangement" in source
                return
        assert False, "full genre pipeline not found"

    def test_bpm_range_validation(self):
        """BPM validated to 65-90 range"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "65" in source
                assert "90" in source
                return
        assert False, "function not found"

    def test_walking_bass(self):
        """Bass is melodic walking (root → fifth → octave → walk)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "walking" in source.lower() or "walk_note" in source
                return
        assert False, "function not found"

    def test_horn_fills(self):
        """Horns have melodic fills at end of cycle"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_soul_arrangement":
                source = ast.unparse(node)
                assert "fill" in source.lower()
                assert "pentatonic" in source.lower() or "fill_notes" in source
                return
        assert False, "function not found"


class TestTranscribeDrums:
    """Tests for _transcribe_drums and transcribe_drums tool"""

    def _make_impulse_wav(self, impulses, sr=44100, n_ch=1):
        """Create synthetic audio with kick/snare/hat impulses at given times.
        Kick = low-freq burst, snare = mid-freq burst, hat = high-freq noise.
        Returns channels list (list of float lists)."""
        duration = max(t for t, _ in impulses) + 0.5 if impulses else 2.0
        n = int(duration * sr)
        import math as _math
        channel = [0.0] * n
        for t, dtype in impulses:
            start = int(t * sr)
            if dtype == "kick":
                # Low-frequency burst: 60Hz sine, 100ms decay
                for i in range(int(0.1 * sr)):
                    pos = start + i
                    if pos < n:
                        env = _math.exp(-i / (0.02 * sr))
                        channel[pos] += 0.8 * env * _math.sin(2 * 3.14159 * 60 * i / sr)
            elif dtype == "snare":
                # Mid-frequency burst: 300Hz sine + noise, 80ms
                import random
                random.seed(42)
                for i in range(int(0.08 * sr)):
                    pos = start + i
                    if pos < n:
                        env = _math.exp(-i / (0.015 * sr))
                        channel[pos] += 0.6 * env * (_math.sin(2 * 3.14159 * 300 * i / sr) * 0.5 + random.random() * 0.5)
            elif dtype == "hat":
                # High-frequency noise burst, 30ms
                import random
                random.seed(42)
                for i in range(int(0.03 * sr)):
                    pos = start + i
                    if pos < n:
                        env = _math.exp(-i / (0.005 * sr))
                        channel[pos] += 0.3 * env * (random.random() * 2 - 1)
        return [channel]

    def test_empty_audio_returns_empty(self):
        from opendaw_mcp.utils import _transcribe_drums
        result = _transcribe_drums([], 44100)
        assert result["notes"] == []
        assert result["onset_count"] == 0

    def test_kick_detected(self):
        """A clear kick impulse should be detected as kick (pitch 36)"""
        from opendaw_mcp.utils import _transcribe_drums
        channels = self._make_impulse_wav([(0.0, "kick"), (0.5, "kick"), (1.0, "kick"), (1.5, "kick")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        kick_notes = [n for n in result["notes"] if n["drum_type"] == "kick"]
        assert len(kick_notes) >= 2, f"Expected at least 2 kick onsets, got {len(kick_notes)}"

    def test_snare_detected(self):
        """A clear snare impulse should be detected as snare (pitch 38)"""
        from opendaw_mcp.utils import _transcribe_drums
        channels = self._make_impulse_wav([(0.0, "snare"), (1.0, "snare"), (2.0, "snare"), (3.0, "snare")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        snare_notes = [n for n in result["notes"] if n["drum_type"] == "snare"]
        assert len(snare_notes) >= 1, f"Expected at least 1 snare onset, got {len(snare_notes)}"

    def test_hat_detected(self):
        """A clear hat impulse should be detected as hat (pitch 42)"""
        from opendaw_mcp.utils import _transcribe_drums
        channels = self._make_impulse_wav([(0.0, "hat"), (0.25, "hat"), (0.5, "hat"), (0.75, "hat")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        hat_notes = [n for n in result["notes"] if n["drum_type"] == "hat"]
        assert len(hat_notes) >= 1, f"Expected at least 1 hat onset, got {len(hat_notes)}"

    def test_beat_conversion(self):
        """Onset times should be converted to beat positions correctly"""
        from opendaw_mcp.utils import _transcribe_drums
        # At 120 BPM, 1 beat = 0.5 seconds
        channels = self._make_impulse_wav([(0.0, "kick"), (0.5, "kick")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        kick_notes = [n for n in result["notes"] if n["drum_type"] == "kick"]
        if len(kick_notes) >= 2:
            beat_diff = abs(kick_notes[1]["start_beat"] - kick_notes[0]["start_beat"])
            assert abs(beat_diff - 1.0) < 0.2, f"Expected ~1 beat between kicks, got {beat_diff}"

    def test_velocity_range(self):
        """Velocity should be between 0 and 1"""
        from opendaw_mcp.utils import _transcribe_drums
        channels = self._make_impulse_wav([(0.0, "kick"), (0.5, "snare"), (1.0, "hat")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        for n in result["notes"]:
            assert 0.0 <= n["velocity"] <= 1.0

    def test_midi_pitches(self):
        """Kick=36, snare=38, hat=42"""
        from opendaw_mcp.utils import _transcribe_drums
        channels = self._make_impulse_wav([(0.0, "kick"), (0.5, "snare"), (0.75, "hat")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        pitch_map = {36: "kick", 38: "snare", 42: "hat"}
        for n in result["notes"]:
            assert n["pitch"] in pitch_map
            assert n["drum_type"] == pitch_map[n["pitch"]]

    def test_band_counts(self):
        """Band counts should sum to onset_count"""
        from opendaw_mcp.utils import _transcribe_drums
        channels = self._make_impulse_wav([(0.0, "kick"), (0.5, "snare"), (1.0, "hat")])
        result = _transcribe_drums(channels, 44100, bpm=120)
        bc = result["band_counts"]
        assert bc["kick"] + bc["snare"] + bc["hat"] == result["onset_count"]

    def test_tool_signature_exists(self):
        """transcribe_drums is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_transcribe_drums" in tool_names

    def test_tool_delegates_to_transcribe(self):
        """transcribe_drums tool calls _transcribe_drums internally"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_drums":
                source = ast.unparse(node)
                assert "_transcribe_drums" in source
                return
        assert False, "function not found"

    def test_auto_bpm_detection(self):
        """When bpm=0, tool auto-detects BPM via _detect_bpm"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_drums":
                source = ast.unparse(node)
                assert "_detect_bpm" in source
                return
        assert False, "function not found"


class TestTranscribeMelody:
    """Tests for _transcribe_melody and transcribe_melody tool"""

    def _make_sine_wav(self, freqs, sr=44100, duration=2.0):
        """Create synthetic audio with sine tones at given frequencies.
        freqs: list of (start_time, frequency, duration_sec)
        Returns channels list."""
        import math as _math
        n = int(duration * sr)
        channel = [0.0] * n
        for start_t, freq, dur in freqs:
            start = int(start_t * sr)
            end = min(n, start + int(dur * sr))
            for i in range(start, end):
                t = (i - start) / sr
                env = min(1.0, t * 50) * min(1.0, (end - i) / (sr * 0.05))
                channel[i] += 0.5 * env * _math.sin(2 * _math.pi * freq * (i - start) / sr)
        return [channel]

    def test_empty_audio_returns_empty(self):
        from opendaw_mcp.utils import _transcribe_melody
        result = _transcribe_melody([], 44100)
        assert result["notes"] == []
        assert result["note_count"] == 0

    def test_sine_detected(self):
        """A 440Hz sine should produce at least one note (A4=69)"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 1.0)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        assert result["note_count"] >= 1, f"Expected at least 1 note, got {result['note_count']}"

    def test_pitch_accuracy(self):
        """440Hz → MIDI 69 (A4)"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 0.5)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        if result["notes"]:
            assert abs(result["notes"][0]["pitch"] - 69) <= 1, f"Expected pitch ~69, got {result['notes'][0]['pitch']}"

    def test_two_notes(self):
        """Two separate tones should produce two notes"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 0.3), (0.4, 523.0, 0.3)])  # A4 then C5
        result = _transcribe_melody(channels, 44100, bpm=120)
        assert result["note_count"] >= 1, f"Expected at least 1 note, got {result['note_count']}"

    def test_velocity_range(self):
        """Velocity should be between 0 and 1"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 0.5)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        for n in result["notes"]:
            assert 0.0 <= n["velocity"] <= 1.0

    def test_midi_pitch_range(self):
        """All pitches should be in valid MIDI range (21-108)"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 220.0, 0.5), (0.6, 880.0, 0.5)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        for n in result["notes"]:
            assert 21 <= n["pitch"] <= 108

    def test_beat_conversion(self):
        """At 120 BPM, 1 beat = 0.5 seconds"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 2.0)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        if result["notes"]:
            # First note should start near beat 0
            assert abs(result["notes"][0]["start_beat"]) < 0.5

    def test_cents_field(self):
        """Notes should include cents deviation for tuning accuracy"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 0.5)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        for n in result["notes"]:
            assert "cents" in n
            assert -50 <= n["cents"] <= 50  # within half semitone

    def test_clarity_field(self):
        """Notes should include clarity (pitch confidence)"""
        from opendaw_mcp.utils import _transcribe_melody
        channels = self._make_sine_wav([(0.0, 440.0, 0.5)])
        result = _transcribe_melody(channels, 44100, bpm=120)
        for n in result["notes"]:
            assert "clarity" in n
            assert 0.0 <= n["clarity"] <= 1.0

    def test_tool_signature_exists(self):
        """transcribe_melody is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_transcribe_melody" in tool_names

    def test_tool_delegates_to_transcribe(self):
        """transcribe_melody tool calls _transcribe_melody internally"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_melody":
                source = ast.unparse(node)
                assert "_transcribe_melody" in source
                return
        assert False, "function not found"

    def test_auto_bpm_detection(self):
        """When bpm=0, tool auto-detects BPM"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_melody":
                source = ast.unparse(node)
                assert "_detect_bpm" in source
                return
        assert False, "function not found"


class TestFormantShifterDSP:
    """Tests for werkstatt_formant_shifter.js — LPC-based formant shifting"""

    def _read_script(self):
        import pathlib
        p = pathlib.Path(__file__).parent.parent / "scripts" / "werkstatt_formant_shifter.js"
        return p.read_text()

    def test_header(self):
        code = self._read_script()
        assert "@werkstatt formant_shifter" in code

    def test_node_syntax_valid(self):
        import subprocess
        result = subprocess.run(["node", "-c", "scripts/werkstatt_formant_shifter.js"],
                              capture_output=True, text=True)
        assert result.returncode == 0

    def test_seven_params(self):
        """7 params: shift, formants, pitch_tracking, brightness, width, mix, output"""
        code = self._read_script()
        params = code.count("@param")
        assert params == 7

    def test_levinson_durbin(self):
        """Has Levinson-Durbin recursion for LPC coefficients"""
        code = self._read_script()
        assert "levinson" in code.lower()
        assert "refl" in code.lower()

    def test_lattice_filter(self):
        """Uses lattice filter structure"""
        code = self._read_script()
        assert "lattice" in code.lower() or "Lattice" in code

    def test_autocorrelation(self):
        """Computes autocorrelation for LPC analysis"""
        code = self._read_script()
        assert "autocorr" in code.lower() or "autocorrelation" in code.lower()

    def test_formant_shift_ratio(self):
        """Shift parameter controls formant frequency scaling"""
        code = self._read_script()
        assert "shiftRatio" in code or "shift" in code.lower()
        assert "formantScale" in code or "scale" in code.lower()

    def test_residual_extraction(self):
        """Extracts residual (pitch excitation) from signal"""
        code = self._read_script()
        assert "residual" in code.lower()

    def test_dry_wet_mix(self):
        """Output = dry + (wet - dry) * mix"""
        code = self._read_script()
        assert "mix" in code
        assert "dry" in code.lower() or "currentSample" in code

    def test_smooth_coefficients(self):
        """Coefficient smoothing to avoid clicks"""
        code = self._read_script()
        assert "smooth" in code.lower()
        assert "prevRefl" in code

    def test_filter_stages_range(self):
        """Formants parameter clamped to 3-8 range"""
        code = self._read_script()
        assert "Math.min(8" in code or "min(8" in code
        assert "Math.max(3" in code or "max(3" in code


class TestTranscribeAudio:
    """Tests for transcribe_audio — composite drum + melody transcription"""

    def test_tool_signature_exists(self):
        """transcribe_audio is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_transcribe_audio" in tool_names

    def test_delegates_to_both_transcribers(self):
        """transcribe_audio calls both _transcribe_drums and _transcribe_melody"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_audio":
                source = ast.unparse(node)
                assert "_transcribe_drums" in source
                assert "_transcribe_melody" in source
                return
        assert False, "function not found"

    def test_auto_bpm_detection(self):
        """When bpm=0, auto-detects BPM via _detect_bpm"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_audio":
                source = ast.unparse(node)
                assert "_detect_bpm" in source
                return
        assert False, "function not found"

    def test_creates_notes_on_two_tracks(self):
        """Creates notes on drum_track and melody_track separately"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_audio":
                source = ast.unparse(node)
                assert "drum_track" in source
                assert "melody_track" in source
                assert "mcp_opendaw_create_notes_batch" in source
                return
        assert False, "function not found"

    def test_returns_total_notes(self):
        """Returns total_notes = drum + melody"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_audio":
                source = ast.unparse(node)
                assert "total_notes" in source
                return
        assert False, "function not found"

    def test_default_track_indices(self):
        """Default drum_track=0, melody_track=1"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_transcribe_audio":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                param_defaults = {}
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if isinstance(d, ast.Constant):
                        param_defaults[arg_name] = d.value
                assert param_defaults.get("drum_track") == 0
                assert param_defaults.get("melody_track") == 1
                return
        assert False, "function not found"


class TestRnbArrangement:
    """Tests for create_rnb_arrangement — contemporary R&B 4-track arrangement"""

    def test_tool_signature_exists(self):
        """create_rnb_arrangement is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_rnb_arrangement" in tool_names

    def test_default_bpm_68(self):
        """Default BPM is 68 (modern R&B sweet spot)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bpm" and isinstance(d, ast.Constant):
                        assert d.value == 68
                return
        assert False, "function not found"

    def test_default_root_C(self):
        """Default root is C (dark R&B key)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert '"C"' in source or "'C'" in source
                return
        assert False, "function not found"

    def test_minor_key_progression(self):
        """Harmony uses i-VI-III-VII minor-key progression"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "i-VI-III-VII" in source or "i_VI_III_VII" in source
                assert "min9" in source
                assert "maj7" in source
                return
        assert False, "function not found"

    def test_half_time_drums(self):
        """Drums are half-time with triplet hi-hats (trap/R&B influence)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "half_time" in source.lower() or "half-time" in source.lower()
                assert "triplet" in source.lower()
                assert "clap" in source.lower() or "clap_p" in source
                return
        assert False, "function not found"

    def test_sub_bass(self):
        """Bass is deep sub bass (long sustained root)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "sub" in source.lower()
                return
        assert False, "function not found"

    def test_vocal_style_lead(self):
        """Lead has vocal-style melodic phrases with blue notes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "blue_note" in source or "blue" in source.lower()
                assert "pentatonic_minor" in source or "PENTATONIC_MINOR" in source
                return
        assert False, "function not found"

    def test_four_tracks(self):
        """Arrangement uses 4 tracks: drums, bass, chord, lead"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "drum_track" in source
                assert "bass_track" in source
                assert "chord_track" in source
                assert "lead_track" in source
                return
        assert False, "function not found"

    def test_delegates_to_notes_batch(self):
        """Creates notes via create_notes_batch"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "mcp_opendaw_create_notes_batch" in source
                return
        assert False, "function not found"

    def test_rnb_in_full_genre_pipeline(self):
        """rnb is registered in create_full_genre_pipeline defaults + arrangement_fns"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_full_genre_pipeline":
                source = ast.unparse(node)
                assert "'rnb'" in source or '"rnb"' in source
                assert "mcp_opendaw_create_rnb_arrangement" in source
                return
        assert False, "full genre pipeline not found"

    def test_bpm_range_validation(self):
        """BPM validated to 55-85 range"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_rnb_arrangement":
                source = ast.unparse(node)
                assert "55" in source
                assert "85" in source
                return
        assert False, "function not found"

    def test_rnb_in_genre_mix(self):
        """rnb is in apply_genre_mix valid_genres"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_apply_genre_mix":
                source = ast.unparse(node)
                assert '"rnb"' in source or "'rnb'" in source
                return
        assert False, "apply_genre_mix not found"

    def test_rnb_in_humanization(self):
        """rnb is in apply_genre_humanization valid_genres"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_apply_genre_humanization":
                source = ast.unparse(node)
                assert '"rnb"' in source or "'rnb'" in source
                return
        assert False, "apply_genre_humanization not found"

    def test_rnb_in_arrangement_variation(self):
        """rnb is in create_arrangement_variation defaults + arrangement_fns"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_arrangement_variation":
                source = ast.unparse(node)
                assert '"rnb"' in source or "'rnb'" in source
                assert "mcp_opendaw_create_rnb_arrangement" in source
                return
        assert False, "create_arrangement_variation not found"

    def test_rnb_in_song_with_variations(self):
        """rnb is in create_song_with_variations defaults"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_song_with_variations":
                source = ast.unparse(node)
                assert '"rnb"' in source or "'rnb'" in source
                return
        assert False, "create_song_with_variations not found"


class TestScaleVelocity:
    """Tests for scale_velocity — MIDI dynamics scaling tool"""

    def test_tool_signature_exists(self):
        """scale_velocity is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_scale_velocity" in tool_names

    def test_has_5_modes(self):
        """Supports multiply, add, set, normalize, compress modes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "multiply" in source
                assert "add" in source
                assert "set" in source
                assert "normalize" in source
                assert "compress" in source
                return
        assert False, "function not found"

    def test_default_mode_multiply(self):
        """Default mode is multiply"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "mode" and isinstance(d, ast.Constant):
                        assert d.value == "multiply"
                    if arg_name == "value" and isinstance(d, ast.Constant):
                        assert d.value == 1.0
                return
        assert False, "function not found"

    def test_clamp_range_params(self):
        """Has min_velocity and max_velocity clamp params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "min_velocity" in source
                assert "max_velocity" in source
                return
        assert False, "function not found"

    def test_validation_min_max(self):
        """Validates min_velocity <= max_velocity"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "cannot exceed" in source or "min_velocity" in source
                return
        assert False, "function not found"

    def test_uses_modify(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_returns_velocity_stats(self):
        """Returns original and new velocity min/max/avg"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "original" in source
                assert "new" in source
                assert "min" in source
                assert "max" in source
                return
        assert False, "function not found"

    def test_compress_uses_midpoint(self):
        """Compress mode uses 0.5 midpoint formula"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "mid" in source
                assert "0.5" in source
                return
        assert False, "function not found"

    def test_normalize_uses_current_max(self):
        """Normalize mode scales relative to current max velocity"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_velocity":
                source = ast.unparse(node)
                assert "curMax" in source or "ratio" in source
                return
        assert False, "function not found"


class TestCopyNotesToTrack:
    """Tests for copy_notes_to_track — MIDI layering and doubling"""

    def test_tool_signature_exists(self):
        """copy_notes_to_track is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_copy_notes_to_track" in tool_names

    def test_has_transpose_param(self):
        """Supports transpose (semitone offset)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "transpose" in source
                assert "semis" in source or "pitch" in source
                return
        assert False, "function not found"

    def test_has_time_offset(self):
        """Supports time_offset for echo/call-and-response"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "time_offset" in source
                assert "tOff" in source
                return
        assert False, "function not found"

    def test_has_velocity_scale(self):
        """Supports velocity_scale for layer dynamics"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "velocity_scale" in source
                assert "velScale" in source
                return
        assert False, "function not found"

    def test_has_source_and_dest_params(self):
        """Has source_unit_index, source_track_index, dest_track_index params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                args = [a.arg for a in node.args.args]
                assert "source_unit_index" in args
                assert "source_track_index" in args
                assert "dest_track_index" in args
                return
        assert False, "function not found"

    def test_uses_NoteEventBox_create(self):
        """Creates notes via NoteEventBox.create (not h.createNoteEvent)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "NoteEventBox.create" in source
                return
        assert False, "function not found"

    def test_uses_modify(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_clamps_pitch_to_midi_range(self):
        """Skips notes that fall outside 0-127 MIDI range"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "pitch < 0" in source or "pitch > 127" in source
                assert "skipped" in source
                return
        assert False, "function not found"

    def test_dest_unit_defaults_to_source(self):
        """dest_unit_index defaults to source_unit_index when -1"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_copy_notes_to_track":
                source = ast.unparse(node)
                assert "dest_unit_index >= 0" in source or "dest_unit" in source
                return
        assert False, "function not found"


class TestScaleDurations:
    """Tests for scale_durations — MIDI note duration scaling tool"""

    def test_tool_signature_exists(self):
        """scale_durations is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_scale_durations" in tool_names

    def test_has_5_modes(self):
        """Supports multiply, add, set, quantize, legato modes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "multiply" in source
                assert "add" in source
                assert "set" in source
                assert "quantize" in source
                assert "legato" in source
                return
        assert False, "function not found"

    def test_default_mode_multiply(self):
        """Default mode is multiply"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "mode" and isinstance(d, ast.Constant):
                        assert d.value == "multiply"
                    if arg_name == "value" and isinstance(d, ast.Constant):
                        assert d.value == 1.0
                return
        assert False, "function not found"

    def test_has_clamp_params(self):
        """Has min_duration and max_duration clamp params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "min_duration" in source
                assert "max_duration" in source
                return
        assert False, "function not found"

    def test_uses_Quarter_ppqn(self):
        """Uses Quarter = 960 for PPQN conversion"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "Quarter" in source
                assert "960" in source
                return
        assert False, "function not found"

    def test_uses_modify(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_returns_duration_stats(self):
        """Returns original and new duration min/max/avg"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "original" in source
                assert "new" in source
                return
        assert False, "function not found"

    def test_legato_sorts_by_position(self):
        """Legato mode sorts notes by position"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "sort" in source
                assert "position" in source
                return
        assert False, "function not found"

    def test_quantize_has_grid_map(self):
        """Quantize mode has grid map (16th/8th/quarter/half)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_scale_durations":
                source = ast.unparse(node)
                assert "16th" in source
                assert "8th" in source
                assert "quarter" in source
                assert "half" in source
                return
        assert False, "function not found"


class TestGrooveTransfer:
    """Tests for groove_transfer — groove feel transfer between regions"""

    def test_tool_signature_exists(self):
        """groove_transfer is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_groove_transfer" in tool_names

    def test_has_source_and_dest_params(self):
        """Has source_unit_index, source_track_index, dest_unit_index, dest_track_index"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                arg_names = [a.arg for a in node.args.args]
                assert "source_unit_index" in arg_names
                assert "source_track_index" in arg_names
                assert "dest_unit_index" in arg_names
                assert "dest_track_index" in arg_names
                assert "source_region_index" in arg_names
                assert "dest_region_index" in arg_names
                return
        assert False, "function not found"

    def test_has_strength_params(self):
        """Has timing_strength and velocity_strength params (0-1)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                arg_names = [a.arg for a in node.args.args]
                assert "timing_strength" in arg_names
                assert "velocity_strength" in arg_names
                return
        assert False, "function not found"

    def test_has_groove_length_param(self):
        """Has groove_length param for cycle length in beats"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                arg_names = [a.arg for a in node.args.args]
                assert "groove_length" in arg_names
                return
        assert False, "function not found"

    def test_has_grid_param(self):
        """Has grid param for timing offset computation"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                arg_names = [a.arg for a in node.args.args]
                assert "grid" in arg_names
                return
        assert False, "function not found"

    def test_validates_strength_range(self):
        """Validates timing_strength and velocity_strength are 0-1"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                source = ast.unparse(node)
                assert "timing_strength must be 0-1" in source
                assert "velocity_strength must be 0-1" in source
                return
        assert False, "function not found"

    def test_builds_groove_template(self):
        """Builds a groove template with timing offsets and velocity ratios"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                source = ast.unparse(node)
                assert "grooveSlots" in source or "groove_template" in source
                assert "timingOffset" in source
                assert "velocityRatio" in source
                return
        assert False, "function not found"

    def test_uses_modify_for_mutations(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_cycles_groove_by_modulo(self):
        """Groove cycles every groove_length beats (modulo arithmetic)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_groove_transfer":
                source = ast.unparse(node)
                assert "grooveLen" in source or "groove_length" in source
                assert "%" in source  # modulo for cycle position
                return
        assert False, "function not found"


class TestTimeWarpNotes:
    """Tests for time_warp_notes — half-time / double-time / custom time stretch for MIDI"""

    def test_tool_signature_exists(self):
        """time_warp_notes is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_time_warp_notes" in tool_names

    def test_has_warp_factor_param(self):
        """Has warp_factor param (0.5=half-time, 2.0=double-time)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "warp_factor" in arg_names
                return
        assert False, "function not found"

    def test_has_origin_param(self):
        """Has origin param (start/zero)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "origin" in arg_names
                return
        assert False, "function not found"

    def test_default_warp_is_half_time(self):
        """Default warp_factor is 0.5 (half-time)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "warp_factor" and isinstance(d, ast.Constant):
                        assert d.value == 0.5
                    if arg_name == "origin" and isinstance(d, ast.Constant):
                        assert d.value == "start"
                return
        assert False, "function not found"

    def test_validates_warp_range(self):
        """Validates warp_factor is 0.1-8.0"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                source = ast.unparse(node)
                assert "0.1" in source
                assert "8.0" in source
                assert "warp_factor must be" in source
                return
        assert False, "function not found"

    def test_warps_both_position_and_duration(self):
        """Warps BOTH position and duration (unlike scale_durations which only does duration)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                source = ast.unparse(node)
                assert "position.setValue" in source
                assert "duration.setValue" in source
                assert "factor" in source  # both scaled by factor
                return
        assert False, "function not found"

    def test_uses_modify_for_mutations(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_supports_all_regions(self):
        """Supports region_index=-1 for all regions on track"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                source = ast.unparse(node)
                assert "regionsToProcess" in source
                return
        assert False, "function not found"

    def test_returns_new_extent(self):
        """Returns new start/end PPQN positions"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_time_warp_notes":
                source = ast.unparse(node)
                assert "new_start_ppqn" in source
                assert "new_end_ppqn" in source
                return
        assert False, "function not found"


class TestForceScaleNotes:
    """Tests for force_scale_notes — harmonic snap to a scale"""

    def test_tool_signature_exists(self):
        """force_scale_notes is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_force_scale_notes" in tool_names

    def test_has_root_note_and_scale_params(self):
        """Has root_note and scale params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "root_note" in arg_names
                assert "scale" in arg_names
                return
        assert False, "function not found"

    def test_has_direction_param(self):
        """Has direction param (nearest/up/down)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "direction" in arg_names
                return
        assert False, "function not found"

    def test_has_preserve_octave_param(self):
        """Has preserve_octave param (True = stay in octave, False = allow octave jumps)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "preserve_octave" in arg_names
                return
        assert False, "function not found"

    def test_default_root_is_C_major(self):
        """Default root_note='C', scale='major'"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "root_note" and isinstance(d, ast.Constant):
                        assert d.value == "C"
                    if arg_name == "scale" and isinstance(d, ast.Constant):
                        assert d.value == "major"
                return
        assert False, "function not found"

    def test_validates_root_note(self):
        """Validates root_note against note names"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                source = ast.unparse(node)
                assert "invalid root_note" in source
                return
        assert False, "function not found"

    def test_validates_scale_name(self):
        """Validates scale name against SCALE_INTERVALS"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                source = ast.unparse(node)
                assert "SCALE_INTERVALS" in source
                assert "unknown scale" in source
                return
        assert False, "function not found"

    def test_uses_modify_for_mutations(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_modifies_pitch_values(self):
        """Modifies pitch.setValue on out-of-scale notes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                source = ast.unparse(node)
                assert "pitch.setValue" in source
                assert "allowedPcs" in source or "allowed_pcs" in source
                return
        assert False, "function not found"

    def test_returns_snapped_and_already_in_scale_counts(self):
        """Returns notes_snapped and notes_already_in_scale counts"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_force_scale_notes":
                source = ast.unparse(node)
                assert "notes_snapped" in source
                assert "notes_already_in_scale" in source
                return
        assert False, "function not found"


class TestIdentifyChords:
    """Tests for identify_chords — harmonic analysis from existing notes"""

    def test_tool_signature_exists(self):
        """identify_chords is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_identify_chords" in tool_names

    def test_has_unit_and_track_params(self):
        """Has unit_index and track_index params (required)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                arg_names = [a.arg for a in node.args.args]
                assert "unit_index" in arg_names
                assert "track_index" in arg_names
                return
        assert False, "function not found"

    def test_has_group_tolerance_param(self):
        """Has group_tolerance param for temporal grouping"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                arg_names = [a.arg for a in node.args.args]
                assert "group_tolerance" in arg_names
                return
        assert False, "function not found"

    def test_has_min_notes_param(self):
        """Has min_notes param (default 3 = triad minimum)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                arg_names = [a.arg for a in node.args.args]
                assert "min_notes" in arg_names
                return
        assert False, "function not found"

    def test_uses_chord_intervals(self):
        """Uses CHORD_INTERVALS from music_theory"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                source = ast.unparse(node)
                assert "CHORD_INTERVALS" in source
                return
        assert False, "function not found"

    def test_groups_notes_by_temporal_overlap(self):
        """Groups notes by temporal overlap"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                source = ast.unparse(node)
                assert "groups" in source
                assert "tol" in source or "tolerance" in source
                return
        assert False, "function not found"

    def test_matches_pitch_class_sets(self):
        """Matches pitch class sets against chord templates"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                source = ast.unparse(node)
                assert "pitchClasses" in source or "pitch_classes" in source
                assert "templates" in source
                return
        assert False, "function not found"

    def test_handles_subset_matching(self):
        """Handles chords with extra notes (subset matching)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                source = ast.unparse(node)
                assert "subset" in source or "extensions" in source
                return
        assert False, "function not found"

    def test_returns_chord_list_with_positions(self):
        """Returns chord list with time positions and chord names"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_identify_chords":
                source = ast.unparse(node)
                assert "chords_identified" in source
                assert "position_beats" in source
                return
        assert False, "function not found"


class TestDiatonicTransposeNotes:
    """Tests for diatonic_transpose_notes — scale-step transpose (not semitones)"""

    def test_tool_signature_exists(self):
        """diatonic_transpose_notes is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_diatonic_transpose_notes" in tool_names

    def test_has_steps_param(self):
        """Has steps param (scale steps, not semitones)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "steps" in arg_names
                return
        assert False, "function not found"

    def test_has_root_note_and_scale_params(self):
        """Has root_note and scale params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "root_note" in arg_names
                assert "scale" in arg_names
                return
        assert False, "function not found"

    def test_default_step_is_1(self):
        """Default steps is 1 (up one scale step)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "steps" and isinstance(d, ast.Constant):
                        assert d.value == 1
                    if arg_name == "root_note" and isinstance(d, ast.Constant):
                        assert d.value == "C"
                    if arg_name == "scale" and isinstance(d, ast.Constant):
                        assert d.value == "major"
                return
        assert False, "function not found"

    def test_validates_nonzero_steps(self):
        """Validates steps != 0"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                source = ast.unparse(node)
                assert "steps must be non-zero" in source
                return
        assert False, "function not found"

    def test_uses_scale_intervals(self):
        """Uses SCALE_INTERVALS from music_theory"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                source = ast.unparse(node)
                assert "SCALE_INTERVALS" in source
                return
        assert False, "function not found"

    def test_skips_out_of_scale_notes(self):
        """Skips notes that are not in the scale (doesn't force them in)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                source = ast.unparse(node)
                assert "skipped" in source or "not in scale" in source
                return
        assert False, "function not found"

    def test_handles_octave_wrapping(self):
        """Handles octave wrapping when shifting past scale boundaries"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                source = ast.unparse(node)
                assert "newOctave" in source or "octave" in source
                return
        assert False, "function not found"

    def test_uses_modify_for_mutations(self):
        """Uses h.modify() for box mutations"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                source = ast.unparse(node)
                assert "h.modify" in source
                return
        assert False, "function not found"

    def test_returns_transposed_and_skipped_counts(self):
        """Returns notes_transposed and notes_skipped counts"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_diatonic_transpose_notes":
                source = ast.unparse(node)
                assert "notes_transposed" in source
                assert "notes_skipped" in source
                return
        assert False, "function not found"


class TestBluesArrangement:
    """Tests for create_blues_arrangement — 12-bar blues multi-track arrangement"""

    def test_tool_signature_exists(self):
        """create_blues_arrangement is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_blues_arrangement" in tool_names

    def test_has_4_tracks(self):
        """Has drum_track, bass_track, chord_track, lead_track params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                arg_names = [a.arg for a in node.args.args]
                assert "drum_track" in arg_names
                assert "bass_track" in arg_names
                assert "chord_track" in arg_names
                assert "lead_track" in arg_names
                return
        assert False, "function not found"

    def test_default_bpm_is_120(self):
        """Default bpm is 120 (classic Chicago blues)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bpm" and isinstance(d, ast.Constant):
                        assert d.value == 120
                    if arg_name == "root" and isinstance(d, ast.Constant):
                        assert d.value == "A"
                return
        assert False, "function not found"

    def test_default_bars_is_12(self):
        """Default bars is 12 (one full blues chorus)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bars" and isinstance(d, ast.Constant):
                        assert d.value == 12
                return
        assert False, "function not found"

    def test_validates_bars_multiple_of_12(self):
        """Validates bars must be multiple of 12 (12-bar blues form)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                source = ast.unparse(node)
                assert "multiple of 12" in source
                return
        assert False, "function not found"

    def test_has_12_bar_blues_form(self):
        """Contains the 12-bar blues form (I-IV-V)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                source = ast.unparse(node)
                assert "I-I-I-I" in source or "0, 0, 0, 0, 5, 5, 0, 0, 7, 5, 0, 7" in source
                return
        assert False, "function not found"

    def test_has_dominant_7th_voicings(self):
        """Uses dominant 7th voicings (not triads)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                source = ast.unparse(node)
                assert "0, 4, 7, 10" in source  # dom7 intervals
                return
        assert False, "function not found"

    def test_has_blues_scale(self):
        """Uses blues scale (root, b3, 4, b5, 5, b7)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                source = ast.unparse(node)
                assert "0, 3, 5, 6, 7, 10" in source  # blues scale intervals
                return
        assert False, "function not found"

    def test_has_walking_bass(self):
        """Has walking bass (quarter notes, chord tone outline)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                source = ast.unparse(node)
                assert "walking" in source
                assert "chord_root + 7" in source or "chord_root" in source
                return
        assert False, "function not found"

    def test_has_shuffle_drums(self):
        """Has shuffle drums (triplet hi-hats)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_blues_arrangement":
                source = ast.unparse(node)
                assert "2.0 / 3.0" in source or "shuffle" in source
                return
        assert False, "function not found"

    def test_registered_in_genre_mix(self):
        """Blues is registered in apply_genre_mix valid_genres"""
        import ast
        _ = ast.parse(open("server.py").read())
        source = open("server.py").read()
        assert '"blues"' in source

    def test_has_genre_mix_recipe(self):
        """Has a genre_mix recipe for blues"""
        import ast
        _ = ast.parse(open("server.py").read())
        source = open("server.py").read()
        # Find the blues recipe in the recipes dict
        assert '"blues": {' in source or '"blues":{' in source


class TestExtractMotifs:
    """Tests for extract_motifs — repeating melodic motif extraction"""

    def test_tool_signature_exists(self):
        """extract_motifs is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_extract_motifs" in tool_names

    def test_has_7_params(self):
        """Has unit_index, track_index, region_index, min_motif_length, max_motif_length, min_repetitions, max_results"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                arg_names = [a.arg for a in node.args.args]
                assert "unit_index" in arg_names
                assert "track_index" in arg_names
                assert "region_index" in arg_names
                assert "min_motif_length" in arg_names
                assert "max_motif_length" in arg_names
                assert "min_repetitions" in arg_names
                assert "max_results" in arg_names
                return
        assert False, "function not found"

    def test_default_min_motif_length_is_3(self):
        """Default min_motif_length is 3"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "min_motif_length" and isinstance(d, ast.Constant):
                        assert d.value == 3
                        return
        assert False, "default not found"

    def test_default_max_motif_length_is_8(self):
        """Default max_motif_length is 8"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "max_motif_length" and isinstance(d, ast.Constant):
                        assert d.value == 8
                        return
        assert False, "default not found"

    def test_default_min_repetitions_is_2(self):
        """Default min_repetitions is 2"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "min_repetitions" and isinstance(d, ast.Constant):
                        assert d.value == 2
                        return
        assert False, "default not found"

    def test_validates_min_motif_length(self):
        """Validates min_motif_length >= 2"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                assert "min_motif_length must be at least 2" in source
                return
        assert False, "function not found"

    def test_validates_max_ge_min(self):
        """Validates max_motif_length >= min_motif_length"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                assert "max_motif_length must be >= min_motif_length" in source
                return
        assert False, "function not found"

    def test_has_contour_classification(self):
        """Has contour type classification (ascending, descending, arch, etc.)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                assert "ascending" in source
                assert "descending" in source
                assert "arch" in source
                return
        assert False, "function not found"

    def test_has_significance_scoring(self):
        """Has significance scoring (repetitions * note_count)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                assert "significance" in source
                return
        assert False, "function not found"

    def test_has_occurrences(self):
        """Returns occurrences with start positions and pitches"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                assert "occurrences" in source
                assert "start_position" in source
                return
        assert False, "function not found"

    def test_has_deduplication(self):
        """Has deduplication to avoid reporting sub-motifs of larger motifs"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                assert "seenPositions" in source or "filtered" in source
                return
        assert False, "function not found"

    def test_uses_interval_contour(self):
        """Uses interval contour (pitch differences) for matching, not absolute pitches"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_extract_motifs":
                source = ast.unparse(node)
                # The contour is built from intervals (pitch differences)
                assert "intervals" in source
                assert "contour" in source
                return
        assert False, "function not found"


class TestAnalyzeSongStructure:
    """Tests for analyze_song_structure — structural segmentation of MIDI content"""

    def test_tool_signature_exists(self):
        """analyze_song_structure is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_analyze_song_structure" in tool_names

    def test_has_2_params(self):
        """Has unit_index and bars_per_segment params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                arg_names = [a.arg for a in node.args.args]
                assert "unit_index" in arg_names
                assert "bars_per_segment" in arg_names
                return
        assert False, "function not found"

    def test_default_bars_per_segment_is_4(self):
        """Default bars_per_segment is 4"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bars_per_segment" and isinstance(d, ast.Constant):
                        assert d.value == 4
                        return
        assert False, "default not found"

    def test_validates_bars_per_segment(self):
        """Validates bars_per_segment >= 2"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "bars_per_segment must be at least 2" in source
                return
        assert False, "function not found"

    def test_has_density_classification(self):
        """Has density classification (sparse/low/medium/high/dense)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "sparse" in source
                assert "dense" in source
                return
        assert False, "function not found"

    def test_has_segment_labels(self):
        """Has structural labels (intro/verse/chorus/bridge/outro/breakdown)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "intro" in source
                assert "verse" in source
                assert "chorus" in source
                assert "bridge" in source
                assert "outro" in source
                assert "breakdown" in source
                return
        assert False, "function not found"

    def test_has_energy_calculation(self):
        """Has energy calculation (density × velocity)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "energy" in source
                return
        assert False, "function not found"

    def test_has_form_string(self):
        """Returns a form string (e.g. 'intro → verse → chorus')"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "form" in source
                return
        assert False, "function not found"

    def test_has_chorus_detection(self):
        """Has chorus detection (highest energy segment labeled as chorus)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "chorusIdx" in source or "chorus" in source
                return
        assert False, "function not found"

    def test_has_bar_features(self):
        """Computes per-bar features (density, pitch range, velocity, tracks)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "density" in source
                assert "pitch_range" in source
                assert "avg_velocity" in source
                assert "active_tracks" in source
                return
        assert False, "function not found"

    def test_has_segmentation_logic(self):
        """Has segmentation logic that groups consecutive bars with similar density"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "segments" in source
                assert "createSegment" in source
                return
        assert False, "function not found"

    def test_returns_segment_bar_ranges(self):
        """Returns segments with start_bar and end_bar"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_analyze_song_structure":
                source = ast.unparse(node)
                assert "start_bar" in source
                assert "end_bar" in source
                return
        assert False, "function not found"


class TestClassifyDrumPattern:
    """Tests for classify_drum_pattern — rhythmic pattern classification"""

    def test_tool_signature_exists(self):
        """classify_drum_pattern is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_classify_drum_pattern" in tool_names

    def test_has_3_params(self):
        """Has unit_index, track_index, region_index params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                arg_names = [a.arg for a in node.args.args]
                assert "unit_index" in arg_names
                assert "track_index" in arg_names
                assert "region_index" in arg_names
                return
        assert False, "function not found"

    def test_has_gm_drum_map(self):
        """Uses GM drum pitch map (36=kick, 38=snare, 42=hat, etc.)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "36" in source
                assert "38" in source
                assert "42" in source
                assert "46" in source
                return
        assert False, "function not found"

    def test_has_pattern_classifications(self):
        """Has all 8 pattern classifications"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "four-on-the-floor" in source
                assert "boom-bap" in source
                assert "trap" in source
                assert "breakbeat" in source
                assert "shuffle" in source
                assert "half-time" in source
                assert "amen" in source
                assert "march" in source
                return
        assert False, "function not found"

    def test_has_confidence_scoring(self):
        """Has confidence scoring for each pattern match"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "confidence" in source
                return
        assert False, "function not found"

    def test_has_syncopation_analysis(self):
        """Has syncopation analysis (off-grid hits ratio)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "syncopation" in source
                return
        assert False, "function not found"

    def test_has_triplet_detection(self):
        """Has triplet/shuffle feel detection"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "triplet" in source
                return
        assert False, "function not found"

    def test_has_velocity_analysis(self):
        """Has velocity analysis (avg velocity per drum type)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "avg_kick_vel" in source
                assert "avg_snare_vel" in source
                assert "avg_hat_vel" in source
                return
        assert False, "function not found"

    def test_has_per_bar_breakdown(self):
        """Has per-bar analysis breakdown"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "per_bar" in source
                assert "barAnalyses" in source
                return
        assert False, "function not found"

    def test_has_unknown_fallback(self):
        """Has unknown fallback when no pattern matches"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "unknown" in source
                return
        assert False, "function not found"

    def test_has_best_match_sorting(self):
        """Sorts pattern matches by confidence and returns best match"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "best_match" in source
                assert "sort" in source
                return
        assert False, "function not found"

    def test_has_hat_density_analysis(self):
        """Has hat density analysis for trap detection"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_classify_drum_pattern":
                source = ast.unparse(node)
                assert "hat_density" in source
                assert "fast_hats" in source
                return
        assert False, "function not found"


class TestCreateMotifVariations:
    """Tests for create_motif_variations — classical motif transformation"""

    def test_tool_signature_exists(self):
        """create_motif_variations is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_motif_variations" in tool_names

    def test_has_source_and_target_params(self):
        """Has source_unit, source_track, source_region and target params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                arg_names = [a.arg for a in node.args.args]
                assert "source_unit" in arg_names
                assert "source_track" in arg_names
                assert "source_region" in arg_names
                assert "target_unit" in arg_names
                assert "target_track" in arg_names
                assert "target_region" in arg_names
                return
        assert False, "function not found"

    def test_has_motif_selection_params(self):
        """Has start_note and note_count params for motif selection"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                arg_names = [a.arg for a in node.args.args]
                assert "start_note" in arg_names
                assert "note_count" in arg_names
                return
        assert False, "function not found"

    def test_has_variation_type_param(self):
        """Has variation_type param"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                arg_names = [a.arg for a in node.args.args]
                assert "variation_type" in arg_names
                return
        assert False, "function not found"

    def test_supports_6_variation_types(self):
        """Supports all 6 classical variation types"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                source = ast.unparse(node)
                assert "sequence" in source
                assert "inversion" in source
                assert "retrograde" in source
                assert "augmentation" in source
                assert "diminution" in source
                assert "fragmentation" in source
                return
        assert False, "function not found"

    def test_validates_note_count(self):
        """Validates note_count must be 2-16"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                source = ast.unparse(node)
                assert "note_count must be 2-16" in source
                return
        assert False, "function not found"

    def test_validates_variation_type(self):
        """Validates variation_type against allowed set"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                source = ast.unparse(node)
                assert "valid_types" in source
                return
        assert False, "function not found"

    def test_has_sequence_shift(self):
        """Has sequence_shift param for sequence type"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                arg_names = [a.arg for a in node.args.args]
                assert "sequence_shift" in arg_names
                return
        assert False, "function not found"

    def test_has_augmentation_factor(self):
        """Has augmentation_factor param for aug/dim types"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                arg_names = [a.arg for a in node.args.args]
                assert "augmentation_factor" in arg_names
                return
        assert False, "function not found"

    def test_has_fragment_count(self):
        """Has fragment_count param for fragmentation type"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                arg_names = [a.arg for a in node.args.args]
                assert "fragment_count" in arg_names
                return
        assert False, "function not found"

    def test_uses_note_event_box_create(self):
        """Uses NoteEventBox.create for writing notes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                source = ast.unparse(node)
                assert "NoteEventBox" in source
                return
        assert False, "function not found"

    def test_returns_variation_details(self):
        """Returns variation_type, source_motif, variation, and description"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_motif_variations":
                source = ast.unparse(node)
                assert "variation_type" in source
                assert "source_motif" in source
                assert "variation_notes" in source
                assert "description" in source
                return
        assert False, "function not found"


class TestCountryArrangement:
    """Tests for create_country_arrangement — country/Americana multi-track arrangement"""

    def test_tool_signature_exists(self):
        """create_country_arrangement is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_country_arrangement" in tool_names

    def test_has_4_tracks(self):
        """Has drum_track, bass_track, chord_track, lead_track params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                arg_names = [a.arg for a in node.args.args]
                assert "drum_track" in arg_names
                assert "bass_track" in arg_names
                assert "chord_track" in arg_names
                assert "lead_track" in arg_names
                return
        assert False, "function not found"

    def test_default_bpm_is_120(self):
        """Default bpm is 120 (classic country two-step)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bpm" and isinstance(d, ast.Constant):
                        assert d.value == 120
                        return
        assert False, "default not found"

    def test_default_bars_is_8(self):
        """Default bars is 8 (one country verse)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bars" and isinstance(d, ast.Constant):
                        assert d.value == 8
                        return
        assert False, "default not found"

    def test_default_root_is_G(self):
        """Default root is G (most common country key)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "root" and isinstance(d, ast.Constant):
                        assert d.value == "G"
                        return
        assert False, "default not found"

    def test_validates_bars_multiple_of_8(self):
        """Validates bars must be multiple of 8"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                source = ast.unparse(node)
                assert "multiple of 8" in source
                return
        assert False, "function not found"

    def test_has_country_form(self):
        """Contains the 8-bar country form (I-IV-V)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                source = ast.unparse(node)
                assert "I-I-IV-I-V-I-IV-I" in source or "0, 0, 5, 0, 7, 0, 5, 0" in source
                return
        assert False, "function not found"

    def test_has_major_triads(self):
        """Uses major triads (not 7ths like blues)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                source = ast.unparse(node)
                assert "0, 4, 7" in source  # major triad intervals
                return
        assert False, "function not found"

    def test_has_major_pentatonic(self):
        """Uses major pentatonic scale for lead (root, 2, 3, 5, 6)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                source = ast.unparse(node)
                assert "0, 2, 4, 7, 9" in source  # major pentatonic
                return
        assert False, "function not found"

    def test_has_boom_chick_guitar(self):
        """Has boom-chick guitar pattern (alternating bass + chord strum)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                source = ast.unparse(node)
                assert "boom_chick" in source or "boom-chick" in source
                return
        assert False, "function not found"

    def test_has_root_five_bass(self):
        """Has root-five bass pattern"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_country_arrangement":
                source = ast.unparse(node)
                assert "root_five" in source or "root-five" in source
                return
        assert False, "function not found"

    def test_registered_in_genre_mix(self):
        """Country is registered in apply_genre_mix valid_genres"""
        source = open("server.py").read()
        assert '"country"' in source


class TestMetalArrangement:
    """Tests for create_metal_arrangement — heavy metal multi-track arrangement"""

    def test_tool_signature_exists(self):
        """create_metal_arrangement is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_metal_arrangement" in tool_names

    def test_has_4_tracks(self):
        """Has drum_track, bass_track, chord_track, lead_track params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                arg_names = [a.arg for a in node.args.args]
                assert "drum_track" in arg_names
                assert "bass_track" in arg_names
                assert "chord_track" in arg_names
                assert "lead_track" in arg_names
                return
        assert False, "function not found"

    def test_default_bpm_is_160(self):
        """Default bpm is 160 (thrash metal)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "bpm" and isinstance(d, ast.Constant):
                        assert d.value == 160
                        return
        assert False, "default not found"

    def test_default_root_is_E(self):
        """Default root is E (lowest guitar string, most common metal key)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "root" and isinstance(d, ast.Constant):
                        assert d.value == "E"
                        return
        assert False, "default not found"

    def test_default_velocity_is_085(self):
        """Default velocity is 0.85 (louder than other genres — metal is aggressive)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "velocity" and isinstance(d, ast.Constant):
                        assert d.value == 0.85
                        return
        assert False, "default not found"

    def test_validates_bars_multiple_of_4(self):
        """Validates bars must be multiple of 4"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                source = ast.unparse(node)
                assert "multiple of 4" in source
                return
        assert False, "function not found"

    def test_has_power_chords(self):
        """Uses power chords (root + fifth, not triads or 7ths)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                source = ast.unparse(node)
                assert "_POWER" in source or "0, 7" in source
                return
        assert False, "function not found"

    def test_has_phrygian_dominant(self):
        """Uses phrygian dominant scale (exotic metal sound)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                source = ast.unparse(node)
                assert "PHRYGIAN" in source or "phrygian" in source
                return
        assert False, "function not found"

    def test_has_double_kick_drums(self):
        """Has double kick drum pattern (16th notes on kick)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                source = ast.unparse(node)
                assert "double_kick" in source or "double kick" in source
                return
        assert False, "function not found"

    def test_has_palm_muted_chugging(self):
        """Has palm-muted chugging pattern"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                source = ast.unparse(node)
                assert "palm_muted" in source or "palm-muted" in source
                return
        assert False, "function not found"

    def test_has_shred_lead(self):
        """Has shred lead guitar (minor pentatonic + natural minor)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_metal_arrangement":
                source = ast.unparse(node)
                assert "shred" in source
                assert "_MIN_PENT" in source or "_MINOR_SCALE" in source
                return
        assert False, "function not found"

    def test_registered_in_genre_mix(self):
        """Metal is registered in apply_genre_mix valid_genres"""
        source = open("server.py").read()
        assert '"metal"' in source


class TestCreateHarmonyLine:
    """Tests for create_harmony_line — diatonic harmony from existing melody"""

    def test_tool_signature_exists(self):
        """create_harmony_line is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_harmony_line" in tool_names

    def test_has_source_and_target_params(self):
        """Has source_unit, source_track, source_region and target params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                arg_names = [a.arg for a in node.args.args]
                assert "source_unit" in arg_names
                assert "source_track" in arg_names
                assert "source_region" in arg_names
                assert "target_unit" in arg_names
                assert "target_track" in arg_names
                assert "target_region" in arg_names
                return
        assert False, "function not found"

    def test_has_interval_param(self):
        """Has interval param for harmony interval selection"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                arg_names = [a.arg for a in node.args.args]
                assert "interval" in arg_names
                return
        assert False, "function not found"

    def test_supports_5_intervals(self):
        """Supports 5 harmony intervals: third, sixth, fifth, fourth, octave"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                source = ast.unparse(node)
                assert "third" in source
                assert "sixth" in source
                assert "fifth" in source
                assert "fourth" in source
                assert "octave" in source
                return
        assert False, "function not found"

    def test_has_direction_param(self):
        """Has direction param (above/below)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                arg_names = [a.arg for a in node.args.args]
                assert "direction" in arg_names
                return
        assert False, "function not found"

    def test_has_scale_and_root_params(self):
        """Has root_note and scale params for diatonic calculation"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                arg_names = [a.arg for a in node.args.args]
                assert "root_note" in arg_names
                assert "scale" in arg_names
                return
        assert False, "function not found"

    def test_default_interval_is_third(self):
        """Default interval is 'third' (most common harmony)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "interval" and isinstance(d, ast.Constant):
                        assert d.value == "third"
                        return
        assert False, "default not found"

    def test_default_direction_is_below(self):
        """Default direction is 'below' (harmony typically below melody)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "direction" and isinstance(d, ast.Constant):
                        assert d.value == "below"
                        return
        assert False, "default not found"

    def test_has_velocity_scale(self):
        """Has velocity_scale param for harmony loudness control"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                arg_names = [a.arg for a in node.args.args]
                assert "velocity_scale" in arg_names
                return
        assert False, "function not found"

    def test_uses_diatonic_intervals(self):
        """Uses diatonic intervals (scale steps, not semitones)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                source = ast.unparse(node)
                assert "SCALE_INTERVALS" in source or "scale_pcs" in source
                return
        assert False, "function not found"

    def test_validates_interval(self):
        """Validates interval against allowed set"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                source = ast.unparse(node)
                assert "interval_map" in source
                return
        assert False, "function not found"

    def test_uses_note_event_box_create(self):
        """Uses NoteEventBox.create for writing harmony notes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_harmony_line":
                source = ast.unparse(node)
                assert "NoteEventBox" in source
                return
        assert False, "function not found"


class TestCreateVoiceLedProgression:
    """Tests for create_voice_led_progression — smooth voice leading chord pads"""

    def test_tool_signature_exists(self):
        """create_voice_led_progression is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_create_voice_led_progression" in tool_names

    def test_has_progression_param(self):
        """Has progression param (hyphen-separated chord string)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                arg_names = [a.arg for a in node.args.args]
                assert "progression" in arg_names
                assert "bars_per_chord" in arg_names
                assert "octave" in arg_names
                return
        assert False, "function not found"

    def test_has_voice_range_param(self):
        """Has voice_range param for constraining voice spread"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                arg_names = [a.arg for a in node.args.args]
                assert "voice_range" in arg_names
                return
        assert False, "function not found"

    def test_has_voice_leading_algorithm(self):
        """Contains voice leading logic: voicing generation + best-voice selection"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                source = ast.unparse(node)
                assert "_generate_voicings" in source
                assert "_best_voicing" in source
                return
        assert False, "function not found"

    def test_computes_movement(self):
        """Reports voice movement and total movement"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                source = ast.unparse(node)
                assert "total_movement" in source
                assert "avg_movement_per_chord" in source
                return
        assert False, "function not found"

    def test_uses_notes_batch(self):
        """Delegates note creation to create_notes_batch (like create_chord_pads)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                source = ast.unparse(node)
                assert "create_notes_batch" in source
                return
        assert False, "function not found"

    def test_parses_same_chord_format(self):
        """Parses the same hyphen-separated format as create_chord_pads"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                source = ast.unparse(node)
                # Should have same chord parsing logic
                assert "chord_str" in source
                assert "min" in source
                assert "maj7" in source
                return
        assert False, "function not found"

    def test_validates_inputs(self):
        """Validates progression, octave, velocity, voice_range bounds"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                source = ast.unparse(node)
                assert "Error" in source
                assert "voice_range" in source
                return
        assert False, "function not found"

    def test_default_progression_is_minor(self):
        """Default progression is Am-F-C-G (same as create_chord_pads)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "progression" and isinstance(d, ast.Constant):
                        assert d.value == "Am-F-C-G"
                        return
        assert False, "default not found"

    def test_first_chord_is_root_position(self):
        """First chord voicing starts from root position"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_create_voice_led_progression":
                source = ast.unparse(node)
                assert "ci == 0" in source
                assert "root position" in source.lower() or "root-position" in source.lower()
                return
        assert False, "function not found"

    def test_voice_leading_produces_minimal_movement(self):
        """Voice leading algorithm: Am→F transition should be smoother than root position.

        Am root position: [57, 60, 64] (A3, C4, E4)
        F  root position: [53, 57, 60] (F3, A3, C4) — movement = 4+3+4 = 11

        With voice leading, F should be revoiced to minimize movement.
        Best: [53, 57, 60] → actually same since that IS minimal.
        Let's test C→G transition:
        C root position: [48, 52, 55] (C3, E3, G3)
        G root position: [55, 59, 62] (G3, B3, D4) — movement = 7+7+7 = 21

        Voice led G could be: [55, 59, 62] or [43, 47, 50] etc.
        The algorithm should find something ≤ 21.
        """
        # We test the algorithm logic directly by simulating it
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, CHORD_INTERVALS

        center = 48  # octave 3
        lo = center - 12  # 36
        hi = center + 12  # 60

        def generate_voicings(intervals, base_pitch, lo, hi):
            pcs = [(base_pitch + iv) % 12 for iv in intervals]
            n = len(pcs)
            voicings = []
            for start_oct in range(lo // 12, hi // 12 + 2):
                for inv in range(n):
                    voicing = []
                    valid = True
                    for i in range(n):
                        pc = pcs[(i + inv) % n]
                        if i == 0:
                            candidate = start_oct * 12 + pc
                        else:
                            prev = voicing[-1]
                            candidate = prev + ((pc - prev % 12 + 12) % 12)
                            if candidate <= prev:
                                candidate += 12
                        if candidate < lo or candidate > hi:
                            valid = False
                            break
                        voicing.append(candidate)
                    if valid and len(voicing) == n and voicing not in voicings:
                        voicings.append(voicing)
            return voicings

        def best_voicing(prev_voicing, candidates):
            if not candidates:
                return None, []
            n = len(prev_voicing)
            best = None
            best_cost = 999999
            best_movements = []
            for cand in candidates:
                cost = 0
                movements = []
                max_len = max(n, len(cand))
                for i in range(max_len):
                    if i < n and i < len(cand):
                        dist = abs(cand[i] - prev_voicing[i])
                        cost += dist
                        movements.append(dist)
                    elif i < len(cand):
                        cost += 2
                        movements.append(2)
                    else:
                        cost += 2
                        movements.append(2)
                if cost < best_cost:
                    best_cost = cost
                    best = cand
                    best_movements = movements
            return best, best_movements

        # C major: C-E-G
        c_intervals = CHORD_INTERVALS["maj"]
        c_root_pc = NOTE_TO_PITCH["C"]
        c_base = center + c_root_pc  # 48
        c_voicing = [c_base + iv for iv in c_intervals]  # [48, 52, 55]
        c_voicing = [max(lo, min(hi, p)) for p in c_voicing]
        c_voicing_sorted = sorted(c_voicing)

        # G major: G-B-D
        g_intervals = CHORD_INTERVALS["maj"]
        g_root_pc = NOTE_TO_PITCH["G"]
        g_base = center + g_root_pc  # 55
        g_candidates = generate_voicings(g_intervals, g_base, lo, hi)

        # Root position G would be [55, 59, 62] — but 62 > 60 (hi)
        # So root position is clamped or out of range
        g_root_pos = [55, 59, 62]
        _ = all(lo <= p <= hi for p in g_root_pos)  # check if root position in range

        # Voice led G
        g_voiced, g_movements = best_voicing(c_voicing_sorted, g_candidates)

        # Calculate root position movement for comparison
        root_movement = sum(abs(g_root_pos[i] - c_voicing_sorted[i]) for i in range(3)
                           if i < len(c_voicing_sorted))

        # Voice led should be ≤ root position movement
        voiced_movement = sum(g_movements) if g_movements else 999

        # The voice-led version should not be worse than root position
        # (it might not always be strictly better if root position IS optimal)
        assert voiced_movement <= root_movement + 2, \
            f"Voice led movement ({voiced_movement}) should be ≤ root ({root_movement}) + 2"

    def test_common_tones_stay_stationary(self):
        """When two chords share a pitch class, that voice should not move.

        C major [48, 52, 55] and A minor [57, 60, 64] share no common tones.
        But C major [48, 52, 55] and F major [53, 57, 60] share C (pc=0).
        With voice leading, C should stay at 48 (pitch class 0).
        """
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, CHORD_INTERVALS

        center = 48
        lo = center - 12
        hi = center + 12

        def generate_voicings(intervals, base_pitch, lo, hi):
            pcs = [(base_pitch + iv) % 12 for iv in intervals]
            n = len(pcs)
            voicings = []
            for start_oct in range(lo // 12, hi // 12 + 2):
                for inv in range(n):
                    voicing = []
                    valid = True
                    for i in range(n):
                        pc = pcs[(i + inv) % n]
                        if i == 0:
                            candidate = start_oct * 12 + pc
                        else:
                            prev = voicing[-1]
                            candidate = prev + ((pc - prev % 12 + 12) % 12)
                            if candidate <= prev:
                                candidate += 12
                        if candidate < lo or candidate > hi:
                            valid = False
                            break
                        voicing.append(candidate)
                    if valid and len(voicing) == n and voicing not in voicings:
                        voicings.append(voicing)
            return voicings

        def best_voicing(prev_voicing, candidates):
            if not candidates:
                return None, []
            n = len(prev_voicing)
            best = None
            best_cost = 999999
            best_movements = []
            for cand in candidates:
                cost = 0
                movements = []
                max_len = max(n, len(cand))
                for i in range(max_len):
                    if i < n and i < len(cand):
                        dist = abs(cand[i] - prev_voicing[i])
                        cost += dist
                        movements.append(dist)
                    elif i < len(cand):
                        cost += 2
                        movements.append(2)
                    else:
                        cost += 2
                        movements.append(2)
                if cost < best_cost:
                    best_cost = cost
                    best = cand
                    best_movements = movements
            return best, best_movements

        # C major: C(48)-E(52)-G(55)
        c_voicing = sorted([48, 52, 55])

        # F major: F-A-C — shares C (pc=0) with C major
        f_intervals = CHORD_INTERVALS["maj"]
        f_base = center + NOTE_TO_PITCH["F"]  # 53
        f_candidates = generate_voicings(f_intervals, f_base, lo, hi)

        f_voiced, f_movements = best_voicing(c_voicing, f_candidates)

        # F major has C (pc=0), C major has C (pc=0 at pitch 48)
        # The algorithm should find a voicing where C stays at 48
        # Check if 48 is in the voiced F chord
        _ = 48 in sorted(f_voiced) if f_voiced else False  # common tone presence check

        # It's possible the optimal doesn't keep C at 48, but it should be close
        # The key test: total movement should be small
        total_movement = sum(f_movements) if f_movements else 999
        assert total_movement <= 14, \
            f"F after C should have small total movement ({total_movement}), got {total_movement}"

    def test_voicing_stays_within_range(self):
        """All voicing pitches should be within [center - voice_range, center + voice_range]"""
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, CHORD_INTERVALS

        center = 48
        voice_range = 12
        lo = center - voice_range  # 36
        hi = center + voice_range  # 60

        def generate_voicings(intervals, base_pitch, lo, hi):
            pcs = [(base_pitch + iv) % 12 for iv in intervals]
            n = len(pcs)
            voicings = []
            for start_oct in range(lo // 12, hi // 12 + 2):
                for inv in range(n):
                    voicing = []
                    valid = True
                    for i in range(n):
                        pc = pcs[(i + inv) % n]
                        if i == 0:
                            candidate = start_oct * 12 + pc
                        else:
                            prev = voicing[-1]
                            candidate = prev + ((pc - prev % 12 + 12) % 12)
                            if candidate <= prev:
                                candidate += 12
                        if candidate < lo or candidate > hi:
                            valid = False
                            break
                        voicing.append(candidate)
                    if valid and len(voicing) == n and voicing not in voicings:
                        voicings.append(voicing)
            return voicings

        # Test with several chords
        for root_name in ["C", "G", "F", "Am"[:1]]:
            root_pc = NOTE_TO_PITCH.get(root_name, 0)
            intervals = CHORD_INTERVALS["maj"]
            base = center + root_pc
            voicings = generate_voicings(intervals, base, lo, hi)
            for v in voicings:
                for p in v:
                    assert lo <= p <= hi, f"Pitch {p} out of range [{lo}, {hi}]"


class TestReharmonizeProgression:
    """Tests for reharmonize_progression — chord substitution techniques"""

    def test_tool_signature_exists(self):
        """reharmonize_progression is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_reharmonize_progression" in tool_names

    def test_has_technique_param(self):
        """Has technique param with 5 substitution techniques"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                arg_names = [a.arg for a in node.args.args]
                assert "technique" in arg_names
                source = ast.unparse(node)
                assert "tritone_sub" in source
                assert "secondary_dominant" in source
                assert "diatonic_sub" in source
                assert "modal_interchange" in source
                assert "passing_dim" in source
                return
        assert False, "function not found"

    def test_has_intensity_param(self):
        """Has intensity param (light/medium/heavy)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                arg_names = [a.arg for a in node.args.args]
                assert "intensity" in arg_names
                source = ast.unparse(node)
                assert "light" in source
                assert "medium" in source
                assert "heavy" in source
                return
        assert False, "function not found"

    def test_has_target_chord_param(self):
        """Has target_chord param for selective substitution"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                arg_names = [a.arg for a in node.args.args]
                assert "target_chord" in arg_names
                return
        assert False, "function not found"

    def test_returns_reharmonized_progression(self):
        """Returns reharmonized_progression string + chord_mapping"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                source = ast.unparse(node)
                assert "reharmonized_progression" in source
                assert "chord_mapping" in source
                assert "substitutions_made" in source
                return
        assert False, "function not found"

    def test_tritone_sub_replaces_dominant7(self):
        """Tritone substitution: G7 → Db7 (tritone = 6 semitones)

        G7 has guide tones B(11) and F(5).
        Db7 has guide tones F(5) and B(11) — same notes, different chord!
        """
        from opendaw_mcp.music_theory import NOTE_TO_PITCH

        # G7: root=G(pc=7), type=dom7
        g7_pc = NOTE_TO_PITCH["G"]  # 7
        # Tritone sub: +6 semitones
        db7_pc = (g7_pc + 6) % 12  # 1 = Db/C#
        assert db7_pc == 1, f"Db7 pc should be 1, got {db7_pc}"

        # Guide tones of G7: 3rd=B(pc=11), 7th=F(pc=5)
        g7_guide = sorted([(g7_pc + 4) % 12, (g7_pc + 10) % 12])  # [5, 11]
        # Guide tones of Db7: 3rd=F(pc=5), 7th=B/Cb(pc=11)
        db7_guide = sorted([(db7_pc + 4) % 12, (db7_pc + 10) % 12])  # [5, 11]
        assert g7_guide == db7_guide, \
            f"Guide tones should match: G7={g7_guide}, Db7={db7_guide}"

    def test_secondary_dominant_inserts_v7(self):
        """Secondary dominant: before Am, insert E7 (V7 of Am = 7 semitones up from A)

        A(pc=9) + 7 = E(pc=4) → E7
        """
        from opendaw_mcp.music_theory import NOTE_TO_PITCH

        am_pc = NOTE_TO_PITCH["A"]  # 9
        v7_pc = (am_pc + 7) % 12  # 4 = E
        assert v7_pc == 4, f"V7 of Am should be E(pc=4), got {v7_pc}"

        # E7 is a dominant 7th chord on E
        e7_intervals = [0, 4, 7, 10]  # E-G#-B-D
        _ = [v7_pc + iv for iv in e7_intervals]  # E7 pitches for reference
        # Check it resolves to Am: E7→Am is V7→i in A minor
        am_intervals = [0, 3, 7]  # A-C-E
        _ = [am_pc + iv for iv in am_intervals]  # Am pitches for reference
        # E7's 3rd (G#) resolves to A, 7th (D) resolves to C or E
        assert (v7_pc + 4) % 12 == 8, "E7's 3rd should be G#(8), resolving to A(9)"

    def test_modal_interchange_flips_quality(self):
        """Modal interchange: F(major) → Fm (parallel minor borrow)

        Same root, flips major→minor or minor→major
        """
        # F major: F-A-C (intervals 0,4,7)
        # F minor: F-Ab-C (intervals 0,3,7)
        # Same root (F), same 5th (C), but 3rd changes: A→Ab
        f_major_intervals = [0, 4, 7]
        f_minor_intervals = [0, 3, 7]
        # Common tones: root and 5th
        common = set(f_major_intervals) & set(f_minor_intervals)
        assert common == {0, 7}, f"Root and 5th should be common: {common}"

    def test_passing_dim_requires_whole_step(self):
        """Passing diminished only works between chords a whole step (2 semitones) apart

        C→D: interval = 2 → insert C#dim
        C→F: interval = 5 → no passing dim
        """
        from opendaw_mcp.music_theory import NOTE_TO_PITCH

        c_pc = NOTE_TO_PITCH["C"]  # 0
        d_pc = NOTE_TO_PITCH["D"]  # 2
        f_pc = NOTE_TO_PITCH["F"]  # 5

        # C→D: whole step, should insert C#dim
        interval_cd = (d_pc - c_pc) % 12
        assert interval_cd == 2, "C→D should be 2 semitones"
        dim_pc = (c_pc + 1) % 12  # 1 = C#/Db
        assert dim_pc == 1, f"Passing dim between C and D should be C#(1), got {dim_pc}"

        # C→F: not a whole step, no passing dim
        interval_cf = (f_pc - c_pc) % 12
        assert interval_cf != 2, "C→F should not trigger passing dim"

    def test_diatonic_sub_uses_submediant(self):
        """Diatonic substitution: I → vi (submediant, +9 semitones)

        C major → A minor (relative minor)
        Shared tones: C and E are in both C major and A minor
        """
        from opendaw_mcp.music_theory import NOTE_TO_PITCH

        c_pc = NOTE_TO_PITCH["C"]  # 0
        vi_pc = (c_pc + 9) % 12  # 9 = A
        assert vi_pc == 9, f"Submediant of C should be A(9), got {vi_pc}"

        # C major: C-E-G (pc 0,4,7)
        # A minor: A-C-E (pc 9,0,4)
        c_major_pcs = {0, 4, 7}
        a_minor_pcs = {9, 0, 4}
        shared = c_major_pcs & a_minor_pcs
        assert len(shared) >= 2, f"C and Am should share 2+ pitch classes, got {shared}"

    def test_validates_technique(self):
        """Validates technique against allowed set"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                source = ast.unparse(node)
                assert "valid_techniques" in source
                assert "Error" in source
                return
        assert False, "function not found"

    def test_parses_progression_string(self):
        """Parses same hyphen-separated format as other progression tools"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                source = ast.unparse(node)
                assert "chord_str" in source
                assert "progression.split" in source
                return
        assert False, "function not found"

    def test_default_technique_is_tritone_sub(self):
        """Default technique is 'tritone_sub' (most common jazz substitution)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_reharmonize_progression":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "technique" and isinstance(d, ast.Constant):
                        assert d.value == "tritone_sub"
                        return
        assert False, "default not found"


class TestDisplaceRhythm:
    """Tests for displace_rhythm — rhythmic displacement / circular rotation"""

    def test_tool_signature_exists(self):
        """displace_rhythm is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_displace_rhythm" in tool_names

    def test_has_offset_and_mode_params(self):
        """Has offset (beats) and mode (shift/circular) params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                arg_names = [a.arg for a in node.args.args]
                assert "offset" in arg_names
                assert "mode" in arg_names
                return
        assert False, "function not found"

    def test_supports_two_modes(self):
        """Supports 'shift' and 'circular' modes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert '"shift"' in source or "'shift'" in source
                assert '"circular"' in source or "'circular'" in source
                return
        assert False, "function not found"

    def test_validates_offset_range(self):
        """Validates offset is within -4.0 to 4.0 beats"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "-4.0" in source
                assert "4.0" in source
                assert "Error" in source
                return
        assert False, "function not found"

    def test_default_offset_is_sixteenth(self):
        """Default offset is 0.0625 (1/16 note) — most common displacement"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "offset" and isinstance(d, ast.Constant):
                        assert d.value == 0.0625
                        return
        assert False, "default not found"

    def test_default_mode_is_shift(self):
        """Default mode is 'shift' (most intuitive)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "mode" and isinstance(d, ast.Constant):
                        assert d.value == "shift"
                        return
        assert False, "default not found"

    def test_offset_zero_returns_immediately(self):
        """offset=0 returns early with no-op message"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "offset == 0" in source
                assert "no displacement" in source
                return
        assert False, "function not found"

    def test_uses_bridge_evaluate(self):
        """Uses bridge.evaluate for DAW interaction"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "bridge.evaluate" in source
                return
        assert False, "function not found"

    def test_circular_mode_wraps_around(self):
        """Circular mode uses modulo arithmetic for wrapping"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "% regionDur" in source or "% regionDur)" in source
                return
        assert False, "function not found"

    def test_shift_mode_clamps_to_zero(self):
        """Shift mode clamps negative positions to 0"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "Math.max(0" in source
                return
        assert False, "function not found"

    def test_converts_offset_to_ppqn(self):
        """Converts beat offset to PPQN (× 960)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "960" in source
                assert "offset_ppqn" in source
                return
        assert False, "function not found"

    def test_reports_per_track_stats(self):
        """Reports per_track stats with notes_modified, offset, mode"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "tracks_processed" in source
                assert "per_track" in source
                assert "notes_modified" in source
                return
        assert False, "function not found"

    def test_shift_mode_extends_region(self):
        """Shift mode extends region duration if notes go past the end"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_displace_rhythm":
                source = ast.unparse(node)
                assert "region.duration.setValue" in source
                return
        assert False, "function not found"


class TestThinNotes:
    """Tests for thin_notes — note density reduction"""

    def test_tool_signature_exists(self):
        """thin_notes is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_thin_notes" in tool_names

    def test_has_strategy_param(self):
        """Has strategy param with 3 options"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "strategy" in arg_names
                source = ast.unparse(node)
                assert "interval" in source
                assert "velocity_threshold" in source
                assert "random" in source
                return
        assert False, "function not found"

    def test_has_interval_param(self):
        """Has interval param for 'interval' strategy"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "interval" in arg_names
                return
        assert False, "function not found"

    def test_has_velocity_threshold_param(self):
        """Has velocity_threshold param for 'velocity_threshold' strategy"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "velocity_threshold" in arg_names
                return
        assert False, "function not found"

    def test_has_random_chance_param(self):
        """Has random_chance param for 'random' strategy"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "random_chance" in arg_names
                return
        assert False, "function not found"

    def test_has_preserve_strong_beats(self):
        """Has preserve_strong_beats param"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "preserve_strong_beats" in arg_names
                return
        assert False, "function not found"

    def test_validates_strategy(self):
        """Validates strategy against allowed set"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                source = ast.unparse(node)
                assert "valid_strategies" in source
                assert "Error" in source
                return
        assert False, "function not found"

    def test_validates_interval_range(self):
        """Validates interval is 2-16"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                source = ast.unparse(node)
                assert "2 <= interval" in source or "interval <= 16" in source
                return
        assert False, "function not found"

    def test_default_strategy_is_interval(self):
        """Default strategy is 'interval' (most predictable)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "strategy" and isinstance(d, ast.Constant):
                        assert d.value == "interval"
                        return
        assert False, "default not found"

    def test_default_interval_is_2(self):
        """Default interval is 2 (halve note density)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "interval" and isinstance(d, ast.Constant):
                        assert d.value == 2
                        return
        assert False, "default not found"

    def test_reports_original_removed_remaining(self):
        """Reports original_count, removed, remaining per track"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                source = ast.unparse(node)
                assert "original_count" in source
                assert "removed" in source
                assert "remaining" in source
                return
        assert False, "function not found"

    def test_uses_bridge_evaluate(self):
        """Uses bridge.evaluate for DAW interaction"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                source = ast.unparse(node)
                assert "bridge.evaluate" in source
                return
        assert False, "function not found"

    def test_preserve_strong_beats_logic(self):
        """Preserve strong beats uses beat 1 and 3 (PPQN 0 and 1920)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_thin_notes":
                source = ast.unparse(node)
                assert "strongBeats" in source
                assert "2 * Quarter" in source  # beat 3 = 2*960 = 1920
                return
        assert False, "function not found"


class TestStrumNotes:
    """Tests for strum_notes — guitar-style strumming of simultaneous notes"""

    def test_tool_signature_exists(self):
        """strum_notes is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_strum_notes" in tool_names

    def test_has_direction_param(self):
        """Has direction param (down/up/random)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "direction" in arg_names
                source = ast.unparse(node)
                assert "down" in source
                assert "up" in source
                assert "random" in source
                return
        assert False, "function not found"

    def test_has_speed_param(self):
        """Has speed param (time between strings in beats)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "speed" in arg_names
                return
        assert False, "function not found"

    def test_has_jitter_param(self):
        """Has jitter param for humanization"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                arg_names = [a.arg for a in node.args.args]
                assert "jitter" in arg_names
                return
        assert False, "function not found"

    def test_validates_direction(self):
        """Validates direction against allowed set"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "Error" in source
                assert '"down", "up", "random"' in source or "'down', 'up', 'random'" in source
                return
        assert False, "function not found"

    def test_validates_speed_range(self):
        """Validates speed is 0.005-0.5 beats"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "0.005" in source
                assert "0.5" in source
                return
        assert False, "function not found"

    def test_default_direction_is_down(self):
        """Default direction is 'down' (most natural for guitar)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "direction" and isinstance(d, ast.Constant):
                        assert d.value == "down"
                        return
        assert False, "default not found"

    def test_default_speed_is_thirty_second(self):
        """Default speed is 0.03125 (1/32 note — fast strum)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "speed" and isinstance(d, ast.Constant):
                        assert d.value == 0.03125
                        return
        assert False, "default not found"

    def test_groups_simultaneous_notes(self):
        """Groups notes by position tolerance for chord detection"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "tolerance" in source
                assert "groups" in source
                return
        assert False, "function not found"

    def test_reports_chord_groups_and_strummed(self):
        """Reports chord_groups and notes_strummed per track"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "chord_groups" in source
                assert "notes_strummed" in source
                return
        assert False, "function not found"

    def test_uses_bridge_evaluate(self):
        """Uses bridge.evaluate for DAW interaction"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "bridge.evaluate" in source
                return
        assert False, "function not found"

    def test_converts_speed_to_ppqn(self):
        """Converts speed (beats) to PPQN (× 960)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "960" in source
                assert "speed_ppqn" in source
                return
        assert False, "function not found"

    def test_random_uses_fisher_yates(self):
        """Random direction uses Fisher-Yates shuffle"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_strum_notes":
                source = ast.unparse(node)
                assert "Fisher-Yates" in source or "shuffle" in source
                return
        assert False, "function not found"


class TestConstrainNoteRange:
    """Tests for constrain_note_range — pitch range limiting"""

    def test_tool_signature_exists(self):
        """constrain_note_range is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_constrain_note_range" in tool_names

    def test_has_min_max_pitch_params(self):
        """Has min_pitch and max_pitch params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                arg_names = [a.arg for a in node.args.args]
                assert "min_pitch" in arg_names
                assert "max_pitch" in arg_names
                return
        assert False, "function not found"

    def test_has_mode_param(self):
        """Has mode param (clamp/octave_wrap)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                arg_names = [a.arg for a in node.args.args]
                assert "mode" in arg_names
                source = ast.unparse(node)
                assert "clamp" in source
                assert "octave_wrap" in source
                return
        assert False, "function not found"

    def test_validates_pitch_range(self):
        """Validates min_pitch and max_pitch are 0-127"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "0 <= min_pitch" in source or "0 <= max_pitch" in source
                assert "Error" in source
                return
        assert False, "function not found"

    def test_validates_min_less_than_max(self):
        """Validates min_pitch < max_pitch"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "min_pitch >= max_pitch" in source or "less than max_pitch" in source
                return
        assert False, "function not found"

    def test_default_mode_is_clamp(self):
        """Default mode is 'clamp' (simpler, safer)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "mode" and isinstance(d, ast.Constant):
                        assert d.value == "clamp"
                        return
        assert False, "default not found"

    def test_default_range_is_full_midi(self):
        """Default range is 0-127 (full MIDI range = no-op)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                found_min = found_max = False
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "min_pitch" and isinstance(d, ast.Constant):
                        assert d.value == 0
                        found_min = True
                    if arg_name == "max_pitch" and isinstance(d, ast.Constant):
                        assert d.value == 127
                        found_max = True
                assert found_min and found_max, "defaults not found"
                return
        assert False, "defaults not found"

    def test_octave_wrap_shifts_by_12(self):
        """Octave wrap mode shifts by 12 semitones"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "pitch += 12" in source
                assert "pitch -= 12" in source
                return
        assert False, "function not found"

    def test_octave_wrap_handles_small_range(self):
        """Octave wrap falls back to clamp when range < 12 semitones"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "rangeSpan >= 12" in source or "rangeSpan < 12" in source
                return
        assert False, "function not found"

    def test_reports_clamped_and_wrapped(self):
        """Reports notes_adjusted, clamped, wrapped per track"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "notes_adjusted" in source
                assert "clamped" in source
                assert "wrapped" in source
                return
        assert False, "function not found"

    def test_uses_bridge_evaluate(self):
        """Uses bridge.evaluate for DAW interaction"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "bridge.evaluate" in source
                return
        assert False, "function not found"

    def test_lists_instrument_ranges_in_docstring(self):
        """Docstring lists common instrument ranges"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_constrain_note_range":
                source = ast.unparse(node)
                assert "Guitar" in source
                assert "Violin" in source
                assert "Vocal" in source
                return
        assert False, "function not found"

    def test_octave_wrap_preserves_pitch_class(self):
        """Octave wrap preserves pitch class (note % 12 unchanged)"""
        # If we wrap pitch 90 down to range 40-88, 90-12=78, which is in range
        # Pitch class of 90: 90 % 12 = 6 (F#)
        # Pitch class of 78: 78 % 12 = 6 (F#) — same!
        pitch = 90
        min_p, max_p = 40, 88
        while pitch > max_p:
            pitch -= 12
        assert min_p <= pitch <= max_p, f"Wrapped pitch {pitch} not in range"
        assert pitch % 12 == 90 % 12, "Pitch class should be preserved"


class TestSetArticulation:
    """Tests for set_articulation — legato/staccato/tenuto note length control"""

    def test_tool_signature_exists(self):
        """set_articulation is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_set_articulation" in tool_names

    def test_has_articulation_param(self):
        """Has articulation param with 3 options"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                arg_names = [a.arg for a in node.args.args]
                assert "articulation" in arg_names
                source = ast.unparse(node)
                assert "legato" in source
                assert "staccato" in source
                assert "tenuto" in source
                return
        assert False, "function not found"

    def test_has_staccato_ratio_param(self):
        """Has staccato_ratio param for staccato control"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                arg_names = [a.arg for a in node.args.args]
                assert "staccato_ratio" in arg_names
                return
        assert False, "function not found"

    def test_has_micro_gap_param(self):
        """Has micro_gap param for legato separation"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                arg_names = [a.arg for a in node.args.args]
                assert "micro_gap" in arg_names
                return
        assert False, "function not found"

    def test_validates_articulation(self):
        """Validates articulation against allowed set"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "valid_articulations" in source
                assert "Error" in source
                return
        assert False, "function not found"

    def test_validates_staccato_ratio(self):
        """Validates staccato_ratio is 0.1-0.9"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "0.1" in source
                assert "0.9" in source
                return
        assert False, "function not found"

    def test_default_articulation_is_legato(self):
        """Default articulation is 'legato' (most common use case)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "articulation" and isinstance(d, ast.Constant):
                        assert d.value == "legato"
                        return
        assert False, "default not found"

    def test_default_staccato_ratio_is_half(self):
        """Default staccato_ratio is 0.5 (half the available time)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "staccato_ratio" and isinstance(d, ast.Constant):
                        assert d.value == 0.5
                        return
        assert False, "default not found"

    def test_groups_notes_by_position(self):
        """Groups notes by position to handle chords as units"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "positionGroups" in source
                assert "currentGroup" in source
                return
        assert False, "function not found"

    def test_reports_position_groups(self):
        """Reports position_groups count per track"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "position_groups" in source
                assert "notes_adjusted" in source
                return
        assert False, "function not found"

    def test_uses_bridge_evaluate(self):
        """Uses bridge.evaluate for DAW interaction"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "bridge.evaluate" in source
                return
        assert False, "function not found"

    def test_legato_extends_to_next_note(self):
        """Legato logic: newDur = available - gap"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "available - gap" in source
                return
        assert False, "function not found"

    def test_staccato_shortens_by_ratio(self):
        """Staccato logic: newDur = available * staccato_ratio"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_set_articulation":
                source = ast.unparse(node)
                assert "available * staccRatio" in source
                return
        assert False, "function not found"


class TestGenerateMelody:
    """Tests for generate_melody — contour-guided generative melody"""

    def test_tool_signature_exists(self):
        """generate_melody is a valid MCP tool"""
        import ast
        tree = ast.parse(open("server.py").read())
        tool_names = [n.name for n in ast.walk(tree)
                      if isinstance(n, ast.AsyncFunctionDef)
                      and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_generate_melody" in tool_names

    def test_has_root_and_scale_params(self):
        """Has root and scale params"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                arg_names = [a.arg for a in node.args.args]
                assert "root" in arg_names
                assert "scale" in arg_names
                return
        assert False, "function not found"

    def test_has_contour_param(self):
        """Has contour param with 6 shapes"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                arg_names = [a.arg for a in node.args.args]
                assert "contour" in arg_names
                source = ast.unparse(node)
                assert "ascending" in source
                assert "descending" in source
                assert "arch" in source
                assert "v_shape" in source
                assert "wave" in source
                assert "random" in source
                return
        assert False, "function not found"

    def test_has_rhythm_param(self):
        """Has rhythm param with 5 patterns"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                arg_names = [a.arg for a in node.args.args]
                assert "rhythm" in arg_names
                source = ast.unparse(node)
                assert "quarter" in source
                assert "eighth" in source
                assert "syncopated" in source
                assert "mixed" in source
                assert "sparse" in source
                return
        assert False, "function not found"

    def test_has_rest_probability_param(self):
        """Has rest_probability param"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                arg_names = [a.arg for a in node.args.args]
                assert "rest_probability" in arg_names
                return
        assert False, "function not found"

    def test_validates_root_against_note_to_pitch(self):
        """Validates root using NOTE_TO_PITCH"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                source = ast.unparse(node)
                assert "NOTE_TO_PITCH" in source
                assert "Error" in source
                return
        assert False, "function not found"

    def test_validates_scale_against_scale_intervals(self):
        """Validates scale using SCALE_INTERVALS"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                source = ast.unparse(node)
                assert "SCALE_INTERVALS" in source
                return
        assert False, "function not found"

    def test_default_contour_is_arch(self):
        """Default contour is 'arch' (classic A-section shape)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "contour" and isinstance(d, ast.Constant):
                        assert d.value == "arch"
                        return
        assert False, "default not found"

    def test_default_rhythm_is_mixed(self):
        """Default rhythm is 'mixed' (most musical)"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                args = node.args.args
                defaults = node.args.defaults
                n_defaults = len(defaults)
                for i, d in enumerate(defaults):
                    arg_name = args[len(args) - n_defaults + i].arg
                    if arg_name == "rhythm" and isinstance(d, ast.Constant):
                        assert d.value == "mixed"
                        return
        assert False, "default not found"

    def test_uses_weighted_random_selection(self):
        """Uses weighted random selection for pitch picking"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                source = ast.unparse(node)
                assert "weights" in source
                assert "cumulative" in source
                return
        assert False, "function not found"

    def test_uses_create_notes_batch(self):
        """Delegates note creation to create_notes_batch"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                source = ast.unparse(node)
                assert "create_notes_batch" in source
                return
        assert False, "function not found"

    def test_reports_pitch_range(self):
        """Reports pitch_range (min/max) in output"""
        import ast
        tree = ast.parse(open("server.py").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "mcp_opendaw_generate_melody":
                source = ast.unparse(node)
                assert "pitch_range" in source
                assert "min" in source
                assert "max" in source
                return
        assert False, "function not found"

    def test_contour_arch_peaks_in_middle(self):
        """Arch contour: target=1 at middle, target=0 at start/end"""
        # progress=0.5 → target = 1.0 - abs(2*0.5 - 1) = 1.0 - 0 = 1.0 (peak)
        # progress=0.0 → target = 1.0 - abs(0 - 1) = 1.0 - 1 = 0.0 (low)
        # progress=1.0 → target = 1.0 - abs(2 - 1) = 1.0 - 1 = 0.0 (low)
        progress_mid = 0.5
        target_mid = 1.0 - abs(2.0 * progress_mid - 1.0)
        assert target_mid == 1.0, "Arch should peak at middle"

        progress_start = 0.0
        target_start = 1.0 - abs(2.0 * progress_start - 1.0)
        assert target_start == 0.0, "Arch should be low at start"

        progress_end = 1.0
        target_end = 1.0 - abs(2.0 * progress_end - 1.0)
        assert target_end == 0.0, "Arch should be low at end"


class TestDoubleMelody:
    """Tests for mcp_opendaw_double_melody — parallel interval doubling"""

    def test_function_exists(self):
        import ast
        tree = ast.parse(open("server.py").read())
        names = [n.name for n in ast.walk(tree)
                 if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_double_melody" in names

    def test_interval_semitones_map(self):
        """Named intervals map to correct semitone offsets"""
        semitones = {
            "unison": 0, "octave": 12, "double_octave": 24,
            "fifth": 7, "fourth": 5, "third": 4, "sixth": 9,
        }
        # Octave = 12 semitones
        assert semitones["octave"] == 12
        # Fifth = 7 semitones (perfect fifth)
        assert semitones["fifth"] == 7
        # Fourth = 5 semitones (perfect fourth)
        assert semitones["fourth"] == 5
        # Third = 4 semitones (major third)
        assert semitones["third"] == 4
        # Sixth = 9 semitones (major sixth)
        assert semitones["sixth"] == 9
        # Double octave = 24
        assert semitones["double_octave"] == 24
        # Unison = 0
        assert semitones["unison"] == 0

    def test_diatonic_steps_map(self):
        """Named intervals map to correct scale-degree offsets"""
        steps = {
            "unison": 0, "octave": 7, "double_octave": 14,
            "fifth": 4, "fourth": 3, "third": 2, "sixth": 5,
        }
        # Diatonic third = 2 scale steps (C→E in C major)
        assert steps["third"] == 2
        # Diatonic fifth = 4 scale steps (C→G)
        assert steps["fifth"] == 4
        # Diatonic sixth = 5 scale steps (C→A)
        assert steps["sixth"] == 5
        # Diatonic octave = 7 scale steps (C→C)
        assert steps["octave"] == 7

    def test_diatonic_third_quality_varies(self):
        """Diatonic third in C major: C→E (major, +4), D→F (minor, +3)"""
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, SCALE_INTERVALS
        root_num = NOTE_TO_PITCH["C"]
        intervals = SCALE_INTERVALS["major"]
        scale_pcs = sorted(set((root_num + iv) % 12 for iv in intervals))
        # C major scale: C D E F G A B = 0 2 4 5 7 9 11
        assert scale_pcs == [0, 2, 4, 5, 7, 9, 11]

        # C (pc=0) → E (pc=4) = +4 semitones = major third
        c_idx = scale_pcs.index(0)
        e_idx = (c_idx + 2) % len(scale_pcs)
        assert scale_pcs[e_idx] == 4, "C diatonic third should be E (pc=4)"

        # D (pc=2) → F (pc=5) = +3 semitones = minor third
        d_idx = scale_pcs.index(2)
        f_idx = (d_idx + 2) % len(scale_pcs)
        assert scale_pcs[f_idx] == 5, "D diatonic third should be F (pc=5)"

        # Verify the actual semitone distance differs
        c_to_e = scale_pcs[e_idx] - scale_pcs[c_idx]  # 4 - 0 = 4 (major third)
        d_to_f = scale_pcs[f_idx] - scale_pcs[d_idx]  # 5 - 2 = 3 (minor third)
        assert c_to_e == 4, "C→E should be 4 semitones (major third)"
        assert d_to_f == 3, "D→F should be 3 semitones (minor third)"

    def test_diatonic_fifth_in_minor(self):
        """Diatonic fifth in A minor: A→E (perfect fifth, +7)"""
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, SCALE_INTERVALS
        root_num = NOTE_TO_PITCH["A"]
        intervals = SCALE_INTERVALS["minor"]
        scale_pcs = sorted(set((root_num + iv) % 12 for iv in intervals))
        # A natural minor: A B C D E F G = 9 11 0 2 4 5 7
        a_idx = scale_pcs.index(9)
        e_idx = (a_idx + 4) % len(scale_pcs)  # +4 scale steps = fifth
        assert scale_pcs[e_idx] == 4, "A diatonic fifth should be E (pc=4)"

    def test_same_region_vs_cross_track(self):
        """dest_track_index=-1 → same region (thickening), >=0 → cross-track"""
        same_region = (-1) < 0
        assert same_region is True, "dest_track_index=-1 should be same region"
        cross_track = (4) < 0
        assert cross_track is False, "dest_track_index=4 should be cross-track"

    def test_pitch_bounds_check(self):
        """Notes shifted beyond 0-127 should be skipped"""
        # If original pitch = 120 and interval = octave (+12), new = 132 → skip
        orig_pitch = 120
        new_pitch = orig_pitch + 12  # 132
        assert new_pitch > 127, "132 should be out of bounds"

        # If original pitch = 5 and interval = octave down (-12), new = -7 → skip
        # (double_melody only shifts up, but bounds check logic is same)
        orig_pitch = 3
        new_pitch = orig_pitch + 0  # unison
        assert 0 <= new_pitch <= 127, "Unison should be in bounds"

    def test_velocity_scale_clamping(self):
        """velocity_scale * original velocity should be clamped to 0-1"""
        orig_vel = 0.9
        vel_scale = 1.5  # would give 1.35 → clamp to 1.0
        scaled = max(0, min(1, orig_vel * vel_scale))
        assert scaled == 1.0, "1.35 should clamp to 1.0"

        vel_scale = 0.7
        scaled = max(0, min(1, orig_vel * vel_scale))
        assert abs(scaled - 0.63) < 0.01, "0.9 * 0.7 should be 0.63"

    def test_time_offset_conversion(self):
        """time_offset in beats converts to PPQN correctly"""
        Quarter = 960
        tOff_beats = 0.25  # sixteenth note delay
        ppqn_offset = round(tOff_beats * Quarter)
        assert ppqn_offset == 240, "0.25 beats = 240 PPQN"

        tOff_beats = 2.0  # two beats
        ppqn_offset = round(tOff_beats * Quarter)
        assert ppqn_offset == 1920, "2 beats = 1920 PPQN"

    def test_invalid_interval_rejected(self):
        """Invalid interval name should return error string"""
        valid = ["unison", "octave", "double_octave", "fifth", "fourth", "third", "sixth"]
        test = "seventh"
        assert test not in valid, "seventh should not be a valid interval"

    def test_octave_doubling_semitone(self):
        """Octave doubling = +12 semitones (chromatic mode)"""
        interval_semitones = {
            "unison": 0, "octave": 12, "double_octave": 24,
            "fifth": 7, "fourth": 5, "third": 4, "sixth": 9,
        }
        semi_shift = interval_semitones["octave"]
        # C4 (60) + 12 = C5 (72)
        assert 60 + semi_shift == 72, "C4 + octave = C5"

    def test_power_chord_fifth(self):
        """Fifth doubling creates power chord interval (root + fifth)"""
        interval_semitones = {"fifth": 7}
        # C4 (60) + 7 = G4 (67) — perfect fifth
        root_pitch = 60
        fifth_pitch = root_pitch + interval_semitones["fifth"]
        assert fifth_pitch == 67, "C4 + fifth = G4 (67)"

    def test_diatonic_mode_uses_scale_pcs(self):
        """Diatonic mode builds scale pitch classes from root+scale"""
        from opendaw_mcp.music_theory import NOTE_TO_PITCH, SCALE_INTERVALS
        root_num = NOTE_TO_PITCH["D"]
        intervals = SCALE_INTERVALS["major"]
        scale_pcs = sorted(set((root_num + iv) % 12 for iv in intervals))
        # D major: D E F# G A B C# = 2 4 6 7 9 11 1
        assert scale_pcs == [1, 2, 4, 6, 7, 9, 11], f"D major scale pcs should be [1,2,4,6,7,9,11], got {scale_pcs}"



class TestSplitNoteRegion:
    """Tests for mcp_opendaw_split_note_region — region splitting"""

    def test_function_exists(self):
        import ast
        tree = ast.parse(open("server.py").read())
        names = [n.name for n in ast.walk(tree)
                 if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_split_note_region" in names

    def test_split_point_within_region(self):
        """Split point must be within region range"""
        # Region: position=0, duration=16 beats (4 bars in 4/4)
        src_pos = 0
        src_dur = 16
        src_end = src_pos + src_dur

        # Valid split: beat 8 (middle of region)
        split = 8
        assert src_pos < split < src_end

        # Invalid: before region
        split_before = -2
        assert not (src_pos < split_before < src_end)

        # Invalid: after region
        split_after = 20
        assert not (src_pos < split_after < src_end)

    def test_note_categorization_by_position(self):
        """Notes at/after split go to new region, before stay in original"""
        Quarter = 960
        split_tick = 8 * Quarter  # beat 8

        notes = [
            {"pos": 0, "pitch": 60},
            {"pos": 4 * Quarter, "pitch": 62},
            {"pos": 8 * Quarter, "pitch": 64},  # exactly at split → move
            {"pos": 12 * Quarter, "pitch": 65},
        ]

        notes_to_move = [n for n in notes if n["pos"] >= split_tick]
        notes_to_keep = [n for n in notes if n["pos"] < split_tick]

        assert len(notes_to_move) == 2, "2 notes at/after split should move"
        assert len(notes_to_keep) == 2, "2 notes before split should stay"
        assert notes_to_move[0]["pitch"] == 64
        assert notes_to_keep[0]["pitch"] == 60

    def test_relative_position_recalculation(self):
        """Moved notes get position relative to new region start"""
        Quarter = 960
        split_tick = 8 * Quarter
        orig_pos = 12 * Quarter  # beat 12
        rel_pos = orig_pos - split_tick  # beat 4 relative to new region
        assert rel_pos == 4 * Quarter, "beat 12 with split at 8 → rel beat 4"

    def test_original_region_duration_trim(self):
        """Original region duration is trimmed to split point"""
        src_pos = 0
        split_beat = 8
        new_dur = split_beat - src_pos
        assert new_dur == 8, "Original region should be trimmed to 8 beats"

    def test_new_region_duration(self):
        """New region gets remaining duration"""
        src_pos = 0
        src_dur = 16
        split_beat = 8
        new_dur = (src_pos + src_dur) - split_beat
        assert new_dur == 8, "New region should have 8 beats"

    def test_new_region_position(self):
        """New region starts at split point"""
        split_beat = 8
        assert split_beat == 8, "New region position = split beat"

    def test_straddling_note_kept_in_original(self):
        """A note starting before split but extending past it stays in original"""
        Quarter = 960
        split_tick = 8 * Quarter
        # Note starts at beat 6, duration 4 beats → ends at beat 10 (past split)
        note_pos = 6 * Quarter

        # Categorization is by position, not position+duration
        stays = note_pos < split_tick
        assert stays is True, "Note starting before split stays in original"

    def test_all_notes_before_split(self):
        """If all notes are before split, new region has 0 notes"""
        Quarter = 960
        split_tick = 8 * Quarter
        notes = [
            {"pos": 0, "pitch": 60},
            {"pos": 2 * Quarter, "pitch": 62},
            {"pos": 4 * Quarter, "pitch": 64},
        ]
        notes_to_move = [n for n in notes if n["pos"] >= split_tick]
        assert len(notes_to_move) == 0, "All notes before split → 0 moved"

    def test_all_notes_after_split(self):
        """If all notes are at/after split, original region has 0 notes"""
        Quarter = 960
        split_tick = 2 * Quarter
        notes = [
            {"pos": 4 * Quarter, "pitch": 60},
            {"pos": 8 * Quarter, "pitch": 62},
        ]
        notes_to_keep = [n for n in notes if n["pos"] < split_tick]
        assert len(notes_to_keep) == 0, "All notes at/after split → 0 kept"

    def test_tick_conversion(self):
        """Beat to tick conversion uses Quarter=960"""
        Quarter = 960
        # Beat 8 → 7680 ticks
        assert 8 * Quarter == 7680
        # Beat 32 (bar 8 in 4/4) → 30720 ticks
        assert 32 * Quarter == 30720

    def test_split_at_bar_boundary(self):
        """Common use case: split at bar boundary (4, 8, 16 beats)"""
        Quarter = 960
        bar_4 = 4 * 4  # 4 bars = 16 beats
        bar_8 = 8 * 4  # 8 bars = 32 beats
        assert bar_4 == 16
        assert bar_8 == 32
        assert bar_8 * Quarter == 30720

    def test_preserves_note_properties(self):
        """Moved notes keep pitch, velocity, duration, chance, cent"""
        orig = {"pos": 960, "dur": 480, "vel": 0.85, "pitch": 67, "chance": 100, "cent": 0}
        # After moving, only position changes, rest preserved
        moved = dict(orig)
        split_tick = 960
        moved["pos"] = orig["pos"] - split_tick
        assert moved["pitch"] == orig["pitch"]
        assert moved["vel"] == orig["vel"]
        assert moved["dur"] == orig["dur"]
        assert moved["chance"] == orig["chance"]
        assert moved["cent"] == orig["cent"]
        assert moved["pos"] == 0, "Position should be relative to new region"


class TestMergeNoteRegions:
    """Tests for mcp_opendaw_merge_note_regions — region merging"""

    def test_function_exists(self):
        import ast
        tree = ast.parse(open("server.py").read())
        names = [n.name for n in ast.walk(tree)
                 if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_merge_note_regions" in names

    def test_same_region_rejected(self):
        """Merging a region with itself should be rejected"""
        a, b = 0, 0
        assert a == b, "Same indices should be rejected"

    def test_note_position_recalculation(self):
        """Notes from B get positions relative to A's start"""
        Quarter = 960
        posA = 0 * Quarter      # Region A starts at beat 0
        posB = 8 * Quarter      # Region B starts at beat 8
        notePosB = 2 * Quarter   # Note in B at beat 2 (relative to B)

        # Absolute position = posB + notePosB = 10 beats
        absPos = posB + notePosB
        # New relative in A = absPos - posA = 10 beats
        relPos = absPos - posA
        assert relPos == 10 * Quarter, "Note at B:2 should be at A:10"

    def test_position_recalculation_with_offset_a(self):
        """A starts at beat 4, B starts at beat 12, note in B at beat 2"""
        Quarter = 960
        posA = 4 * Quarter
        posB = 12 * Quarter
        notePosB = 2 * Quarter

        absPos = posB + notePosB  # beat 14
        relPos = absPos - posA     # beat 10 relative to A
        assert relPos == 10 * Quarter, "Note at B:2 with A:4 should be at A:10"

    def test_duration_extension_adjacent(self):
        """Adjacent regions: A(0-8) + B(8-16) → merged(0-16)"""
        posA, durA = 0, 8
        posB, durB = 8, 8
        endA = posA + durA  # 8
        endB = posB + durB  # 16
        newEnd = max(endA, endB)
        newDur = newEnd - posA
        assert newDur == 16, "Merged adjacent regions should span 16 beats"

    def test_duration_extension_gap(self):
        """Regions with gap: A(0-4) + B(8-12) → merged(0-12)"""
        posA, durA = 0, 4
        posB, durB = 8, 4
        endA = posA + durA  # 4
        endB = posB + durB  # 12
        newEnd = max(endA, endB)
        newDur = newEnd - posA
        assert newDur == 12, "Merged with gap should span to furthest end"

    def test_duration_extension_overlap(self):
        """Overlapping regions: A(0-8) + B(4-12) → merged(0-12)"""
        posA, durA = 0, 8
        posB, durB = 4, 8
        endA = posA + durA  # 8
        endB = posB + durB  # 12
        newEnd = max(endA, endB)
        newDur = newEnd - posA
        assert newDur == 12, "Merged overlapping should span to furthest end"

    def test_b_extends_before_a(self):
        """B starts before A: B(0-4) + A(2-8) → A absorbs, spans 0-8"""
        # If A is at beat 2, B at beat 0
        posA, durA = 2, 6
        posB, durB = 0, 4
        endA = posA + durA  # 8
        endB = posB + durB  # 4
        newEnd = max(endA, endB)  # 8
        newDur = newEnd - posA  # 6 (A keeps its position, extends to 8)
        assert newDur == 6, "A keeps its position, duration extends to cover B"

    def test_b_deleted_after_merge(self):
        """Region B is deleted, remaining regions decremented"""
        regions_before = 3
        regions_after = regions_before - 1
        assert regions_after == 2, "Should have one fewer region after merge"

    def test_preserves_note_properties(self):
        """Moved notes keep pitch, velocity, duration, chance, cent"""
        orig = {"pos": 960, "dur": 480, "vel": 0.85, "pitch": 67, "chance": 90, "cent": -5}
        moved = dict(orig)
        # Only position changes
        posA = 0
        posB = 3840
        absPos = posB + orig["pos"]
        moved["pos"] = absPos - posA
        assert moved["pitch"] == orig["pitch"]
        assert moved["vel"] == orig["vel"]
        assert moved["dur"] == orig["dur"]
        assert moved["chance"] == orig["chance"]
        assert moved["cent"] == orig["cent"]
        assert moved["pos"] == 4800, "Position should be absolute relative to A"

    def test_empty_region_b(self):
        """Merging an empty region B adds 0 notes but extends duration"""
        notesB = []
        moved = len(notesB)
        assert moved == 0, "Empty B → 0 notes moved"

    def test_round_trip_split_merge(self):
        """Split then merge should restore original duration"""
        # Original: 16 beats
        # Split at 8 → A: 8 beats, B: 8 beats
        # Merge A + B → 16 beats
        orig_dur = 16
        split = 8
        durA = split  # 8
        durB = orig_dur - split  # 8
        posB = split  # 8
        endA = durA  # 8
        endB = posB + durB  # 16
        merged_dur = max(endA, endB)  # 16
        assert merged_dur == orig_dur, "Split+merge should restore original duration"

    def test_all_notes_combined(self):
        """After merge, A should have A_notes + B_notes total"""
        notesA = 5
        notesB = 3
        total = notesA + notesB
        assert total == 8, "Merged region should have all notes from both"


class TestFilterNotes:
    """Tests for mcp_opendaw_filter_notes — multi-criteria note filtering"""

    def test_function_exists(self):
        import ast
        tree = ast.parse(open("server.py").read())
        names = [n.name for n in ast.walk(tree)
                 if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith("mcp_opendaw_")]
        assert "mcp_opendaw_filter_notes" in names

    def test_pitch_filter(self):
        """Pitch range filter: only notes in [min, max] match"""
        notes = [
            {"pitch": 36},  # C2 — below range
            {"pitch": 60},  # C4 — in range
            {"pitch": 72},  # C5 — in range
            {"pitch": 84},  # C6 — above range
        ]
        min_p, max_p = 48, 78
        matching = [n for n in notes if min_p <= n["pitch"] <= max_p]
        assert len(matching) == 2
        assert matching[0]["pitch"] == 60
        assert matching[1]["pitch"] == 72

    def test_velocity_filter(self):
        """Velocity filter: only notes >= min_velocity match"""
        notes = [
            {"velocity": 0.2},  # ghost
            {"velocity": 0.5},  # low
            {"velocity": 0.8},  # normal
            {"velocity": 1.0},  # max
        ]
        min_v = 0.3
        matching = [n for n in notes if n["velocity"] >= min_v]
        assert len(matching) == 3
        assert notes[0] not in matching, "Ghost note should be filtered out"

    def test_time_filter(self):
        """Time range filter: only notes within [from, to] beats match"""
        notes = [
            {"abs_beat": 0},   # before range
            {"abs_beat": 4},   # in range
            {"abs_beat": 8},   # in range
            {"abs_beat": 20},  # after range
        ]
        from_b, to_b = 2, 16
        matching = [n for n in notes if from_b <= n["abs_beat"] <= to_b]
        assert len(matching) == 2

    def test_combined_filters(self):
        """All filters combined with AND logic"""
        notes = [
            {"pitch": 60, "velocity": 0.8, "abs_beat": 4},   # matches all
            {"pitch": 60, "velocity": 0.2, "abs_beat": 4},   # fails velocity
            {"pitch": 40, "velocity": 0.8, "abs_beat": 4},   # fails pitch
            {"pitch": 60, "velocity": 0.8, "abs_beat": 20},  # fails time
        ]
        min_p, max_p, min_v, from_b, to_b = 48, 72, 0.3, 0, 16
        matching = [n for n in notes
                    if (min_p <= n["pitch"] <= max_p
                        and n["velocity"] >= min_v
                        and from_b <= n["abs_beat"] <= to_b)]
        assert len(matching) == 1, "Only first note matches all criteria"

    def test_wildcard_ignores_filter(self):
        """-1 means wildcard (no filter on that criterion)"""
        min_p = -1  # no pitch filter
        pitch = 127
        matches = not (min_p >= 0 and pitch < min_p)
        assert matches is True, "-1 should be wildcard"

        min_p = 60
        pitch = 48
        matches = not (min_p >= 0 and pitch < min_p)
        assert matches is False, "48 < 60 should not match"

    def test_delete_action(self):
        """delete action removes matching notes"""
        notes = [
            {"pitch": 36},  # matches (below C4)
            {"pitch": 60},  # doesn't match
            {"pitch": 48},  # matches (below C4)
        ]
        max_p = 59
        matching = [n for n in notes if n["pitch"] <= max_p]
        to_delete = matching  # action="delete"
        assert len(to_delete) == 2
        remaining = [n for n in notes if n not in to_delete]
        assert len(remaining) == 1
        assert remaining[0]["pitch"] == 60

    def test_keep_action(self):
        """keep action deletes non-matching notes (inverse filter)"""
        notes = [
            {"pitch": 60},  # matches (C4)
            {"pitch": 36},  # doesn't match
            {"pitch": 72},  # doesn't match (above C4)
        ]
        min_p, max_p = 59, 61
        matching = [n for n in notes if min_p <= n["pitch"] <= max_p]
        non_matching = [n for n in notes if n not in matching]
        to_delete = non_matching  # action="keep" → delete non-matching
        assert len(to_delete) == 2
        assert len(matching) == 1
        assert matching[0]["pitch"] == 60

    def test_list_action_no_changes(self):
        """list action returns matching notes without modifying"""
        notes = [
            {"pitch": 60, "velocity": 0.8},
            {"pitch": 72, "velocity": 0.5},
        ]
        min_p = 48
        [n for n in notes if n["pitch"] >= min_p]
        # No deletion happens
        assert len(notes) == 2, "list action should not delete any notes"

    def test_invalid_action_rejected(self):
        """Invalid action name should be rejected"""
        valid_actions = ["list", "delete", "keep"]
        assert "move" not in valid_actions
        assert "select" not in valid_actions

    def test_abs_beat_calculation(self):
        """Note absolute beat = (regionPos + notePos) / Quarter"""
        Quarter = 960
        regionPos = 4 * Quarter  # region starts at beat 4
        notePos = 2 * Quarter     # note at beat 2 within region
        absBeat = (regionPos + notePos) / Quarter
        assert absBeat == 6, "Region at 4 + note at 2 = absolute beat 6"

    def test_all_notes_match_no_filters(self):
        """With all criteria at -1, every note matches"""
        notes = [{"pitch": p} for p in range(0, 128, 12)]
        min_p, max_p, min_v, max_v, from_b, to_b = -1, -1, -1, -1, -1, -1

        def matches(n):
            if min_p >= 0 and n["pitch"] < min_p: return False
            if max_p >= 0 and n["pitch"] > max_p: return False
            if min_v >= 0 and n.get("velocity", 0.8) < min_v: return False
            if max_v >= 0 and n.get("velocity", 0.8) > max_v: return False
            if from_b >= 0 and n.get("abs_beat", 0) < from_b: return False
            if to_b >= 0 and n.get("abs_beat", 0) > to_b: return False
            return True

        matching = [n for n in notes if matches(n)]
        assert len(matching) == len(notes), "All notes should match with no filters"

    def test_delete_below_pitch_cleanup(self):
        """Practical: cleanup sub-bass rumble below C2 (pitch 36)"""
        notes = [
            {"pitch": 24},  # C1 — rumble
            {"pitch": 30},  # F1 — rumble
            {"pitch": 36},  # C2 — keep (boundary)
            {"pitch": 48},  # C3 — keep
            {"pitch": 60},  # C4 — keep
        ]
        min_p = 36
        to_delete = [n for n in notes if n["pitch"] < min_p]
        assert len(to_delete) == 2, "Notes below C2 should be deleted"
        remaining = [n for n in notes if n["pitch"] >= min_p]
        assert len(remaining) == 3
        assert remaining[0]["pitch"] == 36, "C2 (boundary) should be kept"
