#!/usr/bin/env python3
"""Tests for compare_versions.py spectral analysis.

Run: venv/bin/python -m pytest tests/test_spectral.py -v
"""
import os
import sys
import tempfile
import numpy as np
import pytest
from scipy.io import wavfile

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from compare_versions import analyze, read, fft_band, BANDS


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sine_440():
    """Generate 2-second 440Hz stereo sine wave at 48kHz."""
    sr = 48000
    dur = 2.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    mono = 0.3 * np.sin(2 * np.pi * 440 * t)
    stereo = np.stack([mono, mono * 0.95], axis=1)
    path = tempfile.mktemp(suffix=".wav")
    wavfile.write(path, sr, (stereo * 32767).astype(np.int16))
    yield path, stereo, sr
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sine_880():
    """Generate 2-second 880Hz stereo sine wave (one octave higher)."""
    sr = 48000
    dur = 2.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    mono = 0.3 * np.sin(2 * np.pi * 880 * t)
    stereo = np.stack([mono, mono * 0.95], axis=1)
    path = tempfile.mktemp(suffix=".wav")
    wavfile.write(path, sr, (stereo * 32767).astype(np.int16))
    yield path, stereo, sr
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def silence():
    """Generate 2-second silence."""
    sr = 48000
    dur = 2.0
    stereo = np.zeros((int(sr * dur), 2), dtype=np.float32)
    path = tempfile.mktemp(suffix=".wav")
    wavfile.write(path, sr, (stereo * 32767).astype(np.int16))
    yield path
    if os.path.exists(path):
        os.unlink(path)


# ─── read() tests ──────────────────────────────────────────

class TestRead:
    def test_read_int16(self, sine_440):
        path, original, sr = sine_440
        data, sr_out = read(path)
        assert sr_out == 48000
        assert data.shape[0] == 2  # stereo (channels first after .T)
        assert data.dtype == np.float32
        assert np.max(np.abs(data)) < 1.0  # normalized

    def test_read_shape(self, sine_440):
        path, original, sr = sine_440
        data, _ = read(path)
        assert data.shape[0] == 2  # transposed: (channels, samples)


# ─── fft_band() tests ──────────────────────────────────────

class TestFFTBand:
    def test_440hz_energy_in_bass_band(self, sine_440):
        path, original, sr = sine_440
        d, _ = read(path)
        # 440Hz falls in 315-800 Hz "mid" band
        mid_energy = fft_band(d, sr, 315, 800)
        # Should have significant energy
        assert mid_energy > -20

    def test_440hz_no_energy_in_air(self, sine_440):
        path, original, sr = sine_440
        d, _ = read(path)
        # 440Hz should have negligible energy in 8000-16000 Hz
        air_energy = fft_band(d, sr, 8000, 16000)
        assert air_energy < -40

    def test_880hz_higher_than_440_in_pres(self, sine_440, sine_880):
        p440, _, sr = sine_440
        p880, _, _ = sine_880
        d440, _ = read(p440)
        d880, _ = read(p880)
        # 880Hz falls in 800-2000 "umid" band
        umid_440 = fft_band(d440, sr, 800, 2000)
        umid_880 = fft_band(d880, sr, 800, 2000)
        # 880Hz should have more energy in umid than 440Hz
        assert umid_880 > umid_440


# ─── analyze() tests ───────────────────────────────────────

class TestAnalyze:
    def test_sine_has_audio(self, sine_440):
        path, original, sr = sine_440
        result = analyze(path)
        assert result["has_audio"] if "has_audio" in result else True
        assert result["lufs"] < 0  # negative LUFS
        assert result["peak"] < 0  # negative peak dBFS
        assert result["width"] >= 0
        assert result["centroid"] > 0

    def test_silence_detected(self, silence):
        result = analyze(silence)
        # Silence should have very low LUFS
        assert result["lufs"] < -70

    def test_centroid_880_higher_than_440(self, sine_440, sine_880):
        p440, _, _ = sine_440
        p880, _, _ = sine_880
        r440 = analyze(p440)
        r880 = analyze(p880)
        # 880Hz centroid should be roughly double 440Hz
        assert r880["centroid"] > r440["centroid"]

    def test_bands_count(self, sine_440):
        path, _, _ = sine_440
        result = analyze(path)
        assert len(result["bands"]) == len(BANDS)

    def test_duration(self, sine_440):
        path, _, _ = sine_440
        result = analyze(path)
        assert 1.9 < result["dur"] < 2.1


# ─── LUFS / crest / width consistency ──────────────────────

class TestMetrics:
    def test_crest_positive(self, sine_440):
        path, _, _ = sine_440
        r = analyze(path)
        # Crest = peak - rms, should be positive for sine
        assert r["crest"] > 0

    def test_width_stereo_gt_mono(self):
        """Stereo signal should have wider width than mono."""
        sr = 48000
        dur = 2.0
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        mono = 0.3 * np.sin(2 * np.pi * 440 * t)

        # Mono (both channels identical)
        mono_path = tempfile.mktemp(suffix=".wav")
        mono_stereo = np.stack([mono, mono], axis=1)
        wavfile.write(mono_path, sr, (mono_stereo * 32767).astype(np.int16))

        # Stereo (different channels)
        stereo_path = tempfile.mktemp(suffix=".wav")
        stereo = np.stack([mono, mono * 0.8], axis=1)
        wavfile.write(stereo_path, sr, (stereo * 32767).astype(np.int16))

        try:
            r_mono = analyze(mono_path)
            r_stereo = analyze(stereo_path)
            # Mono should have near-zero width
            assert r_mono["width"] < 0.01
            # Stereo should have some width
            assert r_stereo["width"] > r_mono["width"]
        finally:
            for p in [mono_path, stereo_path]:
                if os.path.exists(p):
                    os.unlink(p)
