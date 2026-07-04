# Pedalboard Stem Processing (SOTA alternative for openDAW offline effects)

## Context

openDAW's OfflineEngineRenderer silently bypasses Waveshaper, Tidal, Compressor, and Delay.
Only DattorroReverb and Revamp (EQ) work in offline render. For all other processing,
pre-process stems with pedalboard (Python) before importing to openDAW.

## Environment

- Venv: `/tmp/audio_analysis_venv/bin/python` — has pedalboard 0.9.23, pyloudnorm, scipy, soundfile
- Recreate: `songsee/scripts/setup_audio_venv.sh`

## Pedalboard API (verified July 2026)

### Available plugins
```
Bitcrush, Chain, Chorus, Clipping, Compressor, Convolution, Delay, Distortion,
Gain, GSMFullRateCompressor, HighShelfFilter, HighpassFilter, IIRFilter, Invert,
LadderFilter, Limiter, LowShelfFilter, LowpassFilter, Mix, MP3Compressor,
NoiseGate, PeakFilter, Phaser, PitchShift, Reverb, Resample
```

### Key plugins and their parameters

| Plugin | Parameters | Notes |
|--------|-----------|-------|
| `Distortion` | `drive_db` | NO built-in oversampling — aliasing above Nyquist/2 |
| `PeakFilter` | `cutoff_frequency_hz`, `gain_db`, `q` | NOT `PeakingFilter` — name is `PeakFilter` |
| `Compressor` | `threshold_db`, `ratio`, `attack_ms`, `release_ms` | No makeup gain parameter — use `Gain` after |
| `Chorus` | `rate_hz`, `depth`, `centre_delay_ms`, `feedback`, `mix` | Single-tap, basic |
| `Phaser` | `rate_hz`, `centre_frequency_hz`, `depth`, `feedback`, `mix` | |
| `Delay` | `delay_seconds`, `feedback`, `mix` | Simple, no tempo sync |
| `Limiter` | `threshold_db`, `release_ms` | NOT true-peak — needs oversampling wrapper |
| `Resample` | `target_sample_rate`, `quality` | Quality: WindowedSinc128 (best), WindowedSinc64, Linear, etc. |
| `LowpassFilter` | `cutoff_frequency_hz` | For anti-aliasing after oversampled distortion |

### VST3 support
`pedalboard.load_plugin()` and `VST3Plugin` exist — can load external VST3 plugins.
No VST3 plugins installed on this system. All processing uses built-in pedalboard plugins.

## Anti-aliased saturation (SOTA approach)

Pedalboard `Distortion` has no oversampling → aliasing. Manual 4x oversampling:

```python
from pedalboard import Pedalboard, Distortion, LowpassFilter, Resample

SR = 48000
OS_FACTOR = 4
SR_OS = SR * OS_FACTOR

bass_board = Pedalboard([
    Resample(target_sample_rate=SR_OS, quality=Resample.Quality.WindowedSinc128),
    Distortion(drive_db=6.0),
    LowpassFilter(cutoff_frequency_hz=SR/2 * 0.9),  # anti-alias LPF
    Resample(target_sample_rate=SR, quality=Resample.Quality.WindowedSinc128),
    PeakFilter(cutoff_frequency_hz=300, gain_db=2.0, q=1.4),  # fill 200-400Hz dip
])

# Process: pedalboard expects (channels, samples) shape
processed = bass_board(audio.T, sr).T  # back to (samples, channels)
```

## Gain staging

**WRONG: RMS-matching after saturation.** Saturation adds harmonics → RMS goes up →
if you normalize back to original RMS, the spectral change disappears in band analysis.
Saturation SHOULD make the stem louder in harmonic content.

**CORRECT: gain staging with headroom.**
1. Attenuate -6dB before processing (headroom for distortion peaks)
2. Process
3. Restore +6dB
4. Safety clip at -1.0
5. Do NOT RMS-match — let the harmonic content stay

**CORRECT: RMS-matching for compression.** Compressor changes dynamics, not spectral
content. Normalize output RMS to input RMS + add makeup gain separately if desired.

## Per-stem processing recipes (Серебро F11)

### Bass (bass_sat.wav)
- 4x oversampled Distortion drive_db=+6
- PeakFilter 300Hz +2dB Q=1.4 (fill low-mid pocket)
- Result: lowmid +1.2dB, THD 89.8%→96.7%, RMS unchanged (with wrong RMS-match)
- Note: drive +3 with RMS-match = zero spectral change. drive +6 without RMS-match = visible.

### Drums (drums_comp.wav)
- Compressor threshold -18dB, ratio 3:1, attack 3ms, release 80ms
- Makeup gain to match original RMS
- Result: pres +2dB, hats +2.8dB, peak -4.6→-2.2 (makeup raises peak)

### Synths (synth_mod_0/1.wav)
- Chorus: rate 0.3Hz, depth 0.5, centre_delay 15ms, feedback 0.1, mix 0.3
- Phaser: rate 0.15Hz, centre 800Hz, depth 0.3, feedback 0.2, mix 0.2
- Parallel: chorus×0.6 + phaser×0.4
- Note: chorus/phaser are temporal effects — they change phase/movement, not spectral energy.
  Spectral analysis shows ~0 delta. Ear may hear movement. RMS-matched.

### Vocals (vocal_delay_0/1.wav)
- Delay 273ms (1/8 @ 110BPM), feedback 0.15, mix 0.15
- Subtle slap-back. RMS-matched. Spectral delta ~0 at 15% mix.

## Verification

Always measure before/after:
- RMS, peak, LUFS (pyloudnorm)
- Band energy (Welch PSD, 10 bands: sub/bass/lowmid/mid/uppermid/pres/sibilance/hats/air/sparkle)
- THD estimate (harmonic region vs fundamental)
- True-peak (4x oversampled peak detection)

## Key lesson

F10 vs F11 comparison: pedalboard SOTA processing (4x OS distortion, chorus, phaser, delay)
produced spectral deltas within noise of F10. The single-variable changes were too subtle.
The real improvement came from mastering (F12): LR4 multiband + M/S EQ + true-peak limiter.
