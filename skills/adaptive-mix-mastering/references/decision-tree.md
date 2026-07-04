# Decision Tree — Adaptive Mix→Master

Полный алгоритм выбора для агента на каждой стадии пайплайна.
Агент читает метрики → проходит дерево → принимает решение.

## S1: Analyze → Genre Detection

```
INPUT: WAV file
  ↓
Run full_track_analysis.py
  ↓
Read: BPM, LUFS, crest, 7-band RMS, stereo correlation
  ↓
BPM < 80?
  ├─ YES → bass-dominant? → hip-hop / trap
  ├─ NO → BPM 80-100?
  │   ├─ YES → air-dominant? → ambient / chillout
  │   ├─ NO → mid-dominant + crest>14? → ballad / acoustic
  │   └─ NO → bass-dominant + crest<12? → lo-fi / downtempo
  └─ NO → BPM 100-130?
      ├─ YES → scooped mids + corr<0.7? → coldwave / darksynth
      ├─ NO → vocal-forward + balanced? → pop / indie
      └─ NO → guitar-forward + mid-dominant? → rock / alt
      ↓
  BPM 130-150?
      ├─ YES → sub-heavy + crest<10? → techno / house
      └─ NO → BPM >150?
          ├─ YES → sub + breaks? → DnB / neurofunk
          └─ NO → aggressive + fast? → metal / punk
```

## S2: Stem Strategy

```
INPUT: genre profile + source type
  ↓
Source = single WAV (full mix)?
  ├─ YES → Need stem separation
  │   ↓
  │   User wants max quality?
  │   ├─ YES → ensemble_split.py (HTDemucs FT per stem)
  │   └─ NO → bs6_full.py (6 stems one pass, faster)
  │   ↓
  │   Vocal present?
  │   ├─ YES → use PolarFormer for vocals (best SDR)
  │   └─ NO → skip vocal stem
  │   ↓
  │   Anchor: original track at -10 dB, HPF 40Hz + LPF 16kHz
  │
  ├─ NO → Source = separated stems?
  │   ↓
  │   Count stems
  │   ↓
  │   Run band_energy_analysis.py per stem
  │   ↓
  │   Skip split, go to mix
  │
  └─ NO → Source = single instrument?
      ↓
      No split needed, direct to master (skip S3)
```

## S3: Mix → Effect Chain

```
INPUT: stems + genre profile + analysis
  ↓
Mix engine?
├─ User said "opendaw" → openDAW MCP (263 tools)
├─ User said "pedalboard" / "быстро" → pedalboard Python
└─ No preference → openDAW (user built it)
  ↓
Per-stem EQ (from band analysis):
  ↓
Bass stem:
  ├─ 80-200 Hz dominant? → leave, maybe +1 dB shelf at 60
  ├─ 200-500 Hz hole? → lowBell@350 +2 Q 1.2 on master
  └─ Sub boom? → lowShelf@80 -3 dB
  ↓
Vocal stem:
  ├─ 200-500 Hz dominant (normal)? → HPF 80, de-ess if needed
  ├─ 2-6 kHz dip? → presence boost on master
  └─ Air < -40 dB? → highShelf@12k on master
  ↓
Drum stem:
  ├─ Kick + bass conflict? → sidechain drums→bass
  │   └─ threshold -20, ratio 4, attack 5ms, release 80ms
  └─ No conflict? → parallel comp only
  ↓
Saturation (genre-dependent):
  ├─ Coldwave/Industrial → Waveshaper hardclip on bass: +6dB/0.6 mix
  ├─ Techno → DarkSat script: drive 0.5-0.7
  ├─ Hip-hop → minimal, clean sub
  ├─ Rock → NeuralAmp or Waveshaper on guitars
  └─ Pop → transparent, EQ only
  ↓
Reverb (genre-dependent):
  ├─ Coldwave → DattorroReverb: decay 0.7, damping 0.2, wet -10
  ├─ Pop → plate: decay 0.5, wet -6
  ├─ Hip-hop → room: decay 0.3, wet -14
  ├─ Rock → hall: decay 0.8, wet -8
  └─ Ambient → shimmer: decay 0.9, wet -4
  ↓
Pan (stereo layout):
  ├─ Bass → 0.0 (always center)
  ├─ Kick → 0.0 (always center)
  ├─ Vocals → ±0.5-0.7 (if stereo pair)
  ├─ Synths/Other → ±0.7-0.9
  └─ Guitars → ±0.6-0.8
  ↓
Render → measure → compare to targets
```

## S4: Master → Approach Selection

```
INPUT: rendered mix + genre profile + platform target
  ↓
Measure: LUFS, crest, true peak, band RMS, stereo
  ↓
LUFS already at target (±1)?
├─ YES → crest > 14?
│   ├─ YES → ceiling only: pyloudnorm gain to exact, scale to -1.0 dBTP
│   │         NO saturation, NO limiter (lesson #28)
│   └─ NO → gentle: tanh drive 1.5 → gain → ceiling
│
└─ NO → LUFS below target?
    ↓
    Crest > 12?
    ├─ YES → saturation needed
    │   ↓
    │   Genre?
    │   ├─ Coldwave/Industrial → tanh drive 3.0 (dense, crest→10)
    │   ├─ Pop → tanh drive 1.5 (gentle, crest→12)
    │   ├─ Techno → tanh drive 2.5 (driving, crest→8)
    │   └─ Ambient → NO saturation (preserve dynamics, crest>14)
    │   ↓
    │   tanh → iterative pyloudnorm gain → ceiling
    │
    └─ NO → crest already < 12
        ↓
        Gain to target → check peak
        ├─ Peak < -1.0 dBTP? → done (no limiter needed)
        └─ Peak > -1.0 dBTP? → limiter as LAST RESORT
            ↓
            WARNING: pedalboard Limiter pumps LUFS +2-3
            → use iterative: limiter → measure → scale down → re-measure
            → OR: just scale to ceiling and accept lower LUFS
  ↓
Master EQ (from spectral analysis, NOT genre dogma):
  ↓
  Subsonic rumble? → HPF 30 Hz Q 0.7
  Low-mid hole? → lowBell@350 +2 Q 1.2 (gentle)
  Mid dip? → midBell@3k +2 Q 0.8
  No presence? → highShelf@8k +3-4
  No air? → highShelf@12k +8-12
  Need sparkle? → highBell@16k +3 Q 2.0
  ↓
  ONE EQ move per iteration → render → measure → repeat
  ↓
Verify: LUFS ±0.3 of target, peak < -1.0 dBTP, crest in range, stereo OK
```

## S5: Deliver

```
INPUT: mastered track + user signal
  ↓
User said "e2e" / "сделай сам"?
  ├─ YES → deliver mastered WAV + MP3
  │   ↓
  │   User wants processed stems too?
  │   ├─ YES → export per-stem with EQ/effects
  │   └─ NO → just final master
  │
├─ User said "подскажи по эквалайзеру"?
  │   → analysis + EQ advice (freq, gain, Q, type)
  │   → NO file delivery, just coaching
  │
└─ User said "дай стемы"?
    → per-stem processed WAVs, no master
  ↓
Folder organization:
  track_name_mastered/
  ├── stems_raw/
  ├── stems_processed/
  ├── final_master.wav
  ├── final_master.mp3
  └── analysis.txt
  ↓
Report: what done / how to verify / what changed
```

## Quick Reference: Genre → Default Settings

| Genre | Stems | Bass sat | Reverb | Pan width | LUFS | Crest | Master EQ |
|-------|-------|----------|--------|-----------|------|-------|-----------|
| Coldwave | 7 (anchor+drums+bass+vocal×2+other×2) | hardclip +6/0.6 | Dattorro 0.2 damping, -10 wet | ±0.7-0.85 | -14 | 10-13 | HPF30 + lowBell350 + HS12k+10 |
| Techno | 4-5 (drums+bass+synths+pad) | DarkSat 0.6 | plate 0.4, -8 | ±0.8-0.9 | -10 | 6-9 | HPF30 + LS80-2 + HS12k+6 |
| Hip-hop | 4-5 (drums+808+bass+vocal+sample) | clean, EQ only | room 0.3, -14 | ±0.5-0.7 | -11 | 8-12 | HPF30 + midBell3k+2 |
| Pop | 5-6 (drums+bass+vocal+synth+guitar) | transparent | plate 0.5, -6 | ±0.7-0.9 | -10 | 8-11 | HPF30 + HS8k+3 + HS12k+8 |
| Rock | 5-6 (drums+bass+vocal+guitar×2) | amp sim | hall 0.8, -8 | ±0.6-0.8 | -12 | 10-14 | HPF30 + midBell3k+2 + HS8k+4 |
| Ambient | 3-4 (pad+texture+field) | none | shimmer 0.9, -4 | ±0.9 | -16 | 14-18 | HPF30 + HS12k+6 |
| DnB | 5-6 (drums+bass+sub+atmos+vocal) | sub drive | plate 0.3, -12 | ±0.8-0.9 | -10 | 6-9 | HPF30 + LS80+2 + HS12k+6 |

**Это defaults, не догма.** Агент корректирует по анализу трека.
