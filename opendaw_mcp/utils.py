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


def _err(msg: str, code: str | None = None, hint: str | None = None) -> str:
    """Unified error response. Backward compatible — code/hint optional."""
    d = {"error": msg}
    if code:
        d["error_code"] = code
    if hint:
        d["hint"] = hint
    return json.dumps(d)


# Common error codes for consistent error handling across tools
ERR_BRIDGE = "BRIDGE_ERROR"
ERR_NOT_FOUND = "NOT_FOUND"
ERR_INVALID_PARAM = "INVALID_PARAMETER"
ERR_TIMEOUT = "TIMEOUT"


def _wrap_eval(result) -> str:
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    return _limit_output(json.dumps(result))


# Context-mode output sandboxing
# When OPENDAW_MCP_OUTPUT_LIMIT is set, tool responses are truncated to N chars
# with a summary footer. This prevents bulky JSON from flooding the agent's context.
_OUTPUT_LIMIT = int(os.environ.get("OPENDAW_MCP_OUTPUT_LIMIT", "0"))  # 0 = unlimited


def _limit_output(s: str) -> str:
    """Truncate tool output to OPENDAW_MCP_OUTPUT_LIMIT chars if set.

    Preserves valid JSON by truncating arrays/objects and adding a summary.
    When limit is 0 (default), no truncation — full output returned.
    """
    if _OUTPUT_LIMIT <= 0 or len(s) <= _OUTPUT_LIMIT:
        return s

    # Try to parse as JSON for smart truncation
    try:
        data = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        # Not JSON — simple truncation
        return s[:_OUTPUT_LIMIT] + f"\n... [truncated, {len(s) - _OUTPUT_LIMIT} chars omitted]"

    # Smart JSON truncation
    if isinstance(data, dict):
        # Keep error fields, truncate large value fields
        truncated = {}
        for k, v in data.items():
            v_str = json.dumps(v) if not isinstance(v, str) else v
            if len(v_str) > _OUTPUT_LIMIT // 4:
                truncated[k] = v_str[:_OUTPUT_LIMIT // 4] + "..."
            else:
                truncated[k] = v
        truncated["__truncated"] = True
        truncated["__original_length"] = len(s)
        return json.dumps(truncated, indent=2)
    elif isinstance(data, list):
        # Keep first N items
        keep_n = max(1, _OUTPUT_LIMIT // max(len(json.dumps(data[0])) if data else 1, 1))
        truncated = data[:keep_n]
        return json.dumps({
            "items": truncated,
            "total": len(data),
            "shown": len(truncated),
            "__truncated": True,
        }, indent=2)

    return s[:_OUTPUT_LIMIT] + f"\n... [truncated, {len(s) - _OUTPUT_LIMIT} chars omitted]"


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


# Krumhansl-Schmuckler key profiles (major / minor)
_KS_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_KS_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _fft_radix2(re: list, im: list) -> None:
    """In-place radix-2 Cooley-Tukey FFT. len(re) must be power of 2."""
    import math as _m

    n = len(re)
    if n <= 1:
        return
    # Bit reversal
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    # Cooley-Tukey
    length = 2
    while length <= n:
        ang = -2.0 * _m.pi / length
        wlen_re = _m.cos(ang)
        wlen_im = _m.sin(ang)
        half = length // 2
        for i in range(0, n, length):
            w_re, w_im = 1.0, 0.0
            for k in range(half):
                u_re = re[i + k]
                u_im = im[i + k]
                v_re = re[i + k + half] * w_re - im[i + k + half] * w_im
                v_im = re[i + k + half] * w_im + im[i + k + half] * w_re
                re[i + k] = u_re + v_re
                im[i + k] = u_im + v_im
                re[i + k + half] = u_re - v_re
                im[i + k + half] = u_im - v_im
                nw_re = w_re * wlen_re - w_im * wlen_im
                w_im = w_re * wlen_im + w_im * wlen_re
                w_re = nw_re
        length <<= 1


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _detect_key(channels: list, sample_rate: int) -> dict:
    """Detect musical key of audio using chroma features + Krumhansl-Schmuckler profiles.

    Pure Python (no numpy):
    1. Mix to mono
    2. Short-time FFT (4096-point, Hann window, 75% overlap)
    3. Map spectral bins to 12 pitch classes (chroma vector)
    4. Correlate chroma with major/minor key profiles for all 12 roots
    5. Best correlation → key + mode

    Returns dict with: key (e.g. "A"), mode ("major"/"minor"), confidence (0-1),
    alternatives (top 3), chroma (12-element list).
    """
    import math as _m

    if not channels or not channels[0]:
        return {"key": "C", "mode": "major", "confidence": 0.0,
                "alternatives": [], "chroma": [0.0] * 12}

    n_frames = len(channels[0])
    n_ch = len(channels)

    # 1. Mix to mono
    mono = [sum(channels[c][i] for c in range(n_ch)) / n_ch for i in range(n_frames)]

    # 2. STFT parameters
    fft_size = 4096
    hop_size = fft_size // 4  # 75% overlap
    if n_frames < fft_size:
        # Too short for FFT — fallback to zero-padded single frame
        fft_size = 1
        while fft_size < n_frames:
            fft_size <<= 1
        fft_size = max(256, fft_size)
        hop_size = fft_size

    # Hann window
    hann = [0.5 - 0.5 * _m.cos(2.0 * _m.pi * i / (fft_size - 1)) for i in range(fft_size)]

    # 3. Accumulate chroma across all frames
    chroma = [0.0] * 12
    n_frames_processed = 0
    pos = 0
    while pos + fft_size <= n_frames:
        # Window the frame
        frame = [mono[pos + i] * hann[i] for i in range(fft_size)]
        re = list(frame)
        im = [0.0] * fft_size
        _fft_radix2(re, im)

        # Magnitude spectrum (first half only — real signal symmetry)
        half = fft_size // 2
        for k in range(1, half):
            mag = _m.sqrt(re[k] * re[k] + im[k] * im[k])
            # Map bin k to pitch class
            freq = k * sample_rate / fft_size
            if freq < 55.0 or freq > 2000.0:
                continue  # Skip sub-bass noise and harsh highs
            midi = 69 + 12 * _m.log2(freq / 440.0)
            pc = int(round(midi)) % 12
            chroma[pc] += mag

        n_frames_processed += 1
        pos += hop_size

    if n_frames_processed == 0 or sum(chroma) == 0:
        return {"key": "C", "mode": "major", "confidence": 0.0,
                "alternatives": [], "chroma": [0.0] * 12}

    # Normalize chroma
    total = sum(chroma)
    chroma_norm = [c / total for c in chroma]

    # 4. Correlate with Krumhansl-Schmuckler profiles for all 24 keys
    def _correlate(a, b):
        n = len(a)
        ma = sum(a) / n
        mb = sum(b) / n
        num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
        da = _m.sqrt(sum((a[i] - ma) ** 2 for i in range(n)))
        db = _m.sqrt(sum((b[i] - mb) ** 2 for i in range(n)))
        if da == 0 or db == 0:
            return 0.0
        return num / (da * db)

    results = []
    for root in range(12):
        rotated = [chroma_norm[(root + i) % 12] for i in range(12)]
        corr_major = _correlate(rotated, _KS_MAJOR)
        corr_minor = _correlate(rotated, _KS_MINOR)
        results.append((_NOTE_NAMES[root], "major", corr_major))
        results.append((_NOTE_NAMES[root], "minor", corr_minor))

    # Sort by correlation descending
    results.sort(key=lambda x: x[2], reverse=True)

    best = results[0]
    # Confidence: ratio of best to second best
    second = results[1][2] if len(results) > 1 else 0.0
    confidence = min(1.0, max(0.0, (best[2] - second) / max(0.01, best[2])) if best[2] > 0 else 0.0)

    alternatives = [
        {"key": r[0], "mode": r[1], "correlation": round(r[2], 4)}
        for r in results[1:4]
    ]

    return {
        "key": best[0],
        "mode": best[1],
        "confidence": round(confidence, 3),
        "correlation": round(best[2], 4),
        "alternatives": alternatives,
        "chroma": [round(c, 6) for c in chroma_norm],
    }


def _transcribe_drums(channels: list, sample_rate: int, bpm: float = None,
                       sensitivity: float = 1.5, min_gap: float = 0.03) -> dict:
    """Transcribe drum onsets from audio into MIDI notes.

    Pure Python drum transcription:
    1. Split into 3 frequency bands (kick <250Hz, snare 250-2500Hz, hat >2500Hz)
    2. Per-band onset detection (energy spike above local average)
    3. Classify: kick (low-band onset dominant), snare (mid-band), hat (high-band)
    4. Estimate velocity from onset amplitude
    5. Convert onset times to beat positions (if bpm provided)

    Returns dict with: notes (list of {pitch, start_beat, start_sec, duration,
    velocity, drum_type}), bpm, onset_count, duration_seconds.
    MIDI pitches: kick=36, snare=38, hat=42.
    """
    if not channels or not channels[0]:
        return {"notes": [], "bpm": bpm or 120.0, "onset_count": 0, "duration_seconds": 0.0}

    n_frames = len(channels[0])
    duration = n_frames / sample_rate
    n_ch = len(channels)

    # Mix to mono
    mono = []
    for i in range(n_frames):
        s = sum(channels[c][i] for c in range(n_ch)) / n_ch
        mono.append(s)

    # Band-split via simple IIR filters
    # Kick: lowpass ~250 Hz (one-pole)
    # Snare: bandpass 250-2500 Hz (lowpass + highpass cascade)
    # Hat: highpass ~2500 Hz (one-pole HPF)

    def _one_pole_lp(data, cutoff):
        """One-pole lowpass: y[n] = y[n-1] + a*(x[n] - y[n-1])"""
        dt = 1.0 / sample_rate
        a = dt / (dt + 1.0 / (2 * 3.14159 * cutoff))
        out = [0.0] * len(data)
        out[0] = data[0] * a
        for i in range(1, len(data)):
            out[i] = out[i - 1] + a * (data[i] - out[i - 1])
        return out

    def _one_pole_hp(data, cutoff):
        """One-pole highpass: y[n] = a*(y[n-1] + x[n] - x[n-1])"""
        dt = 1.0 / sample_rate
        a = dt / (dt + 1.0 / (2 * 3.14159 * cutoff))
        out = [0.0] * len(data)
        for i in range(1, len(data)):
            out[i] = a * (out[i - 1] + data[i] - data[i - 1])
        return out

    kick_band = _one_pole_lp(mono, 250)
    snare_lp = _one_pole_lp(mono, 2500)
    snare_band = _one_pole_hp(snare_lp, 250)
    hat_band = _one_pole_hp(mono, 2500)

    # Energy envelope per band (512-sample windows ~12ms at 44.1kHz)
    win_size = 512
    n_windows = n_frames // win_size
    if n_windows < 8:
        return {"notes": [], "bpm": bpm or 120.0, "onset_count": 0, "duration_seconds": duration}

    def _energy_envelope(data):
        env = []
        for w in range(n_windows):
            start = w * win_size
            e = sum(data[start + j] ** 2 for j in range(win_size)) / win_size
            env.append(e)
        return env

    kick_env = _energy_envelope(kick_band)
    snare_env = _energy_envelope(snare_band)
    hat_env = _energy_envelope(hat_band)

    # Onset detection per band
    def _detect_onsets(env, local_window_size):
        onsets = []
        local_window = max(4, local_window_size)
        for i in range(2, n_windows - 1):
            lo = max(0, i - local_window)
            hi = min(n_windows, i + local_window)
            local_avg = sum(env[lo:hi]) / max(1, hi - lo)
            # Onset: energy spike above local average AND rising
            if (env[i] > local_avg * sensitivity and
                    env[i] > env[i - 1] and env[i] > env[i - 2]):
                onset_time = i * win_size / sample_rate
                onset_amp = env[i] / (local_avg + 1e-10)
                onsets.append((onset_time, onset_amp))
        return onsets

    kick_onsets = _detect_onsets(kick_env, n_windows // 80)
    snare_onsets = _detect_onsets(snare_env, n_windows // 80)
    hat_onsets = _detect_onsets(hat_env, n_windows // 100)

    # Merge onsets with minimum gap to avoid duplicates
    # Build note list with pitch classification
    notes = []
    drum_pitch = {"kick": 36, "snare": 38, "hat": 42}
    drum_dur = {"kick": 0.15, "snare": 0.12, "hat": 0.04}
    all_onsets = []

    for t, amp in kick_onsets:
        all_onsets.append((t, amp, "kick"))
    for t, amp in snare_onsets:
        all_onsets.append((t, amp, "snare"))
    for t, amp in hat_onsets:
        all_onsets.append((t, amp, "hat"))

    # Sort by time
    all_onsets.sort(key=lambda x: x[0])

    # Deduplicate: merge near-simultaneous onsets of same type
    filtered = []
    last_time_by_type = {"kick": -1, "snare": -1, "hat": -1}
    for t, amp, dtype in all_onsets:
        if t - last_time_by_type[dtype] >= min_gap:
            filtered.append((t, amp, dtype))
            last_time_by_type[dtype] = t

    # Normalize amplitudes to velocity 0-1
    max_amp = max((a for _, a, _ in filtered), default=1.0)
    if max_amp < 1e-10:
        max_amp = 1.0

    # Convert to notes
    actual_bpm = bpm if bpm and bpm > 0 else 120.0
    beats_per_sec = actual_bpm / 60.0

    for t, amp, dtype in filtered:
        vel = min(1.0, amp / max_amp)
        start_beat = t * beats_per_sec
        notes.append({
            "pitch": drum_pitch[dtype],
            "start_beat": round(start_beat, 4),
            "start_sec": round(t, 4),
            "duration": drum_dur[dtype],
            "velocity": round(vel, 3),
            "drum_type": dtype,
        })

    return {
        "notes": notes,
        "bpm": actual_bpm,
        "onset_count": len(notes),
        "duration_seconds": round(duration, 2),
        "band_counts": {
            "kick": sum(1 for n in notes if n["drum_type"] == "kick"),
            "snare": sum(1 for n in notes if n["drum_type"] == "snare"),
            "hat": sum(1 for n in notes if n["drum_type"] == "hat"),
        },
    }


def _transcribe_melody(channels: list, sample_rate: int, bpm: float = None,
                        frame_size: int = 2048, hop_size: int = 512,
                        min_freq: float = 50.0, max_freq: float = 2000.0,
                        onset_threshold: float = 0.05) -> dict:
    """Transcribe monophonic melody from audio into MIDI notes.

    Pure Python pitch detection via autocorrelation:
    1. Mix to mono
    2. For each frame: compute autocorrelation → find fundamental frequency
    3. Convert frequency → MIDI pitch (with cents deviation)
    4. Group consecutive similar-pitch frames into notes
    5. Detect note onsets (energy jumps) and offsets (energy drops)
    6. Convert frame times to beat positions (if bpm provided)

    Returns dict with: notes (list of {pitch, start_beat, start_sec, duration,
    velocity, cents}), bpm, note_count, duration_seconds.
    """
    import math as _math

    if not channels or not channels[0]:
        return {"notes": [], "bpm": bpm or 120.0, "note_count": 0, "duration_seconds": 0.0}

    n_frames = len(channels[0])
    duration = n_frames / sample_rate
    n_ch = len(channels)

    # Mix to mono
    mono = []
    for i in range(n_frames):
        s = sum(channels[c][i] for c in range(n_ch)) / n_ch
        mono.append(s)

    min_lag = int(sample_rate / max_freq)
    max_lag = int(sample_rate / min_freq)
    if max_lag > frame_size:
        max_lag = frame_size

    n_hops = (n_frames - frame_size) // hop_size
    if n_hops < 2:
        return {"notes": [], "bpm": bpm or 120.0, "note_count": 0, "duration_seconds": duration}

    def _detect_pitch(frame):
        """Autocorrelation pitch detection. Returns (freq, clarity) or (None, 0)."""
        # Normalize frame
        energy = sum(s * s for s in frame)
        if energy < 1e-8:
            return None, 0.0

        # Compute autocorrelation for lag range
        best_lag = 0
        best_corr = 0.0
        for lag in range(min_lag, max_lag):
            corr = 0.0
            for i in range(len(frame) - lag):
                corr += frame[i] * frame[i + lag]
            corr = corr / (len(frame) - lag)
            if corr > best_corr:
                best_corr = corr
                best_lag = lag

        if best_lag == 0 or best_corr < 0.1:
            return None, 0.0

        # Parabolic interpolation for sub-sample accuracy
        if best_lag > min_lag and best_lag < max_lag - 1:
            # Recompute neighbors
            corr_m = 0.0
            corr_p = 0.0
            for i in range(len(frame) - best_lag + 1):
                corr_m += frame[i] * frame[i + best_lag - 1]
            for i in range(len(frame) - best_lag - 1):
                corr_p += frame[i] * frame[i + best_lag + 1]
            denom = corr_m + best_corr + corr_p
            if denom > 0:
                shift = 0.5 * (corr_m - corr_p) / denom
                best_lag = best_lag + shift

        freq = sample_rate / best_lag
        clarity = min(1.0, best_corr / (energy / len(frame) + 1e-10))
        return freq, clarity

    def _freq_to_midi(freq):
        """Convert frequency to MIDI note + cents deviation."""
        if freq <= 0:
            return None, 0
        midi_float = 69 + 12 * _math.log2(freq / 440.0)
        midi_note = round(midi_float)
        cents = round((midi_float - midi_note) * 100)
        return midi_note, cents

    # Process frames
    frame_pitches = []  # (time_sec, freq, clarity, energy)
    for h in range(n_hops):
        start = h * hop_size
        frame = mono[start:start + frame_size]
        t = start / sample_rate

        # Frame energy
        fe = sum(s * s for s in frame) / frame_size
        if fe < onset_threshold:
            frame_pitches.append((t, None, 0.0, fe))
            continue

        freq, clarity = _detect_pitch(frame)
        frame_pitches.append((t, freq, clarity, fe))

    # Group consecutive pitched frames into notes
    notes = []
    actual_bpm = bpm if bpm and bpm > 0 else 120.0
    beats_per_sec = actual_bpm / 60.0

    current_note = None  # {start_time, pitches: [(freq, clarity)], energy}

    for t, freq, clarity, energy in frame_pitches:
        if freq is not None and clarity > 0.15:
            midi_note, cents = _freq_to_midi(freq)
            if midi_note is not None and 21 <= midi_note <= 108:
                if current_note is None:
                    # Start new note
                    current_note = {
                        "start_time": t,
                        "pitches": [(midi_note, cents, clarity)],
                        "energies": [energy],
                    }
                else:
                    # Check if pitch is similar to current note
                    last_pitch = current_note["pitches"][-1][0]
                    if abs(midi_note - last_pitch) <= 1:
                        # Same note — extend
                        current_note["pitches"].append((midi_note, cents, clarity))
                        current_note["energies"].append(energy)
                    else:
                        # Different pitch — close current note, start new
                        notes.append(current_note)
                        current_note = {
                            "start_time": t,
                            "pitches": [(midi_note, cents, clarity)],
                            "energies": [energy],
                        }
        else:
            # Silence or low clarity — close current note
            if current_note is not None:
                notes.append(current_note)
                current_note = None

    if current_note is not None:
        notes.append(current_note)

    # Convert note groups to output format
    result_notes = []
    for note in notes:
        if len(note["pitches"]) < 2:
            continue  # too short — skip

        start_t = note["start_time"]
        # Duration: number of frames * hop time
        end_t = start_t + len(note["pitches"]) * hop_size / sample_rate
        dur = end_t - start_t

        # Average pitch (most common)
        pitch_counts = {}
        for p, c, cl in note["pitches"]:
            pitch_counts[p] = pitch_counts.get(p, 0) + 1
        avg_pitch = max(pitch_counts, key=pitch_counts.get)

        # Average cents
        relevant_cents = [c for p, c, cl in note["pitches"] if p == avg_pitch]
        avg_cents = sum(relevant_cents) / len(relevant_cents) if relevant_cents else 0

        # Velocity from energy
        avg_energy = sum(note["energies"]) / len(note["energies"])
        velocity = min(1.0, max(0.1, (avg_energy / 0.1) ** 0.5))

        # Average clarity
        avg_clarity = sum(cl for _, _, cl in note["pitches"]) / len(note["pitches"])

        start_beat = start_t * beats_per_sec

        result_notes.append({
            "pitch": avg_pitch,
            "start_beat": round(start_beat, 4),
            "start_sec": round(start_t, 4),
            "duration": round(dur, 4),
            "velocity": round(velocity, 3),
            "cents": round(avg_cents),
            "clarity": round(avg_clarity, 3),
        })

    return {
        "notes": result_notes,
        "bpm": actual_bpm,
        "note_count": len(result_notes),
        "duration_seconds": round(duration, 2),
        "frame_size": frame_size,
        "hop_size": hop_size,
    }


def _analyze_spectrum(channels: list, sample_rate: int, n_bands: int = 7) -> dict:
    """Spectral analysis of audio across frequency bands.

    Pure Python (no numpy):
    1. Mix to mono
    2. STFT (8192-point, Hann window, 50% overlap)
    3. Average power spectrum across all frames
    4. Divide into standard frequency bands:
       - sub_bass:  20-60 Hz
       - bass:      60-250 Hz
       - low_mids:  250-500 Hz
       - mids:      500-2000 Hz
       - high_mids: 2000-4000 Hz
       - presence:  4000-6000 Hz
       - brilliance:6000-20000 Hz
    5. Per band: RMS (linear), peak (dB), energy percentage
    6. Global: spectral centroid (brightness), spectral rolloff (95%),
       spectral spread (variance), low/high balance ratio

    Returns dict with band analysis and global spectral descriptors.
    """
    import math as _m

    if not channels or not channels[0]:
        return _empty_spectrum()

    n_frames = len(channels[0])
    n_ch = len(channels)

    # 1. Mix to mono
    mono = [sum(channels[c][i] for c in range(n_ch)) / n_ch for i in range(n_frames)]

    # 2. STFT parameters
    fft_size = 8192
    hop_size = fft_size // 2  # 50% overlap
    if n_frames < fft_size:
        fft_size = 1
        while fft_size < n_frames:
            fft_size <<= 1
        fft_size = max(256, fft_size)
        hop_size = fft_size
    if fft_size < 256:
        return _empty_spectrum()

    # Hann window
    hann = [0.5 - 0.5 * _m.cos(2.0 * _m.pi * i / (fft_size - 1)) for i in range(fft_size)]

    # 3. Accumulate power spectrum
    half = fft_size // 2
    accum_power = [0.0] * half
    n_frames_processed = 0
    pos = 0
    while pos + fft_size <= n_frames:
        frame = [mono[pos + i] * hann[i] for i in range(fft_size)]
        re = list(frame)
        im = [0.0] * fft_size
        _fft_radix2(re, im)
        for k in range(1, half):
            mag = _m.sqrt(re[k] * re[k] + im[k] * im[k])
            accum_power[k] += mag * mag  # power
        n_frames_processed += 1
        pos += hop_size

    if n_frames_processed == 0:
        return _empty_spectrum()

    # Average power spectrum
    avg_power = [p / n_frames_processed for p in accum_power]

    # 4. Frequency bands (ISO standard crossover frequencies)
    bands = [
        ("sub_bass", 20.0, 60.0),
        ("bass", 60.0, 250.0),
        ("low_mids", 250.0, 500.0),
        ("mids", 500.0, 2000.0),
        ("high_mids", 2000.0, 4000.0),
        ("presence", 4000.0, 6000.0),
        ("brilliance", 6000.0, 20000.0),
    ]

    bin_freq = sample_rate / fft_size  # Hz per bin

    band_results = []
    total_energy = 0.0

    for name, f_lo, f_hi in bands:
        bin_lo = max(1, int(f_lo / bin_freq))
        bin_hi = min(half - 1, int(f_hi / bin_freq))
        if bin_lo >= bin_hi:
            band_results.append({
                "name": name, "freq_lo": f_lo, "freq_hi": f_hi,
                "rms": 0.0, "peak_db": -120.0, "energy_pct": 0.0,
            })
            continue
        band_power = sum(avg_power[k] for k in range(bin_lo, bin_hi + 1))
        band_rms = _m.sqrt(band_power / (bin_hi - bin_lo + 1))
        band_peak = max(avg_power[k] for k in range(bin_lo, bin_hi + 1))
        band_peak_db = 10 * _m.log10(band_peak) if band_peak > 0 else -120.0
        band_rms_db = 10 * _m.log10(band_rms) if band_rms > 0 else -120.0
        total_energy += band_power
        band_results.append({
            "name": name, "freq_lo": f_lo, "freq_hi": f_hi,
            "rms": round(band_rms, 6), "rms_db": round(band_rms_db, 1),
            "peak_db": round(band_peak_db, 1), "energy": round(band_power, 6),
        })

    # Energy percentages
    if total_energy > 0:
        for br in band_results:
            br["energy_pct"] = round(100.0 * br.get("energy", 0.0) / total_energy, 1)

    # 5. Global spectral descriptors
    # Spectral centroid: weighted mean frequency
    freqs = [k * bin_freq for k in range(1, half)]
    powers = avg_power[1:half]
    total_p = sum(powers)
    if total_p > 0:
        centroid = sum(f * p for f, p in zip(freqs, powers)) / total_p
        # Spectral spread (variance around centroid)
        spread = _m.sqrt(sum(p * (f - centroid) ** 2 for f, p in zip(freqs, powers)) / total_p)
        # Spectral rolloff (95th percentile)
        cumulative = 0.0
        rolloff_freq = 0.0
        for f, p in zip(freqs, powers):
            cumulative += p
            if cumulative >= 0.95 * total_p:
                rolloff_freq = f
                break
    else:
        centroid = 0.0
        spread = 0.0
        rolloff_freq = 0.0

    # Low/high balance: ratio of energy below 250 Hz to above 250 Hz
    low_energy = sum(br.get("energy", 0.0) for br in band_results[:2])  # sub_bass + bass
    high_energy = sum(br.get("energy", 0.0) for br in band_results[2:])  # everything else
    low_high_ratio = low_energy / high_energy if high_energy > 0 else 0.0

    # Spectral crest factor: peak / mean of spectrum
    peak_power = max(powers) if powers else 0.0
    mean_power = total_p / len(powers) if powers else 0.0
    crest = peak_power / mean_power if mean_power > 0 else 0.0

    return {
        "bands": band_results,
        "spectral_centroid_hz": round(centroid, 1),
        "spectral_spread_hz": round(spread, 1),
        "spectral_rolloff_95_hz": round(rolloff_freq, 1),
        "low_high_ratio": round(low_high_ratio, 3),
        "spectral_crest": round(crest, 2),
        "fft_size": fft_size,
        "frames_analyzed": n_frames_processed,
        "sample_rate": sample_rate,
    }


def _empty_spectrum() -> dict:
    """Return empty spectrum result for invalid input."""
    bands = [
        {"name": n, "freq_lo": lo, "freq_hi": hi, "rms": 0.0, "rms_db": -120.0,
         "peak_db": -120.0, "energy": 0.0, "energy_pct": 0.0}
        for n, lo, hi in [
            ("sub_bass", 20.0, 60.0), ("bass", 60.0, 250.0),
            ("low_mids", 250.0, 500.0), ("mids", 500.0, 2000.0),
            ("high_mids", 2000.0, 4000.0), ("presence", 4000.0, 6000.0),
            ("brilliance", 6000.0, 20000.0),
        ]
    ]
    return {
        "bands": bands,
        "spectral_centroid_hz": 0.0,
        "spectral_spread_hz": 0.0,
        "spectral_rolloff_95_hz": 0.0,
        "low_high_ratio": 0.0,
        "spectral_crest": 0.0,
        "fft_size": 0,
        "frames_analyzed": 0,
        "sample_rate": 0,
    }


def _analyze_stereo(channels: list, sample_rate: int) -> dict:
    """Stereo analysis of audio — width, L/R balance, mono compatibility, mid/side energy.

    Pure Python (no numpy):
    1. Requires stereo (2 channels) input — mono returns special status
    2. Compute per-sample Mid (L+R)/2 and Side (L-R)/2
    3. RMS of Mid and Side across entire track
    4. Stereo width = Side RMS / Mid RMS (0 = mono, 1 = hard panned)
    5. L/R balance: difference in RMS between left and right
    6. Mono compatibility: phase correlation coefficient (-1 to +1)
       +1 = perfectly in phase (mono safe), 0 = uncorrelated, -1 = out of phase
    7. Per-band stereo width: divide Side/Mid ratio into 3 frequency regions
       (low <250Hz, mid 250-4000Hz, high >4000Hz) using simple lowpass/highpass
    8. Phase issues: count samples where L and R have opposite signs

    Returns dict with stereo descriptors and per-region width.
    """
    import math as _m

    if not channels or not channels[0]:
        return {
            "is_stereo": False, "stereo_width": 0.0, "lr_balance": 0.0,
            "phase_correlation": 0.0, "mid_rms": 0.0, "side_rms": 0.0,
            "mono_compatible": True, "phase_issues_pct": 0.0,
            "regions": [], "sample_rate": sample_rate,
        }

    n_ch = len(channels)
    n_frames = len(channels[0])

    # Mono input — no stereo information
    if n_ch < 2:
        return {
            "is_stereo": False,
            "stereo_width": 0.0,
            "lr_balance": 0.0,
            "phase_correlation": 1.0,
            "mid_rms": round(_m.sqrt(sum(s * s for s in channels[0][:min(n_frames, sample_rate * 10)]) / max(1, min(n_frames, sample_rate * 10))), 6),
            "side_rms": 0.0,
            "mono_compatible": True,
            "phase_issues_pct": 0.0,
            "regions": [],
            "message": "Mono audio — no stereo information available",
            "sample_rate": sample_rate,
        }

    left = channels[0]
    right = channels[1]

    # Compute Mid and Side
    mid = [(left[i] + right[i]) / 2.0 for i in range(n_frames)]
    side = [(left[i] - right[i]) / 2.0 for i in range(n_frames)]

    # RMS calculations (sample entire track, or first 10 seconds if very long)
    analysis_len = min(n_frames, sample_rate * 30)  # cap at 30 seconds
    mid_rms = _m.sqrt(sum(mid[i] * mid[i] for i in range(analysis_len)) / analysis_len)
    side_rms = _m.sqrt(sum(side[i] * side[i] for i in range(analysis_len)) / analysis_len)
    left_rms = _m.sqrt(sum(left[i] * left[i] for i in range(analysis_len)) / analysis_len)
    right_rms = _m.sqrt(sum(right[i] * right[i] for i in range(analysis_len)) / analysis_len)

    # Stereo width: Side/Mid ratio (0 = mono, higher = wider)
    stereo_width = side_rms / mid_rms if mid_rms > 0 else 0.0

    # L/R balance: -1 = fully left, 0 = centered, +1 = fully right
    lr_balance = 0.0
    if left_rms + right_rms > 0:
        lr_balance = (right_rms - left_rms) / (left_rms + right_rms)

    # Phase correlation coefficient
    # corr = sum(L*R) / sqrt(sum(L^2) * sum(R^2))
    lr_dot = sum(left[i] * right[i] for i in range(analysis_len))
    l_sq = sum(left[i] * left[i] for i in range(analysis_len))
    r_sq = sum(right[i] * right[i] for i in range(analysis_len))
    if l_sq > 0 and r_sq > 0:
        phase_corr = lr_dot / _m.sqrt(l_sq * r_sq)
    else:
        phase_corr = 1.0

    # Phase issues: samples where L and R have opposite signs
    phase_issues = sum(1 for i in range(analysis_len) if left[i] * right[i] < 0)
    phase_issues_pct = 100.0 * phase_issues / analysis_len

    # Mono compatibility: phase correlation > 0 means mono-safe
    mono_compatible = phase_corr > 0.0

    # Per-region stereo width using simple band splitting
    # Use one-pole filters to split into low/mid/high
    def _one_pole_lowpass(data, cutoff_hz, sr):
        alpha = 2.0 * _m.pi * cutoff_hz / sr
        alpha = min(alpha, 0.95)
        out = [0.0] * len(data)
        out[0] = data[0]
        for i in range(1, len(data)):
            out[i] = out[i - 1] + alpha * (data[i] - out[i - 1])
        return out

    def _one_pole_highpass(data, cutoff_hz, sr):
        alpha = 2.0 * _m.pi * cutoff_hz / sr
        alpha = min(alpha, 0.95)
        out = [0.0] * len(data)
        out[0] = data[0]
        for i in range(1, len(data)):
            out[i] = alpha * (out[i - 1] + data[i] - data[i - 1])
        return out

    regions = []
    region_cutoffs = [("low", 250.0), ("mid", 4000.0), ("high", 20000.0)]

    # Split side signal into frequency regions
    lp_side = _one_pole_lowpass(side, 250.0, sample_rate)
    hp_from_low = _one_pole_highpass(side, 250.0, sample_rate)
    mid_band = _one_pole_lowpass(hp_from_low, 4000.0, sample_rate)
    high_band = _one_pole_highpass(hp_from_low, 4000.0, sample_rate)

    # Same for mid
    lp_mid = _one_pole_lowpass(mid, 250.0, sample_rate)
    hp_mid_from_low = _one_pole_highpass(mid, 250.0, sample_rate)
    mid_mid_band = _one_pole_lowpass(hp_mid_from_low, 4000.0, sample_rate)
    high_mid_band = _one_pole_highpass(hp_mid_from_low, 4000.0, sample_rate)

    band_sides = [lp_side, mid_band, high_band]
    band_mids = [lp_mid, mid_mid_band, high_mid_band]

    for idx, (name, cutoff) in enumerate(region_cutoffs):
        bs = band_sides[idx]
        bm = band_mids[idx]
        bs_rms = _m.sqrt(sum(bs[i] * bs[i] for i in range(analysis_len)) / analysis_len)
        bm_rms = _m.sqrt(sum(bm[i] * bm[i] for i in range(analysis_len)) / analysis_len)
        w = bs_rms / bm_rms if bm_rms > 0 else 0.0
        regions.append({
            "name": name,
            "freq_range": "20-250 Hz" if name == "low" else ("250-4000 Hz" if name == "mid" else "4000+ Hz"),
            "width": round(w, 3),
            "side_rms": round(bs_rms, 6),
            "mid_rms": round(bm_rms, 6),
        })

    return {
        "is_stereo": True,
        "stereo_width": round(stereo_width, 3),
        "lr_balance": round(lr_balance, 3),
        "phase_correlation": round(phase_corr, 3),
        "mid_rms": round(mid_rms, 6),
        "side_rms": round(side_rms, 6),
        "left_rms": round(left_rms, 6),
        "right_rms": round(right_rms, 6),
        "mono_compatible": mono_compatible,
        "phase_issues_pct": round(phase_issues_pct, 1),
        "regions": regions,
        "frames_analyzed": analysis_len,
        "sample_rate": sample_rate,
    }


def _analyze_dynamics(channels: list, sample_rate: int) -> dict:
    """Dynamics analysis — crest factor, loudness range, transient density, segment RMS.

    Pure Python (no numpy):
    1. Mix to mono
    2. Global peak and RMS → crest factor (peak/RMS ratio in dB)
    3. Short-term RMS (300ms windows, 100ms hop) → loudness contour
    4. Loudness range (LRA): difference between 95th and 10th percentile of RMS windows
    5. Segment RMS: divide track into 10 equal segments, RMS per segment → variation
    6. Transient density: count energy spikes (>2x local average) per second
    7. Dynamic range: max window RMS - min window RMS (in dB)
    8. PLR (Peak-to-Loudness Ratio): true peak dB - LUFS (approximate)

    Returns dict with dynamics descriptors and compression suggestions.
    """
    import math as _m

    if not channels or not channels[0]:
        return {
            "crest_factor_db": 0.0, "loudness_range_db": 0.0,
            "transient_density": 0.0, "dynamic_range_db": 0.0,
            "segment_rms variation": 0.0, "segments": [],
            "sample_rate": sample_rate,
        }

    n_frames = len(channels[0])
    n_ch = len(channels)

    # 1. Mix to mono
    mono = [sum(channels[c][i] for c in range(n_ch)) / n_ch for i in range(n_frames)]

    # 2. Global peak and RMS
    peak = max(abs(s) for s in mono)
    analysis_len = min(n_frames, sample_rate * 30)
    rms = _m.sqrt(sum(mono[i] * mono[i] for i in range(analysis_len)) / analysis_len)

    peak_db = 20 * _m.log10(peak) if peak > 0 else -120.0
    rms_db = 20 * _m.log10(rms) if rms > 0 else -120.0
    crest_factor_db = peak_db - rms_db

    # 3. Short-term RMS windows (300ms, 100ms hop)
    win_size = int(0.3 * sample_rate)
    hop_size = int(0.1 * sample_rate)
    if win_size == 0 or hop_size == 0 or n_frames < win_size:
        return {
            "crest_factor_db": round(crest_factor_db, 1),
            "loudness_range_db": 0.0,
            "transient_density": 0.0,
            "dynamic_range_db": 0.0,
            "segment_variation_db": 0.0,
            "segments": [],
            "peak_db": round(peak_db, 1),
            "rms_db": round(rms_db, 1),
            "sample_rate": sample_rate,
            "frames_analyzed": analysis_len,
        }

    rms_windows = []
    pos = 0
    while pos + win_size <= n_frames:
        wr = _m.sqrt(sum(mono[pos + j] * mono[pos + j] for j in range(win_size)) / win_size)
        rms_windows.append(wr)
        pos += hop_size

    if not rms_windows:
        return {
            "crest_factor_db": round(crest_factor_db, 1),
            "loudness_range_db": 0.0,
            "transient_density": 0.0,
            "dynamic_range_db": 0.0,
            "segment_variation_db": 0.0,
            "segments": [],
            "peak_db": round(peak_db, 1),
            "rms_db": round(rms_db, 1),
            "sample_rate": sample_rate,
            "frames_analyzed": analysis_len,
        }

    # Convert to dB
    rms_db_windows = [20 * _m.log10(r) if r > 0 else -120.0 for r in rms_windows]

    # 4. Loudness range: 95th - 10th percentile
    sorted_db = sorted(rms_db_windows)
    n_w = len(sorted_db)
    p10_idx = int(n_w * 0.10)
    p95_idx = int(n_w * 0.95)
    lra_db = sorted_db[p95_idx] - sorted_db[p10_idx] if p95_idx > p10_idx else 0.0

    # 5. Dynamic range: max - min window RMS
    max_win_db = max(rms_db_windows)
    min_win_db = min(rms_db_windows)
    dyn_range_db = max_win_db - min_win_db

    # 6. Segment RMS: divide into 10 segments
    n_segments = 10
    seg_size = n_frames // n_segments
    segments = []
    if seg_size > 0:
        for s in range(n_segments):
            start = s * seg_size
            end = min(start + seg_size, n_frames)
            seg_rms = _m.sqrt(sum(mono[i] * mono[i] for i in range(start, end)) / (end - start))
            seg_db = 20 * _m.log10(seg_rms) if seg_rms > 0 else -120.0
            segments.append({
                "index": s,
                "start_sec": round(start / sample_rate, 1),
                "end_sec": round(end / sample_rate, 1),
                "rms_db": round(seg_db, 1),
            })

    # Segment variation
    seg_dbs = [s["rms_db"] for s in segments] if segments else []
    seg_variation = max(seg_dbs) - min(seg_dbs) if seg_dbs else 0.0

    # 7. Transient density: count energy spikes per second
    # Spike = sample where |amplitude| > 2 * local RMS (within 50ms window)
    local_win = int(0.05 * sample_rate)
    transient_count = 0
    for i in range(local_win, analysis_len - local_win, hop_size):
        local_rms = _m.sqrt(sum(mono[j] * mono[j] for j in range(i - local_win, i + local_win)) / (2 * local_win))
        if local_rms > 0:
            # Check if this window has a spike
            local_peak = max(abs(mono[j]) for j in range(i - local_win, i + local_win))
            if local_peak > 2.0 * local_rms:
                transient_count += 1

    duration_sec = analysis_len / sample_rate
    transient_density = transient_count / duration_sec if duration_sec > 0 else 0.0

    return {
        "crest_factor_db": round(crest_factor_db, 1),
        "loudness_range_db": round(lra_db, 1),
        "dynamic_range_db": round(dyn_range_db, 1),
        "transient_density": round(transient_density, 2),
        "transient_count": transient_count,
        "segment_variation_db": round(seg_variation, 1),
        "segments": segments,
        "peak_db": round(peak_db, 1),
        "rms_db": round(rms_db, 1),
        "max_window_db": round(max_win_db, 1),
        "min_window_db": round(min_win_db, 1),
        "n_windows": len(rms_windows),
        "sample_rate": sample_rate,
        "frames_analyzed": analysis_len,
    }


def _resolve_audio_file(filename: str, export_dir: str = None) -> str | None:
    """Resolve audio filename to absolute path — DRY helper for all analysis tools.

    Tries: export_dir/filename.wav → export_dir/filename → abs → cwd/filename.
    Returns absolute path or None.
    """
    import os as _os
    if export_dir is None:
        export_dir = _os.environ.get("OPENDAW_EXPORT_DIR",
                                      _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "exports"))
    fname = filename if filename.endswith(".wav") else filename + ".wav"
    fpath = _os.path.join(export_dir, fname)
    if _os.path.exists(fpath):
        return fpath
    fpath = filename if _os.path.isabs(filename) else _os.path.join(_os.getcwd(), filename)
    return fpath if _os.path.exists(fpath) else None


def _load_wav_for_analysis(filename: str) -> tuple:
    """Load + parse WAV file for analysis — DRY helper.

    Returns (channels, sample_rate, fpath) or raises FileNotFoundError.
    """
    fpath = _resolve_audio_file(filename)
    if fpath is None:
        raise FileNotFoundError(f"Audio file not found: {filename}")
    with open(fpath, "rb") as f:
        raw = f.read()
    wav = _parse_wav(raw)
    return wav["channels"], wav["sample_rate"], fpath
