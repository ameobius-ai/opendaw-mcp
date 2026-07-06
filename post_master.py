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


def limiter(data, target_lufs=-14.0, sr=48000, true_peak_ceiling=0.891):
    """Apply LUFS normalization + soft limiter for true peak.

    true_peak_ceiling=0.891 ≈ -1.0 dBFS
    """
    # Measure current LUFS
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data.T)

    # Calculate gain needed
    gain_db = target_lufs - lufs
    gain_lin = 10 ** (gain_db / 20)

    # Apply gain
    boosted = data * gain_lin

    # Soft limiter (tanh saturation) to catch peaks
    ceiling = true_peak_ceiling
    # Only limit samples above ceiling
    peak = np.max(np.abs(boosted))
    if peak > ceiling:
        # Calculate makeup to bring peak to ceiling before saturation
        ratio = ceiling / peak * 1.01  # slight margin
        boosted = boosted * ratio

        # Soft clip with tanh
        abs_data = np.abs(boosted)
        mask = abs_data > ceiling * 0.9
        if np.any(mask):
            # Apply tanh only to near-ceiling samples
            over = boosted[mask]
            boosted[mask] = np.tanh(over / ceiling) * ceiling

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

    # Step 1: High-shelf +4dB at 8kHz (open air)
    print("\n=== Step 1: High-shelf +4dB @ 8kHz ===")
    data = high_shelf(data, sr, 8000, 4.0)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 2: Bell +2dB at 12kHz (more air)
    print("\n=== Step 2: Bell +2dB @ 12kHz ===")
    data = bell_eq(data, sr, 12000, 2.0, q=0.7)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 3: Bell +1.5dB at 350Hz (fill lowmid)
    print("\n=== Step 3: Bell +1.5dB @ 350Hz (lowmid fill) ===")
    data = bell_eq(data, sr, 350, 1.5, q=1.0)
    print(f"  Done. Peak: {20*np.log10(np.max(np.abs(data))+1e-10):.2f} dBFS")

    # Step 4: LUFS normalize + limiter → -14 LUFS, -1.0 dBTP
    print("\n=== Step 4: LUFS target -14 + true peak limiter ===")
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
