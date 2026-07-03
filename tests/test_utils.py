"""
Unit tests for pure Python helper functions in server.py.

These tests don't require a running openDAW instance — they verify
the utility functions that handle JSON serialization, filename sanitization,
and path traversal protection.
"""
import json
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
