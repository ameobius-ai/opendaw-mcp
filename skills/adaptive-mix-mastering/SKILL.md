---
name: adaptive-mix-mastering
description: "Universal AI-driven mix→master pipeline with decision points. Agent analyzes input, selects genre strategy, stem count, effect chain, LUFS target, and mastering approach. openDAW MCP + pedalboard + pyloudnorm. Adapts to any genre — coldwave, techno, hip-hop, ambient, rock, pop."
tags: [audio, mixing, mastering, opendaw, adaptive, pipeline, ai-driven, pedalboard, pyloudnorm]
---

# Adaptive Mix→Master Pipeline

Универсальный пайплайн сведения и мастеринга где агент сам выбирает развилки.
Не привязан к жанру — анализирует вход, определяет стратегию, применяет.

## Когда использовать

- Юзер приносит трек (Suno WAV, стемы, или готовый микс) и хочет его свести/смастерить
- Юзер говорит "сведи", "смастери", "сделай микс", "доведи трек"
- Юзер даёт стемы и хочет финальный мастер
- Юзер хочет E2E: от сырых стемов до готового WAV/MP3

## Архитектура: 5 стадий × decision points

```
Input → [S1: Analyze] → [S2: Stem Strategy] → [S3: Mix] → [S4: Master] → [S5: Deliver]
              ↓              ↓                    ↓           ↓              ↓
         genre detect    stem count        effect chain   LUFS target    format
         BPM detect      split method      pan strategy   crest target   cleanup
         key detect      anchor choice     saturation     EQ approach    stems export
         LUFS measure    venv setup        sidechain      limiter?       folder org
```

## Stage 1: Analyze (ВСЕГДА сначала)

**Принцип: никогда не предлагай EQ/микс без анализа.** Сначала данные, потом решения.

### Анализ входа

```bash
# Analysis venv (librosa + pyloudnorm + pedalboard)
VENV=/tmp/audio_analysis_venv/bin/python
# Recreate after reboot: bash <songsee_dir>/scripts/setup_audio_venv.sh

# Full analysis (LUFS, true peak, crest, 7-band RMS, stereo)
$VENV <songsee_dir>/scripts/full_track_analysis.py input.wav

# Compare two versions
$VENV <songsee_dir>/scripts/full_track_analysis.py new.wav --compare old.wav

# Per-stem band analysis
$VENV <songsee_dir>/scripts/band_energy_analysis.py stem.wav
```

### Decision Point: Genre Detection

Агент определяет жанр по признакам. Не угадывает — читает метрики:

| Signal | Metric | How to read |
|--------|--------|-------------|
| BPM | librosa.beat.tempo | <100=slow/ballad, 100-130=rock/pop, 120-140=techno, 140-180=DnB, 70-90=hip-hop |
| Spectral balance | 7-band RMS | bass-dominant=electronic/hip-hop, mid-dominant=rock/vocal, air-dominant=ambient |
| Crest factor | crest = peak - LUFS | >15=dynamic(jazz/classical), 10-15=balanced, <10=loud/compressed |
| Stereo width | correlation | >0.8=narrow(mono-ish), 0.3-0.7=normal, <0.3=wide/phasey |
| LUFS | integrated | -23=quiet(raw), -18=pre-mix, -14=mastered, -8=loud/clipping |

### Decision Point: Genre Profile

После анализа агент выбирает профиль. Профиль = набор целей, не жёсткая процедура.

**Профили (не исчерпывающие — агент может создавать новые):**

| Genre | BPM | LUFS target | Crest target | Stereo | Character |
|-------|-----|-------------|--------------|--------|-----------|
| Coldwave/Darksynth | 90-120 | -14 | 10-13 | wide (corr 0.5-0.7) | scooped mids, dark, dense |
| Techno | 125-135 | -9 to -11 | 6-9 | wide | driving, sub-heavy, compressed |
| Hip-hop | 70-90 | -10 to -12 | 8-12 | narrow-center | vocal forward, sub-bass, 808 |
| Ambient | 60-90 | -16 to -20 | 14-18 | very wide | spacious, air-dominant, dynamic |
| Rock | 100-140 | -12 to -14 | 10-14 | center-focused | guitar-forward, mid-dominant |
| Pop | 100-130 | -10 to -12 | 8-11 | wide | vocal forward, balanced spectrum |
| DnB/Neurofunk | 160-180 | -9 to -11 | 6-9 | wide | sub + breakbeats, aggressive |

**ВАЖНО:** это ориентиры, не догма. Агент корректирует по треку. Если coldwave трек уже на -14 LUFS с crest 16 — не продавливай через tanh. Если pop трек звучит dense при -12 — не добавляй лимитер.

## Stage 2: Stem Strategy

### Decision Point: Stem Count

| Input type | Stems | Method |
|------------|-------|--------|
| Suno WAV (full track) | 4-7 | Demucs/BS-Roformer split |
| Already separated stems | as-is | skip split |
| Single instrument | 1 | no split, direct process |
| Mix that needs rebalancing | 4-6 | Demucs (bass/drums/vocals/other) |

### Decision Point: Split Method

**MCP tool (preferred — agent-native, auto-imports into DAW):**
```python
# mcp_opendaw_split_stems(input_path, mode, import_to_daw=True)
# 7 modes: ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise
# Returns stem file paths + sample IDs (if import_to_daw=True)

# Fast 6-stem split + auto-import into DAW
mcp_opendaw_split_stems("track.wav", mode="bs6", import_to_daw=True)
# → 6 stems loaded, sample_ids returned for place_audio_region

# Max quality ensemble
mcp_opendaw_split_stems("track.wav", mode="ensemble", import_to_daw=True)
# → 4 specialist stems (bass 11.96 SDR, drums 11.13, vocals 11.00, other)

# Vocal-only extraction
mcp_opendaw_split_stems("track.wav", mode="polarformer")
# → 1 stem (vocals, SDR 11.00)
```

**CLI (when DAW not running):**
```bash
SPLIT=~/projects/creative-studio/stem-splitter/venv/bin/python
SCRIPT=~/projects/creative-studio/stem-splitter/sota_splitter.py

# Fast (6 stems one pass, 15s for 30s audio)
$SPLIT $SCRIPT input.wav -o /tmp/stems -m bs6

# Max quality (ensemble — specialist per stem, ~4.5min for 4-min track)
$SPLIT $SCRIPT input.wav -o /tmp/stems -m ensemble

# Vocal dereverb (run AFTER polarformer, on vocals.wav)
$SPLIT $SCRIPT /tmp/stems/vocals.wav -o /tmp/dry -m dereverb

# Drum separation (run AFTER scnet/bs6, on drums.wav)
$SPLIT $SCRIPT /tmp/stems/drums.wav -o /tmp/drumkit -m drumsep
```

**Mode selection:**
| Need | Mode | Stems | Speed |
|------|------|-------|-------|
| Final mix (max quality) | ensemble | 4 | slowest (3 passes) |
| Quick 4-stem | scnet | 4 | medium |
| 6 stems (guitar/piano) | bs6 | 6 | fast |
| Vocals only | polarformer | 1 | fast |
| Dry vocals | dereverb | 2 | fast (run on vocals.wav) |
| Drum kit breakdown | drumsep | 4 | medium (run on drums.wav) |
| Clean noisy MP3 | denoise | 2 | fast (run before split) |

### Decision Point: Anchor Strategy

| Situation | Anchor | Level |
|-----------|--------|-------|
| Suno track (has vocal) | cover/original | -10 dB, HPF+LPF |
| Instrumental | original | -12 dB, HPF only |
| Already separated | none | — |
| Dense mix (needs glue) | original | -8 dB, wide filter |

### Stem cleanup (if needed)

- PolarFormer pre-start bleed: zero vocal stems ONLY (not all stems)
- DC offset: `werkstatt_dcremover.js` or pedalboard HighpassFilter
- Silence trim: pyloudnorm or librosa.effects.trim

## Stage 3: Mix (openDAW or pedalboard)

### Decision Point: Mix Engine

| When | Engine | Why |
|------|--------|-----|
| User says "opendaw" / "наш mcp" | openDAW MCP | agent-native, 385 tools, real-time |
| User says "быстро" / "pedalboard" | pedalboard Python | faster, no browser needed |
| Default (no preference) | openDAW | user built it, prefers it (lesson #16) |

### openDAW mix workflow

```python
# MCP tools (377 available, key ones for mixing):
# mcp_opendaw_create_audio_track() → track index
# mcp_opendaw_load_audio(file_path, name) → sample_id
# mcp_opendaw_create_audio_clip(sample_id, unit_idx, clip_idx, track_idx, bpm)
# mcp_opendaw_add_effect(unit_idx, effect_type) → effect_idx
# mcp_opendaw_set_effect_parameter(unit_idx, effect_idx, param_name, value)
# mcp_opendaw_set_track_volume(track_idx, db)
# mcp_opendaw_set_track_pan(track_idx, pan)  # -1.0..+1.0
# mcp_opendaw_create_send(...) → reverb/delay sends
# mcp_opendaw_render_audio(...) → WAV output
```

### Decision Point: Effect Chain

Агент строит chain по жанру и анализу. НЕ копирует coldwave chain — адаптирует.

**Bass treatment:**
| Genre | Approach | Tool |
|-------|----------|------|
| Coldwave/Industrial | hardclip saturation | Waveshaper +6dB/0.6 mix |
| Techno/House | gentle sat + sub boost | pedalboard or DarkSat script |
| Hip-hop | clean sub + 808 | minimal, EQ only |
| Rock | amp sim | NeuralAmp or Waveshaper |
| Pop | transparent | EQ only |

**Vocal treatment:**
| Genre | Reverb | Delay | Compression |
|-------|--------|-------|-------------|
| Coldwave | DattorroReverb, damping 0.2, wet -10 | none | gentle |
| Pop | plate, wet -6 | slap -20ms | medium |
| Hip-hop | room, wet -14 | quarter @-18 | aggressive |
| Rock | hall, wet -8 | none | medium |
| Ambient | shimmer, wet -4 | dotted @-12 | transparent |

**Drum treatment:**
| Genre | Approach | Sidechain? |
|-------|----------|------------|
| Electronic | parallel comp + EQ | yes (drums→bass) |
| Acoustic | gentle comp, EQ | no |
| Hip-hop | transient preserve, 808 sidechain | 808→bass |
| Rock | room reverb, parallel comp | no |

### Decision Point: Pan Strategy

| Stem | Default pan | Adjustment |
|------|-------------|------------|
| Bass | center (0.0) | always center |
| Kick | center (0.0) | always center |
| Snare | center ±0.2 | slight |
| Vocals | ±0.5-0.7 (if stereo pair) | genre-dependent |
| Synths/Other | ±0.7-0.9 | wide for electronic |
| Guitars | ±0.6-0.8 (L/R pair) | hard for rock |
| Hats | ±0.3-0.5 | natural spread |

**ВАЖНО:** Suno Studio render collapses stereo (correlation 0.84+). Pan in openDAW/pedalboard, NOT Suno Studio.

### Decision Point: Sidechain

| When | How |
|------|-----|
| Electronic with kick+bass | drums→bass compressor: threshold -20, ratio 4, attack 5ms, release 80ms |
| Hip-hop with 808 | 808→bass or just EQ carve |
| No kick-bass conflict | skip sidechain |

openDAW sidechain: `p.boxGraph.registerEdge(sourceAu.audioEffects.output, compEffect.sideChain)`

## Stage 4: Master

### Decision Point: LUFS Target

| Platform | Target | Notes |
|----------|--------|-------|
| Spotify | -14 LUFS | standard streaming |
| YouTube | -14 LUFS | same as Spotify |
| Apple Music | -16 LUFS | quieter |
| SoundCloud | -10 to -12 | louder OK |
| Club/Festival | -8 to -10 | loud, compressed |
| User preference | ASKED | always honor |

### Decision Point: Mastering Approach

**КРИТИЧНО: если микс уже на target LUFS — не мастера агрессивно.** Lesson #28: don't over-master.

| Mix state | Approach | Tools |
|-----------|----------|-------|
| LUFS at target, crest >14 | ceiling only (-1.0 dBTP scale) | pyloudnorm gain |
| LUFS at target, crest 10-14 | gentle saturation + ceiling | tanh drive 1.5, scale |
| LUFS below target, crest >14 | saturation → gain → ceiling | tanh + pyloudnorm |
| LUFS below target, crest <10 | gain → limiter (watch pumping!) | pedalboard Limiter or iterative |
| LUFS above target | scale down only | pyloudnorm gain |

### Mastering chain (adaptive)

```python
import numpy as np, pyloudnorm as pyln

# Step 1: Saturation (ONLY if crest > 12 and needs density)
if crest > 12:
    drive = 1.5 if genre == "pop" else 3.0 if genre == "coldwave" else 2.0
    driven = mix * drive
    saturated = np.tanh(driven) / np.tanh(drive)
else:
    saturated = mix

# Step 2: Iterative LUFS gain (converges 2-3 iterations)
meter = pyln.Meter(sr)
target_lufs = -14.0  # adjust per platform
work = saturated.copy()
for i in range(5):
    cur = meter.integrated_loudness(work.mean(axis=1))
    delta = target_lufs - cur
    if abs(delta) < 0.2: break
    work = work * (10 ** (delta / 20))

# Step 3: Ceiling (no limiter if possible)
CEILING = 10 ** (-1.0 / 20)  # -1.0 dBTP
peak = np.max(np.abs(work.mean(axis=1)))
if peak > CEILING:
    work = work * (CEILING / peak)

# Step 4: Limiter ONLY if crest still > ceiling after gain
# WARNING: pedalboard Limiter pumps LUFS +2-3 above target
# Use ONLY as last resort, then re-measure and scale down
```

### Decision Point: Master EQ

EQ approach зависит от спектрального анализа, не от жанра догмы:

| Problem (from analysis) | Fix |
|-------------------------|-----|
| Subsonic rumble (<30 Hz) | HPF 30 Hz Q 0.7 12 dB/oct |
| Low-mid hole (200-500 Hz) | lowBell@350 +2 dB Q 1.2 (gentle — genre-typical in some) |
| Mid dip (2-6 kHz) | midBell@3k +2 dB Q 0.8 |
| Lack of presence | highShelf@8k +3-4 dB |
| Lack of air | highShelf@12k +8-12 dB |
| Need sparkle | highBell@16k +3 dB Q 2.0 |
| Sub boom (>80 Hz excess) | lowShelf@80 -2-3 dB |

**Single-variable principle:** ОДИН EQ move за итерацию. Render → measure → suggest next → repeat.

### Verify after master

```bash
$VENV <songsee_dir>/scripts/full_track_analysis.py mastered.wav --compare premaster.wav
```

Check: LUFS at target ±0.3, true peak < -1.0 dBTP, crest in genre range, stereo width maintained.

## Stage 5: Deliver

### Decision Point: Output Format

| User signal | Deliver |
|-------------|---------|
| "дай финал" / "e2e" | mastered WAV + MP3 |
| "дай стемы" | per-stem processed WAVs |
| "дай и то и то" | both |
| "подскажи по эквалайзеру" | EQ advice only (no file) |

### File delivery

```python
# Write to user's Downloads or Desktop
import soundfile as sf, os
out_dir = f"/mnt/c/Users/{username}/Downloads/{track_name}_mastered/"
os.makedirs(out_dir, exist_ok=True)
sf.write(f"{out_dir}/final_master.wav", mastered, sr)
# MP3 via ffmpeg
os.system(f"ffmpeg -i {out_dir}/final_master.wav -q:a 2 {out_dir}/final_master.mp3")
```

### Folder organization (user preference — lesson #23)

```
track_name_mastered/
├── stems_raw/          # unprocessed stems
├── stems_processed/    # with EQ/effects
├── final_master.wav    # mastered
├── final_master.mp3    # compressed
└── analysis.txt        # LUFS, crest, band RMS
```

## Key Lessons (from coldwave sessions, generalized)

1. **Analyze BEFORE suggesting.** Never recommend EQ/mix moves without running the analyzer first. Each track is different.
2. **Single-variable iteration.** ONE change per iteration. 3 changes at once = impossible to tell what worked.
3. **Don't over-master.** If mix already at -14 LUFS with crest >14, mastering = ceiling only. Saturation kills dynamics.
4. **User wants both modes.** E2E ("сделай сам") AND coaching ("подскажи по эквалайзеру"). Read the signal.
5. **Ranges not single values.** Give "-4 to -6 dB", not "-3 dB". User applies ~1/3 of recommendations.
6. **Suno Studio collapses stereo.** Pan in real DAW (openDAW/pedalboard), not Suno Studio.
7. **Pedalboard Limiter pumps LUFS.** +2-3 above target. Use tanh + pyloudnorm + ceiling instead.
8. **openDAW effects work in offline render.** Waveshaper, DattorroReverb, Revamp, Delay, Tidal, Compressor — all verified. Compressor has minor ProcessPhase bug (first block ~0.01s, inaudible).
9. **Maximizer at effect index 0.** Find effects by class name, not hardcoded index.
10. **Credential persistence is step 1.** Save tokens immediately when user provides them.
11. **Stem splitter is persistent.** ~/projects/creative-studio/stem-splitter/ survives reboot. /tmp does not.
12. **bs6 "guitar" stem = catch-all.** Stem names are model labels, not instrument detectors. Check RMS per stem.

## Tooling Reference

### Venvs
- **Analysis**: `/tmp/audio_analysis_venv/bin/python` (librosa, pyloudnorm, pedalboard, matplotlib). Recreate: `bash <songsee_dir>/scripts/setup_audio_venv.sh`
- **Stem splitter**: `~/projects/creative-studio/stem-splitter/venv/bin/python` (torch, demucs, MSST). Persistent.
- **openDAW MCP**: `~/projects/creative-studio/agent-daw/opendaw-mcp/venv/` (server.py, 385 tools)

### openDAW MCP
- Server: `~/projects/creative-studio/agent-daw/opendaw-mcp/server.py`
- Headless: `~/projects/creative-studio/agent-daw/headless-daw/` (Vite port 5174)
- 386 MCP tools, 80+ orchestration tools, 110 DSP scripts
- See `opendaw-automation` skill for full API reference (385 tools)

### DSP Scripts (108 available)
- 15 Werkstatt (audio effects): darksat, coldfold, reverb, chorus, phaser, lookahead, shimmer, paulstretch, envfollower, adsr_trim, granular, pitch_shift, dcremover, allpass, ringmod_env
- 9 Apparat (instruments): darkbass, coldlead, subcrusher, ringmod, fm
- 10 Spielwerk (MIDI effects): arpeggiator, powerchord, chordmemory, strum, velocity, mididelay

### Related skills
- `opendaw-automation` — 386 MCP tools API reference
- `coldwave-mix-mastering` — coldwave-specific session log (F01→F12, Glass.wav)
- `stem-splitter-local` — SOTA stem separation (Demucs, BS-Roformer, MSST)
- `songsee` — audio analysis CLI (spectrograms, features)
- `suno-studio-stem-mixing` — Suno Studio stem mixing workflow
