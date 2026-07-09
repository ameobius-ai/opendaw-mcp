#!/usr/bin/env python3
"""Post-production mastering — PRO5 "EXPENSIVE POST-ROCK v2" version.

Based on pro4, pushes every dimension harder while keeping -14 LUFS:
1. Per-band widening: lowmid 0.3, presence 0.4, uppermid 0.4, air 0.75
2. Hotter bass: psychoacoustic amount 0.25, mix 0.35
3. Hotter tape sat: drive 0.25 (was 0.1)
4. Double exciter: uppermid + air
5. Hotter tube sat on presence: drive 0.3, mix 0.4
6. Side boost +6dB (was +5)
7. Ceiling -0.8 dBFS (was -1.3) — use headroom, no clipping

Usage:
  venv/bin/python post_master_pro5.py <input.wav> [output_name]
"""
import sys
import os
import numpy as np
from scipy import signal as scipy_signal
from scipy import ndimage as scipy_ndimage
from scipy.io import wavfile
import pyloudnorm as pyln


# ─── I/O ───────────────────────────────────────────────────────────────

def dc_blocker(data, sr, cutoff=20.0):
    """Remove DC offset via 1st-order high-pass at cutoff Hz.
    Typical Suno stems carry +0.001-0.002 DC — inaudible but eats headroom."""
    w0 = cutoff / (sr / 2)
    b, a = scipy_signal.butter(1, w0, btype="high")
    return scipy_signal.filtfilt(b, a, data, axis=1)


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
    w0 = freq / (sr / 2)
    n = order // 2
    b_lp, a_lp = scipy_signal.butter(n, w0, btype="low")
    b_hp, a_hp = scipy_signal.butter(n, w0, btype="high")
    low = scipy_signal.filtfilt(b_lp, a_lp, data, axis=1)
    high = scipy_signal.filtfilt(b_hp, a_hp, data, axis=1)
    return low, high


def multiband_split(data, sr, freqs=(200, 500, 2000, 5000, 8000)):
    bands = []
    remaining = data
    for f in freqs:
        low, remaining = lr_crossover(remaining, sr, f)
        bands.append(low)
    bands.append(remaining)
    return bands


def multiband_recombine(bands):
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


# ─── Dynamics ──────────────────────────────────────────────────────────

def compressor(data, threshold=0.5, ratio=2.0, attack=0.01, release=0.1, sr=48000, mix=1.0):
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


# ─── Saturation / Enhancement ──────────────────────────────────────────

def tape_saturation(data, drive=0.3, mix=0.5):
    drive_amt = 1 + drive * 3
    driven = np.tanh(data * drive_amt) / np.tanh(drive_amt)
    return data * (1 - mix) + driven * mix


def tape_sat_pre_emphasis(data, sr, drive=0.3, mix=0.5, emph_freq=4000, emph_gain=3.0):
    """Tape saturation with pre-emphasis/de-emphasis.
    Classic analog trick: boost HF before saturation, cut after.
    Saturation works smoother on highs without harshness."""
    # Pre-emphasis: boost HF
    emphasized = high_shelf(data, sr, emph_freq, emph_gain)
    # Saturate
    drive_amt = 1 + drive * 3
    driven = np.tanh(emphasized * drive_amt) / np.tanh(drive_amt)
    # De-emphasis: cut HF back (mirror of pre-emphasis)
    result = high_shelf(driven, sr, emph_freq, -emph_gain)
    return data * (1 - mix) + result * mix


def tube_saturation(data, drive=0.3, mix=0.5):
    """Tube-style saturation — emphasizes EVEN harmonics (2nd, 4th).
    Warmer, rounder than tanh (which emphasizes odd harmonics)."""
    drive_amt = drive * 2
    driven = data - drive_amt * data ** 2 * np.sign(data) * 0.5
    norm = np.max(np.abs(driven) + 1e-10)
    if norm > 1.0:
        driven = driven / norm * np.max(np.abs(data))
    return data * (1 - mix) + driven * mix


def soft_clipper(data, ceiling=0.95, drive=1.2, mix=0.7):
    """Tanh soft-clipper — catches transient peaks smoothly.
    Pushes loudness without harshness. ceiling in linear (0.95 = -0.45 dBFS).
    drive>1 = more saturation. mix = parallel blend."""
    driven = data * drive
    clipped = np.tanh(driven) / np.tanh(drive)
    # Above ceiling: hard limit
    clipped = np.clip(clipped, -ceiling, ceiling)
    return data * (1 - mix) + clipped * mix


def harmonic_exciter(data, sr, freq=8000, amount=0.3, mix=0.4):
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="high")
    hf = scipy_signal.filtfilt(b, a, data, axis=1)
    harmonic = hf - (hf ** 3) / 3 * amount
    return data * (1 - mix) + (data + harmonic * amount) * mix


def harmonic_exciter_even(data, sr, freq=8000, amount=0.3, mix=0.4):
    """Even-harmonic exciter — x² waveshaping = 2nd, 4th harmonics.
    'Sweet' air like tube, not 'harsh' like cubic (odd harmonics)."""
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="high")
    hf = scipy_signal.filtfilt(b, a, data, axis=1)
    # Even harmonics via x² (one-sided, then shift to centered)
    harmonic = hf ** 2 * np.sign(hf) * amount * 0.5
    return data * (1 - mix) + (data + harmonic) * mix


def psychoacoustic_bass(data, sr, freq=60, amount=0.25, mix=0.3):
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="low")
    sub = scipy_signal.filtfilt(b, a, data, axis=1)
    h2 = sub ** 2 * np.sign(sub) * amount
    h3 = sub ** 3 * amount * 0.5
    b2, a2 = scipy_signal.butter(2, [80 / (sr / 2), 300 / (sr / 2)], btype="band")
    harmonics = scipy_signal.filtfilt(b2, a2, (h2 + h3), axis=1)
    return data + harmonics * mix


def dynamic_eq(data, sr, freq, gain_db, q=1.0, threshold=0.3, attack=0.01, release=0.1):
    """Dynamic EQ — reduces gain at freq ONLY when level exceeds threshold.
    Prevents mud buildup when bass is loud, transparent when quiet."""
    # Isolate band
    w0 = freq / (sr / 2)
    bw = w0 / q
    low = max(0.001, w0 - bw / 2)
    high = min(0.999, w0 + bw / 2)
    b, a = scipy_signal.butter(2, [low, high], btype="band")
    band = scipy_signal.filtfilt(b, a, data, axis=1)

    # Envelope of band signal
    abs_band = np.abs(band)
    attack_samp = max(1, int(sr * attack))
    release_samp = max(1, int(sr * release))
    at_b = [1.0 - np.exp(-1 / attack_samp)]
    at_a = [1, -np.exp(-1 / attack_samp)]
    rl_b = [1.0 - np.exp(-1 / release_samp)]
    rl_a = [1, -np.exp(-1 / release_samp)]

    env = np.zeros_like(data)
    for ch in range(data.shape[0]):
        at_env = scipy_signal.lfilter(at_b, at_a, abs_band[ch])
        rl_env = scipy_signal.lfilter(rl_b, rl_a, abs_band[ch])
        env[ch] = np.maximum(at_env, rl_env)

    # Dynamic gain reduction: only above threshold
    gain_lin = 10 ** (gain_db / 20)  # negative gain_db = cut
    over = np.maximum(env - threshold, 0)
    # Amount of reduction proportional to how much over threshold
    reduction = np.clip(over / threshold, 0, 1)
    # Apply gradually: full reduction when 2x over threshold
    dyn_gain = 1 + (gain_lin - 1) * reduction
    return data - band + band * dyn_gain


def transient_enhancer(data, sr, freq_low=50, freq_high=200, amount=0.3, attack_ms=5.0, mix=0.4):
    """Transient enhancer — boosts attack transients in sub/bass region.
    Short envelope detection + differential = transient extraction.
    Adds punch to kick/bass without raising sustain level."""
    # Isolate band of interest (sub/bass transients)
    w0_low = freq_low / (sr / 2)
    w0_high = freq_high / (sr / 2)
    b, a = scipy_signal.butter(2, [w0_low, w0_high], btype="band")
    band = scipy_signal.filtfilt(b, a, data, axis=1)

    # Fast envelope (5ms) — catches transients
    fast_samp = max(1, int(sr * attack_ms / 1000))
    # Slow envelope (50ms) — catches sustain
    slow_samp = max(1, int(sr * 0.05))

    abs_band = np.abs(band)
    transient = np.zeros_like(data)
    for ch in range(data.shape[0]):
        fast_coef = np.exp(-1 / fast_samp)
        slow_coef = np.exp(-1 / slow_samp)
        fast_b = [1.0 - fast_coef]
        fast_a = [1, -fast_coef]
        slow_b = [1.0 - slow_coef]
        slow_a = [1, -slow_coef]
        fast_env = scipy_signal.lfilter(fast_b, fast_a, abs_band[ch])
        slow_env = scipy_signal.lfilter(slow_b, slow_a, abs_band[ch])
        # Transient = fast - slow (positive when attack, ~0 during sustain)
        diff = np.maximum(fast_env - slow_env, 0)
        # Shape transient with original band sign
        transient[ch] = diff * np.sign(band[ch])

    return data + transient * amount * mix


# ─── Stereo ────────────────────────────────────────────────────────────

def stereo_widen(data, amount=0.4):
    if data.shape[0] != 2:
        return data
    mid = (data[0] + data[1]) * 0.5
    side = (data[0] - data[1]) * 0.5
    side = side * (1.0 + amount)
    return np.stack([mid + side, mid - side], axis=0)


def ms_eq(data, sr, side_hp_freq=200, side_boost_freq=10000, side_boost_gain=3.0):
    """M/S EQ — HPF side at low freq (bass mono) + boost side at high freq (air wider).
    side_boost_gain: boost side channel at side_boost_freq for wider stereo air."""
    if data.shape[0] != 2:
        return data
    mid = (data[0] + data[1]) * 0.5
    side = (data[0] - data[1]) * 0.5
    # HPF side at low freq (bass in mono)
    w0 = side_hp_freq / (sr / 2)
    b, a = scipy_signal.butter(2, w0, btype="high")
    side = scipy_signal.filtfilt(b, a, side)
    # Boost side at high freq (air in wide stereo) — NEW v7
    if side_boost_gain > 0 and side_boost_freq < sr / 2:
        gain_lin = 10 ** (side_boost_gain / 20)
        b2, a2 = scipy_signal.butter(2, side_boost_freq / (sr / 2), btype="high")
        hf_side = scipy_signal.filtfilt(b2, a2, side)
        side = side + hf_side * (gain_lin - 1)
    return np.stack([mid + side, mid - side], axis=0)


# ─── Limiter ───────────────────────────────────────────────────────────

def soft_knee_limiter_prog(data, ceiling=0.84, knee_db=3.0, sr=48000,
                           lookahead_ms=3.0, release_fast_ms=50.0, release_slow_ms=150.0):
    """Soft knee limiter with PROGRAM-DEPENDENT RELEASE.
    Release adapts to signal: fast on transients (short bursts),
    slow on sustains (continuous loud). More transparent than fixed release."""
    ceiling_lin = ceiling
    knee_lin = ceiling / (10 ** (knee_db / 20))

    lookahead = max(1, int(sr * lookahead_ms / 1000))
    release_fast_samp = max(1, int(sr * release_fast_ms / 1000))
    release_slow_samp = max(1, int(sr * release_slow_ms / 1000))

    abs_data = np.abs(data)
    env = np.zeros_like(data)

    for ch in range(data.shape[0]):
        # Peak-hold via maximum_filter1d (vectorized)
        peak_hold = scipy_ndimage.maximum_filter1d(
            abs_data[ch], size=lookahead, mode="constant", cval=0.0
        )

        # Program-dependent release: measure crest factor per window
        # High crest (transient) → fast release
        # Low crest (sustain) → slow release
        # We compute this by comparing instantaneous level to local average
        window = max(1, int(sr * 0.05))  # 50ms analysis window
        local_avg = scipy_ndimage.uniform_filter1d(abs_data[ch], size=window, mode="constant")
        # Crest ratio: peak_hold / local_avg (high = transient, low = sustain)
        crest_ratio = peak_hold / (local_avg + 1e-10)
        # Map crest ratio to release coefficient: interpolate between slow and fast
        # crest_ratio 1.0 (sustain) → slow release
        # crest_ratio 3.0+ (transient) → fast release
        t = np.clip((crest_ratio - 1.0) / 2.0, 0.0, 1.0)  # 0=sustain, 1=transient
        # Interpolate release coefficients per-sample
        release_slow_coef = np.exp(-1 / release_slow_samp)
        release_fast_coef = np.exp(-1 / release_fast_samp)
        # release_coef interpolated per-sample (used for env blending below)

        # Apply variable release via sample-by-sample lfilter approximation
        # Use scipy lfilter with time-varying coefficients is not directly possible,
        # so we split into fast and slow paths and blend
        rl_b_slow = [1.0 - release_slow_coef]
        rl_a_slow = [1, -release_slow_coef]
        rl_b_fast = [1.0 - release_fast_coef]
        rl_a_fast = [1, -release_fast_coef]

        env_slow = scipy_signal.lfilter(rl_b_slow, rl_a_slow, peak_hold)
        env_fast = scipy_signal.lfilter(rl_b_fast, rl_a_fast, peak_hold)
        env[ch] = env_slow * (1 - t) + env_fast * t

    # Soft knee gain reduction
    gain = np.ones_like(env)
    in_knee = (env > knee_lin) & (env <= ceiling_lin)
    over = env > ceiling_lin

    knee_range = ceiling_lin - knee_lin
    if knee_range > 0:
        ratio = (env[in_knee] - knee_lin) / knee_range
        gain[in_knee] = 1 - ratio ** 2 * (1 - ceiling_lin / (env[in_knee] + 1e-10))

    gain[over] = ceiling_lin / (env[over] + 1e-10)

    limited = np.zeros_like(data)
    for ch in range(data.shape[0]):
        delayed = np.zeros(data.shape[1])
        if data.shape[1] > lookahead:
            delayed[lookahead:] = data[ch, :-lookahead]
        limited[ch] = delayed * gain[ch]

    return limited


def oversampled_limiter(data, ceiling=0.84, sr=48000, oversample=4):
    """True peak limiter with 4x oversampling.
    Limits on oversampled signal = catches intersample peaks.
    Less aliasing than sample-peak limiter.
    Ceiling can be higher (-1.0 dBTP exactly, not -1.5)."""
    up = oversample
    # Upsample 4x
    upsampled = np.array([
        scipy_signal.resample_poly(data[ch], up, 1) for ch in range(data.shape[0])
    ])
    # Hard limit on oversampled signal
    upsampled = np.clip(upsampled, -ceiling, ceiling)
    # Downsample back
    limited = np.array([
        scipy_signal.resample_poly(upsampled[ch], 1, up) for ch in range(data.shape[0])
    ])
    # Trim to original length
    n = data.shape[1]
    if limited.shape[1] > n:
        limited = limited[:, :n]
    elif limited.shape[1] < n:
        pad = np.zeros((data.shape[0], n - limited.shape[1]))
        limited = np.concatenate([limited, pad], axis=1)
    return limited


# ─── True Peak / LUFS ──────────────────────────────────────────────────

def true_peak_measure(data, sr):
    upsampled = np.array([scipy_signal.resample_poly(data[ch], 4, 1) for ch in range(data.shape[0])])
    peak = np.max(np.abs(upsampled))
    return 20 * np.log10(peak + 1e-10), peak


def lufs_normalize(data, target_lufs, sr):
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data.T)
    gain_db = target_lufs - lufs
    data = data * (10 ** (gain_db / 20))
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
        output_name = f"{base}_pro5"

    TARGET_LUFS = -12.0   # golden middle — loud enough, no clipping
    CEILING = 0.912       # -0.8 dBFS ceiling — use headroom, no clipping

    print(f"Input: {input_path}")

    data, sr = read_wav(input_path)
    dur = data.shape[1] / sr
    print(f"  Duration: {dur:.1f}s, SR: {sr}, Channels: {data.shape[0]}")
    print(f"  Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    meter = pyln.Meter(sr)
    lufs_in = meter.integrated_loudness(data.T)
    print(f"  Input LUFS: {lufs_in:.2f}")
    print(f"  TARGET: {TARGET_LUFS} LUFS, ceiling -1.0 dBFS")

    # ═══ Step 0: DC blocker (NEW pro3.1) ═══
    print("\n=== Step 0: DC blocker (HPF @ 20Hz) ===")
    dc_before = float(np.mean(data))
    data = dc_blocker(data, sr, cutoff=20.0)
    dc_after = float(np.mean(data))
    print(f"  DC offset: {dc_before:+.6f} → {dc_after:+.6f}")

    # ═══ Step 1: Pre-normalize to target LUFS ═══
    print(f"\n=== Step 1: Pre-normalize to {TARGET_LUFS} LUFS ===")
    data, lufs_pre, gain_pre = lufs_normalize(data, TARGET_LUFS, sr)
    print(f"  Gain: {gain_pre:+.1f} dB, LUFS: {lufs_pre:.2f} → {TARGET_LUFS}")

    # ═══ Step 2: 5-band multiband split ═══
    print("\n=== Step 2: Multiband split (200/500/2000/5000/8000 Hz) ===")
    bands = multiband_split(data, sr, freqs=(200, 500, 2000, 5000, 8000))
    print("  6 bands: sub, bass, lowmid, presence, uppermid, air")

    # ═══ Step 3: Per-band processing ═══
    print("\n=== Step 3: Per-band processing (6 bands) ===")

    # Sub (<200Hz): HOTTER psychoacoustic bass + transient + par.comp (NO mono)
    print("  sub: psychoacoustic bass (HOT) + transient + par.comp (NO mono)")
    bands[0] = psychoacoustic_bass(bands[0], sr, freq=60, amount=0.25, mix=0.35)
    bands[0] = transient_enhancer(bands[0], sr, freq_low=50, freq_high=200, amount=0.35, attack_ms=5.0, mix=0.45)
    sub_comp = compressor(bands[0], threshold=0.2, ratio=4.0, attack=0.005, release=0.2, sr=sr, mix=1.0)
    bands[0] = bands[0] * 0.6 + sub_comp * 0.4

    # Bass (200-500Hz): mud cut + HOTTER tube sat
    print("  bass: mud cut -2dB @ 250 + tube sat (drive 0.25)")
    bands[1] = bell_eq(bands[1], sr, 250, -2.0, q=1.2)
    bands[1] = tube_saturation(bands[1], drive=0.25, mix=0.4)

    # Lowmid (500-2k): warmth + dyn EQ + HOTTER tape sat + WIDEN
    print("  lowmid: +3dB @ 700 + dyn EQ + tape sat (HOT) + widen 0.3")
    bands[2] = bell_eq(bands[2], sr, 700, 3.0, q=1.0)
    bands[2] = dynamic_eq(bands[2], sr, freq=300, gain_db=-2.0, q=1.5, threshold=0.2, attack=0.01, release=0.1)
    bands[2] = tape_sat_pre_emphasis(bands[2], sr, drive=0.25, mix=0.3, emph_freq=4000, emph_gain=3.0)
    bands[2] = stereo_widen(bands[2], amount=0.3)

    # Presence (2k-5k): boost + HOTTER tube + par.comp + WIDEN
    print("  presence: +5@3k +4@4k +3@5k + tube (HOT) + par.comp + widen 0.4")
    bands[3] = bell_eq(bands[3], sr, 3000, 5.0, q=1.0)
    bands[3] = bell_eq(bands[3], sr, 4000, 4.0, q=1.0)
    bands[3] = bell_eq(bands[3], sr, 5000, 3.0, q=1.0)
    bands[3] = tube_saturation(bands[3], drive=0.3, mix=0.4)
    pres_comp = compressor(bands[3], threshold=0.25, ratio=4.0, attack=0.003, release=0.12, sr=sr, mix=1.0)
    bands[3] = bands[3] * 0.5 + pres_comp * 0.5
    bands[3] = stereo_widen(bands[3], amount=0.4)

    # Upper-mid (5k-8k): vocal clarity + EXCITER (NEW pro5) + WIDEN
    print("  uppermid: +2dB @ 6k + exciter (NEW) + widen 0.4")
    bands[4] = bell_eq(bands[4], sr, 6000, 2.0, q=1.0)
    bands[4] = harmonic_exciter_even(bands[4], sr, freq=6000, amount=0.2, mix=0.3)
    bands[4] = stereo_widen(bands[4], amount=0.4)

    # Air (>8k): boost + EVEN exciter + bell + WIDEN 0.75
    print("  air: high-shelf +4dB + EVEN exciter + bell +3dB @ 12k + widen 0.75")
    bands[5] = high_shelf(bands[5], sr, 8000, 4.0)
    bands[5] = harmonic_exciter_even(bands[5], sr, freq=8000, amount=0.3, mix=0.45)
    bands[5] = bell_eq(bands[5], sr, 12000, 3.0, q=0.7)
    bands[5] = stereo_widen(bands[5], amount=0.75)

    # ═══ Step 4: Recombine + glue comp ═══
    print("\n=== Step 4: Recombine bands + glue comp (ratio 1.8) ===")
    data = multiband_recombine(bands)
    data = compressor(data, threshold=0.4, ratio=1.8, attack=0.015, release=0.12, sr=sr, mix=0.4)
    lufs_recomb = meter.integrated_loudness(data.T)
    print(f"  LUFS after recombine + glue: {lufs_recomb:.2f}")

    # ═══ Step 5: M/S EQ — side HPF + side air boost + WIDER ═══
    print("\n=== Step 5: M/S EQ (side HPF 200Hz + side boost +6dB @ 10k + widen 0.5) ===")
    data = ms_eq(data, sr, side_hp_freq=200, side_boost_freq=10000, side_boost_gain=6.0)
    data = stereo_widen(data, amount=0.5)

    # ═══ Step 6: Re-normalize to target LUFS ═══
    print(f"\n=== Step 6: Re-normalize to {TARGET_LUFS} LUFS ===")
    data, _, gain_recomb = lufs_normalize(data, TARGET_LUFS, sr)
    print(f"  Gain: {gain_recomb:+.1f} dB")

    # ═══ Step 7: SOFT CLIPPER (NEW pro3) — analog loudness ═══
    print("\n=== Step 7: Soft clipper (tanh, ceiling 0.95, drive 1.3) ===")
    data = soft_clipper(data, ceiling=0.95, drive=1.3, mix=0.7)
    peak_after_clip = 20*np.log10(np.max(np.abs(data))+1e-10)
    print(f"  Peak after soft clip: {peak_after_clip:.2f} dBFS")

    # ═══ Step 8: Soft knee + oversampled true peak limiter ═══
    print("\n=== Step 8: Soft knee + oversampled limiter (ceiling -1.0 dBFS) ===")
    data = soft_knee_limiter_prog(data, ceiling=CEILING, knee_db=2.0, sr=sr,
                                  lookahead_ms=3.0, release_fast_ms=40.0, release_slow_ms=120.0)
    data = oversampled_limiter(data, ceiling=CEILING, sr=sr, oversample=4)

    # ═══ Step 9: Final LUFS correction ═══
    print(f"\n=== Step 9: Final LUFS correction → {TARGET_LUFS} ===")
    lufs_final = meter.integrated_loudness(data.T)
    correction = TARGET_LUFS - lufs_final
    if abs(correction) > 0.1:
        data = data * (10 ** (correction / 20))
        data = oversampled_limiter(data, ceiling=CEILING, sr=sr, oversample=4)
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
