#!/usr/bin/env python3
"""A/B FFT comparator for mastered WAV versions.

Compares multiple WAV files across 9 frequency bands, stereo width,
LUFS, crest factor, and spectral centroid. Shows delta between versions.

Usage:
  venv/bin/python compare_versions.py file1.wav file2.wav [file3.wav ...]
  venv/bin/python compare_versions.py --dir exports/        # compare all WAVs in dir
  venv/bin/python compare_versions.py --last exports/ 3     # last 3 by mtime
"""
import os
import sys
import glob
import numpy as np
from scipy.io import wavfile
import pyloudnorm as pyln

BANDS = [
    (20, 30, "infra"),
    (30, 80, "sub"),
    (80, 200, "bass"),
    (200, 315, "lowmid"),
    (315, 800, "mid"),
    (800, 2000, "umid"),
    (2000, 5000, "pres"),
    (5000, 8000, "bril"),
    (8000, 16000, "air"),
]


def read(path):
    sr, d = wavfile.read(path)
    if d.dtype == np.int16: d = d.astype(np.float32) / 32768.0
    elif d.dtype == np.int32: d = d.astype(np.float32) / 2147483648.0
    elif d.dtype != np.float32: d = d.astype(np.float32)
    if d.ndim == 1: d = np.stack([d, d])
    return d.T, sr


def fft_band(d, sr, lo, hi):
    fft = np.fft.rfft(d[0])
    freqs = np.fft.rfftfreq(len(d[0]), 1 / sr)
    mask = (freqs >= lo) & (freqs < hi)
    energy = np.mean(np.abs(fft[mask]) ** 2) / max(len(mask), 1)
    return 20 * np.log10(np.sqrt(energy) + 1e-10)


def analyze(path):
    d, sr = read(path)
    peak = 20 * np.log10(np.max(np.abs(d)) + 1e-10)
    rms = 20 * np.log10(np.sqrt(np.mean(d ** 2)) + 1e-10)
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(d.T)
    crest = peak - rms
    mid = (d[0] + d[1]) / 2
    side = (d[0] - d[1]) / 2
    width = np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-10)
    fft = np.fft.rfft(d[0])
    freqs = np.fft.rfftfreq(len(d[0]), 1 / sr)
    mag = np.abs(fft)
    centroid = np.sum(freqs * mag) / (np.sum(mag) + 1e-10)
    bands = [fft_band(d, sr, lo, hi) for lo, hi, _ in BANDS]
    return {
        "name": os.path.basename(path),
        "lufs": lufs,
        "peak": peak,
        "rms": rms,
        "crest": crest,
        "width": width,
        "centroid": centroid,
        "bands": bands,
        "dur": d.shape[1] / sr,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: compare_versions.py file1.wav [file2.wav ...] | --dir <dir> | --last <dir> <N>")
        sys.exit(1)

    if sys.argv[1] == "--dir":
        files = sorted(glob.glob(os.path.join(sys.argv[2], "*.wav")))
    elif sys.argv[1] == "--last":
        d = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        all_files = sorted(glob.glob(os.path.join(d, "*.wav")), key=os.path.getmtime, reverse=True)
        files = all_files[:n]
    else:
        files = sys.argv[1:]

    if not files:
        print("No files to compare")
        sys.exit(1)

    results = []
    for f in files:
        if not os.path.exists(f):
            print(f"  MISSING: {f}")
            continue
        results.append(analyze(f))

    if len(results) < 1:
        print("No valid files")
        sys.exit(1)

    # Print table
    band_labels = [l for _, _, l in BANDS]
    header = f"{'name':<20} {'LUFS':>6} {'peak':>6} {'crest':>6} {'width':>6} {'cent':>5}"
    for bl in band_labels:
        header += f" {bl:>5}"
    print(header)
    print("-" * len(header))

    for r in results:
        line = f"{r['name']:<20} {r['lufs']:6.1f} {r['peak']:6.1f} {r['crest']:6.1f} {r['width']:6.3f} {r['centroid']:5.0f}"
        for v in r["bands"]:
            line += f" {v:5.1f}"
        print(line)

    # Delta table (each vs first)
    if len(results) >= 2:
        print(f"\nDELTA (each vs {results[0]['name']}):")
        ref = results[0]
        header = f"{'name':<20} {'Δlufs':>6} {'Δpeak':>6} {'Δcrst':>6} {'Δwdth':>6}"
        for bl in band_labels:
            header += f" {bl:>5}"
        print(header)
        print("-" * len(header))
        for r in results[1:]:
            line = f"{r['name']:<20} {r['lufs']-ref['lufs']:+6.1f} {r['peak']-ref['peak']:+6.1f} {r['crest']-ref['crest']:+6.1f} {r['width']-ref['width']:+6.3f}"
            for i, v in enumerate(r["bands"]):
                line += f" {v-ref['bands'][i]:+5.1f}"
            print(line)


if __name__ == "__main__":
    main()
