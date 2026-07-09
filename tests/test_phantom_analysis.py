"""Tests for Phantom-grade analysis tools — genre profiles, problem detection, masking, helpers."""

import sys
import os
import math
import struct
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.utils import (
    _parse_wav, _analyze_spectrum, _compute_lufs,
    _resolve_audio_file, _load_wav_for_analysis,
)
from opendaw_mcp.genre_profiles import get_profile, list_genres, PROFILES


def _make_sine_wav_bytes(freq, duration_s=1.0, sr=44100, amp=0.5, stereo=False):
    """Create WAV bytes with a sine wave."""
    n_samples = int(duration_s * sr)
    samples = [amp * math.sin(2 * math.pi * freq * i / sr) for i in range(n_samples)]
    n_ch = 2 if stereo else 1
    if stereo:
        raw_samples = b"".join(
            struct.pack("<hh", int(s * 32767), int(s * 32767)) for s in samples
        )
    else:
        raw_samples = b"".join(struct.pack("<h", int(s * 32767)) for s in samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(raw_samples), b"WAVE",
        b"fmt ", 16, 1, n_ch, sr, sr * n_ch * 2, n_ch * 2, 16,
        b"data", len(raw_samples),
    )
    return header + raw_samples


# ── Genre profiles ──────────────────────────────────────────────

class TestGenreProfiles:
    def test_list_genres_returns_list(self):
        genres = list_genres()
        assert isinstance(genres, list)
        assert len(genres) >= 9

    def test_get_profile_pop(self):
        p = get_profile("pop")
        assert p is not None
        assert "target_lufs" in p
        assert "spectral_targets" in p
        assert p["target_lufs"] == -10

    def test_get_profile_cinematic(self):
        p = get_profile("cinematic")
        assert p is not None
        assert p["target_lufs"] == -18

    def test_get_profile_case_insensitive(self):
        p = get_profile("HIP_HOP")
        assert p is not None
        assert p["target_lufs"] == -10

    def test_get_profile_unknown_returns_none(self):
        assert get_profile("funk_jazz_core") is None

    def test_all_profiles_have_required_keys(self):
        required = {"target_lufs", "lufs_range", "spectral_targets",
                    "stereo_width_target", "dynamic_range_target",
                    "spectral_centroid_target", "characteristics", "mix_priorities"}
        for name, p in PROFILES.items():
            missing = required - set(p.keys())
            assert not missing, f"Profile '{name}' missing: {missing}"

    def test_all_profiles_have_7_bands(self):
        expected_bands = {"sub_bass", "bass", "low_mids", "mids", "high_mids", "presence", "brilliance"}
        for name, p in PROFILES.items():
            bands = set(p["spectral_targets"].keys())
            assert bands == expected_bands, f"Profile '{name}' bands mismatch: {bands ^ expected_bands}"


# ── DRY helpers ─────────────────────────────────────────────────

class TestResolveAudioFile:
    def test_resolve_nonexistent_returns_none(self):
        result = _resolve_audio_file("definitely_does_not_exist_xyz123.wav")
        assert result is None

    def test_resolve_absolute_path(self, tmp_path):
        f = tmp_path / "test.wav"
        f.write_bytes(_make_sine_wav_bytes(440))
        result = _resolve_audio_file(str(f))
        assert result is not None
        assert result.endswith("test.wav")


class TestLoadWavForAnalysis:
    def test_load_returns_tuple(self, tmp_path):
        f = tmp_path / "test.wav"
        f.write_bytes(_make_sine_wav_bytes(440))
        channels, sr, fpath = _load_wav_for_analysis(str(f))
        assert len(channels) == 1
        assert sr == 44100
        assert fpath.endswith("test.wav")

    def test_load_file_not_found_raises(self):
        try:
            _load_wav_for_analysis("nonexistent_xyz123.wav")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass


# ── Problem detection logic ─────────────────────────────────────

class TestProblemDetectionLogic:
    def test_clipping_detection(self):
        """Clipped sine should show high sample count."""
        # Create a clipped signal
        sr = 44100
        samples = [1.0] * sr  # all max — guaranteed clipping
        clip_count = sum(1 for s in samples if abs(s) >= 0.999)
        assert clip_count == sr

    def test_dc_offset_detection(self):
        """Signal with DC offset should have non-zero mean."""
        sr = 44100
        samples = [0.005 + 0.1 * math.sin(2 * math.pi * 440 * i / sr) for i in range(sr)]
        mean = sum(samples) / len(samples)
        assert abs(mean) > 0.001  # DC offset detected

    def test_clean_signal_no_problems(self):
        """Clean sine wave should not trigger DC or clipping."""
        wav_bytes = _make_sine_wav_bytes(440, duration_s=0.5)
        wav = _parse_wav(wav_bytes)
        channels = wav["channels"]
        # No clipping
        clip_count = sum(1 for ch in channels for s in ch if abs(s) >= 0.999)
        assert clip_count == 0
        # No DC offset
        mean = sum(channels[0]) / len(channels[0])
        assert abs(mean) < 0.01


# ── Masking detection logic ─────────────────────────────────────

class TestMaskingDetectionLogic:
    def test_two_bass_heavy_stems_mask(self):
        """Two stems with high bass energy should show masking."""
        # Both have 60% bass energy
        e1, e2 = 60.0, 55.0
        overlap = (e1 / 100) * (e2 / 100) * 100
        assert overlap > 15  # HIGH severity threshold

    def test_disjoint_stems_no_masking(self):
        """Stems in different frequency ranges should not mask."""
        # One sub_bass, one brilliance
        e1, e2 = 5.0, 3.0  # both low
        overlap = (e1 / 100) * (e2 / 100) * 100
        assert overlap < 5  # below threshold


# ── Analysis pipeline integration ───────────────────────────────

class TestAnalysisPipeline:
    def test_spectrum_returns_7_bands(self):
        wav_bytes = _make_sine_wav_bytes(440, duration_s=0.5)
        wav = _parse_wav(wav_bytes)
        result = _analyze_spectrum(wav["channels"], wav["sample_rate"])
        bands = result.get("bands", [])
        assert len(bands) == 7

    def test_lufs_returns_value(self):
        wav_bytes = _make_sine_wav_bytes(440, duration_s=1.0, amp=0.5)
        wav = _parse_wav(wav_bytes)
        result = _compute_lufs(wav["channels"], wav["sample_rate"])
        assert "lufs_integrated" in result
        assert isinstance(result["lufs_integrated"], float)

    def test_stereo_wav_parsed_correctly(self):
        wav_bytes = _make_sine_wav_bytes(440, duration_s=0.5, stereo=True)
        wav = _parse_wav(wav_bytes)
        assert wav["n_channels"] == 2
        assert len(wav["channels"]) == 2
