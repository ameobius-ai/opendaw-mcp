---
name: opendaw-genres
description: "Genre-specific production templates for openDAW MCP. Concrete parameters per genre — BPM, track layout, drum patterns, bass lines, chord progressions, effect chains, pan, LUFS targets. Techno, coldwave, hip-hop, ambient, DnB, house, lofi, trap. Not theory — actual tool calls and values."
tags: [opendaw, mcp, genres, templates, production, techno, coldwave, hip-hop, ambient, dnb, house, lofi, trap]
---

# openDAW Genre Templates

Жанровые шаблоны с конкретными параметрами. Не теория — реальные tool calls и значения.
Агент выбирает жанр → применяет шаблон → получает рабочий скелет трека.

## Когда использовать

- Юзер называет жанр: «сделай techno», «набросай coldwave», «хочу hip-hop бит»
- Юзер даёт референс: «как у Crystal Castles», «в стиле Burial»
- Нужно быстро создать скелет трека в конкретном жанре
- Нужно понять какие параметры (BPM, эффекты, pan) типичны для жанра

## Как использовать

1. Определить жанр (по прямому названию или по референсу)
2. Применить BPM + time signature
3. Создать track layout (количество и типы треков)
4. Заполнить drum pattern / bass line / chords
5. Навесить effect chain
6. Настроить pan + levels
7. Мастерить под жанровый LUFS target

## Genre Profiles

### Techno

| Parameter | Value |
|-----------|-------|
| BPM | 128-135 |
| Time signature | 4/4 |
| LUFS target | -9 to -11 |
| Crest | 6-9 |
| Stereo | wide (corr 0.5-0.7) |
| Character | driving, sub-heavy, compressed |

**Track layout (5 tracks):**
```
1. Drums (Note track + Playfield) — kick, clap, hat, ride
2. Bass (Note track + Vaporisateur) — rolling sub
3. Lead synth (Note track + Vaporisateur) — acid 303-ish
4. Pad (Note track + Vaporisateur) — dark sustain
5. FX (Audio track) — risers, impacts
```

**Drum pattern:**
```python
pattern = {
    "kick":  "x...x...x...x...",  # 4-on-floor
    "clap":  "....x.......x...",  # 2 & 4
    "hihat": "o.o.o.o.o.o.o.o.",  # 8ths, soft
    "ride":  "..o...o...o...o."   # off-beat
}
```

**Bass line (rolling):**
```python
# 16th note rolling bass, root note A1 (33)
notes = []
for beat in range(16):
    notes.append({"pitch": 33, "start": beat * 0.25, "duration": 0.125, "velocity": 0.7})
```

**Effect chain:**
```
Drums:  Compressor(4:1, -15dB) → Revamp EQ(+60Hz, +4k)
Bass:   Revamp EQ(HPF 30, -200Hz) → Waveshaper(drive 0.4)
Lead:   Waveshaper(drive 0.6) → Delay(send, 1/4, -18dB) → Reverb(send, -14dB)
Pad:    DattorroReverb(send, -8dB, decay 0.8)
Master: Revamp EQ → Compressor(2:1, glue) → Maximizer(-1dBTP)
```

**Sidechain:** drums → bass, threshold -20, ratio 4, attack 5ms, release 80ms

---

### Coldwave / Darksynth

| Parameter | Value |
|-----------|-------|
| BPM | 90-120 |
| Time signature | 4/4 |
| LUFS target | -14 |
| Crest | 10-13 |
| Stereo | wide (corr 0.5-0.7) |
| Character | scooped mids, dark, dense |

**Track layout (7 tracks):**
```
1. Drums (Note + Playfield) — drum machine, 80s style
2. Bass (Note + Vaporisateur) — dark, driving
3. Vocal lead (Note + Vaporisateur) — melodic, reverb-soaked
4. Pad (Note + Vaporisateur) — minor key sustain
5. Arp (Note + Vaporisateur + Spielwerk arpeggiator) — persistent
6. Noise/FX (Audio) — tape hiss, atmos
7. Vocal (Audio) — if Suno stem
```

**Drum pattern:**
```python
pattern = {
    "kick":  "x.......x.......",  # slow, heavy
    "snare": "....x.......x...",  # 2 & 4
    "hihat": "o.o.o.o.o.o.o.o.",  # 8ths
    "clap":  "....x.......x..."   # layer with snare
}
```

**Chord progression (minor):**
```python
chords = [["A", "min"], ["F", "maj7"], ["C", "maj"], ["G", "dom7"]]
```

**Effect chain:**
```
Drums:  Revamp EQ(HPF 60, +4k snare) → Compressor(3:1) → DattorroReverb(send, -10dB, damping 0.2)
Bass:   Waveshaper(hardclip, drive 0.8) → Revamp EQ(-200Hz mud)
Lead:   DattorroReverb(send, -8dB, decay 0.7) → Delay(send, 1/8, -20dB)
Pad:    DattorroReverb(send, -6dB, decay 0.9, damping 0.3)
Arp:    Delay(send, 1/16, -16dB) → Reverb(send, -12dB)
Master: Revamp EQ(scooped mids: -2dB@500, +3dB@12k) → Maximizer(-1dBTP)
```

---

### Hip-Hop

| Parameter | Value |
|-----------|-------|
| BPM | 70-90 |
| Time signature | 4/4 |
| LUFS target | -10 to -12 |
| Crest | 8-12 |
| Stereo | narrow-center (corr 0.6-0.8) |
| Character | vocal forward, sub-bass, 808 |

**Track layout (4-5 tracks):**
```
1. Drums (Note + Playfield) — boom bap or trap
2. 808 bass (Note + Vaporisateur) — sub-bass
3. Sample/melody (Audio or Note + Vaporisateur) — loop
4. Vocal (Audio) — if Suno stem
5. FX (Audio) — occasional
```

**Drum pattern (boom bap):**
```python
pattern = {
    "kick":  "x.......x.x.....",
    "snare": "....x.......x...",
    "hihat": "o.o.o.o.o.o.o.o."
}
```

**Drum pattern (trap):**
```python
pattern = {
    "kick":  "x.....x...x.....",
    "snare": "....x.......x...",
    "hihat": "o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.o."  # 16ths, roll
}
```

**808 bass:**
```python
# Long 808 notes on root, glide between
notes = [
    {"pitch": 36, "start": 0.0, "duration": 2.0, "velocity": 0.9},   # C2
    {"pitch": 36, "start": 2.0, "duration": 2.0, "velocity": 0.9},
    {"pitch": 33, "start": 4.0, "duration": 2.0, "velocity": 0.9},   # A1
    {"pitch": 38, "start": 6.0, "duration": 2.0, "velocity": 0.9},   # D2
]
```

**Effect chain:**
```
Drums:  Compressor(4:1, -12dB, slow attack 10ms) → Revamp EQ(+60Hz kick, +4k snare)
808:    Revamp EQ(HPF 20, -60Hz boom) → Compressor(2:1, glue)
Sample: Revamp EQ(HPF 150, LPF 8k) → StereoTool(width 0.8)
Vocal:  Revamp EQ(HPF 100, +air 12k) → Compressor(3:1) → DattorroReverb(send, -14dB, decay 0.3)
Master: Revamp EQ → Compressor(2:1) → Maximizer(-1dBTP)
```

**Sidechain:** 808 → bass (if separate), or kick → 808 gentle duck

---

### Ambient

| Parameter | Value |
|-----------|-------|
| BPM | 60-90 |
| Time signature | 4/4 or 3/4 |
| LUFS target | -16 to -20 |
| Crest | 14-18 |
| Stereo | very wide (corr 0.2-0.5) |
| Character | spacious, air-dominant, dynamic |

**Track layout (3-4 tracks):**
```
1. Pad (Note + Vaporisateur) — sustained, evolving
2. Texture (Note + Vaporisateur + Werkstatt granular) — granular
3. Field recording (Audio) — natural sound
4. Bell/melodic (Note + Vaporisateur) — sparse, random
```

**No drums** (or very sparse pulse).

**Chord progression (major 7ths):**
```python
chords = [["C", "maj7"], ["A", "min7"], ["F", "maj7"], ["G", "maj7"]]
```

**Effect chain:**
```
Pad:      DattorroReverb(send, -4dB, decay 0.9, damping 0.4) → StereoTool(width 1.5)
Texture:  werkstatt_granular_stretch.js(stretch 4x) → DattorroReverb(send, -6dB)
Field:    Revamp EQ(HPF 200) → DattorroReverb(send, -8dB)
Bell:     DattorroReverb(send, -3dB, decay 0.95) → Delay(send, 1/2, -16dB)
Master:   Revamp EQ(+air 12k +6dB) → Maximizer(-1dBTP, transparent)
```

**No sidechain. No compression on master (keep dynamics).**

---

### DnB / Neurofunk

| Parameter | Value |
|-----------|-------|
| BPM | 160-180 |
| Time signature | 4/4 |
| LUFS target | -9 to -11 |
| Crest | 6-9 |
| Stereo | wide (corr 0.4-0.6) |
| Character | sub + breakbeats, aggressive |

**Track layout (5-6 tracks):**
```
1. Drums (Note + Playfield) — breakbeats
2. Bass (Note + Vaporisateur) — reese / neuro
3. Sub (Note + Vaporisateur) — clean sub
4. Lead/atmos (Note + Vaporisateur) — dark
5. FX (Audio) — impacts, risers
6. Vocal (Audio) — if Suno stem
```

**Drum pattern (Amen-style break):**
```python
pattern = {
    "kick":  "x.....x.x.......x.....x.x.......",
    "snare": "....x.......x.......x.......x...",
    "hihat": "o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.o."
}
```

**Reese bass:**
```python
# Detuned saw, lowpass, long notes
notes = [
    {"pitch": 33, "start": 0.0, "duration": 4.0, "velocity": 0.8},
    {"pitch": 33, "start": 4.0, "duration": 4.0, "velocity": 0.8},
]
# Vaporisateur: waveform=Saw(2), detune both oscs, cutoff low
```

**Effect chain:**
```
Drums:  Compressor(8:1, -10dB, fast attack 1ms) → Revamp EQ(+60Hz, +5k)
Bass:   Waveshaper(drive 1.0) → Revamp EQ(HPF 30, +80Hz) → Compressor(4:1)
Sub:    Revamp EQ(HPF 20, LPF 120) — clean only
Lead:   Waveshaper(drive 0.8) → DattorroReverb(send, -14dB, decay 0.4)
Master: Revamp EQ → Compressor(3:1) → Maximizer(-1dBTP)
```

**Sidechain:** drums → bass+sub, aggressive (ratio 6, release 40ms)

---

### House

| Parameter | Value |
|-----------|-------|
| BPM | 120-130 |
| Time signature | 4/4 |
| LUFS target | -10 to -12 |
| Crest | 8-11 |
| Stereo | wide (corr 0.4-0.6) |
| Character | groove, soulful, warm |

**Track layout (5-6 tracks):**
```
1. Drums (Note + Playfield) — 4-on-floor
2. Bass (Note + Vaporisateur) — groovy
3. Chords (Note + Vaporisateur) — stab
4. Lead (Note + Vaporisateur) — melodic
5. Vocal (Audio) — if Suno stem
6. FX (Audio) — risers, sweeps
```

**Drum pattern:**
```python
pattern = {
    "kick":  "x...x...x...x...",  # 4-on-floor
    "clap":  "....x.......x...",  # 2 & 4
    "hihat": "..o...o...o...o.",  # off-beat 8ths
    "open":  "....o.......o..."   # open hat on off
}
```

**Chord stab (minor 9):**
```python
chords = [["F", "min9"], ["C", "min9"], ["G", "min9"], ["D", "min9"]]
```

**Effect chain:**
```
Drums:  Compressor(3:1, -12dB) → Revamp EQ(+60Hz, +10k)
Bass:   Revamp EQ(HPF 40) → Waveshaper(gentle, drive 0.3)
Chords: Delay(send, 1/8, -18dB) → DattorroReverb(send, -10dB, decay 0.5)
Lead:   DattorroReverb(send, -8dB) → Delay(send, 1/4, -16dB)
Master: Revamp EQ → Compressor(2:1) → Maximizer(-1dBTP)
```

**Sidechain:** drums → bass, gentle (ratio 3, release 100ms)

---

### Lofi

| Parameter | Value |
|-----------|-------|
| BPM | 70-90 |
| Time signature | 4/4 |
| LUFS target | -14 to -16 |
| Crest | 12-16 |
| Stereo | narrow (corr 0.6-0.8) |
| Character | warm, dusty, vinyl, relaxed |

**Track layout (4 tracks):**
```
1. Drums (Note + Playfield) — lazy swing
2. Bass (Note + Vaporisateur) — warm
3. Chords (Note + Vaporisateur) — jazz extensions
4. Sample (Audio) — vinyl crackle, old record
```

**Drum pattern (swing):**
```python
pattern = {
    "kick":  "x.......x.x.....",
    "snare": "....x.......x...",
    "hihat": "o..o..o..o..o..o."  # swung 8ths
}
# Apply groove shuffle: 0.3-0.5
```

**Chord progression (jazz):**
```python
chords = [["D", "min7"], ["G", "dom7"], ["C", "maj7"], ["F", "maj7"]]
```

**Effect chain:**
```
Drums:  Revamp EQ(LPF 8k, -4dB) → werkstatt_darksat.js(drive 0.2, tone 0.3)
Bass:   Revamp EQ(HPF 50, LPF 2k) → werkstatt_darksat.js(drive 0.3)
Chords: werkstatt_darksat.js(drive 0.2) → DattorroReverb(send, -12dB, decay 0.3)
Sample: Revamp EQ(HPF 200, LPF 6k) → werkstatt_darksat.js(drive 0.4)
Master: Revamp EQ(-3dB@4k, +2dB@12k) → Maximizer(-1dBTP, transparent)
```

**Groove:** `set_groove_shuffle(0.35)`, `set_groove_timing(0.2)`

**No sidechain. No aggressive compression. Keep it lazy.**

---

### Trap

| Parameter | Value |
|-----------|-------|
| BPM | 140-160 (or 70-80 half-time) |
| Time signature | 4/4 |
| LUFS target | -10 to -12 |
| Crest | 8-12 |
| Stereo | wide drums, center 808 |
| Character | hard kicks, rolling hats, dark 808s |

**Track layout (4 tracks):**
```
1. Drums (Note + Playfield) — hard kick, fast hats
2. 808 (Note + Vaporisateur) — gliding sub
3. Melody (Note + Vaporisateur or Audio) — dark minor
4. FX (Audio) — risers
```

**Drum pattern:**
```python
pattern = {
    "kick":  "x.....x...x.x...",
    "snare": "....x.......x...",
    "hihat": "o.o.o.o.o.o.o.o.o.o.o.o.o.o.o.o."  # 16ths with rolls
}
```

**808 with glide:**
```python
# Long slides between notes
notes = [
    {"pitch": 36, "start": 0.0, "duration": 1.5, "velocity": 0.9},
    {"pitch": 39, "start": 1.5, "duration": 1.5, "velocity": 0.9},  # slide up
    {"pitch": 33, "start": 3.0, "duration": 2.0, "velocity": 0.9},  # slide down
]
# Vaporisateur: set glide/portamento
```

**Effect chain:**
```
Drums:  Compressor(6:1, -8dB, attack 2ms) → Revamp EQ(+60Hz, +5k)
808:    Revamp EQ(HPF 20) → Compressor(2:1) → werkstatt_darksat.js(drive 0.5)
Melody: DattorroReverb(send, -12dB, decay 0.4) → Delay(send, 1/8, -20dB)
Master: Revamp EQ → Maximizer(-1dBTP)
```

## Pan Reference

| Element | Pan | Notes |
|---------|-----|-------|
| Kick | 0.0 | always center |
| Bass/808 | 0.0 | always center |
| Sub | 0.0 | always center |
| Snare | 0.0 | usually center |
| Vocals | 0.0 | center, the focus |
| Hats | ±0.3-0.5 | slight spread |
| Synths | ±0.5-0.7 | wide for electronic |
| Guitars | ±0.6-0.8 | hard L/R pairs |
| Pads | ±0.7-0.9 | widest |
| Room/Ambience | ±0.8-1.0 | extreme width |

## Genre → Orchestration Tool

```python
# Quick genre skeleton (one call)
await mcp_opendaw_create_genre_track("techno", bpm=130)
await mcp_opendaw_create_genre_track("lofi", bpm=82)
# Creates: 2 synth AUs (Vaporisateur), chord notes, bass notes, drum pattern
# Each genre has hardcoded BPM, drum pattern, bass line, chord progression
```

**Note:** `create_genre_track` creates a basic skeleton. For full genre templates above, build manually with individual tools for more control.

## Genre → Mastering

```python
# One-call mastering with genre-appropriate settings
await mcp_opendaw_add_mastering_chain(target_lufs=-14, style="balanced")     # coldwave, lofi
await mcp_opendaw_add_mastering_chain(target_lufs=-10, style="loud")         # techno, DnB, trap
await mcp_opendaw_add_mastering_chain(target_lufs=-12, style="warm")         # hip-hop, house
await mcp_opendaw_add_mastering_chain(target_lufs=-16, style="transparent")  # ambient
# Styles: balanced, warm, loud, transparent
```

## Related Skills

- `adaptive-mix-mastering` — full mix→master pipeline with decision points
- `opendaw-track-architecture` — tracks, regions, clips, notes
- `opendaw-sound-design` — instruments + DSP
- `opendaw-effect-routing` — effect chains, sends, sidechain
- `suno-to-opendaw` — Suno→stems→openDAW E2E
- `opendaw-automation` — 420 MCP tools full API reference

## Multi-Track Arrangement Tools (14 genres)

One-call genre sections across 3-4 tracks. Replaces 100+ individual create_note calls.

### Decision Tree: Which Arrangement?

```
User wants...
├── Electronic dance?
│   ├── Fast + breakbeat?        → create_dnb_arrangement (174 BPM, Amen, Reese)
│   ├── Four-on-floor?
│   │   ├── Off-beat bass?       → create_house_arrangement (124 BPM, "untz-untz")
│   │   ├── Sustained drone?     → create_techno_arrangement (130 BPM, hypnotic, min 8 bars)
│   │   └── Half-time + wobble?  → create_dubstep_arrangement (140 BPM, feels like 70)
│   ├── Trap rolls + 808?        → create_trap_arrangement (140 BPM, F# minor)
│   ├── Nostalgic 80s + arp?     → create_synthwave_arrangement (110 BPM, Am, i-VI-III-VII)
│   └── Euphoric + supersaw?     → create_trance_arrangement (138 BPM, Fm, rolling bass)
├── 70s dance / feel-good?
│   └── Octave bass + strings?   → create_disco_arrangement (120 BPM, G major, I-vi-IV-V)
├── Organic / band?
│   ├── Guitar-driven?
│   │   ├── Power chords, I-IV-V? → create_rock_arrangement (120 BPM, E default)
│   │   └── Skank + one-drop?     → create_reggae_arrangement (80 BPM, A minor)
│   ├── Bass-driven groove?
│   │   ├── Vamp, 16th syncopation? → create_funk_arrangement (100 BPM, Funky Drummer)
│   │   └── Polyrhythm, horns?      → create_afrobeat_arrangement (120 BPM, Fela Kuti)
│   ├── Jazz?                      → create_jazz_arrangement (120 BPM, ii-V-I, swing)
│   └── Song structure needed?     → create_pop_arrangement (120 BPM, verse-chorus-bridge)
```

### All 14 Arrangements

| Tool | Genre | Tracks | BPM | Key | Key Feature |
|------|-------|--------|-----|-----|-------------|
| `create_dnb_arrangement` | DnB | 3 | 140-200 | F | Amen breakbeat + Reese + pad |
| `create_liquid_dnb_arrangement` | Liquid DnB | 4 | 160-185 | F | Smooth breakbeat + melodic sub-bass + min9/maj9 pads + soulful lead |
| `create_house_arrangement` | House | 3 | 110-140 | C | Four-on-floor + off-beat bass + stabs |
| `create_trap_arrangement` | Trap | 3 | 120-170 | F# | Trap rolls + 808 slides + bell |
| `create_techno_arrangement` | Techno | 3 | 120-150 | C | Four-on-floor + sub drone + Detroit stabs |
| `create_dubstep_arrangement` | Dubstep | 3 | 130-155 | G | Half-time + wobble bass + arp |
| `create_synthwave_arrangement` | Synthwave | 4 | 90-130 | A | Arpeggiated 16th bass + i-VI-III-VII + dreamy pads |
| `create_trance_arrangement` | Trance | 4 | 128-145 | F | Rolling off-beat 8th bass + supersaw arp + snare rush |
| `create_disco_arrangement` | Disco | 4 | 110-130 | G | Syncopated octave bass + 16th open hats + strings + wah |
| `create_afrobeat_arrangement` | Afrobeat | 4 | 95-135 | F | Polyrhythm + ostinato + horns + chanka |
| `create_rock_arrangement` | Rock | 4 | 80-180 | E | Rock beat + power chords + I-IV-V |
| `create_jazz_arrangement` | Jazz | 4 | 50-220 | F | Swing ride + walking bass + ii-V-I |
| `create_pop_arrangement` | Pop | 4 | 85-145 | C | Song structure + I-V-vi-IV |
| `create_funk_arrangement` | Funk | 4 | 85-120 | D | Vamp + Funky Drummer + slap bass |
| `create_reggae_arrangement` | Reggae | 4 | 60-100 | A | One-drop + skank + melodic bass lead |
| `create_lofi_arrangement` | Lofi Hip-Hop | 4 | 65-95 | F | Boom-bap + jazzy ii-V-I + sleepy pentatonic |
| `create_soul_arrangement` | Soul | 4 | 65-90 | C | Gospel drums + walking bass + Rhodes I-IV-vi-V + Motown horns |
| `create_rnb_arrangement` | R&B | 4 | 55-85 | C | Half-time drums + sub bass + dark min9 chords + vocal-style lead |
| `create_blues_arrangement` | Blues | 4 | 70-160 | A | Shuffle drums + walking bass + dom7 stabs + blues scale lead (12-bar form) |

### Drum Pattern Comparison

| Genre | Kick | Snare | Unique |
|-------|------|-------|--------|
| House | Every beat | Clap 2+4 | Four-on-floor |
| Techno | Every beat | Clap 2+4 | Industrial hats |
| Synthwave | Every beat (soft) | 2+4 | Retro 80s, softer than house |
| Trance | Every beat (hard) | Clap 2+4 | Open hats on off-beats, snare rush |
| Disco | Every beat | Clap 2+4 | 16th OPEN hats (busier than house) |
| Rock | 1 & 3 | 2 & 4 | Straight backbeat |
| Jazz | Sporadic | Ghost on swung 8ths | Spang-a-lang ride |
| Funk | Syncopated | 2+4 + ghosts | 16th-note hats |
| Reggae | 3 ONLY | 3 ONLY (with kick) | One-drop, empty on 1 |
| Dubstep | 1 ONLY | 3 ONLY | Half-time, feels like 70 |
| Afrobeat | Syncopated | None (clave) | 12/8 polyrhythm |

### Bass Pattern Comparison

| Genre | Bass Style | Unique |
|-------|-----------|--------|
| Synthwave | Arpeggiated 16ths (root-octave-fifth-octave) | Relentless arp engine |
| Trance | Rolling off-beat 8ths (root-octave) | Sustained, driving, off-beat |
| Disco | Syncopated octave (root-octave-fifth) | Melodic hook, bass IS the song |
| House | Off-beat stabs | Syncopated pulse |
| Techno | Sub-bass drone | Sustained, not rhythmic |
| Reggae | Melodic lead (root-octave-fifth-root) | Bass IS the lead instrument |
| Jazz | Walking (quarter notes through ii-V-I) | Chord-tone movement |
| Funk | Slap (thumb/pluck, 16th density) | 16 notes per bar |
| Rock | Root-fifth walking | Locks with kick |

### Full Pipeline: Create → Mix → Humanize → Master

Three capability layers transform raw arrangements into finished tracks:

```
1. CREATE notes
   ├── Loop-based?          → create_XXX_arrangement (14 genres)
   ├── Song structure?      → create_genre_sections (8 electronic: intro→buildup→drop→breakdown→outro)
   ├── Varied sections?     → create_arrangement_variation (14 genres: drum density/bass octave/melody transform)
   ├── Full song w/ vars?   → create_song_with_variations (14 genres: 12 presets, one call)
   └── One-call?            → create_full_genre_pipeline (14 genres, all steps in one call)

2. MIX (effects per track)
   └── apply_genre_mix (14 genres: compressor/EQ/saturation/reverb/delay/sidechain per genre)

3. HUMANIZE (make MIDI feel alive)
   └── apply_genre_humanization (14 genres: jazz=loose+swing, electronic=tight, funk=behind beat)

4. MASTER
   └── add_mastering_chain (LUFS target: -14 Spotify, -10 loud, -16 Apple)

5. RENDER
   └── render_full_song (auto-detect length, export WAV)
```

#### Which structure tool to use?

| Need | Tool | Genres |
|------|------|--------|
| Loop-based section (8-16 bars) | `create_XXX_arrangement` | 14 genres |
| Full song with DJ structure | `create_genre_sections` | 8 electronic |
| Varied sections (real transforms) | `create_arrangement_variation` | 14 genres |
| Full song w/ variations (one call) | `create_song_with_variations` | 14 genres |
| Zero-to-render in one call | `create_full_genre_pipeline` | 14 genres |

#### Humanization intensity by genre

| Genre | Timing | Velocity | Swing | Bias |
|-------|--------|----------|-------|------|
| Jazz | 0.20 (loosest) | 0.20 | 0.66 | — |
| Reggae | 0.12 | 0.15 | — | +0.03 (laid-back) |
| Funk | 0.10 | 0.15 | — | +0.02 (pocket) |
| Rock | 0.10 | 0.12 | — | — |
| Afrobeat | 0.12 | 0.15 | — | — |
| Disco | 0.06 | 0.10 | — | — |
| Pop | 0.05 | 0.08 | — | — |
| Synthwave | 0.04 | 0.06 | — | — |
| DnB/House/Trap/Dubstep | 0.03 | 0.05 | — | — |
| Liquid DnB | 0.05 | 0.08 | — | +0.01 (pocket) |
| Techno/Trance | 0.02 (tightest) | 0.04 | — | — |

Per-track scaling: drums=1.0, melody=0.8, harmony=0.7, bass=0.5 (bass stays tight)

#### Section energy profile (create_genre_sections)

```
energy  1.0 ┤                    ████
        0.7 ┤          ████████  ░░░░
        0.6 ┤          ░░░░░░░░  ░░░░  ████████
        0.5 ┤  ████████░░░░░░░░  ░░░░  ░░░░░░░░
        0.4 ┤  ░░░░░░░░░░░░░░░░  ░░░░  ░░░░░░░░████
            └──intro───buildup───drop───breakdown──outro──
```
