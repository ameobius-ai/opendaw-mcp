---
name: opendaw-audio-engineer
description: Audio engineering methodology for opendaw-mcp. When to use FET vs VCA compression, how to read crest factor, when a mix is ready for mastering, genre-specific decision-making.
---

# Audio Engineer Methodology

## Decision Framework: Mix Readiness

Before mastering, verify:
- **LUFS**: -16 to -10 LUFS depending on genre (see genre profiles)
- **True peak**: below -1.0 dBTP (no clipping)
- **Crest factor**: 6-12 dB (too low = over-compressed, too high = inconsistent)
- **Phase correlation**: > 0.3 overall (check bass region especially)
- **Spectral centroid**: within genre target range

Use `render_and_analyze` → check these before proceeding to master.

## Compressor Type Selection

| Type | Sound | When to use | Attack | Release |
|------|-------|-------------|--------|---------|
| FET | Punchy, fast | Drums, vocals, parallel | 1-10ms | 50-150ms |
| Opto (LA-2A) | Smooth, musical | Bass, vocals glue | program-dependent | program-dependent |
| VCA | Transparent | Bus, mix glue | 10-30ms | 100-300ms |
| Vari-Mu | Warm, vintage | Master bus, glue | 20-50ms | 200-500ms |

In openDAW: Compressor effect has threshold, ratio, attack, release.
For FET-style: fast attack (5ms), fast release (80ms), ratio 4:1.
For glue: slow attack (20ms), auto release, ratio 2:1.

## Reading Analysis Results

### Crest Factor (dynamics)
- > 15 dB: very dynamic (classical, jazz) — likely needs compression
- 10-15 dB: natural dynamics — good for most genres
- 6-10 dB: controlled — good for pop, rock
- < 6 dB: over-compressed — reduce compression

### Spectral Centroid
- < 1000 Hz: very dark/muddy — boost highs
- 1000-2500 Hz: warm — good for lo-fi, cinematic
- 2500-4000 Hz: balanced — good for pop, rock
- > 4000 Hz: bright — good for EDM, pop
- > 6000 Hz: harsh — cut highs

### LUFS by Platform
- Spotify: -14 LUFS (turns down louder tracks)
- Apple Music: -16 LUFS
- YouTube: -14 LUFS
- CD: no target
- Club: -8 to -6 LUFS

## Frequency Masking Quick Guide

Common conflicts and solutions:
1. **Kick + Bass (60-120 Hz)**: Sidechain, or EQ kick's fundamental vs bass fundamental
2. **Bass + Guitar (200-400 Hz)**: Cut guitar at 250 Hz
3. **Vocal + Guitar (2-4 kHz)**: Cut guitar at 3 kHz, boost vocal at 3 kHz
4. **Snare + Lead (1-3 kHz)**: Pan apart or cut lead at 2 kHz
5. **Multiple synths (200-800 Hz)**: Assign each a frequency pocket

Use `detect_frequency_masking` after `export_stems` to find conflicts.

## Mix Workflow (opendaw-mcp)

1. **Compose** — create instruments, program MIDI, set BPM
2. **Arrange** — structure: intro→verse→chorus→bridge→outro
3. **Gain stage** — set all channel volumes to -6 to -3 dB
4. **EQ per channel** — cut problem frequencies (use `detect_problems`)
5. **Compression** — add per-channel compressors (use `add_bass_chain`, `add_drum_chain`, `add_vocal_chain`)
6. **Bus routing** — group channels, add bus compression
7. **Master** — `add_mastering_chain` or `auto_master`
8. **Verify** — `render_and_analyze` → check LUFS, spectral, problems
9. **Iterate** — fix issues from analysis, re-render, re-verify

## When to Send Back

A mix is NOT ready for mastering if:
- Clipping detected (detect_problems → clipping)
- Phase correlation < 0 (analyze_phase)
- LUFS > -6 (over-limited, no room for mastering)
- Spectral mud > 30% in low_mids (detect_problems → mud)
- Dynamic range < 4 dB crest (over-compressed)
