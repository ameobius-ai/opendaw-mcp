# BandLab Mastering Presets — Reverse-Engineered (July 2026)

## Source

BandLab mastering is server-side DSP. Client sends: `preset` (slug), `intensity` (0-1),
`inputGain`, `lowFreqGain`, `midFreqGain`, `highFreqGain`, `eqBypass`, `bypass`.

Reverse-engineered via spectral comparison of before/after demo audio pairs
hosted on bandlab.com CDN (8 presets × 2 files = 16 m4a files).

## 8 Presets

| Preset | slug | shortDescription | Engineer | LUFS Δ | peak Δ | crest Δ | width Δ | centroid Δ |
|--------|------|-----------------|----------|--------|--------|---------|---------|------------|
| Universal | cdMaster | Natural dynamic and tonal balancing | Mike Tucci (Masterdisk NYC) | +2.3 | +0.9 | -1.5 | +0.7 | +55 |
| Fire | bassBoostMastering | Punchy lows and midrange clarity | — | +6.6 | +2.0 | -7.0 | -8.9 | -177 |
| Clarity | enhanceClarity | Pristine highs with light dynamic expansion | — | -1.3 | -1.2 | -0.2 | +0.1 | +17 |
| Tape | tapeMaster | Warm saturation with analog dynamics | — | +3.0 | +0.4 | -2.5 | +1.2 | +21 |
| Natural | naturalMastering | Balanced dynamics and gentle compression | Maria Elisa Ayerbe | +7.3 | +3.7 | -3.7 | 0.0 | -39 |
| Spatial | spatialMastering | Atmospheric reverb and enhanced stereo width | — | +6.8 | +4.1 | -2.5 | +7.4 | +200 |
| Cinematic | cinematicMastering | Intense saturation and harmonic distortion | — | +4.4 | +4.5 | +0.1 | +0.1 | +3 |
| Punch | punchMastering | Energetic bass combined with boosted highs | Will Quinnell (Sterling Sound) | +7.3 | +4.3 | -2.6 | +7.2 | +628 |

## EQ Curves (band deltas in dB)

### Universal — flat balance, gentle everything
```
sub:      +2.3   bass:    +2.3   lowmid:  +2.4   mid:      +2.4
uppermid: +2.5   pres:    +2.7   sibilance: +3.0  hats:    +3.3
air:      +3.7   sparkle: +4.4
```
Nearly flat with slight high-frequency tilt. Least aggressive. Good default.

### Fire — midrange focus, heavy compression, NARROWS stereo
```
sub:      +5.8   bass:    +7.2   lowmid:  +7.3   mid:      +7.2
uppermid: +6.7   pres:    +5.7   sibilance: +4.2  hats:    +2.8
air:      +1.6   sparkle: -1.0
```
Boosts low-mid, cuts air. Crest -7 = aggressive compression. Width -8.9 = mono-fies.
For dense, loud, in-your-face mixes. NOT for coldwave (kills stereo and air).

### Clarity — UNIQUE: makes QUIETER, not louder
```
sub:      -1.0   bass:    -1.0   lowmid:  -1.1   mid:      -1.0
uppermid: -1.0   pres:    -1.0   sibilance: -0.8  hats:    -0.6
air:      -0.3   sparkle: +0.4
```
Only preset with negative LUFS. Attenuates everything except sparkle.
Spectral repair / enhancement, not loudness maximization.

### Tape — warm, analog, gentle
```
sub:      +3.0   bass:    +3.3   lowmid:  +3.3   mid:      +3.2
uppermid: +3.1   pres:    +3.0   sibilance: +2.8  hats:    +2.6
air:      +2.3   sparkle: +2.0
```
Nearly uniform +3dB with slight low-tilt. Saturation character (crest -2.5).
Width +1.2 = slightly wider. Warm, vintage.

### Natural — loudest, neutral spectrum
```
sub:      +7.0   bass:    +7.2   lowmid:  +7.1   mid:      +7.0
uppermid: +6.9   pres:    +6.8   sibilance: +6.6  hats:    +6.4
air:      +6.2   sparkle: +5.9
```
Uniform +7dB = pure loudness, no EQ character. Compression -3.7 crest.
The "just make it louder" preset.

### Spatial — stereo widening + reverb
```
sub:      +5.5   bass:    +6.0   lowmid:  +6.3   mid:      +6.5
uppermid: +6.7   pres:    +7.0   sibilance: +7.4  hats:    +7.7
air:      +8.0   sparkle: +8.5
```
High-frequency tilt (+8.5 sparkle). Width +7.4 = strongest stereo widening.
Atmospheric, ambient. Good for coldwave reverb character.

### Cinematic — uniform lift, no compression
```
sub:      +2.3   bass:    +4.8   lowmid:  +4.4   mid:      +4.3
uppermid: +4.2   pres:    +5.2   sibilance: +6.6  hats:    +7.1
air:      +7.7   sparkle: +11.5
```
Crest +0.1 = NO compression. Pure harmonic enhancement. Sparkle +11.5 = biggest HF lift.
Saturation/distortion character without dynamic control.

### Punch — most aggressive, sub + sparkle
```
sub:      +12.1  bass:    +8.6   lowmid:  +5.2   mid:      +5.5
uppermid: +7.7   pres:    +11.2  sibilance: +15.0  hats:   +15.6
air:      +17.2  sparkle: +17.6
```
Sub +12, sparkle +17.6. Widest EQ curve. Width +7.2 = strong stereo.
Centroid +628Hz = massive spectral shift upward. For energetic bass+high tracks.

## Key Insights for Our Pipeline

1. **BandLab presets are NOT adaptive** — fixed DSP chains tuned by engineers. No AI.
2. **LUFS targets vary wildly**: Clarity -1.3 (quieter!) vs Natural/Punch +7.3.
   BandLab does NOT target -14 LUFS — they let presets decide loudness.
3. **Crest factor is the key differentiator**: Fire -7.0 (squashed) vs Cinematic +0.1 (no compression).
   Our F12 had crest 3.0 — too compressed. BandLab Universal keeps 14-15.
4. **Stereo width is a preset feature, not a master-only thing**: Spatial +7.4, Punch +7.2.
   Our M/S processing added width but not at this magnitude.
5. **Clarity is unique** — it's a spectral repair tool, not a loudness maximizer.
   Could be useful for fixing muddy mixes without changing loudness.

## Hybrid Preset for Coldwave (proposed)

Combine: Natural (LUFS target) + Punch (sub boost) + Cinematic (sparkle lift) + Spatial (width)
But keep crest 8-12, not 3. Our F12 over-compressed.

## Demo audio URLs (for future reference)

All at: `https://www.bandlab.com/web-app/common/static/`
- universal: kpop4u-mastered/unmastered
- fire: space-juice-mastered/unmastered
- clarity: fuchsia-days-mastered/unmastered
- tape: tape-mastered/unmastered
- natural: natural-mastered/unmastered
- spatial: spatial-mastered/unmastered
- cinematic: cinematic-mastered/unmastered
- punch: punch-mastered/unmastered
