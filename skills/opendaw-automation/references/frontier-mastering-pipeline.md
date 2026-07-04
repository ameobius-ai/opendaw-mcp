# Frontier Mastering Pipeline (pedalboard + scipy)

Verified July 1, 2026 (session 11). F11 → F12 master for Серебро.

## Pipeline

```
Input (-20.6 LUFS)
  → LR4 3-band crossover (250Hz / 4kHz, phase-coherent)
  → Per-band compression (different attack/release per band)
  → Sum back
  → M/S EQ (M: warmth+mud, S: width+air)
  → Air shelf +2dB @12kHz
  → LUFS targeting (over-shoot gain → limit → measure → attenuate to target)
  → True-peak limiter (4x oversampled, WindowedSinc128)
  → TP verification + safety clip
  → Post-limiter LUFS correction (pure gain, no limiter interaction)
Output (-14.2 LUFS, -1.2dBTP)
```

## LR4 Crossover (Linkwitz-Riley 4th order)

LR4 = two cascaded Butterworth 2nd order filters. -6dB at crossover frequency, 24dB/octave slope.

```python
from scipy.signal import butter, sosfiltfilt
import numpy as np

def lr4_lowpass(fc, sr):
    sos1 = butter(2, fc, 'lowpass', fs=sr, output='sos')
    sos2 = butter(2, fc, 'lowpass', fs=sr, output='sos')
    return np.vstack([sos1, sos2])

def lr4_highpass(fc, sr):
    sos1 = butter(2, fc, 'highpass', fs=sr, output='sos')
    sos2 = butter(2, fc, 'highpass', fs=sr, output='sos')
    return np.vstack([sos1, sos2])

# Bandpass = LR4 HPF(fc_lo) → LR4 LPF(fc_hi)
def apply_lr4(audio, sos):
    if audio.ndim == 2:
        return np.stack([sosfiltfilt(sos, audio[:,ch]) for ch in range(audio.shape[1])], axis=1)
    return sosfiltfilt(sos, audio)
```

**⚠️ Reconstruction error:** `sosfiltfilt` on LR4 gives ~0.18 reconstruction error (not perfect). For phase-perfect reconstruction, use linear-phase FIR crossovers instead. In practice, 0.18 error is inaudible at mix level.

## Per-band Compression Settings

| Band | Range | Threshold | Ratio | Attack | Release | Purpose |
|------|-------|-----------|-------|--------|---------|---------|
| Low | <250Hz | -18dB | 2.5:1 | 15ms | 150ms | Control sub energy, slow = no pumping |
| Mid | 250-4kHz | -16dB | 2.0:1 | 8ms | 80ms | Vocal/instrument density |
| High | >4kHz | -20dB | 1.8:1 | 3ms | 50ms | Transient control, preserve air |

## M/S Processing

```python
def to_ms(stereo):
    M = (stereo[:,0] + stereo[:,1]) / 2
    S = (stereo[:,0] - stereo[:,1]) / 2
    return np.stack([M, S], axis=1)

def to_lr(ms):
    L = ms[:,0] + ms[:,1]
    R = ms[:,0] - ms[:,1]
    return np.stack([L, R], axis=1)
```

- M channel: LowShelf +1dB @120Hz (warmth), Peak -1.5dB @300Hz (mud control)
- S channel: HighShelf +2dB @10kHz (stereo width / air in sides)

## LUFS Targeting (post-limiter)

Real mastering: limiter changes LUFS relationship non-linearly. Strategy:

1. Measure pre-gain LUFS
2. Over-shoot gain by +2dB above target (push limiter into meaningful GR)
3. Apply oversampled limiter
4. Measure post-limiter LUFS
5. Attenuate to exact target (pure gain, no limiter interaction)

```python
gain = (LUFS_TARGET - cur_lufs) + 2.0  # over-shoot
gained = audio * 10**(gain/20)
# ... limit ...
final_lufs = meter.integrated_loudness(limited.mean(axis=1))
if final_lufs > LUFS_TARGET:
    atten = 10**((LUFS_TARGET - final_lufs)/20)
    limited = limited * atten
```

## True-Peak Limiting (4x oversampled)

```python
from pedalboard import Resample, Limiter

SR_OS = SR * 4  # 192kHz
limit_board = Pedalboard([
    Resample(target_sample_rate=SR_OS, quality=Resample.Quality.WindowedSinc128),
    Limiter(threshold_db=-1.0, release_ms=100),
    Resample(target_sample_rate=SR, quality=Resample.Quality.WindowedSinc128),
])
```

**Post-limiter intersample peak verification:**
4x oversample AGAIN (cubic interpolation) to detect remaining intersample peaks. If TP > ceiling, attenuate channel individually.

## F12 Results

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| LUFS | -20.6 | -14.2 | -14.0 |
| peak | -4.0dB | -2.8dB | — |
| truePeak | -3.9dB | -1.2dB | -1.0dBTP |
| LRA | 6.6 | 3.0 | — |
| air | -49.2dB | -39.9dB | — |
| sub | -34.5dB | -26.5dB | — |

**Remaining issues:**
- TP -1.2 vs ceiling -1.0: 0.2dB over (intersample peak not fully caught). Add harder safety clip or 8x oversampling.
- LR4 reconstruction error 0.18: consider linear-phase FIR for next pass.
- LRA 3.0: heavy compression from limiter. Could reduce over-shoot gain for less GR.

## Pedalboard plugin availability on this system

No VST3 plugins installed. pedalboard.load_plugin() works but has no targets. All processing done with built-in pedalboard plugins + scipy.signal. For VST3 access, would need to install LSP/Calf/Zamulator plugins.

## Available pedalboard plugins (v0.9.23)

```
Bitcrush, Chorus, Clipping, Compressor, Convolution, Delay, Distortion,
Gain, GSMFullRateCompressor, HighShelfFilter, HighpassFilter, IIRFilter,
Invert, LadderFilter, Limiter, LowShelfFilter, LowpassFilter,
MP3Compressor, Mix, NoiseGate, PeakFilter, Phaser, PitchShift, Resample,
Reverb, Chain
```

Key params:
- `PeakFilter`: cutoff_frequency_hz, gain_db, q
- `Distortion`: drive_db (only)
- `Compressor`: threshold_db, ratio, attack_ms, release_ms
- `Limiter`: threshold_db, release_ms
- `Resample`: target_sample_rate, quality (WindowedSinc8/16/32/64/128/256, Linear, CatmullRom, Lagrange, ZeroOrderHold)
- `Chorus`: rate_hz, depth, centre_delay_ms, feedback, mix
- `Phaser`: rate_hz, centre_frequency_hz, depth, feedback, mix
- `Delay`: delay_seconds, feedback, mix
