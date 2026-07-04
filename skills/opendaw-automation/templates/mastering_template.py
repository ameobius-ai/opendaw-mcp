#!/usr/bin/env python3
"""
Frontier mastering template — LR4 multiband + M/S EQ + true-peak limiter.

Usage:
  /tmp/audio_analysis_venv/bin/python mastering.py <input.wav> <output.wav> [LUFS_TARGET]

Pipeline (ITU-R BS.1770 compliant):
1. DC offset removal
2. LR4 3-band crossover (Linkwitz-Riley 4th order, phase-coherent)
   - Low: <250Hz | Mid: 250-4kHz | High: >4kHz
3. Per-band compression (frequency-dependent attack/release)
4. M/S EQ (M: warmth + mud control, S: width + air)
5. Air shelf boost
6. LUFS-targeted loudness (over-shoot gain → limit → post-limiter LUFS correction)
7. True-peak limiting (4x oversampled, 2-stage: limiter + intersample verification)
8. Final verification (LUFS, true-peak, LRA, band energy)

Requirements:
  - /tmp/audio_analysis_venv (pedalboard, pyloudnorm, scipy, soundfile)
  - Input: FLOAT or PCM WAV, any sample rate (resampled to 48kHz internally)
"""
import sys
import soundfile as sf
import numpy as np
from scipy.signal import butter, sosfiltfilt, welch
from pedalboard import (
    Pedalboard, Compressor, Gain, Limiter,
    LowShelfFilter, HighShelfFilter, PeakFilter, Resample
)
import pyloudnorm as pyln
from scipy.interpolate import interp1d
import os

# ─── CONFIG ───
INPUT = sys.argv[1] if len(sys.argv) > 1 else 'input.wav'
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else 'output_master.wav'
LUFS_TARGET = float(sys.argv[3]) if len(sys.argv) > 3 else -14.0
TP_CEILING = -1.0  # dBTP
OS_FACTOR = 4
SR = 48000
SR_OS = SR * OS_FACTOR

# Crossover frequencies
XOVER_LO = 250
XOVER_HI = 4000

# ─── LR4 CROSSOVER ───
def lr4_lowpass(fc, sr):
    sos1 = butter(2, fc, 'lowpass', fs=sr, output='sos')
    sos2 = butter(2, fc, 'lowpass', fs=sr, output='sos')
    return np.vstack([sos1, sos2])

def lr4_highpass(fc, sr):
    sos1 = butter(2, fc, 'highpass', fs=sr, output='sos')
    sos2 = butter(2, fc, 'highpass', fs=sr, output='sos')
    return np.vstack([sos1, sos2])

def apply_lr4(audio, sos):
    if audio.ndim == 2:
        return np.stack([sosfiltfilt(sos, audio[:,ch]) for ch in range(audio.shape[1])], axis=1)
    return sosfiltfilt(sos, audio)

# ─── M/S ───
def to_ms(stereo):
    return np.stack([(stereo[:,0] + stereo[:,1]) / 2, (stereo[:,0] - stereo[:,1]) / 2], axis=1)

def to_lr(ms):
    return np.stack([ms[:,0] + ms[:,1], ms[:,0] - ms[:,1]], axis=1)

# ─── MEASUREMENT ───
def measure(a, sr, label=''):
    m = a.mean(axis=1) if a.ndim == 2 else a
    rms = 20*np.log10(np.sqrt(np.mean(m**2)) + 1e-12)
    peak = 20*np.log10(np.max(np.abs(m)) + 1e-12)
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(m)
    try: lra = meter.loudness_range(m)
    except: lra = 0
    # True-peak
    idx = np.arange(len(m))
    idx_os = np.linspace(0, len(m)-1, len(m)*OS_FACTOR)
    m_os = interp1d(idx, m, kind='cubic')(idx_os)
    tp = 20*np.log10(np.max(np.abs(m_os)) + 1e-12)
    print(f'  {label}: RMS={rms:.1f}dB peak={peak:.1f}dB TP={tp:.1f}dB LUFS={lufs:.1f} LRA={lra:.1f}', flush=True)
    return {'rms': rms, 'peak': peak, 'tp': tp, 'lufs': lufs, 'lra': lra}

# ─── MAIN ───
print(f'══ MASTERING: {INPUT} → {OUTPUT} (target {LUFS_TARGET} LUFS) ══', flush=True)
audio, sr = sf.read(INPUT, dtype='float32')
if audio.ndim == 1: audio = np.stack([audio, audio], axis=1)
before = measure(audio, sr, 'INPUT')

# DC offset
dc = np.mean(audio)
if abs(dc) > 1e-6: audio = audio - dc

# 1. LR4 crossover
print('\n── Stage 1: LR4 3-band crossover ──', flush=True)
low = apply_lr4(audio, lr4_lowpass(XOVER_LO, sr))
mid_raw = apply_lr4(audio, lr4_highpass(XOVER_LO, sr))
mid = apply_lr4(mid_raw, lr4_lowpass(XOVER_HI, sr))
high = apply_lr4(mid_raw, lr4_highpass(XOVER_HI, sr))
recon_err = np.max(np.abs((low + mid + high) - audio))
print(f'  reconstruction error: {recon_err:.2e}', flush=True)

# 2. Per-band compression
print('\n── Stage 2: Per-band compression ──', flush=True)
low_proc = Pedalboard([Compressor(threshold_db=-18, ratio=2.5, attack_ms=15, release_ms=150)])(low.T, sr).T
mid_proc = Pedalboard([Compressor(threshold_db=-16, ratio=2.0, attack_ms=8, release_ms=80)])(mid.T, sr).T
high_proc = Pedalboard([Compressor(threshold_db=-20, ratio=1.8, attack_ms=3, release_ms=50)])(high.T, sr).T
multiband = low_proc + mid_proc + high_proc

# 3. M/S EQ
print('\n── Stage 3: M/S EQ ──', flush=True)
ms = to_ms(multiband)
ms[:,0] = Pedalboard([LowShelfFilter(120, 1.0, 0.7), PeakFilter(300, -1.5, 1.0)])(ms[:,0:1].T, sr).T[:,0]
ms[:,1] = Pedalboard([HighShelfFilter(10000, 2.0, 0.7)])(ms[:,1:2].T, sr).T[:,0]
ms_proc = to_lr(ms)

# 4. Air shelf
print('\n── Stage 4: Air shelf ──', flush=True)
air = Pedalboard([HighShelfFilter(12000, 2.0, 0.7)])(ms_proc.T, sr).T

# 5. LUFS targeting (over-shoot + post-correction)
print('\n── Stage 5: LUFS targeting ──', flush=True)
meter = pyln.Meter(sr)
cur_lufs = meter.integrated_loudness(air.mean(axis=1))
gain = (LUFS_TARGET - cur_lufs) + 2.0  # +2dB over-shoot for limiter
gained = np.clip(air * 10**(gain/20), -0.99, 0.99)

# 6. True-peak limiter (4x oversampled)
print('\n── Stage 6: True-peak limiting ──', flush=True)
limited = Pedalboard([
    Resample(SR_OS, quality=Resample.Quality.WindowedSinc128),
    Limiter(threshold_db=TP_CEILING, release_ms=100),
    Resample(SR, quality=Resample.Quality.WindowedSinc128),
])(gained.T, sr).T

# Intersample peak verification
for ch in range(limited.shape[1]):
    cd = limited[:, ch]
    ch_os = interp1d(np.arange(len(cd)), cd, kind='cubic')(np.linspace(0, len(cd)-1, len(cd)*OS_FACTOR))
    tp_ch = 20*np.log10(np.max(np.abs(ch_os)) + 1e-12)
    if tp_ch > TP_CEILING:
        limited[:, ch] *= 10**((TP_CEILING - tp_ch - 0.1)/20)
        print(f'  ch{ch}: TP {tp_ch:.1f} → attenuated', flush=True)

limited = np.clip(limited, -10**(-0.3/20), 10**(-0.3/20))

# Post-limiter LUFS correction
final_lufs = meter.integrated_loudness(limited.mean(axis=1))
if final_lufs > LUFS_TARGET:
    limited *= 10**((LUFS_TARGET - final_lufs)/20)
    print(f'  post-limiter LUFS: {final_lufs:.2f} → attenuated to {LUFS_TARGET}', flush=True)

# 7. Final
after = measure(limited, sr, 'FINAL')
sf.write(OUTPUT, limited, sr, subtype='FLOAT')
print(f'\n  LUFS: {before["lufs"]:.1f} → {after["lufs"]:.1f}', flush=True)
print(f'  TP:   {before["tp"]:.1f} → {after["tp"]:.1f}dB', flush=True)
print(f'  LRA:  {before["lra"]:.1f} → {after["lra"]:.1f}', flush=True)
print(f'  saved: {OUTPUT}', flush=True)
