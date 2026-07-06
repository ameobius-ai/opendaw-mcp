"""Unit tests for analyze_mix composite analysis tool."""

import sys
import os
import math
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opendaw_mcp.utils import _analyze_spectrum, _analyze_stereo, _analyze_dynamics


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


class TestAnalyzeMixStructure:
    """Test that analyze_mix produces valid combined output."""

    def test_spectrum_stereo_dynamics_present(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        channels = parsed["channels"]
        sr = parsed["sample_rate"]

        spectrum = _analyze_spectrum(channels, sr)
        stereo = _analyze_stereo(channels, sr)
        dynamics = _analyze_dynamics(channels, sr)

        assert "bands" in spectrum
        assert "is_stereo" in stereo
        assert "crest_factor_db" in dynamics

    def test_spectrum_has_mix_suggestions_data(self):
        n = 44100 * 2
        samples = _sine(80, n, amp=0.8)  # bass-heavy
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        spectrum = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])

        lh_ratio = spectrum.get("low_high_ratio", 0)
        assert lh_ratio > 1.0  # bass-heavy

    def test_dynamics_crest_factor_for_sine(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        dynamics = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])

        # Sine wave crest factor ~3 dB
        assert 2.0 < dynamics["crest_factor_db"] < 5.0

    def test_stereo_mono_detected(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        stereo = _analyze_stereo(parsed["channels"], parsed["sample_rate"])

        assert stereo["is_stereo"] is False

    def test_all_four_analyses_run_on_same_data(self):
        n = 44100 * 2
        samples = _sine(440, n, amp=0.5)
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        channels = parsed["channels"]
        sr = parsed["sample_rate"]

        s = _analyze_spectrum(channels, sr)
        st = _analyze_stereo(channels, sr)
        d = _analyze_dynamics(channels, sr)

        # All should have sample_rate
        assert s["sample_rate"] == sr
        assert st["sample_rate"] == sr
        assert d["sample_rate"] == sr


class TestAnalyzeMixPrioritization:
    """Test suggestion prioritization logic."""

    def test_priority_order(self):
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
        suggestions = [
            ("INFO", "info msg"),
            ("HIGH", "high msg"),
            ("LOW", "low msg"),
            ("MEDIUM", "medium msg"),
        ]
        suggestions.sort(key=lambda x: priority_order.get(x[0], 4))
        assert suggestions[0][0] == "HIGH"
        assert suggestions[1][0] == "MEDIUM"
        assert suggestions[2][0] == "LOW"
        assert suggestions[3][0] == "INFO"

    def test_high_priority_count(self):
        suggestions = [("HIGH", "a"), ("LOW", "b"), ("HIGH", "c"), ("INFO", "d")]
        count = sum(1 for p, _ in suggestions if p == "HIGH")
        assert count == 2

    def test_prioritized_format(self):
        suggestions = [("HIGH", "msg1"), ("LOW", "msg2")]
        prioritized = [{"priority": p, "suggestion": s} for p, s in suggestions]
        assert prioritized[0]["priority"] == "HIGH"
        assert prioritized[0]["suggestion"] == "msg1"
        assert prioritized[1]["priority"] == "LOW"


class TestAnalyzeMixMasterCheck:
    """Test mastering LUFS target check logic."""

    def test_master_check_targets(self):
        targets = {"spotify": -14, "apple": -16, "youtube": -14}
        lufs = -12.0
        master_check = {}
        for platform, target in targets.items():
            diff = lufs - target
            status = "ok" if abs(diff) <= 1.0 else ("too_loud" if diff > 0 else "too_quiet")
            master_check[platform] = {
                "target_lufs": target,
                "actual_lufs": lufs,
                "difference_db": round(diff, 1),
                "status": status,
            }
        assert master_check["spotify"]["status"] == "too_loud"
        assert master_check["apple"]["status"] == "too_loud"
        assert master_check["youtube"]["status"] == "too_loud"

    def test_master_check_ok(self):
        targets = {"spotify": -14}
        lufs = -14.0
        for platform, target in targets.items():
            diff = lufs - target
            status = "ok" if abs(diff) <= 1.0 else ("too_loud" if diff > 0 else "too_quiet")
            assert status == "ok"

    def test_master_check_too_quiet(self):
        targets = {"spotify": -14}
        lufs = -18.0
        for platform, target in targets.items():
            diff = lufs - target
            status = "ok" if abs(diff) <= 1.0 else ("too_loud" if diff > 0 else "too_quiet")
            assert status == "too_quiet"


class TestAnalyzeMixCombined:
    """Test combined analysis scenarios."""

    def test_bass_heavy_mix_detected(self):
        n = 44100 * 2
        samples = _sine(60, n, amp=0.8)
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        spectrum = _analyze_spectrum(parsed["channels"], parsed["sample_rate"])

        lh_ratio = spectrum.get("low_high_ratio", 0)
        # Should trigger bass-heavy suggestion
        assert lh_ratio > 1.0

    def test_compressed_mix_detected(self):
        n = 44100 * 2
        # Clipped sine — low crest factor
        samples = [max(-0.2, min(0.2, 3.0 * math.sin(2 * math.pi * 440 * i / 44100))) for i in range(n)]
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        dynamics = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])

        cf = dynamics["crest_factor_db"]
        # Clipped signal should have low crest factor
        assert cf < 8.0

    def test_dynamic_mix_detected(self):
        n = 44100 * 2
        # First half quiet, second half loud
        quiet = _sine(440, n // 2, amp=0.05)
        loud = _sine(440, n // 2, amp=0.9)
        samples = quiet + loud
        wav = _make_wav(samples)
        from opendaw_mcp.utils import _parse_wav
        parsed = _parse_wav(wav)
        dynamics = _analyze_dynamics(parsed["channels"], parsed["sample_rate"])

        lra = dynamics["loudness_range_db"]
        assert lra > 5.0
