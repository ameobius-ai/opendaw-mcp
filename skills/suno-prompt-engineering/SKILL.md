---
name: suno-prompt-engineering
description: "Suno AI prompt engineering for agents: meta-tags, style tags, vocal anchors, behavior tags, version selection, persona management, anti-drift strategies. Concentrates 20+ KB files into one actionable skill. Use when generating Suno tracks or helping users craft prompts."
tags: [suno, prompts, ai-music, vocal-anchors, behavior-tags, custom-mode, persona, v5]
---

# Suno Prompt Engineering

Концентрат KB (`/creative-studio/kb/suno/`) в один actionable скил.
Когда юзер просит сгенерить трек, сделать промпт, или спрашивает про Suno — читай это.

## Decision: какая версия?

| Модель | chirp ID | Когда |
|--------|----------|-------|
| v5 | `sun/chirp-v5` | **Дефолт.** Более естественный, человечный вокал. Пользователь предпочитает. |
| v5-5 | `sun/chirp-v5-5` | Лучший синтаксис, больше контроля. Но вокал синтетичнее. Только если просят. |
| v4-5-plus | `sun/chirp-v4-5-plus` | Длинные треки до 8 мин. |
| v4-5 | `sun/chirp-v4-5` | Чистый вокал, стабильный. |

**Подтверждай версию** если юзер не указал. Дефолт = v5.

## Custom Mode: структура промпта

### Lyrics box (лирика + meta-tags)

**Квадратные скобки `[ ]` — структурные/технические теги, ВСЕГДА английский:**
```
[Intro]
[Verse]
[Pre-Chorus]
[Chorus]
[Bridge]
[Drop]
[Build]
[Climax]
[Catchy Hook]
[Outro]
[Instrumental Break]
```

**Behavior tags** (v5+) — говорят секции *что делать*, не только как называться:
```
[Structure: Focused Performance]    — tight storytelling, medium energy
[Structure: Build-up]               — rising tension, instruments layering
[Structure: Anthemic Peak]          — track's biggest moment, peak hook
[Structure: Minimalist Breakdown]   — stripped down, space, few instruments
[Structure: Cinematic Drop]         — dramatic hit after pause
[Structure: Outro Fade]             — gradual fade-out
[Structure: Spoken Bridge]          — spoken instead of melodic
[Structure: Call and Response]      — two voices trading lines
```

**Pipe combinations** — комбинированные теги через `|`:
```
[Chorus | High Energy | Anthemic | Electric Guitar Solo]
[Verse | Whispered | Close-mic | Sparse Drums]
[Bridge | Half-time | 808 sub bass | Vinyl static]
[Pre-chorus | Build-up | Rolling Toms | Crescendo]
[Drop | Distorted Guitar | Stadium crowd ambience]
```

**Instrument switches:**
```
[Rhodes] [Synth Pad] [Distorted Guitar] [Breakbeat] [808 Bass] [Music Box]
```

**Круглые скобки `( )` — ТОЛЬКО backing vocals / подпевка:**
- `ржавчина на пальцах (ржавчина)` → основная строка + эхо-подпевка
- **НЕ** использовать для транскрипции/ромадзи — Suno споёт обе строки
- Транскрипция идёт отдельно от лирики

### Style box (жанр/настроение/инструменты/вокал)

**Style = только жанр, настроение, инструменты, вокальный стиль, эпоха, продакшен:**
```
darksynth, coldwave, overdriven bass, deep baritone, 110 BPM
```

**Категории что работают:**
- Жанр: house, techno, dnb, folk, synthwave, coldwave, trap...
- Настроение: melancholic, uplifting, dark, aggressive, dreamy...
- Инструменты: analog synth, acoustic guitar, 808, overdriven bass...
- Вокал: warm male vocal, ethereal female, deep baritone, raspy...
- Эпоха: 80s, 90s, modern, retro...
- Продакшен: lo-fi, polished, raw, bedroom, cinematic...

**Vocal anchors в Style** (детальные многокомпонентные блоки):
```
[Vocal: male, deep husky timbre, relaxed but intense delivery, clear diction, precise rhythm, modern rap-adjacent tone]
[Vocal: male, raspy gritty timbre, dynamic shifts from quiet verse to throat-shredding belt on chorus, anguished delivery]
[Vocal: female, ethereal soprano with breathy textures, floating legato delivery, reverb-drenched atmospheric presence]
```

**Что Suno игнорирует:** слишком специфичные технические термины, DAW-команды.
**Что Suno усиливает:** жанровые якоря, вокальные дескрипторы, эмоциональные слова.

**Негативные описания:** `no screaming`, `no shouting` — работают когда продублированы в style И лирике.

**Пользователь на v5.0:** bracketed vocals в Style НЕ работают. Solo instruments только в Lyrics tags. Style bleeds instruments. Подтверждай v5.0/v5.5 сначала.

## Vocal Anchors (24 готовых блока)

### MALE (8)
| Сценарий | Тег |
|----------|-----|
| Rap-edge, noir pop | `[Vocal: male, deep husky timbre, relaxed but intense delivery, clear diction, precise rhythm, modern rap-adjacent tone]` |
| Soul ballads, R&B | `[Vocal: male, warm crooner baritone, jazz phrasing, slight vibrato on long notes, intimate microphone presence]` |
| Grunge, rock | `[Vocal: male, raspy gritty timbre, dynamic shifts from quiet verse to throat-shredding belt on chorus, anguished delivery]` |
| R&B, dream-pop | `[Vocal: male, airy floating falsetto, breathy intimate close-mic delivery, subtle stacked harmonies, vulnerable tone]` |
| Country, americana | `[Vocal: male, gravelly weathered timbre, twangy drawl, conversational storytelling cadence, authentic and lived-in]` |
| Cloud rap | `[Vocal: male, monotone melodic rap, flat affect delivery, lazy cadence, autotune-friendly, atmospheric haze]` |
| Post-punk, coldwave | `[Vocal: male, deadpan baritone, monotone delivery, detached cold delivery, sparse phrasing, post-punk aesthetic]` |
| Folk, indie | `[Vocal: male, warm conversational tenor, gentle strumming cadence, raw acoustic intimacy, weathered storytelling]` |

### FEMALE (8)
| Сценарий | Тег |
|----------|-----|
| Ethereal, ambient | `[Vocal: female, ethereal soprano with breathy textures, floating legato delivery, reverb-drenched atmospheric presence]` |
| Pop, power ballad | `[Vocal: female, powerful belting mezzo-soprano, controlled vibrato, dynamic range from whisper to full-chest belt, pop precision]` |
| Jazz, soul | `[Vocal: female, smoky jazz alto, behind-the-beat phrasing, rich lower register, velvet timbre with slight rasp]` |
| Folk, indie | `[Vocal: female, clear folk soprano, crystalline tone, precise enunciation, gentle fingerpicked guitar cadence, rustic warmth]` |
| R&B, neo-soul | `[Vocal: female, silky R&B soprano, melismatic runs, breathy falsetto flips, gospel-influenced phrasing, smooth transitions]` |
| Punk, riot grrrl | `[Vocal: female, raw punk delivery, shouted melodic vocals, throat-tearing intensity, anti-technical passionate scream]` |
| Opera, cinematic | `[Vocal: female, operatic soprano, trained classical technique, precise pitch control, dramatic dynamic shifts, orchestral blend]` |
| Trap, drill | `[Vocal: female, auto-tuned melodic rap, pitched-up vocal effect, rhythmic triplet flows, trap cadence with sung hooks]` |

### SPECIAL (8)
| Сценарий | Тег |
|----------|-----|
| Choir | `[Vocal: mixed choir, layered harmonies, four-part vocal arrangement, cathedral acoustics, unified ensemble delivery]` |
| Spoken word | `[Vocal: spoken word, theatrical narration, dramatic pauses, intimate whisper-to-shout dynamics, no melodic content]` |
| Childlike | `[Vocal: childlike soprano, innocent delivery, simple melodic phrases, music-box accompaniment, dreamlike quality]` |
| Gregorian | `[Vocal: gregorian chant, male monastic drone, latin liturgical text, modal harmony, cathedral reverb, timeless devotion]` |
| Distorted | `[Vocal: vocoded distorted vocals, robotic processed delivery, synthetic harmonizer artifacts, cyberpunk aesthetic]` |
| Whispered | `[Vocal: whispered intimate vocals, ASMR-adjacent close-mic, breath as percussion, barely-there melodic fragments]` |
| Falsetto choir | `[Vocal: stacked falsetto choir, Beach Boys harmonies, lush vocal layering, sunshine pop arrangement, soaring soprano blend]` |
| Throat singing | `[Vocal: overtone singing, dual-pitch throat technique, guttural drone with harmonic overtones, traditional tuvan style]` |

## Genre → BPM (справочник)

Избегай догадок. Проверяй по KB `suno/genre_bpm_map.md` (420 жанров). Ключевые:

| Жанр | BPM |
|------|-----|
| russian-pop | 118 |
| eurodance | 133 |
| boom-bap | 91 |
| vaporwave | 72 |
| darksynth | 110 |
| dnb | 174 |
| house | 128 |
| techno | 130 |
| lofi | 80 |
| trap | 140 |
| ambient | 70 |
| coldwave | 110 |
| post-punk | 130 |

## Persona & Drift

**Проблема:** после ~2 куплета (~1.5 мин) вокал уходит от persona-референса, становится «суновским».

**Обходы:**
1. Короткие треки → экстендить от сильного участка
2. Extensions от сильного участка, не от конца
3. Регенерация с того же persona когда дрейф заметен

## v5.5 Advanced (T16.PRO)

**Mid-Side локализация:**
- `focused mono low-end, rock-solid center, driving localized sub-bass` (моно-низ)
- `ultra-wide panoramic air, shimmering stereo fields, immersive dimension` (стерео-верх)
- `perfectly separated vocal pocket, pristine sonic hierarchy` (вокальный карман)

**Транзиенты:**
- `crisp snapping attack, hyper-detailed transient definition, biting articulation` (острая атака)
- `legato flowing textures, bowed organic sustain, smooth blurred transients` (мягкая атака)

**Сайдчейн:**
- `interlocking groove, breathing rhythm, pumping sidechained bassline-kick integration`

**Compound descriptors** (дефисное объединение для 120-символьного лимита):
- `darksynth-coldwave` вместо двух слов
- `overdriven-bass` вместо `overdriven bass`

## Пайплайн генерации (из KB procedures/generation-workflow.md)

1. **Ресёрч KB** — genre_bpm, vocal_anchors, behavior_tags, prompts, v5-advanced
2. **Уточнение с юзером** — жанр, вокал (муж/жен), BPM, настроение, explicit?
3. **Сборка промпта** — Lyrics (структура + лирика), Style (жанр + вокал + BPM), model, negative
4. **Генерация** — chirp_generate, 2 вариации, скачать
5. **Фидбек** — что хорошо/плохо, mem0 запись

**Чек-лист перед генерацией:**
- [ ] Жанр определён? BPM проверен по genre_bpm_map?
- [ ] Вокал: муж/жен? Vocal anchor выбран?
- [ ] Структура: секции расставлены в Lyrics?
- [ ] Behavior tags для ключевых секций?
- [ ] Style: жанр + настроение + инструменты + вокал + BPM?
- [ ] Negative tags если нужно (no screaming)?
- [ ] Версия подтверждена (v5 дефолт)?
- [ ] Лирика прошла анти-AI пайплайн?

## Anti-AI лирика (критично)

Перед вставкой лирики в Suno — прогон через пайплайн (см. SOUL.md):
- Убрать клише: «вечность», «симфония», «гармония», «мелодия души»
- Сломать бинарные оппозиции свет/тьма
- Неточные рифмы вместо глагольных
- Конкретные образы вместо абстракций
- Один бьющий образ лучше трёх красивых

## Инструмент

`chirp_generate` — генерация. Simple mode (prompt only) или custom mode (prompt=lyrics, style, title, instrumental). 2 вариации за запрос. Возвращает audio URLs + artwork.

## KB References

- `kb/suno/prompts.md` — полный гайд по промптам
- `kb/suno/vocal_anchors.md` — 24 якоря
- `kb/suno/behavior_tags.md` — 48 behavior тегов
- `kb/suno/genre_bpm_map.md` — 420 жанров → BPM
- `kb/suno/v5-advanced.md` — T16.PRO фреймворк
- `kb/suno/persona.md` — дрейф персоны
- `kb/suno/versions.md` — сравнение версий
- `kb/suno/siliconsense_guides.md` — 10 гайдов v5.5
- `kb/suno/moods_usecases.md` — 217 moods + 394 use cases
- `kb/suno/procedures/generation-workflow.md` — полный пайплайн
- `kb/suno/procedures/v5-advanced-framework.md` — 8 шагов T16.PRO
- `kb/suno/procedures/rock-vocal-no-scream.md` — ровный рок-вокал
- `kb/suno/procedures/arrangement-fix.md` — фикс пропадающих инструментов
- `kb/suno/vocals.md` — триггеры визга и рабочие дескрипторы
- `kb/suno/stem_mixing.md` — стем-микс
- `kb/suno/quirks.md` — веб-глюки
- `kb/suno/arrangement.md` — инструменты в припеве
- `kb/suno/moods_usecases.md` — словари moods/use_cases
