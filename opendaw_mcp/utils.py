"""
Utility functions for opendaw-mcp.

Pure Python helpers for WAV parsing, LUFS measurement, JSON serialization,
filename sanitization, and path traversal protection.
"""

import json
import os


def _parse_wav(raw: bytes) -> dict:
    """Parse a WAV file's RIFF header and return format info + de-interleaved float samples.

    Returns dict with: audio_format (1=PCM, 3=float32), n_channels, sample_rate,
    bits_per_sample, n_frames, channels (list of float lists), or raises ValueError.
    """
    import struct

    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("Not a valid WAV file")
    pos = 12
    n_channels = sample_rate = n_frames = 0
    bits_per_sample = 16
    audio_format = 1
    audio_data = b""
    while pos < len(raw) - 8:
        chunk_id = raw[pos : pos + 4]
        chunk_size = struct.unpack_from("<I", raw, pos + 4)[0]
        if chunk_id == b"fmt ":
            audio_format = struct.unpack_from("<H", raw, pos + 8)[0]
            n_channels = struct.unpack_from("<H", raw, pos + 10)[0]
            sample_rate = struct.unpack_from("<I", raw, pos + 12)[0]
            bits_per_sample = struct.unpack_from("<H", raw, pos + 22)[0]
        elif chunk_id == b"data":
            audio_data = raw[pos + 8 : pos + 8 + chunk_size]
            bytes_per_sample = bits_per_sample // 8
            n_frames = chunk_size // (bytes_per_sample * n_channels)
        pos += 8 + chunk_size + (chunk_size % 2)
    if not audio_data:
        raise ValueError("No data chunk in WAV")
    # Convert to float samples
    if audio_format == 3 and bits_per_sample == 32:
        fmt = f"<{n_frames * n_channels}f"
        samples = list(struct.unpack(fmt, audio_data))
    elif audio_format == 1 and bits_per_sample == 16:
        fmt = f"<{n_frames * n_channels}h"
        samples = [s / 32768.0 for s in struct.unpack(fmt, audio_data)]
    elif audio_format == 1 and bits_per_sample == 24:
        samples = [
            int.from_bytes(audio_data[i : i + 3], "little", signed=True) / 8388608.0
            for i in range(0, len(audio_data), 3)
        ]
    elif audio_format == 1 and bits_per_sample == 32:
        fmt = f"<{n_frames * n_channels}i"
        samples = [s / 2147483648.0 for s in struct.unpack(fmt, audio_data)]
    else:
        raise ValueError(f"Unsupported WAV format: {audio_format}/{bits_per_sample}bit")
    # De-interleave
    channels = [[] for _ in range(n_channels)]
    for i, s in enumerate(samples):
        channels[i % n_channels].append(s)
    return {
        "audio_format": audio_format,
        "n_channels": n_channels,
        "sample_rate": sample_rate,
        "bits_per_sample": bits_per_sample,
        "n_frames": n_frames,
        "channels": channels,
    }


def _compute_lufs(channels: list, sample_rate: int) -> dict:
    """Compute ITU-R BS.1770-4 integrated LUFS and true peak from de-interleaved float channels.

    Returns dict with: lufs_integrated, true_peak_db, max_sample, blocks_measured, gated_blocks.
    """
    import math

    n_channels = len(channels)
    n_frames = len(channels[0]) if channels else 0
    # K-weighting biquad coefficients (computed from sample_rate)
    f0, G, Q = 1681.974450955533, 3.9998432737, 0.7081754356
    K = math.tan(math.pi * f0 / sample_rate)
    Vh, Vb = 10 ** (G / 20.0), 10 ** (G / 40.0)
    a0_ = 1.0 + K / Q + K * K
    s_b0, s_b1, s_b2 = (Vh + Vb * K / Q + K * K) / a0_, 2.0 * (K * K - Vh) / a0_, (Vh - Vb * K / Q + K * K) / a0_
    s_a1, s_a2 = 2.0 * (K * K - 1.0) / a0_, (1.0 - K / Q + K * K) / a0_
    f0r, Qr = 38.1354708761, 0.5003270373
    Kr = math.tan(math.pi * f0r / sample_rate)
    ar0 = 1.0 + Kr / Qr + Kr * Kr
    r_b0, r_b1, r_b2 = 1.0 / ar0, -2.0 / ar0, 1.0 / ar0
    r_a1, r_a2 = 2.0 * (Kr * Kr - 1.0) / ar0, (1.0 - Kr / Qr + Kr * Kr) / ar0

    def _biquad(data, b0, b1, b2, a1, a2):
        out = [0.0] * len(data)
        x1 = x2 = y1 = y2 = 0.0
        for i in range(len(data)):
            x = data[i]
            y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            out[i] = y
            x2, x1, y2, y1 = x1, x, y1, y
        return out

    k_weighted = [
        _biquad(_biquad(ch, s_b0, s_b1, s_b2, s_a1, s_a2), r_b0, r_b1, r_b2, r_a1, r_a2)
        for ch in channels
    ]
    block_size = int(0.4 * sample_rate)
    hop_size = int(0.1 * sample_rate)
    if block_size == 0 or hop_size == 0:
        raise ValueError(f"Sample rate too low: {sample_rate}")
    ch_weights = [1.0] * n_channels
    for i in range(2, n_channels):
        ch_weights[i] = 1.41
    blocks_ms, pos = [], 0
    while pos + block_size <= n_frames:
        block_ms = sum(
            ch_weights[c] * sum(s * s for s in k_weighted[c][pos : pos + block_size]) / block_size
            for c in range(n_channels)
        )
        blocks_ms.append(block_ms)
        pos += hop_size
    if not blocks_ms:
        raise ValueError("Not enough samples for LUFS measurement")
    abs_gate_ms = 10 ** ((-70.0 + 0.691) / 10.0)
    gated_blocks = [ms for ms in blocks_ms if ms > abs_gate_ms]
    if not gated_blocks:
        raise ValueError("All blocks below absolute gate (-70 LUFS)")
    mean_ms = sum(gated_blocks) / len(gated_blocks)
    rel_gate_ms = 10 ** ((10 * math.log10(mean_ms) - 0.691 - 10) / 10.0)
    rel_gated = [ms for ms in gated_blocks if ms > rel_gate_ms]
    final_ms = sum(rel_gated) / len(rel_gated) if rel_gated else mean_ms
    lufs = -0.691 + 10 * math.log10(final_ms)
    max_sample = max(max(abs(s) for s in ch) for ch in channels)
    true_peak_db = 20 * math.log10(max_sample) if max_sample > 0 else -float("inf")
    return {
        "lufs_integrated": round(lufs, 1),
        "true_peak_db": round(true_peak_db, 2),
        "max_sample": round(max_sample, 6),
        "blocks_measured": len(blocks_ms),
        "gated_blocks": len(gated_blocks),
    }


def _ok(data=None) -> str:
    d = {"success": True, **(data or {})}
    d["success"] = True  # ensure success is always True
    return json.dumps(d)


def _err(msg: str) -> str:
    return json.dumps({"error": msg})


def _wrap_eval(result) -> str:
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    return json.dumps(result)


def _unwrap_eval(s) -> any:
    """Parse a JSON string from _wrap_eval back to dict/list."""
    if isinstance(s, str):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, ValueError):
            return s
    return s


def _safe_filename(name: str) -> str:
    """Sanitize a filename: strip quotes/backslashes, remove extension, prevent path traversal."""
    safe = name.replace('"', "").replace("'", "").replace("\\", "/")
    # Strip common audio extensions (case-insensitive)
    for ext in (".wav", ".mp3", ".flac", ".dawproject"):
        if safe.lower().endswith(ext):
            safe = safe[: -len(ext)]
    # Prevent path traversal: only allow basename
    safe = os.path.basename(safe)
    # Remove any remaining path separators
    safe = safe.replace("/", "").replace("\\", "")
    return safe or "output"


def _safe_path(export_dir: str, filename: str, ext: str = "wav") -> str:
    """Build a safe file path inside export_dir, preventing path traversal."""
    safe = _safe_filename(filename)
    path = os.path.join(export_dir, f"{safe}.{ext}")
    # Verify the resolved path is inside export_dir
    if not os.path.abspath(path).startswith(os.path.abspath(export_dir)):
        path = os.path.join(export_dir, f"output.{ext}")
    return path


def _clamp_script_param(value: float, mapping: str, min_val: float, max_val: float) -> tuple:
    """Clamp a script parameter value based on its mapping type.

    Mirrors the JS-side clamping in set_script_param.
    Returns (clamped_value, was_clamped).
    """
    original = value
    if mapping == "bool":
        result = 1 if value >= 0.5 else 0
    elif mapping == "int":
        result = round(value)
        result = max(min_val, min(max_val, result))
    else:  # unipolar, linear, exp
        result = max(min_val, min(max_val, value))
    return (float(result), result != original)


def _detect_bpm(channels: list, sample_rate: int) -> dict:
    """Detect BPM from audio using energy-based onset detection + autocorrelation.

    Pure Python implementation (no numpy required):
    1. Mix down to mono
    2. Compute energy envelope (1024-sample windows)
    3. Detect onset peaks (energy spikes above local average)
    4. Compute inter-onset intervals
    5. Autocorrelation of onset train → dominant periodicity → BPM

    Returns dict with: bpm, confidence, onset_count, duration_seconds.
    BPM range: 60-200. Confidence: 0-1 based on autocorrelation peak sharpness.
    """
    if not channels or not channels[0]:
        return {"bpm": 120.0, "confidence": 0.0, "onset_count": 0, "duration_seconds": 0.0}

    n_frames = len(channels[0])
    duration = n_frames / sample_rate

    # 1. Mix to mono
    n_ch = len(channels)
    mono = []
    for i in range(n_frames):
        s = sum(channels[c][i] for c in range(n_ch)) / n_ch
        mono.append(s)

    # 2. Energy envelope (1024-sample windows ~23ms at 44.1kHz)
    win_size = 1024
    n_windows = n_frames // win_size
    if n_windows < 10:
        return {"bpm": 120.0, "confidence": 0.0, "onset_count": 0, "duration_seconds": duration}

    energy = []
    for w in range(n_windows):
        start = w * win_size
        e = sum(mono[start + j] ** 2 for j in range(win_size)) / win_size
        energy.append(e)

    # 3. Onset detection: energy spike above local average
    onsets = []
    local_window = max(4, n_windows // 50)  # ~2s local window
    for i in range(1, n_windows):
        lo = max(0, i - local_window)
        hi = min(n_windows, i + local_window)
        local_avg = sum(energy[lo:hi]) / max(1, hi - lo)
        if energy[i] > local_avg * 1.5 and energy[i] > energy[i - 1]:
            onset_time = i * win_size / sample_rate
            onsets.append(onset_time)

    if len(onsets) < 4:
        return {"bpm": 120.0, "confidence": 0.0, "onset_count": len(onsets), "duration_seconds": duration}

    # 4. Autocorrelation of onset train
    # Build onset density function at 10ms resolution
    hop = 0.01  # 10ms
    n_hops = int(duration / hop)
    onset_signal = [0.0] * n_hops
    for t in onsets:
        idx = int(t / hop)
        if idx < n_hops:
            onset_signal[idx] = 1.0

    # Test BPM range 60-200 → lag in hops
    min_bpm = 60
    max_bpm = 200
    best_bpm = 120.0
    best_score = 0.0

    for bpm in range(min_bpm, max_bpm + 1):
        period = 60.0 / bpm  # seconds per beat
        lag = int(period / hop)  # lag in hops
        if lag >= n_hops or lag < 2:
            continue
        # Autocorrelation at this lag
        score = sum(onset_signal[i] * onset_signal[i + lag]
                     for i in range(n_hops - lag))
        # Normalize by lag (shorter lags have fewer terms)
        score = score / (n_hops - lag)
        # Also test half-time and double-time
        lag_half = lag // 2
        lag_double = lag * 2
        if lag_half >= 2 and lag_half < n_hops:
            score_half = sum(onset_signal[i] * onset_signal[i + lag_half]
                              for i in range(n_hops - lag_half)) / (n_hops - lag_half)
            score = max(score, score_half * 0.8)
        if lag_double < n_hops:
            score_double = sum(onset_signal[i] * onset_signal[i + lag_double]
                                for i in range(n_hops - lag_double)) / (n_hops - lag_double)
            score = max(score, score_double * 0.8)

        if score > best_score:
            best_score = score
            best_bpm = float(bpm)

    # Confidence: peak sharpness relative to average
    avg_score = best_score / max(1, len(onsets))
    confidence = min(1.0, avg_score * 10)

    return {
        "bpm": round(best_bpm, 1),
        "confidence": round(confidence, 2),
        "onset_count": len(onsets),
        "duration_seconds": round(duration, 2),
    }
