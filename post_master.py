#!/usr/bin/env python3
"""Post-production mastering — professional multiband architecture.

Pipeline: crossover split → per-band EQ/sat/comp → recombine →
stereo widen → lookahead brickwall limiter → true peak verify →
post-limiter air polish → LUFS verify.

Usage:
  venv/bin/python post_master.py <input.wav> [output_name]
"""
import sys
import os
import numpy as np
from scipy import signal as scipy_signal
from scipy import ndimage as scipy_ndimage
from scipy.io import wavfile
import pyloudnorm as pyln


# ─── I/O ───────────────────────────────────────────────────────────────

def read_wav(path):
    sr, data = wavfile.read(path)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.float64:
        data = data.astype(np.float32)
    elif data.dtype != np.float32:
        data = data.astype(np.float32) / np.max(np.abs(data))
    if data.ndim == 1:
        data = np.stack([data, data], axis=0)
    else:
        data = data.T
    return data, sr


def write_wav(path, data, sr):
    data = np.clip(data, -1.0, 1.0)
    wavfile.write(path, sr, data.T.astype(np.float32))


# ─── Crossovers (Linkwitz-Riley, phase-coherent) ───────────────────────

def lr_crossover(data, sr, freq, order=4):
    """Linkwitz-Riley crossover (4th order = -6dB at crossover, phase-coherent).
    Returns (low, high)."""
    w0 = freq / (sr / 2)
    n = order // 2
    b_lp, a_lp = scipy_signal.butter(n, w0, btype="low")
    b_hp, a_hp = scipy_signal.butter(n, w0, btype="high")
    low = scipy_signal.filtfilt(b_lp, a_lp, data, axis=1)
    high = scipy_signal.filtfilt(b_hp, a_hp, data, axis=1)
    return low, high


def multiband_split(data, sr, freqs=(200, 2000, 8000)):
    """Split into N+1 bands using cascaded LR4 crossovers.
    freqs=(200, 2000, 8000) → sub, bass, mid, high."""
    bands = []
    remaining = data
    for f in freqs:
        low, remaining = lr_crossover(remaining, sr, f)
        bands.append(low)
    bands.append(remaining)
    return bands


def multiband_recombine(bands):
    """Sum bands back together (phase-coherent due to LR4)."""
    return np.sum(bands, axis=0)


# ─── EQ ────────────────────────────────────────────────────────────────

def high_shelf(data, sr, freq, gain_db):
    w0 = freq / (sr / 2)
    if w0 >= 1.0:
        return data
    gain_lin = 10 ** (gain_db / 20)
    b, a = scipy_signal.butter(2, w0, btype="high")
    filtered = scipy_signal.filtfilt(b, a, data, axis=1)
    return data + filtered * (gain_lin - 1)


def bell_eq(data, sr, freq, gain_db, q=1.0):
    w0 = freq / (sr / 2)
    if w0 >= 1.0 or w0 <= 0:
        return data
    gain_lin = 10 ** (gain_db / 20)
    bw = w0 / q
    low = max(0.001, w0 - bw / 2)
    high = min(0.999, w0 + bw / 2)
    b, a = scipy_signal.butter(2, [low, high], btype="band")
    filtered = scipy_signal.filtfilt(b, a, data, axis=1)
    return data + filtered * (gain_lin - 1)


def low_shelf(data, sr, freq, gain_db):
    """Low-shelf EQ boost/cut."""
    w0 = freq / (sr / 2)
    if w0 >= 1.0:
        return data
    gain_lin = 10 ** (gain_db / 20)
    b, a = scipy_signal.butter(2, w0, btype="low")
    filtered = scipy_signal.filtfilt(b, a, data, axis=1)
    return data + filtered * (gain_lin - 1)


# ─── Dynamics ──────────────────────────────────────────────────────────

def compressor(data, threshold=0.5, ratio=2.0, attack=0.01, release=0.1, sr=48000, mix=1.0):
    """Vectorized compressor via scipy.signal.lfilter envelope follower."""
    attack_samp = max(1, int(sr * attack))
    release_samp = max(1, int(sr * release))
    abs_data = np.abs(data)

    at_b = [1.0 - np.exp(-1 / attack_samp)]
    at_a = [1, -np.exp(-1 / attack_samp)]
    rl_b = [1.0 - np.exp(-1 / release_samp)]
    rl_a = [1, -np.exp(-1 / release_samp)]

    env = np.zeros_like(data)
    for ch in range(data.shape[0]):
        at_env = scipy_signal.lfilter(at_b, at_a, abs_data[ch])
        rl_env = scipy_signal.lfilter(rl_b, rl_a, abs_data[ch])
        env[ch] = np.maximum(at_env, rl_env)

    over = np.maximum(env - threshold, 0)
    gain_reduction = 1 / (1 + over * (ratio - 1) / threshold)
    compressed = data * gain_reduction
    return data * (1 - mix) + compressed * mix


def lookahead_limiter(data, ceiling=0.891, lookahead_ms=3.0, release_ms=80.0, sr=48000):
    """Lookahead brickwall limiter — catches transients smoothly.
    Uses scipy maximum_filter1d for vectorized peak-hold."""
    lookahead = max(1, int(sr * lookahead_ms / 1000))
    release_samp = max(1, int(sr * release_ms / 1000))
    release_coef = np.exp(-1 / release_samp)

    abs_data = np.abs(data)
    env = np.zeros_like(data)

    for ch in range(data.shape[0]):
        # Peak-hold via maximum_filter1d (vectorized)
        # Window = lookahead, gives max of upcoming samples
        peak_hold = scipy_ndimage.maximum_filter1d(
            abs_data[ch], size=lookahead, mode="constant", cval=0.0
        )
        # Exponential release smoothing via lfilter
        rl_b = [1.0 - release_coef]
        rl_a = [1, -release_coef]
        env[ch] = scipy_signal.lfilter(rl_b, rl_a, peak_hold)

    # Gain reduction: only where envelope exceeds ceiling
    gain = np.where(env > ceiling, ceiling / (env + 1e-10), 1.0)

    # Apply gain with lookahead delay
    limited = np.zeros_like(data)
    for ch in range(data.shape[0]):
        delayed = np.zeros(data.shape[1])
        if data.shape[1] > lookahead:
            delayed[lookahead:] = data[ch, :-lookahead]
        limited[ch] = delayed * gain[ch]

    return limited


# ─── Saturation / Enhancement ──────────────────────────────────────────

def tape_saturation(data, drive=0.3, mix=0.5):
    drive_amt = 1 + drive * 3
    driven = np.tanh(data * drive_amt) / np.tanh(drive_amt)
    return data * (1 - mix) + driven * mix


def harmonic_exciter(data, sr, freq=8000, amount=0.3, mix=0.4):
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="high")
    hf = scipy_signal.filtfilt(b, a, data, axis=1)
    harmonic = hf - (hf ** 3) / 3 * amount
    return data * (1 - mix) + (data + harmonic * amount) * mix


def psychoacoustic_bass(data, sr, freq=60, amount=0.25, mix=0.3):
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="low")
    sub = scipy_signal.filtfilt(b, a, data, axis=1)
    h2 = sub ** 2 * np.sign(sub) * amount
    h3 = sub ** 3 * amount * 0.5
    b2, a2 = scipy_signal.butter(2, [80 / (sr / 2), 300 / (sr / 2)], btype="band")
    harmonics = scipy_signal.filtfilt(b2, a2, (h2 + h3), axis=1)
    return data + harmonics * mix


# ─── Stereo ────────────────────────────────────────────────────────────

def stereo_widen(data, amount=0.4):
    if data.shape[0] != 2:
        return data
    mid = (data[0] + data[1]) * 0.5
    side = (data[0] - data[1]) * 0.5
    side = side * (1.0 + amount)
    return np.stack([mid + side, mid - side], axis=0)


# ─── True Peak Measurement ─────────────────────────────────────────────

def true_peak_measure(data, sr):
    """Measure true peak with 4x oversampling."""
    upsampled = scipy_signal.resample_poly(data.flatten(), 4, 1) if data.ndim == 1 else \
        np.array([scipy_signal.resample_poly(data[ch], 4, 1) for ch in range(data.shape[0])])
    peak = np.max(np.abs(upsampled))
    return 20 * np.log10(peak + 1e-10), peak


# ─── LUFS Targeting ────────────────────────────────────────────────────

def lufs_normalize(data, target_lufs, sr):
    """Normalize to target LUFS with iterative correction."""
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data.T)
    gain_db = target_lufs - lufs
    data = data * (10 ** (gain_db / 20))
    # Second pass for accuracy
    lufs2 = meter.integrated_loudness(data.T)
    correction = target_lufs - lufs2
    if abs(correction) > 0.1:
        data = data * (10 ** (correction / 20))
    return data, lufs, gain_db + correction


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = os.path.join(os.path.dirname(__file__), "exports", "last_light_of_summer.wav")

    if len(sys.argv) > 2:
        output_name = sys.argv[2]
    else:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{base}_mastered"

    print(f"Input: {input_path}")

    data, sr = read_wav(input_path)
    dur = data.shape[1] / sr
    print(f"  Duration: {dur:.1f}s, SR: {sr}, Channels: {data.shape[0]}")
    print(f"  Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    meter = pyln.Meter(sr)
    lufs_in = meter.integrated_loudness(data.T)
    print(f"  Input LUFS: {lufs_in:.2f}")

    # ═══ Step 1: Pre-normalize to -14 LUFS ═══
    print("\n=== Step 1: Pre-normalize to -14 LUFS ===")
    data, lufs_pre, gain_pre = lufs_normalize(data, -14.0, sr)
    print(f"  Gain: {gain_pre:+.1f} dB, LUFS: {lufs_pre:.2f} → -14.00")

    # ═══ Step 2: Multiband split (LR4 crossovers) ═══
    print("\n=== Step 2: Multiband split (200/2000/8000 Hz) ===")
    bands = multiband_split(data, sr, freqs=(200, 2000, 8000))
    print("  Bands: sub(<200), bass(200-2k), mid(2k-8k), high(>8k)")

    # ═══ Step 3: Per-band processing ═══
    print("\n=== Step 3: Per-band processing ===")

    # Sub band (<200Hz): psychoacoustic bass + parallel comp for density
    print("  sub: psychoacoustic bass + parallel comp (dense sub)")
    bands[0] = psychoacoustic_bass(bands[0], sr, freq=60, amount=0.15, mix=0.2)
    # Parallel compression: dry + heavily compressed for density without losing punch
    sub_compressed = compressor(bands[0], threshold=0.2, ratio=4.0, attack=0.005, release=0.2, sr=sr, mix=1.0)
    bands[0] = bands[0] * 0.6 + sub_compressed * 0.4
    # Mono collapse (bass should be centered — pro standard)
    mono_sub = (bands[0][0] + bands[0][1]) * 0.5
    bands[0] = np.stack([mono_sub, mono_sub], axis=0)

    # Bass band (200-2k): mud cut + lowmid fill + tape sat
    print("  bass: mud cut -2dB @ 250 + lowmid +3dB @ 350 + tape sat")
    bands[1] = bell_eq(bands[1], sr, 250, -2.0, q=1.2)
    bands[1] = bell_eq(bands[1], sr, 350, 3.0, q=1.0)
    bands[1] = tape_saturation(bands[1], drive=0.15, mix=0.25)
    # Partial mono collapse (keep some stereo on bass, but centered)
    mid_b = (bands[1][0] + bands[1][1]) * 0.5
    side_b = (bands[1][0] - bands[1][1]) * 0.5
    bands[1] = np.stack([mid_b + side_b * 0.3, mid_b - side_b * 0.3], axis=0)

    # Mid band (2k-8k): presence boost + parallel comp for density
    print("  mid: presence +3dB @ 3k + +2dB @ 5k + parallel comp")
    bands[2] = bell_eq(bands[2], sr, 3000, 3.0, q=1.0)
    bands[2] = bell_eq(bands[2], sr, 5000, 2.0, q=1.0)
    # Parallel compression on mid — brings presence forward
    mid_compressed = compressor(bands[2], threshold=0.3, ratio=3.0, attack=0.005, release=0.15, sr=sr, mix=1.0)
    bands[2] = bands[2] * 0.5 + mid_compressed * 0.5

    # High band (>8k): air boost + harmonic exciter — NO limiter here!
    print("  high: high-shelf +4dB @ 8k + exciter + bell +3dB @ 12k")
    bands[3] = high_shelf(bands[3], sr, 8000, 4.0)
    bands[3] = harmonic_exciter(bands[3], sr, freq=8000, amount=0.25, mix=0.4)
    bands[3] = bell_eq(bands[3], sr, 12000, 3.0, q=0.7)
    # Widen ONLY high band (air in stereo, bass in mono)
    bands[3] = stereo_widen(bands[3], amount=0.5)

    # ═══ Step 4: Recombine + glue comp on full mix ═══
    print("\n=== Step 4: Recombine bands + glue comp ===")
    data = multiband_recombine(bands)
    # Light glue compression on full mix (binds bands together)
    data = compressor(data, threshold=0.5, ratio=1.5, attack=0.02, release=0.15, sr=sr, mix=0.3)
    lufs_recomb = meter.integrated_loudness(data.T)
    print(f"  LUFS after recombine + glue: {lufs_recomb:.2f}")

    # ═══ Step 5: Stereo widen (M/S +30% — high band already widened) ═══
    print("\n=== Step 5: Stereo widen (M/S +30%) ===")
    data = stereo_widen(data, amount=0.3)

    # ═══ Step 6: Re-normalize to -14 LUFS ═══
    print("\n=== Step 6: Re-normalize to -14 LUFS ===")
    data, _, gain_recomb = lufs_normalize(data, -14.0, sr)
    print(f"  Gain: {gain_recomb:+.1f} dB")

    # ═══ Step 7: Lookahead brickwall limiter ═══
    print("\n=== Step 7: Lookahead brickwall limiter ===")
    data = lookahead_limiter(data, ceiling=0.891, lookahead_ms=3.0, release_ms=80.0, sr=sr)

    # ═══ Step 8: Final LUFS correction ═══
    print("\n=== Step 8: Final LUFS correction ===")
    lufs_final = meter.integrated_loudness(data.T)
    correction = -14.0 - lufs_final
    if abs(correction) > 0.1:
        data = data * (10 ** (correction / 20))
        # Soft clip if correction pushed above ceiling
        peak = np.max(np.abs(data))
        if peak > 0.891:
            data = np.tanh(data / 0.891) * 0.891
    lufs_final = meter.integrated_loudness(data.T)
    print(f"  LUFS: {lufs_final:.2f}")

    # ═══ Final report ═══
    peak_out = np.max(np.abs(data))
    tp_db, tp_lin = true_peak_measure(data, sr)
    print("\n=== FINAL ===")
    print(f"  LUFS: {lufs_in:.2f} → {lufs_final:.2f}")
    print(f"  Sample peak: {20*np.log10(peak_out+1e-10):.2f} dBFS ({peak_out:.4f})")
    print(f"  True peak (4x OS): {tp_db:.2f} dBTP")

    # Write
    output_path = os.path.join(os.path.dirname(__file__), "exports", f"{output_name}.wav")
    write_wav(output_path, data, sr)
    size_mb = os.path.getsize(output_path) / 1048576
    print(f"\nOutput: {output_path} ({size_mb:.1f}MB)")

    import shutil
    desktop = f"/mnt/c/Users/admin/Desktop/{output_name}.wav"
    shutil.copy2(output_path, desktop)
    print(f"Copied to: {desktop}")


if __name__ == "__main__":
    main()
