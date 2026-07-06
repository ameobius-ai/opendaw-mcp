"""Unit tests for dynamics analysis (_analyze_dynamics)."""

import sys
import os
import math
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.utils import _analyze_dynamics, _parse_wav


def _make_wav(samples, sr=44100, n_channels=1):
    """Create a WAV from float sample list."""
    if n_channels == 1:
        raw = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * 32767)))) for s in samples
        )
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + len(raw), b"WAVE",
            b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16, b"data", len(raw),
        )
    else:
        raw = b""
        n = len(samples) // 2
        for i in range(n):
            l = max(-32768, min(32767, int(samples[2 * i] * 32767)))
            r = max(-32768, min(32767, int(samples[2 * i + 1] * 32767)))
            raw += struct.pack("<hh", l, r)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + len(raw), b"WAVE",
            b"fmt ", 16, 1, 2, sr, sr * 4, 4, 16, b"data", len(raw),
        )
    return header + raw


def _sine(freq, n, sr=44100, amp=0.5):
    return [amp * math.sin(2 * math.pi * freq * i / sr) for i in range(n)]


def _square_wave(freq, n, sr=44100, amp=0.5):
    """Square wave — high crest factor (lots of harmonics)."""
    return [amp * (1 if math.sin(2 * math.pi * freq * i / sr) > 0 else -1) for i in range(n)]


def _compressed_sine(freq, n, sr=44100, amp=0.9):
    """Overdriven sine — low crest factor (clipped/squashed)."""
    return [max(-0.3, min(0.3, amp * math.sin(2 * math.pi * freq * i / sr) * 3)) for i in range(n)]


def _transient_rich(n, sr=44100, amp=0.8):
    """Signal with regular transients — spikes every 0.1s."""
    out = [0.0] * n
    spike_interval = int(0.1 * sr)
    spike_len = 50
    for pos in range(0, n - spike_len, spike_interval):
        for j in range(spike_len):
            out[pos + j] = amp * (1.0 - j / spike_len)
    return out


class TestAnalyzeDynamicsValidation:
    """Test input validation and edge cases."""

    def test_empty_channels(self):
        result = _analyze_dynamics([], 44100)
        assert result["crest_factor_db"] == 0.0

    def test_empty_channel_data(self):
        result = _analyze_dynamics([[]], 44100)
        assert result["crest_factor_db"] == 0.0

    def test_silence(self):
        n = 44100
        samples = [0.0] * n
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["crest_factor_db"] == 0.0 or result["rms_db"] == -120.0

    def test_short_audio(self):
        samples = _sine(440, 1000)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert "crest_factor_db" in result


class TestAnalyzeDynamicsCrestFactor:
    """Test crest factor measurement."""

    def test_pure_sine_crest_factor(self):
        n = 44100
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        # Sine wave crest factor = 3.01 dB
        assert 2.5 < result["crest_factor_db"] < 4.0

    def test_compressed_signal_lower_crest(self):
        n = 44100
        normal = _sine(440, n, amp=0.3)
        compressed = _compressed_sine(440, n, amp=0.9)
        wav_n = _make_wav(normal)
        wav_c = _make_wav(compressed)
        result_n = _analyze_dynamics(_parse_wav(wav_n)["channels"], 44100)
        result_c = _analyze_dynamics(_parse_wav(wav_c)["channels"], 44100)
        assert result_c["crest_factor_db"] < result_n["crest_factor_db"]

    def test_peak_db_present(self):
        n = 44100
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert "peak_db" in result
        assert abs(result["peak_db"] - (-6.0)) < 1.0  # amp=0.5 → ~-6 dB


class TestAnalyzeDynamicsLoudnessRange:
    """Test loudness range measurement."""

    def test_constant_signal_low_lra(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["loudness_range_db"] < 3.0

    def test_varying_signal_higher_lra(self):
        # First half quiet, second half loud
        n = 44100 * 2
        quiet = _sine(440, n // 2, amp=0.1)
        loud = _sine(440, n // 2, amp=0.9)
        samples = quiet + loud
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["loudness_range_db"] > 5.0

    def test_dynamic_range_db_positive(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["dynamic_range_db"] >= 0.0


class TestAnalyzeDynamicsSegments:
    """Test segment RMS analysis."""

    def test_returns_10_segments(self):
        n = 44100 * 3
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert len(result["segments"]) == 10

    def test_segment_has_required_fields(self):
        n = 44100 * 3
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        for seg in result["segments"]:
            assert "index" in seg
            assert "start_sec" in seg
            assert "end_sec" in seg
            assert "rms_db" in seg

    def test_constant_signal_low_variation(self):
        n = 44100 * 3
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["segment_variation_db"] < 2.0

    def test_varying_signal_high_variation(self):
        n = 44100 * 3
        # Build signal with varying levels per segment
        samples = []
        for seg in range(10):
            amp = 0.1 + 0.08 * seg  # increasing amplitude
            seg_samples = _sine(440, n // 10, amp=amp)
            samples.extend(seg_samples)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["segment_variation_db"] > 3.0


class TestAnalyzeDynamicsTransients:
    """Test transient density measurement."""

    def test_transient_rich_high_density(self):
        n = 44100 * 2
        samples = _transient_rich(n)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["transient_density"] > 5.0

    def test_pure_sine_low_density(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["transient_density"] < 5.0

    def test_transient_count_positive(self):
        n = 44100 * 2
        samples = _transient_rich(n)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["transient_count"] > 0


class TestAnalyzeDynamicsStructure:
    """Test structural properties."""

    def test_result_has_required_keys(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert "crest_factor_db" in result
        assert "loudness_range_db" in result
        assert "dynamic_range_db" in result
        assert "transient_density" in result
        assert "segments" in result
        assert "peak_db" in result
        assert "rms_db" in result
        assert "sample_rate" in result

    def test_frames_analyzed_positive(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["frames_analyzed"] > 0

    def test_n_windows_positive(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["n_windows"] > 0

    def test_stereo_audio(self):
        n = 44100 * 2
        sr = 44100
        left = _sine(440, n, sr=sr, amp=0.5)
        right = _sine(440, n, sr=sr, amp=0.5)
        interleaved = []
        for i in range(n):
            interleaved.append(left[i])
            interleaved.append(right[i])
        wav = _make_wav(interleaved, sr=sr, n_channels=2)
        parsed = _parse_wav(wav)
        result = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])
        assert result["frames_analyzed"] > 0
