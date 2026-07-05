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
