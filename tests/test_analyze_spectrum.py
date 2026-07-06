"""Unit tests for spectral analysis (_analyze_spectrum)."""

import sys
import os
import math
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.utils import _analyze_spectrum, _parse_wav, _empty_spectrum


def _make_sine_wav(freq, duration_s=1.0, sr=44100, amp=0.5):
    """Create a WAV file bytes with a single sine wave."""
    n_samples = int(duration_s * sr)
    samples = [amp * math.sin(2 * math.pi * freq * i / sr) for i in range(n_samples)]
    # 16-bit mono PCM
    raw_samples = b"".join(struct.pack("<h", int(s * 32767)) for s in samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(raw_samples), b"WAVE",
        b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
        b"data", len(raw_samples),
    )
    return header + raw_samples


def _make_multi_sine_wav(freqs, duration_s=1.0, sr=44100, amp=0.3):
    """Create a WAV with multiple sine waves summed."""
    n_samples = int(duration_s * sr)
    samples = []
    for i in range(n_samples):
        s = sum(amp * math.sin(2 * math.pi * f * i / sr) for f in freqs)
        samples.append(max(-1.0, min(1.0, s)))
    raw_samples = b"".join(struct.pack("<h", int(s * 32767)) for s in samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(raw_samples), b"WAVE",
        b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
        b"data", len(raw_samples),
    )
    return header + raw_samples


class TestAnalyzeSpectrumValidation:
    """Test input validation and edge cases."""

    def test_empty_channels(self):
        result = _analyze_spectrum([], 44100)
        assert result["spectral_centroid_hz"] == 0.0
        assert result["frames_analyzed"] == 0

    def test_empty_channel_data(self):
        result = _analyze_spectrum([[]], 44100)
        assert result["spectral_centroid_hz"] == 0.0

    def test_short_audio(self):
        # Very short audio (less than FFT size)
        samples = [0.1] * 100
        result = _analyze_spectrum([samples], 44100)
        assert "bands" in result
        assert len(result["bands"]) == 7

    def test_silence(self):
        samples = [0.0] * 44100
        result = _analyze_spectrum([samples], 44100)
        assert result["spectral_centroid_hz"] == 0.0
        assert result["low_high_ratio"] == 0.0

    def test_empty_spectrum_helper(self):
        result = _empty_spectrum()
        assert len(result["bands"]) == 7
        assert all(b["energy_pct"] == 0.0 for b in result["bands"])
        assert result["spectral_centroid_hz"] == 0.0


class TestAnalyzeSpectrumBands:
    """Test frequency band analysis."""

    def test_returns_7_bands(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert len(result["bands"]) == 7

    def test_band_names(self):
        wav = _make_sine_wav(440, duration_s=1.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        names = [b["name"] for b in result["bands"]]
        assert names == ["sub_bass", "bass", "low_mids", "mids",
                         "high_mids", "presence", "brilliance"]

    def test_band_freq_ranges(self):
        wav = _make_sine_wav(440, duration_s=1.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        bands = result["bands"]
        assert bands[0]["freq_lo"] == 20.0
        assert bands[0]["freq_hi"] == 60.0
        assert bands[6]["freq_lo"] == 6000.0
        assert bands[6]["freq_hi"] == 20000.0

    def test_band_has_required_fields(self):
        wav = _make_sine_wav(440, duration_s=1.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        for b in result["bands"]:
            assert "name" in b
            assert "freq_lo" in b
            assert "freq_hi" in b
            assert "rms" in b
            assert "rms_db" in b
            assert "peak_db" in b
            assert "energy" in b
            assert "energy_pct" in b

    def test_energy_pct_sums_to_100(self):
        wav = _make_multi_sine_wav([80, 400, 2000, 8000], duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        total = sum(b["energy_pct"] for b in result["bands"])
        assert abs(total - 100.0) < 1.0

    def test_low_frequency_dominant_in_bass_band(self):
        wav = _make_sine_wav(80, duration_s=2.0, amp=0.8)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        bass_band = next(b for b in result["bands"] if b["name"] == "bass")
        assert bass_band["energy_pct"] > 30

    def test_high_frequency_dominant_in_brilliance(self):
        wav = _make_sine_wav(8000, duration_s=2.0, amp=0.5)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        # 8000 Hz falls in brilliance band
        brill = next(b for b in result["bands"] if b["name"] == "brilliance")
        assert brill["energy_pct"] > 20

    def test_mid_frequency_in_mids_band(self):
        wav = _make_sine_wav(1000, duration_s=2.0, amp=0.5)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        mids = next(b for b in result["bands"] if b["name"] == "mids")
        assert mids["energy_pct"] > 30


class TestAnalyzeSpectrumDescriptors:
    """Test global spectral descriptors."""

    def test_spectral_centroid_positive(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["spectral_centroid_hz"] > 0

    def test_higher_freq_higher_centroid(self):
        wav_low = _make_sine_wav(200, duration_s=2.0, amp=0.5)
        wav_high = _make_sine_wav(5000, duration_s=2.0, amp=0.5)
        parsed_low = _parse_wav(wav_low)
        parsed_high = _parse_wav(wav_high)
        result_low = _analyze_spectrum(parsed_low["channels"], parsed_low["sample_rate"])
        result_high = _analyze_spectrum(parsed_high["channels"], parsed_high["sample_rate"])
        assert result_high["spectral_centroid_hz"] > result_low["spectral_centroid_hz"]

    def test_spectral_spread_positive(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["spectral_spread_hz"] >= 0

    def test_spectral_rolloff_positive(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["spectral_rolloff_95_hz"] > 0

    def test_low_high_ratio_bass_heavy(self):
        wav = _make_sine_wav(80, duration_s=2.0, amp=0.8)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["low_high_ratio"] > 1.0

    def test_low_high_ratio_treble_heavy(self):
        wav = _make_sine_wav(8000, duration_s=2.0, amp=0.5)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["low_high_ratio"] < 1.0

    def test_spectral_crest_positive(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["spectral_crest"] > 0

    def test_spectral_crest_higher_for_pure_tone(self):
        # Pure sine should have higher crest than multi-tone
        wav_pure = _make_sine_wav(440, duration_s=2.0, amp=0.5)
        wav_multi = _make_multi_sine_wav([100, 440, 1000, 4000, 8000], duration_s=2.0, amp=0.2)
        parsed_pure = _parse_wav(wav_pure)
        parsed_multi = _parse_wav(wav_multi)
        result_pure = _analyze_spectrum(parsed_pure["channels"], parsed_pure["sample_rate"])
        result_multi = _analyze_spectrum(parsed_multi["channels"], parsed_multi["sample_rate"])
        assert result_pure["spectral_crest"] > result_multi["spectral_crest"]

    def test_frames_analyzed_positive(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["frames_analyzed"] > 0

    def test_fft_size_power_of_2(self):
        wav = _make_sine_wav(440, duration_s=2.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["fft_size"] > 0
        assert result["fft_size"] & (result["fft_size"] - 1) == 0  # power of 2


class TestAnalyzeSpectrumStructure:
    """Test structural properties."""

    def test_result_has_required_keys(self):
        wav = _make_sine_wav(440, duration_s=1.0)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert "bands" in result
        assert "spectral_centroid_hz" in result
        assert "spectral_spread_hz" in result
        assert "spectral_rolloff_95_hz" in result
        assert "low_high_ratio" in result
        assert "spectral_crest" in result
        assert "fft_size" in result
        assert "frames_analyzed" in result
        assert "sample_rate" in result

    def test_sample_rate_preserved(self):
        wav = _make_sine_wav(440, duration_s=1.0, sr=48000)
        parsed = _parse_wav(wav)
        result = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])
        assert result["sample_rate"] == 48000

    def test_stereo_audio(self):
        # Create stereo audio
        n = 44100
        sr = 44100
        left = [0.5 * math.sin(2 * math.pi * 440 * i / sr) for i in range(n)]
        right = [0.5 * math.sin(2 * math.pi * 880 * i / sr) for i in range(n)]
        result = _analyze_spectrum([left, right], sr)
        assert result["frames_analyzed"] > 0
        assert result["spectral_centroid_hz"] > 0
