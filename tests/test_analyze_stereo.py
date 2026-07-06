"""Unit tests for stereo analysis (_analyze_stereo)."""

import sys
import os
import math
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.utils import _analyze_stereo, _parse_wav


def _make_stereo_wav(left_samples, right_samples, sr=44100):
    """Create a stereo WAV from separate L/R float sample lists."""
    n = min(len(left_samples), len(right_samples))
    raw_samples = b""
    for i in range(n):
        l = max(-32768, min(32767, int(left_samples[i] * 32767)))
        r = max(-32768, min(32767, int(right_samples[i] * 32767)))
        raw_samples += struct.pack("<hh", l, r)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(raw_samples), b"WAVE",
        b"fmt ", 16, 1, 2, sr, sr * 4, 4, 16,
        b"data", len(raw_samples),
    )
    return header + raw_samples


def _make_mono_wav(samples, sr=44100):
    """Create a mono WAV from float sample list."""
    raw_samples = b"".join(
        struct.pack("<h", max(-32768, min(32767, int(s * 32767)))) for s in samples
    )
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(raw_samples), b"WAVE",
        b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
        b"data", len(raw_samples),
    )
    return header + raw_samples


def _sine(freq, n, sr=44100, amp=0.5):
    return [amp * math.sin(2 * math.pi * freq * i / sr) for i in range(n)]


class TestAnalyzeStereoValidation:
    """Test input validation and edge cases."""

    def test_empty_channels(self):
        result = _analyze_stereo([], 44100)
        assert result["is_stereo"] is False
        assert result["stereo_width"] == 0.0

    def test_empty_channel_data(self):
        result = _analyze_stereo([[]], 44100)
        assert result["is_stereo"] is False

    def test_mono_audio(self):
        samples = _sine(440, 8000)
        wav = _make_mono_wav(samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["is_stereo"] is False
        assert "Mono audio" in result.get("message", "")

    def test_silence_stereo(self):
        n = 8000
        wav = _make_stereo_wav([0.0] * n, [0.0] * n)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["is_stereo"] is True
        assert result["mid_rms"] == 0.0


class TestAnalyzeStereoWidth:
    """Test stereo width measurement."""

    def test_identical_channels_mono_width(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["is_stereo"] is True
        assert result["stereo_width"] < 0.01  # essentially mono

    def test_hard_pan_left(self):
        n = 8000
        left = _sine(440, n, amp=0.5)
        right = [0.0] * n
        wav = _make_stereo_wav(left, right)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["lr_balance"] < -0.5  # strongly left

    def test_hard_pan_right(self):
        n = 8000
        left = [0.0] * n
        right = _sine(440, n, amp=0.5)
        wav = _make_stereo_wav(left, right)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["lr_balance"] > 0.5  # strongly right

    def test_wider_with_different_signals(self):
        n = 8000
        left = _sine(440, n, amp=0.5)
        right = _sine(880, n, amp=0.5)  # different freq = decorrelated
        wav = _make_stereo_wav(left, right)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["stereo_width"] > 0.1

    def test_identical_high_width_than_mono(self):
        n = 8000
        mono_samples = _sine(440, n)
        wav_mono = _make_stereo_wav(mono_samples, mono_samples)
        parsed_mono = _parse_wav(wav_mono)
        result_mono = _analyze_stereo(parsed_mono["channels"], parsed_mono["sample_rate"])

        left = _sine(440, n, amp=0.5)
        right = _sine(660, n, amp=0.5)  # different freq = decorrelated
        wav_wide = _make_stereo_wav(left, right)
        parsed_wide = _parse_wav(wav_wide)
        result_wide = _analyze_stereo(parsed_wide["channels"], parsed_wide["sample_rate"])

        assert result_wide["stereo_width"] > result_mono["stereo_width"]


class TestAnalyzeStereoPhase:
    """Test phase correlation."""

    def test_identical_channels_perfect_correlation(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["phase_correlation"] > 0.99

    def test_inverted_phase_negative_correlation(self):
        n = 8000
        left = _sine(440, n, amp=0.5)
        right = [-s for s in left]
        wav = _make_stereo_wav(left, right)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["phase_correlation"] < -0.9
        assert result["mono_compatible"] is False

    def test_mono_compatible_true_for_identical(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["mono_compatible"] is True

    def test_phase_issues_with_inverted(self):
        n = 8000
        left = _sine(440, n, amp=0.5)
        right = [-s for s in left]
        wav = _make_stereo_wav(left, right)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["phase_issues_pct"] > 90  # almost all samples opposite polarity


class TestAnalyzeStereoRegions:
    """Test per-region stereo width."""

    def test_returns_3_regions(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert len(result["regions"]) == 3

    def test_region_names(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        names = [r["name"] for r in result["regions"]]
        assert names == ["low", "mid", "high"]

    def test_region_has_width(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        for r in result["regions"]:
            assert "width" in r
            assert "side_rms" in r
            assert "mid_rms" in r
            assert r["width"] >= 0

    def test_mono_channels_all_regions_zero(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        for r in result["regions"]:
            assert r["width"] < 0.01


class TestAnalyzeStereoStructure:
    """Test structural properties."""

    def test_result_has_required_keys(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert "is_stereo" in result
        assert "stereo_width" in result
        assert "lr_balance" in result
        assert "phase_correlation" in result
        assert "mid_rms" in result
        assert "side_rms" in result
        assert "mono_compatible" in result
        assert "phase_issues_pct" in result
        assert "regions" in result
        assert "sample_rate" in result

    def test_frames_analyzed_positive(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["frames_analyzed"] > 0

    def test_sample_rate_preserved(self):
        n = 48000
        samples = _sine(440, n, sr=48000)
        wav = _make_stereo_wav(samples, samples, sr=48000)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert result["sample_rate"] == 48000

    def test_left_right_rms_present(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert "left_rms" in result
        assert "right_rms" in result
        assert result["left_rms"] > 0
        assert result["right_rms"] > 0

    def test_balance_zero_for_identical(self):
        n = 8000
        samples = _sine(440, n)
        wav = _make_stereo_wav(samples, samples)
        parsed = _parse_wav(wav)
        result = _analyze_stereo(parsed["channels"], parsed["sample_rate"])
        assert abs(result["lr_balance"]) < 0.01
