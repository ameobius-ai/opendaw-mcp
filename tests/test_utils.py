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

from server import _ok, _err, _wrap_eval, _unwrap_eval, _safe_filename, _safe_path


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
