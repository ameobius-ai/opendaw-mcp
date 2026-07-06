#!/usr/bin/env python3
"""Post-production mastering for rendered WAV files.

Applies: high-shelf EQ (open air), true peak limiter, LUFS targeting.
Used after openDAW render — Werkstatt on master bus doesn't work in offline render,
so mastering is done here in Python (scipy + pyloudnorm).

Usage:
  venv/bin/python post_master.py <input.wav> [output_name]

If no args, processes exports/last_light_of_summer.wav.
Output goes to exports/<name>_mastered.wav + copied to Desktop.
"""
import sys
import os
import numpy as np
from scipy import signal as scipy_signal
from scipy.io import wavfile
import pyloudnorm as pyln


def read_wav(path):
    """Read WAV file, return (float32 stereo [2, N], sample_rate)."""
    sr, data = wavfile.read(path)

    # Convert to float32
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.float32:
        pass  # already float
    elif data.dtype == np.float64:
        data = data.astype(np.float32)
    else:
        data = data.astype(np.float32) / np.max(np.abs(data))

    if data.ndim == 1:
        data = np.stack([data, data], axis=0)
    else:
        data = data.T  # [channels, samples]

    return data, sr


def write_wav(path, data, sr):
    """Write float32 stereo to 32-bit float WAV."""
    data = np.clip(data, -1.0, 1.0)
    # scipy wavfile writes float32 directly
    stereo = data.T  # [samples, channels]
    wavfile.write(path, sr, stereo.astype(np.float32))


def high_shelf(data, sr, freq, gain_db):
    """Apply high-shelf EQ boost using scipy butterworth."""
    # Design high-shelf filter
    w0 = freq / (sr / 2)  # normalized frequency
    if w0 >= 1.0:
        return data

    gain_lin = 10 ** (gain_db / 20)
    # Use butterworth highpass + blend for shelf approximation
    b, a = scipy_signal.butter(2, w0, btype="high")
    filtered = scipy_signal.filtfilt(b, a, data, axis=1)
    # Blend: dry + (filtered * gain - filtered) = dry + filtered * (gain - 1)
    return data + filtered * (gain_lin - 1)


def bell_eq(data, sr, freq, gain_db, q=1.0):
    """Apply bell/peaking EQ using scipy."""
    w0 = freq / (sr / 2)
    if w0 >= 1.0 or w0 <= 0:
        return data

    gain_lin = 10 ** (gain_db / 20)
    # Bandpass filter for the bell region
    bw = w0 / q
    low = max(0.001, w0 - bw / 2)
    high = min(0.999, w0 + bw / 2)
    b, a = scipy_signal.butter(2, [low, high], btype="band")
    filtered = scipy_signal.filtfilt(b, a, data, axis=1)
    return data + filtered * (gain_lin - 1)


def stereo_widen(data, amount=0.4):
    """Widen stereo via M/S processing. amount=0 neutral, 1=max wide."""
    if data.shape[0] != 2:
        return data
    mid = (data[0] + data[1]) * 0.5
    side = (data[0] - data[1]) * 0.5
    side = side * (1.0 + amount)
    return np.stack([mid + side, mid - side], axis=0)


def tape_saturation(data, drive=0.3, mix=0.5):
    """Light tape saturation — adds warmth and 'glue' to the mix.
    drive: 0-1 (0=clean, 1=heavy), mix: 0-1 (dry/wet)."""
    drive_amt = 1 + drive * 3
    driven = np.tanh(data * drive_amt) / np.tanh(drive_amt)
    return data * (1 - mix) + driven * mix


def harmonic_exciter(data, sr, freq=8000, amount=0.3, mix=0.4):
    """Harmonic exciter — generates 2nd/3rd harmonics above freq Hz.
    Adds 'expensive' air without just turning up the volume."""
    # Split: highpass to isolate HF
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="high")
    hf = scipy_signal.filtfilt(b, a, data, axis=1)
    # Generate harmonics via waveshaping (cubic = odd harmonics)
    harmonic = hf - (hf ** 3) / 3 * amount
    return data * (1 - mix) + (data + harmonic * amount) * mix


def psychoacoustic_bass(data, sr, freq=60, amount=0.25, mix=0.3):
    """Psychoacoustic bass enhancement — generates harmonics of sub frequencies
    so the brain 'hears' fundamental even on small speakers.
    freq: target sub frequency, amount: harmonic strength."""
    # Isolate sub
    b, a = scipy_signal.butter(2, freq / (sr / 2), btype="low")
    sub = scipy_signal.filtfilt(b, a, data, axis=1)
    # Generate 2nd and 3rd harmonics
    h2 = sub ** 2 * np.sign(sub) * amount
    h3 = sub ** 3 * amount * 0.5
    # Bandpass harmonics to 80-300Hz (where small speakers can reproduce)
    b2, a2 = scipy_signal.butter(2, [80 / (sr / 2), 300 / (sr / 2)], btype="band")
    harmonics = scipy_signal.filtfilt(b2, a2, (h2 + h3), axis=1)
    return data + harmonics * mix


def glue_compressor(data, threshold=0.5, ratio=2.0, attack=0.01, release=0.1, sr=48000, mix=0.5):
    """Light glue compression — binds the mix together.
    Slow attack, fast-ish release, low ratio.
    Vectorized via scipy.signal.lfilter for envelope follower — O(n) not O(n) Python loop."""
    attack_samp = max(1, int(sr * attack))
    release_samp = max(1, int(sr * release))
    abs_data = np.abs(data)

    # Vectorized envelope follower using lfilter
    # Attack: one-pole filter with fast response (small coefficient = fast)
    # Release: one-pole filter with slow response (large coefficient = slow)
    # We use a single combined envelope: max of attack and release paths
    at_b = [1.0 - np.exp(-1 / attack_samp)]
    at_a = [1, -np.exp(-1 / attack_samp)]
    rl_b = [1.0 - np.exp(-1 / release_samp)]
    rl_a = [1, -np.exp(-1 / release_samp)]

    env = np.zeros_like(data)
    for ch in range(data.shape[0]):
        # Attack envelope (follows rising signal)
        at_env = scipy_signal.lfilter(at_b, at_a, abs_data[ch])
        # Release envelope (follows falling signal)
        rl_env = scipy_signal.lfilter(rl_b, rl_a, abs_data[ch])
        # Combined: take max (peak hold behavior)
        env[ch] = np.maximum(at_env, rl_env)

    # Compression
    over = np.maximum(env - threshold, 0)
    gain_reduction = 1 / (1 + over * (ratio - 1) / threshold)
    compressed = data * gain_reduction
    return data * (1 - mix) + compressed * mix


def limiter(data, target_lufs=-14.0, sr=48000, true_peak_ceiling=0.891, max_gain_db=8.0):
    """Apply LUFS normalization + soft limiter for true peak.

    true_peak_ceiling=0.891 ≈ -1.0 dBFS
    max_gain_db caps the maximum gain to prevent excessive boost on quiet tracks.
    """
    # Measure current LUFS
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data.T)

    # Calculate gain needed
    gain_db = min(target_lufs - lufs, max_gain_db)
    gain_lin = 10 ** (gain_db / 20)

    # Apply gain
    boosted = data * gain_lin

    # Multi-stage soft limiting: hard knee limiter at ceiling
    ceiling = true_peak_ceiling

    # First pass: aggressive tanh saturation to tame transients
    # This allows higher LUFS without hard clipping
    abs_data = np.abs(boosted)
    peak = np.max(abs_data)

    if peak > ceiling:
        # Calculate drive to bring RMS up while taming peaks
        # Use tanh: y = ceiling * tanh(x / ceiling)
        # This compresses peaks while preserving RMS
        boosted = np.tanh(boosted / ceiling) * ceiling

    # Second pass: final hard clip at ceiling (safety)
    boosted = np.clip(boosted, -ceiling, ceiling)

    return boosted, gain_db, lufs


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

    # Read
    data, sr = read_wav(input_path)
    dur = data.shape[1] / sr
    print(f"  Duration: {dur:.1f}s, SR: {sr}, Channels: {data.shape[0]}")
    print(f"  Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Measure input LUFS
    meter = pyln.Meter(sr)
    lufs_in = meter.integrated_loudness(data.T)
    print(f"  Input LUFS: {lufs_in:.2f}")

    # Step 0: Pre-normalize to -14 LUFS (gain staging before EQ)
    print("\n=== Step 0: Pre-normalize to -14 LUFS ===")
    pre_gain = -14.0 - lufs_in
    data = data * (10 ** (pre_gain / 20))
    lufs_pre = meter.integrated_loudness(data.T)
    print(f"  Gain: {pre_gain:+.1f} dB, LUFS now: {lufs_pre:.2f}")

    # Step 1: HPF 40Hz (subsonic cleanup, keep sub bass)
    print("\n=== Step 1: HPF 40Hz (subsonic cleanup) ===")
    b, a = scipy_signal.butter(2, 40 / (sr / 2), btype="high")
    data = scipy_signal.filtfilt(b, a, data, axis=1)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 2: Bass mud cut -2dB at 250Hz
    print("\n=== Step 2: Bell -2dB @ 250Hz (bass mud cut) ===")
    data = bell_eq(data, sr, 250, -2.0, q=1.2)

    # Step 3: Lowmid fill +3dB at 350Hz
    print("\n=== Step 3: Bell +3dB @ 350Hz (lowmid fill) ===")
    data = bell_eq(data, sr, 350, 3.0, q=1.0)

    # Step 4: Presence +2dB at 3kHz
    print("\n=== Step 4: Bell +2dB @ 3kHz (presence) ===")
    data = bell_eq(data, sr, 3000, 2.0, q=1.0)

    # Step 4b: Presence +1dB at 5kHz
    print("\n=== Step 4b: Bell +1dB @ 5kHz ===")
    data = bell_eq(data, sr, 5000, 1.0, q=1.0)

    # Step 5: Psychoacoustic bass @ 60Hz (sub enhance)
    print("\n=== Step 5: Psychoacoustic bass @ 60Hz ===")
    data = psychoacoustic_bass(data, sr, freq=60, amount=0.15, mix=0.2)

    # Step 6: Tape saturation (warmth, light)
    print("\n=== Step 6: Tape saturation (warmth, light) ===")
    data = tape_saturation(data, drive=0.15, mix=0.25)

    # Step 7: Glue compression (subtle, vectorized)
    print("\n=== Step 7: Glue compression (2:1, subtle) ===")
    data = glue_compressor(data, threshold=0.6, ratio=1.5, attack=0.02, release=0.15, sr=sr, mix=0.3)

    # Step 8: Stereo widen (M/S +60%)
    print("\n=== Step 8: Stereo widen (M/S +60%) ===")
    data = stereo_widen(data, amount=0.6)

    # Step 9: Limiter → -14 LUFS, -1.0 dBTP
    print("\n=== Step 9: Limiter → -14 LUFS ===")
    data, gain_db, lufs_lim = limiter(data, target_lufs=-14.0, sr=sr, true_peak_ceiling=0.891)
    print(f"  Gain: {gain_db:+.1f} dB, LUFS: {lufs_lim:.2f}")

    # Step 10: POST-LIMITER air polish (not affected by limiter)
    print("\n=== Step 10: Post-limiter air polish ===")
    data = high_shelf(data, sr, 8000, 2.0)
    data = harmonic_exciter(data, sr, freq=8000, amount=0.15, mix=0.25)
    data = bell_eq(data, sr, 12000, 1.5, q=0.7)
    # Soft limiter for post-air peaks (tanh, no hard clip)
    peak_post = np.max(np.abs(data))
    if peak_post > 0.891:
        data = np.tanh(data / 0.891) * 0.891
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Final report
    peak_out = np.max(np.abs(data))
    lufs_out = meter.integrated_loudness(data.T)
    print("\n=== FINAL ===")
    print(f"  LUFS: {lufs_in:.2f} → {lufs_out:.2f}")
    print(f"  Peak: {20*np.log10(peak_out+1e-10):.2f} dBFS ({peak_out:.4f})")

    # Write
    output_path = os.path.join(os.path.dirname(__file__), "exports", f"{output_name}.wav")
    write_wav(output_path, data, sr)
    size_mb = os.path.getsize(output_path) / 1048576
    print(f"\nOutput: {output_path} ({size_mb:.1f}MB)")

    # Copy to Desktop
    import shutil
    desktop = f"/mnt/c/Users/admin/Desktop/{output_name}.wav"
    shutil.copy2(output_path, desktop)
    print(f"Copied to: {desktop}")


if __name__ == "__main__":
    main()
