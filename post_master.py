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

def tube_saturation(data, drive=0.3, mix=0.5):
    """Tube-style saturation — emphasizes EVEN harmonics (2nd, 4th).
    Warmer, rounder than tanh (which emphasizes odd harmonics).
    Uses x - a*x² curve for asymmetric (tube-like) distortion."""
    drive_amt = drive * 2
    # Asymmetric waveshaping: even harmonics
    driven = data - drive_amt * data ** 2 * np.sign(data) * 0.5
    # Normalize to prevent level change
    norm = np.max(np.abs(driven) + 1e-10)
    if norm > 1.0:
        driven = driven / norm * np.max(np.abs(data))
    return data * (1 - mix) + driven * mix


def soft_knee_limiter(data, ceiling=0.84, knee_db=3.0, sr=48000, lookahead_ms=3.0, release_ms=100.0):
    """Soft knee limiter — gradual compression curve near ceiling.
    More transparent than hard clip. Knee starts below ceiling."""
    ceiling_lin = ceiling
    knee_lin = ceiling / (10 ** (knee_db / 20))  # knee starts here

    lookahead = max(1, int(sr * lookahead_ms / 1000))
    release_samp = max(1, int(sr * release_ms / 1000))
    release_coef = np.exp(-1 / release_samp)

    abs_data = np.abs(data)
    env = np.zeros_like(data)

    for ch in range(data.shape[0]):
        peak_hold = scipy_ndimage.maximum_filter1d(
            abs_data[ch], size=lookahead, mode="constant", cval=0.0
        )
        rl_b = [1.0 - release_coef]
        rl_a = [1, -release_coef]
        env[ch] = scipy_signal.lfilter(rl_b, rl_a, peak_hold)

    # Soft knee gain reduction
    # Below knee: no reduction
    # Between knee and ceiling: gradual (quadratic) reduction
    # Above ceiling: full reduction to ceiling
    gain = np.ones_like(env)
    in_knee = (env > knee_lin) & (env <= ceiling_lin)
    over = env > ceiling_lin

    # Quadratic soft knee: 1 - ((env - knee) / (ceiling - knee))² * (1 - ceiling/env)
    knee_range = ceiling_lin - knee_lin
    if knee_range > 0:
        ratio = (env[in_knee] - knee_lin) / knee_range
        gain[in_knee] = 1 - ratio ** 2 * (1 - ceiling_lin / (env[in_knee] + 1e-10))

    gain[over] = ceiling_lin / (env[over] + 1e-10)

    # Apply with lookahead delay
    limited = np.zeros_like(data)
    for ch in range(data.shape[0]):
        delayed = np.zeros(data.shape[1])
        if data.shape[1] > lookahead:
            delayed[lookahead:] = data[ch, :-lookahead]
        limited[ch] = delayed * gain[ch]

    return limited


def ms_eq(data, sr, side_hp_freq=200):
    """M/S EQ — highpass the side channel to tighten bass in stereo.
    Bass frequencies should be mono (centered). Side HPF removes
    stereo information below side_hp_freq, tightening the image."""
    if data.shape[0] != 2:
        return data
    mid = (data[0] + data[1]) * 0.5
    side = (data[0] - data[1]) * 0.5
    # Highpass side channel
    w0 = side_hp_freq / (sr / 2)
    b, a = scipy_signal.butter(2, w0, btype="high")
    side = scipy_signal.filtfilt(b, a, side)
    return np.stack([mid + side, mid - side], axis=0)


def stereo_widen(data, amount=0.4):
    """Widen stereo via M/S processing. amount=0 neutral, 1=max wide."""
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

    # ═══ Step 2: Multiband split (5-band: 200/500/2000/5000/8000 Hz) ═══
    print("\n=== Step 2: Multiband split (200/500/2000/5000/8000 Hz) ===")
    bands = multiband_split(data, sr, freqs=(200, 500, 2000, 5000, 8000))
    print("  Bands: sub(<200), bass(200-500), lowmid(500-2k), presence(2k-5k), high(>8k)")
    # Note: band[3] = 5k-8k (upper-mid), band[4] = >8k (air)
    # 5-band: sub, bass, lowmid, presence, uppermid, air → 6 bands from 5 crossovers
    # Actually: freqs=(200,500,2000,5000,8000) → 6 bands: sub, bass, lowmid, mid, uppermid, air

    # ═══ Step 3: Per-band processing ═══
    print("\n=== Step 3: Per-band processing (6 bands) ===")

    # Sub band (<200Hz): psychoacoustic bass + parallel comp for density
    print("  sub: psychoacoustic bass + parallel comp (dense sub)")
    bands[0] = psychoacoustic_bass(bands[0], sr, freq=60, amount=0.15, mix=0.2)
    sub_compressed = compressor(bands[0], threshold=0.2, ratio=4.0, attack=0.005, release=0.2, sr=sr, mix=1.0)
    bands[0] = bands[0] * 0.6 + sub_compressed * 0.4
    # Mono collapse (bass should be centered — pro standard)
    mono_sub = (bands[0][0] + bands[0][1]) * 0.5
    bands[0] = np.stack([mono_sub, mono_sub], axis=0)

    # Bass band (200-500Hz): mud cut + tape sat
    print("  bass: mud cut -2dB @ 250 + tape sat")
    bands[1] = bell_eq(bands[1], sr, 250, -2.0, q=1.2)
    bands[1] = tape_saturation(bands[1], drive=0.15, mix=0.25)

    # Lowmid band (500-2k): lowmid fill + tape
    print("  lowmid: +3dB @ 700 + tape sat (warmth)")
    bands[2] = bell_eq(bands[2], sr, 700, 3.0, q=1.0)
    bands[2] = tape_saturation(bands[2], drive=0.1, mix=0.2)

    # Presence band (2k-5k): presence boost + tube saturation
    print("  presence: +5dB @ 3k + +4dB @ 4k + +3dB @ 5k + tube sat")
    bands[3] = bell_eq(bands[3], sr, 3000, 5.0, q=1.0)
    bands[3] = bell_eq(bands[3], sr, 4000, 4.0, q=1.0)
    bands[3] = bell_eq(bands[3], sr, 5000, 3.0, q=1.0)
    bands[3] = tube_saturation(bands[3], drive=0.2, mix=0.3)
    # Parallel compression on presence — 60/40 for more forward
    pres_compressed = compressor(bands[3], threshold=0.3, ratio=3.0, attack=0.005, release=0.15, sr=sr, mix=1.0)
    bands[3] = bands[3] * 0.6 + pres_compressed * 0.4

    # Upper-mid band (5k-8k): slight presence boost
    print("  uppermid: +2dB @ 6k (vocal clarity)")
    bands[4] = bell_eq(bands[4], sr, 6000, 2.0, q=1.0)

    # Air band (>8k): air boost + harmonic exciter — isolated!
    print("  air: high-shelf +4dB @ 8k + exciter + bell +3dB @ 12k + widen")
    bands[5] = high_shelf(bands[5], sr, 8000, 4.0)
    bands[5] = harmonic_exciter(bands[5], sr, freq=8000, amount=0.25, mix=0.4)
    bands[5] = bell_eq(bands[5], sr, 12000, 3.0, q=0.7)
    bands[5] = stereo_widen(bands[5], amount=0.5)

    # ═══ Step 4: Recombine + glue comp on full mix ═══
    print("\n=== Step 4: Recombine bands + glue comp ===")
    data = multiband_recombine(bands)
    # Light glue compression on full mix (binds bands together)
    data = compressor(data, threshold=0.5, ratio=1.5, attack=0.02, release=0.15, sr=sr, mix=0.3)
    lufs_recomb = meter.integrated_loudness(data.T)
    print(f"  LUFS after recombine + glue: {lufs_recomb:.2f}")

    # ═══ Step 5: M/S EQ (tighten bass in stereo) + widen ═══
    print("\n=== Step 5: M/S EQ (side HPF 200Hz) + widen +30% ===")
    data = ms_eq(data, sr, side_hp_freq=200)
    data = stereo_widen(data, amount=0.3)

    # ═══ Step 6: Re-normalize to -14 LUFS ═══
    print("\n=== Step 6: Re-normalize to -14 LUFS ===")
    data, _, gain_recomb = lufs_normalize(data, -14.0, sr)
    print(f"  Gain: {gain_recomb:+.1f} dB")

    # ═══ Step 7: Soft knee brickwall limiter ═══
    print("\n=== Step 7: Soft knee limiter (ceiling 0.84, knee 3dB) ===")
    data = soft_knee_limiter(data, ceiling=0.84, knee_db=3.0, sr=sr, lookahead_ms=3.0, release_ms=100.0)

    # ═══ Step 8: Final LUFS correction + brickwall ═══
    print("\n=== Step 8: Final LUFS correction + brickwall ===")
    lufs_final = meter.integrated_loudness(data.T)
    correction = -14.0 - lufs_final
    if abs(correction) > 0.1:
        data = data * (10 ** (correction / 20))
    # Final brickwall: hard clip at ceiling (catches anything LUFS correction raised)
    data = np.clip(data, -0.84, 0.84)
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
