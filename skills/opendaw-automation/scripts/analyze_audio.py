#!/usr/bin/env python3
"""
Lightweight Audio Analysis Utility for Rapid Track Triage.
Analyzes peak levels, RMS, crest factor, frequency band energy distribution, and phase correlation (overall and low-end).
"""

import os
import sys
import subprocess
import tempfile
import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import butter, lfilter

def convert_to_wav(input_path):
    """Convert input audio file to a standard 44.1kHz 16-bit WAV file in temp directory."""
    temp_wav = os.path.join(tempfile.gettempdir(), "audio_triage_temp.wav")
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', input_path, '-ar', '44100', temp_wav],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return temp_wav
    except subprocess.CalledProcessError as e:
        print(f"Error: FFmpeg conversion failed. Ensure ffmpeg is installed. Details: {e}", file=sys.stderr)
        sys.exit(1)

def butter_lowpass_filter(data, cutoff, fs, order=4):
    """Apply a butterworth lowpass filter to isolate low frequencies."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)

def main():
    if len(sys.argv) < 2:
        print("Usage: ./analyze_audio.py <path_to_audio_file>", file=sys.stderr)
        sys.exit(1)

    input_audio = sys.argv[1]
    if not os.path.exists(input_audio):
        print(f"Error: File not found: {input_audio}", file=sys.stderr)
        sys.exit(1)

    # Convert if not already WAV
    is_temp_wav = False
    if not input_audio.lower().endswith('.wav'):
        print(f"Converting {os.path.basename(input_audio)} to WAV for analysis...")
        wav_path = convert_to_wav(input_audio)
        is_temp_wav = True
    else:
        wav_path = input_audio

    try:
        sample_rate, data = wav.read(wav_path)
        
        # Convert to float32 normalized representation
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            data = (data.astype(np.float32) - 128.0) / 128.0
        else:
            data = data.astype(np.float32)

        # Handle channels
        if len(data.shape) > 1:
            left = data[:, 0]
            right = data[:, 1]
            is_stereo = True
        else:
            left = right = data
            is_stereo = False

        print("\n=== AUDIO TRIAGE ANALYSIS ===")
        print(f"File: {os.path.basename(input_audio)}")
        print(f"Sample Rate: {sample_rate} Hz")
        print(f"Channels: {'Stereo' if is_stereo else 'Mono'}")
        
        # Calculate Peak
        peak_l = np.max(np.abs(left))
        peak_r = np.max(np.abs(right))
        print(f"Peak Level (L/R): {peak_l:.3f} / {peak_r:.3f}")

        # Calculate RMS
        rms_l = np.sqrt(np.mean(left**2))
        rms_r = np.sqrt(np.mean(right**2))
        rms_db_l = 20 * np.log10(rms_l + 1e-6)
        rms_db_r = 20 * np.log10(rms_r + 1e-6)
        print(f"RMS Level (L/R): {rms_db_l:.2f} dB / {rms_db_r:.2f} dB")

        # Dynamic Range / Crest Factor
        crest_l = 20 * np.log10(peak_l / (rms_l + 1e-6))
        print(f"Crest Factor (L): {crest_l:.2f} dB")

        # Phase and Stereo Correlation
        if is_stereo:
            overall_corr = np.corrcoef(left[::10], right[::10])[0, 1]
            print(f"Overall Stereo Correlation: {overall_corr:.3f}")
            
            # Low-end phase correlation (below 150 Hz)
            try:
                # Downsample for faster filter execution on long tracks
                ds_factor = 10
                low_left = butter_lowpass_filter(left[::ds_factor], 150, sample_rate / ds_factor)
                low_right = butter_lowpass_filter(right[::ds_factor], 150, sample_rate / ds_factor)
                bass_corr = np.corrcoef(low_left, low_right)[0, 1]
                print(f"Bass Stereo Correlation (<150Hz): {bass_corr:.3f}")
                if bass_corr < 0.2:
                    print("⚠️ WARNING: Poor low-frequency phase correlation. Potential mono-compatibility issues.")
            except Exception as e:
                print(f"Could not calculate bass correlation: {e}")

        # Frequency Band Analysis (FFT on a central segment to check balance)
        print("\n--- Frequency Balance (Center 5s Segment) ---")
        midpoint = len(left) // 2
        segment_len = int(5 * sample_rate)
        start = max(0, midpoint - segment_len // 2)
        end = min(len(left), start + segment_len)
        
        left_seg = left[start:end]
        yf = np.fft.rfft(left_seg)
        xf = np.fft.rfftfreq(len(left_seg), 1 / sample_rate)
        magnitude_db = 20 * np.log10(np.abs(yf) + 1e-6)

        def get_band_energy(low, high):
            indices = np.where((xf >= low) & (xf <= high))[0]
            if len(indices) == 0:
                return -100
            return np.mean(magnitude_db[indices])

        sub_bass = get_band_energy(20, 60)
        bass = get_band_energy(60, 250)
        low_mid = get_band_energy(250, 500)
        mid = get_band_energy(500, 2000)
        high_mid = get_band_energy(2000, 4000)
        highs = get_band_energy(4000, 20000)

        print(f"Sub-Bass (20-60 Hz):    {sub_bass:.1f} dB (rel)")
        print(f"Bass (60-250 Hz):        {bass:.1f} dB (rel)")
        print(f"Low-Mid (250-500 Hz):    {low_mid:.1f} dB (rel)")
        print(f"Mid (500-2000 Hz):       {mid:.1f} dB (rel)")
        print(f"High-Mid (2000-4000 Hz): {high_mid:.1f} dB (rel)")
        print(f"Highs (4000-20000 Hz):   {highs:.1f} dB (rel)")

        # Simple mix diagnostic
        sub_high_diff = sub_bass - highs
        print(f"Sub-to-High Balance:    {sub_high_diff:.1f} dB diff")
        if sub_high_diff > 30:
            print("💡 MIX NOTE: Heavy sub-bass bias. High-end might feel recessed/peachy.")
        elif sub_high_diff < 10:
            print("💡 MIX NOTE: Bright/lean mix. Sub-bass might feel thin.")

    finally:
        if is_temp_wav and os.path.exists(wav_path):
            os.remove(wav_path)

if __name__ == "__main__":
    main()
