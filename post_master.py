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

    # Step 1: HPF 80Hz on mix (remove subsonic mud from vocals/guitars)
    print("\n=== Step 1: HPF 80Hz (subsonic cleanup) ===")
    b, a = scipy_signal.butter(2, 80 / (sr / 2), btype="high")
    data = scipy_signal.filtfilt(b, a, data, axis=1)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 2: Bass cut -2dB at 250Hz (reduce mud)
    print("\n=== Step 2: Bell -2dB @ 250Hz (bass mud cut) ===")
    data = bell_eq(data, sr, 250, -2.0, q=1.2)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 3: Lowmid fill +3dB at 350Hz
    print("\n=== Step 3: Bell +3dB @ 350Hz (lowmid fill) ===")
    data = bell_eq(data, sr, 350, 3.0, q=1.0)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 4: Presence +3dB at 3kHz (vocal face)
    print("\n=== Step 4: Bell +3dB @ 3kHz (presence) ===")
    data = bell_eq(data, sr, 3000, 3.0, q=1.0)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 5: High-shelf +5dB at 8kHz (open air)
    print("\n=== Step 5: High-shelf +5dB @ 8kHz (air) ===")
    data = high_shelf(data, sr, 8000, 5.0)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 6: Bell +3dB at 12kHz (more air)
    print("\n=== Step 6: Bell +3dB @ 12kHz (air top) ===")
    data = bell_eq(data, sr, 12000, 3.0, q=0.7)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 7: Stereo widen (M/S processing)
    print("\n=== Step 7: Stereo widen (M/S +40%) ===")
    data = stereo_widen(data, amount=0.4)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 8: LUFS normalize + limiter → -14 LUFS, -1.0 dBTP
    print("\n=== Step 8: LUFS target -14 + true peak limiter ===")
    data, gain_db, lufs_pre = limiter(data, target_lufs=-14.0, sr=sr, true_peak_ceiling=0.891)
    peak_out = np.max(np.abs(data))
    lufs_out = meter.integrated_loudness(data.T)
    print(f"  Gain applied: +{gain_db:.1f} dB")
    print(f"  LUFS: {lufs_pre:.2f} → {lufs_out:.2f}")
    print(f"  Peak: {20*np.log10(peak_out+1e-10):.2f} dBFS ({peak_out:.4f})")
    print("  True peak ceiling: -1.0 dBFS (0.891)")

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
