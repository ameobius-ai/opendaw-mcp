#!/usr/bin/env python3
"""
Professional stem processing via pedalboard — for openDAW offline render workaround.
openDAW's Waveshaper/Compressor/Tidal don't work in OfflineEngineRenderer.
Pre-process stems here, then import processed WAVs into openDAW.

Quality standard: float32, RMS-matched, gain-staged, spectrally verified.

Usage:
  /tmp/audio_analysis_venv/bin/python pedalboard_stem_processing.py

Input:  /home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems/{bass_0,drums_1}.wav
Output: same dir: bass_sat.wav, drums_comp.wav

Then edit render script STEMS to use 'bass_sat.wav' and 'drums_comp.wav' instead.
"""
import soundfile as sf
import numpy as np
from pedalboard import Pedalboard, Compressor, PeakFilter, Distortion
from scipy.signal import welch
import pyloudnorm as pyln
import os

STEMS_DIR = '/home/ameobius/projects/creative-studio/agent-daw/headless-daw/public/stems'

def load_stem(path):
    audio, sr = sf.read(path, dtype='float32')
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    return audio, sr

def save_stem(path, audio, sr):
    sf.write(path, audio, sr, subtype='FLOAT')

def measure(audio, sr, label=''):
    if audio.ndim == 2:
        mono = audio.mean(axis=1)
    else:
        mono = audio
    rms = np.sqrt(np.mean(mono**2))
    rms_db = 20 * np.log10(rms + 1e-12)
    peak = np.max(np.abs(mono))
    peak_db = 20 * np.log10(peak + 1e-12)
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(mono)
    f, Pxx = welch(mono, sr, nperseg=8192, window='hann')
    bands = {}
    for name, lo, hi in [('sub',20,80), ('bass',80,200), ('lowmid',200,400),
                          ('mid',400,1000), ('pres',2000,5000), ('hats',8000,12000),
                          ('air',12000,20000)]:
        mask = (f >= lo) & (f <= hi)
        bands[name] = 10*np.log10(np.sum(Pxx[mask]) + 1e-12)
    print(f'  {label}: RMS={rms_db:.1f}dB peak={peak_db:.1f}dB LUFS={lufs:.1f}')
    print('    bands: ' + ' '.join(f'{k}={v:.1f}' for k,v in bands.items()))
    return {'rms_db': rms_db, 'peak_db': peak_db, 'lufs': lufs, 'bands': bands}

def rms_normalize(processed, original):
    """RMS-match: processed has same RMS as original — only spectral content changes."""
    orig_mono = original.mean(axis=1) if original.ndim == 2 else original
    proc_mono = processed.mean(axis=1) if processed.ndim == 2 else processed
    orig_rms = np.sqrt(np.mean(orig_mono**2))
    proc_rms = np.sqrt(np.mean(proc_mono**2))
    factor = orig_rms / (proc_rms + 1e-12)
    print(f'  RMS normalization: {20*np.log10(factor):+.1f}dB')
    return processed * factor

# ═══ BASS: Distortion + PeakFilter ═══
print('══ BASS PROCESSING ══')
bass_in = os.path.join(STEMS_DIR, 'bass_0.wav')
bass_out = os.path.join(STEMS_DIR, 'bass_sat.wav')
audio, sr = load_stem(bass_in)
print(f'  input: {bass_in} ({audio.shape}, {sr}Hz)')
measure(audio, sr, 'BEFORE')

# Gain staging: -6dB headroom
audio_hot = audio * 10**(-6/20)
bass_board = Pedalboard([
    Distortion(drive_db=3.0),
    PeakFilter(cutoff_frequency_hz=300, gain_db=2.0, q=1.4),
])
processed = bass_board(audio_hot.T, sr).T
processed = processed * 10**(6/20)  # restore
processed = rms_normalize(processed, audio)
processed = np.clip(processed, -1.0, 1.0)
measure(processed, sr, 'AFTER')
save_stem(bass_out, processed, sr)
print(f'  saved: {bass_out}')

# ═══ DRUMS: Compressor + makeup ═══
print('\n══ DRUMS PROCESSING ══')
drums_in = os.path.join(STEMS_DIR, 'drums_1.wav')
drums_out = os.path.join(STEMS_DIR, 'drums_comp.wav')
audio_d, sr_d = load_stem(drums_in)
print(f'  input: {drums_in} ({audio_d.shape}, {sr_d}Hz)')
measure(audio_d, sr_d, 'BEFORE')

drums_board = Pedalboard([
    Compressor(threshold_db=-18.0, ratio=3.0, attack_ms=3.0, release_ms=80.0),
])
processed_d = drums_board(audio_d.T, sr_d).T
processed_d = rms_normalize(processed_d, audio_d)  # makeup = RMS match
processed_d = np.clip(processed_d, -1.0, 1.0)
measure(processed_d, sr_d, 'AFTER')
save_stem(drums_out, processed_d, sr_d)
print(f'  saved: {drums_out}')

print('\n══ DONE ══')
