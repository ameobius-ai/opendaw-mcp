---
name: suno-to-opendaw
description: "End-to-end pipeline: Suno AI generation → download → SOTA stem separation → openDAW import → mix/master → export. The killer workflow that no other MCP server offers. 7 stem-split modes, 377 DAW tools, 108 DSP scripts, adaptive mastering, auto BPM+key detection, one-call remix. From prompt to finished track."
tags: [suno, opendaw, stem-splitting, mix-master, pipeline, e2e, ai-music, workflow]
---

# Suno → openDAW Pipeline

Полный цикл: от промпта к Suno → через stem separation → в openDAW → к готовому треку.
Это уникальный workflow — генерация, разбор, сведение, мастеринг в одной цепочке.

## Когда использовать

- Юзер принес Suno трек и хочет его доработать (свести, смастерить, переработать)
- Юзер хочет сгенерировать трек с нуля и довести до ума
- Юзер говорит «сделай из Suno нормальный трек», «разбери на стемы», «доведи»
- Юзер хочет remix/remake на основе Suno генерации

## Архитектура: 6 стадий

```
Prompt → [S1: Generate] → [S2: Split] → [S3: Import] → [S4: Arrange] → [S5: Mix] → [S6: Master+Export]
              ↓               ↓              ↓              ↓             ↓              ↓
         Suno API        7 modes        load_audio      regions       effects        LUFS target
         2 variations    GPU local      sample IDs      clips         sends          platform
         style tags      SDR-ranked     Playfield       tempo         sidechain      format
```

## Stage 1: Generate (Suno)

### Decision Point: Generation Mode

| User signal | Mode | How |
|-------------|------|-----|
| «сгенерируй трек», «сделай бит» | Simple mode | `chirp_generate(prompt)` — 2 variations |
| «напиши лирику и сгенерируй» | Custom mode | `chirp_generate(prompt=lyrics, style, title)` |
| «инструментал без вокала» | Custom + instrumental | `chirp_generate(prompt, style, instrumental=True)` |
| «мужской/женский вокал» | Custom + vocal_gender | `chirp_generate(prompt, style, vocal_gender="m"/"f")` |

### Suno prompt engineering

Style tags — жанр + настроение + инструменты + эпоха + продакшен:

```python
# Coldwave example
chirp_generate(
    prompt="cold dark coldwave analog synth bass heavy reverb 80s post-punk",
    style="coldwave, darksynth, analog synthesis, heavy reverb, driving bass, 90 BPM",
    title="Glass Caves"
)

# Techno
chirp_generate(
    prompt="driving techno acid 303 rolling bass hypnotic",
    style="techno, acid, rolling bass, hypnotic, 130 BPM, club"
)
```

**Suno style tags that work:** genre names, mood adjectives, instrument names, BPM, era references, production terms.
**Suno ignores:** overly specific mixing instructions, exact frequency values, plugin names.

### Decision Point: Model Selection

| Need | Model | Why |
|------|-------|-----|
| Best quality | `sun/chirp-v5-5` | latest, cleanest vocal |
| Fast iteration | `sun/chirp-v5` | quick, good enough |
| Long forms (>4 min) | `sun/chirp-v4-5-plus` | up to 8 min |
| Raw/lo-fi aesthetic | `sun/chirp-v3-5` | grittier, sometimes fitting |

### Result

Suno возвращает 2 вариации: audio URLs + artwork + lyrics. Выбираем лучшую (или обе для A/B).

```python
result = chirp_generate(prompt="...", style="...", title="...")
# result → [{title, audio_url, image_url, lyric, state}, ...]
# Download audio_url → local file for next stage
await mcp_opendaw_download_audio(url=result[0]["audio_url"], filename="suno_track.wav")
# → /tmp/suno_track.wav ready for import_audio_to_tracks
```

## Stage 2: Split (Stem Separation)

### Decision Point: Split Mode

7 SOTA моделей, все локально на GPU. Выбор по задаче:

| Goal | Mode | Stems | Speed (30s) | SDR | When |
|------|------|-------|-------------|-----|------|
| Max quality final mix | `ensemble` | 4 (bass/drums/vocals/other) | 90s | 11.0-11.96 | final production |
| Quick 4-stem | `scnet` | 4 | 45s | ~10 | fast iteration |
| 6 stems (guitar/piano) | `bs6` | 6 | 15s | ~9 | need more separation |
| Vocals only | `polarformer` | 1 | 23s | 11.00 | vocal isolation |
| Dry vocals (de-reverb) | `dereverb` | 2 | 16s | — | run AFTER polarformer |
| Drum kit breakdown | `drumsep` | 4 (kick/snare/hat/other) | 68s | — | run AFTER scnet/bs6 |
| Clean noisy source | `denoise` | 2 | 16s | — | run BEFORE split |

### Pipeline: 2-pass split (best quality)

```python
# Pass 1: 6-stem split (fast, good separation)
mcp_opendaw_split_stems("suno_track.wav", mode="bs6", import_to_daw=True)
# → bass, drums, vocals, other, guitar, piano

# Pass 2 (optional): drum breakdown
mcp_opendaw_split_stems("stems/drums.wav", mode="drumsep", import_to_daw=True)
# → kick, snare, hihat, other

# Pass 2 (optional): dry vocals
mcp_opendaw_split_stems("stems/vocals.wav", mode="dereverb", import_to_daw=True)
# → dry vocals, reverb residual
```

### Decision Point: Stem Count by Goal

| Goal | Stems needed | Mode chain |
|------|-------------|------------|
| Simple remix | 4 (bass/drums/vocals/other) | `ensemble` or `scnet` |
| Full control mix | 6+ | `bs6` → optional `drumsep` |
| Vocal extraction only | 1-2 | `polarformer` → `dereverb` |
| Instrumental remake | 3 (drums/bass/other) | `scnet` (drop vocals) |
| Drum replacement | 4 (kick/snare/hat/other) | `bs6` → `drumsep` on drums |

### Pitfall: Stem names ≠ instrument detection

`bs6` "guitar" stem is a catch-all — check RMS per stem. Stem names are model labels, not ground truth. Always verify with ears.

## Stage 3: Import (openDAW)

**One call.** `import_audio_to_tracks` replaces all manual load + create + place calls.

### Simple import (no stem splitting)

```python
# File → single track in DAW
await mcp_opendaw_import_audio_to_tracks(file_path="/tmp/suno_track.wav")
# Returns: {tracks_created: 1, tracks: [{stem: "full", unit_index, track_index, sample_id, duration}]}
```

### Stem-split import (one call = split + create + load + place × N stems)

```python
# File → 6 stems → 6 tracks, each loaded and placed
await mcp_opendaw_import_audio_to_tracks(
    file_path="/tmp/suno_track.wav",
    mode="bs6",      # 6-stem separation
    start_beat=0,    # position on timeline
)
# Returns: {tracks_created: 6, tracks: [{stem: "bass", ...}, {stem: "drums", ...}, ...]}
```

### Full download-to-import (Suno CDN URL → DAW)

```python
# S1+S2+S3 in two calls:
dl = await mcp_opendaw_download_audio(url=suno_audio_url, filename="track.wav")
imp = await mcp_opendaw_import_audio_to_tracks(file_path="/tmp/track.wav", mode="bs6")
# → 6 stems in DAW, ready for mixing
```

### Decision Point: Anchor Strategy

| Situation | Anchor | Treatment |
|-----------|--------|-----------|
| Suno track with vocal | original (full mix) | -10 dB, HPF+LPF, ghost reference |
| Instrumental | original | -12 dB, HPF only |
| Full remake (no original) | none | build from stems only |
| Dense mix needs glue | original | -8 dB, wide filter |

Anchor = original track playing quietly alongside stems for reference/glue. Not always needed.

## Stage 4: Arrange (openDAW)

### Decision Point: Keep Suno arrangement or rebuild?

| Goal | Approach |
|------|----------|
| Polish (keep structure) | Stems as-is, just mix |
| Remix (change structure) | Cut/copy/reorder regions |
| Remake (new structure) | Build new arrangement from stem fragments |
| Extend (add sections) | Duplicate regions, add new parts |
| **Auto-remix (new)** | **`remix_track` — one call: analyze + import + harmony + mix + master** |

### Auto-analysis: BPM + key detection (new)

`analyze_track` runs BPM + key + LUFS + duration + dynamic range in one call:

```python
# One call — full analysis
result = await mcp_opendaw_analyze_track("/tmp/suno_track.wav")
# → {bpm: 128.0, key: "A", mode: "minor", lufs_integrated: -14.2,
#    duration_seconds: 30.0, dynamic_range_db: 8.5, chroma: [...]}

# Auto-match project tempo
await mcp_opendaw_set_bpm(result["bpm"])

# Auto-generate matching progression from detected key
await mcp_opendaw_create_progression_from_key(
    key=result["key"], mode=result["mode"], style="synthwave")
# → Am-F-C-G (diatonic, key-matched)
```

### One-call remix (new)

`remix_track` does the entire pipeline in one call:

```python
# 7 steps in 1 call: analyze → set_bpm → import → progression → harmony → mix → master
await mcp_opendaw_remix_track(
    filename="/tmp/suno_track.wav",
    genre="synthwave",
    style="synthwave",
    stem_mode="bs6",
    add_counter_melody=True,
    master_lufs=-14,
)
# → remix_complete: True, ready_for_export: True
await mcp_opendaw_render_full(filename="remix_final")
```

### Audio-to-MIDI transcription (new)

Three tools convert audio into editable MIDI — extract drums, melody, or both:

```python
# 1. Drum transcription — kick/snare/hat from any audio
result = await mcp_opendaw_transcribe_drums("/tmp/suno_track.wav", bpm=120)
# → {notes_created: 42, band_counts: {kick: 12, snare: 8, hat: 22}}

# 2. Melody transcription — pitched notes (bass, vocal, lead)
result = await mcp_opendaw_transcribe_melody("/tmp/suno_track.wav", bpm=120)
# → {notes_created: 15, avg_clarity: 0.78}

# 3. Composite — drums + melody in one call on 2 tracks
result = await mcp_opendaw_transcribe_audio("/tmp/suno_track.wav", bpm=0)
# → bpm auto-detected, drums on track 0, melody on track 1

# Full Suno-to-MIDI-remix pipeline:
# 1. Generate track with Suno (chirp_generate)
# 2. Download audio
# 3. Transcribe to MIDI
# 4. Replace instruments, quantize, rearrange
# 5. Render
await mcp_opendaw_transcribe_audio("/tmp/suno_track.wav")
# → full MIDI reconstruction on 2 tracks, ready to edit
```

### Region operations

```python
# Trim stem to specific section
await mcp_opendaw_set_region_duration(unit, track, region, new_duration_beats)

# Loop a section
await mcp_opendaw_set_region_loop(unit, track, region, loop_beats=4.0)

# Duplicate a section (verse → verse 2)
await mcp_opendaw_duplicate_region(unit, track, region, find_free_space=True)

# Move stem fragment to new position
await mcp_opendaw_set_region_position(track, region, position_beats=32.0)
```

### Tempo matching

Suno generates at its own BPM. openDAW project BPM must match:

```python
# Detect BPM from stems (librosa)
# Then set project BPM
await mcp_opendaw_set_bpm(detected_bpm)
```

### Adding new elements

```python
# Add a synth layer on top of Suno stems
synth_track = await mcp_opendaw_create_note_track(0)
await mcp_opendaw_create_instrument(0, "Vaporisateur")
await mcp_opendaw_create_note_region(0, synth_track, position=0, duration=16)
await mcp_opendaw_create_notes_batch(0, synth_track, region, notes_json)

# Add a drum machine layer
drum_track = await mcp_opendaw_create_note_track(0)
await mcp_opendaw_create_instrument(0, "Playfield")
await mcp_opendaw_create_drum_pattern(0, drum_track, region, pattern_json)
```

## Stage 5: Mix (openDAW)

See `adaptive-mix-mastering` skill for full mix pipeline. Key Suno-specific points:

### Suno stereo collapse

Suno Studio render collapses stereo (correlation 0.84+). Pan in openDAW:

```python
# Re-pan stems for width
await mcp_opendaw_set_track_pan(unit, drums_track, 0.0)     # center
await mcp_opendaw_set_track_pan(unit, bass_track, 0.0)      # center
await mcp_opendaw_set_track_pan(unit, vocal_track, 0.3)     # slight R
await mcp_opendaw_set_track_pan(unit, other_track, -0.5)    # L
await mcp_opendaw_set_track_pan(unit, guitar_track, 0.7)    # hard R
await mcp_opendaw_set_track_pan(unit, piano_track, -0.7)    # hard L
```

### Suno frequency characteristics

| Stem | Typical issues | Fix |
|------|---------------|-----|
| Vocals | dark, lacks air | highShelf@12k +6-8 dB |
| Bass | muddy 200-400 Hz | lowBell@300 -3 dB Q 1.2 |
| Drums | compressed, lacks punch | parallel comp, transient boost |
| Other | dense, masks vocals | HPF 200 Hz, -3 dB overall |

### Effect chain per stem (decision points)

| Stem | Chain | Key params |
|------|-------|------------|
| Vocals | Revamp EQ → Compressor → DattorroReverb (send) | HPF 100, +air, 3:1 comp, reverb -8dB |
| Bass | Revamp EQ → Waveshaper (gentle) | HPF 30, -200Hz mud, drive 0.3 |
| Drums | Compressor (parallel) → Revamp EQ | 4:1 comp, +60Hz kick, +4k snare crack |
| Other | Revamp EQ → StereoTool | HPF 150, width 1.3 |
| Guitar | Revamp EQ → Delay (send) | HPF 100, delay 1/4 -18dB |
| Piano | Revamp EQ → Reverb (send) | HPF 80, reverb -10dB |

### Sidechain (if electronic)

```python
# Drums → bass sidechain
await mcp_opendaw_create_sidechain(drums_unit, bass_unit, bass_comp_effect_idx)
# Settings: threshold -20, ratio 4, attack 5ms, release 80ms
```

## Stage 6: Master + Export

### Decision Point: Platform Target

| Platform | LUFS | Approach |
|----------|------|----------|
| Spotify/YouTube | -14 | standard, ceiling -1.0 dBTP |
| Apple Music | -16 | quieter, more dynamic |
| SoundCloud | -10 to -12 | louder OK |
| Club/festival | -8 to -10 | loud, compressed |
| User preference | ASKED | always honor |

### Mastering chain

```python
# One-call mastering
await mcp_opendaw_add_mastering_chain(target_lufs=-14, style="balanced")
# Adds: Revamp EQ → Compressor → Maximizer on output bus

# Or manual chain for control
await mcp_opendaw_add_effect(output_unit, "Revamp")    # EQ
await mcp_opendaw_add_effect(output_unit, "Compressor") # glue
# Maximizer already on Output unit (auto-added)
```

### Export

```python
# Final master
await mcp_opendaw_render_audio("/tmp/final.wav")

# Stems for further processing
await mcp_opendaw_export_stems("/tmp/stems/")

# dawproject for Ableton/Bitwig interchange
await mcp_opendaw_export_dawproject("remix_project")
```

### Verify

```bash
# Measure LUFS, true peak, crest
python3 -c "
import pyloudnorm as pyln, soundfile as sf
y, sr = sf.read('final.wav')
meter = pyln.Meter(sr)
print(f'LUFS: {meter.integrated_loudness(y):.1f}')
print(f'True peak: {20*np.log10(np.max(np.abs(y))):.1f} dB')
"
```

## Complete E2E Example

### 4-call pipeline (recommended — uses remix_track)

```python
import asyncio
from server import (
    bridge,
    mcp_opendaw_download_audio,
    mcp_opendaw_remix_track,
    mcp_opendaw_render_full,
)

async def suno_remix_4call(suno_url: str):
    """Full pipeline: Suno URL → remix → render. 4 calls total."""
    await bridge.start()

    # Call 1: Download Suno track
    dl = await mcp_opendaw_download_audio(url=suno_url, filename="suno_track.wav")
    path = dl["file_path"]

    # Call 2: Full remix (analyze + set_bpm + import + progression + harmony + mix + master)
    remix = await mcp_opendaw_remix_track(
        filename=path,
        genre="synthwave",
        style="synthwave",
        stem_mode="bs6",
        add_counter_melody=True,
        master_lufs=-14,
    )

    # Call 3: Render
    await mcp_opendaw_render_full(filename="remix_final", sample_rate=48000)

    await bridge.stop()
    return f"Done: {remix}"

# asyncio.run(suno_remix_4call("https://cdn.suno.ai/abc123.wav"))
```

### Manual pipeline (full control — 7 calls)

```python
import asyncio
from server import (
    bridge,
    mcp_opendaw_download_audio,
    mcp_opendaw_analyze_track,
    mcp_opendaw_set_bpm,
    mcp_opendaw_import_audio_to_tracks,
    mcp_opendaw_create_progression_from_key,
    mcp_opendaw_create_harmonic_arrangement,
    mcp_opendaw_apply_genre_mix,
    mcp_opendaw_add_mastering_chain,
    mcp_opendaw_render_full,
)

async def suno_to_opendaw_full(suno_url: str):
    """Manual pipeline: full control over each step."""
    await bridge.start()

    # S1: Download
    dl = await mcp_opendaw_download_audio(url=suno_url, filename="suno_track.wav")
    path = dl["file_path"]

    # S2: Analyze (BPM + key + LUFS in one call)
    analysis = await mcp_opendaw_analyze_track(path)

    # S3: Set BPM
    await mcp_opendaw_set_bpm(bpm=analysis["bpm"])

    # S4: Import stems
    imp = await mcp_opendaw_import_audio_to_tracks(file_path=path, mode="bs6")

    # S5: Auto-progression from detected key
    prog = await mcp_opendaw_create_progression_from_key(
        key=analysis["key"], mode=analysis["mode"], style="synthwave")

    # S6: Harmonic arrangement + mix + master
    await mcp_opendaw_create_harmonic_arrangement(
        "-".join(prog["progression"]), pad_octave=-1, bass_pattern="")
    await mcp_opendaw_apply_genre_mix("synthwave", sidechain=True)
    await mcp_opendaw_add_mastering_chain(target_lufs=-14)

    # S7: Render
    await mcp_opendaw_render_full(filename="suno_final", sample_rate=48000)

    await bridge.stop()
    return f"Done: {imp['tracks_created']} stems → mixed → mastered → rendered"

# asyncio.run(suno_to_opendaw_full("https://cdn.suno.ai/abc123.wav"))
```

## Pitfalls (Suno-specific)

1. **Suno stereo collapse** — correlation 0.84+, pan in openDAW not Suno Studio
2. **Stem names ≠ instruments** — "guitar" in bs6 is catch-all, check RMS
3. **Vocal bleed** — PolarFormer pre-start bleed: zero vocal stems ONLY
4. **Tempo drift** — Suno BPM can drift ±0.5, detect from stems not metadata
5. **Loud stems** — Suno renders hot (-8 to -10 LUFS), normalize before mixing
6. **DC offset** — some Suno renders have DC, use `werkstatt_dcremover.js` or HPF 30Hz
7. **Phase issues** — splitting/recombining can cause phase cancellation, check mono compatibility
8. **Vocal reverb residual** — `dereverb` mode leaves reverb tail, may need manual cleanup

## Related Skills

- `adaptive-mix-mastering` — full mix→master pipeline with decision points
- `opendaw-track-architecture` — tracks, regions, clips, notes, tempo
- `opendaw-sound-design` — instruments + scriptable DSP
- `opendaw-effect-routing` — effect chains, sends, sidechain, render
- `opendaw-automation` — 416 MCP tools full API reference

## Tooling

- **Suno**: `chirp_generate` (7 models, simple/custom mode, 2 variations per call)
- **Download**: `mcp_opendaw_download_audio` (URL → local file, streaming, 60s timeout)
- **Analysis**: `mcp_opendaw_analyze_track` (BPM + key + LUFS + duration + DR, one call)
- **BPM**: `mcp_opendaw_detect_bpm` (onset + autocorrelation, pure Python)
- **Key**: `mcp_opendaw_detect_key` (chroma + Krumhansl-Schmuckler, pure Python FFT)
- **Progression**: `mcp_opendaw_create_progression_from_key` (diatonic, 6 styles, 12 templates)
- **Remix**: `mcp_opendaw_remix_track` (7-step pipeline in one call)
- **Import**: `mcp_opendaw_import_audio_to_tracks` (file → stems → tracks, one call)
- **Stem splitter**: `mcp_opendaw_split_stems` (7 modes, GPU local)
- **openDAW MCP**: v1.241.0 (v1.241.0)
- **DSP scripts**: 108 scripts (88 Werkstatt + 9 Apparat + 10 Spielwerk)
- **Mix**: `apply_genre_mix` (15 genres), `apply_full_mix` (one-call chains+mastering)
- **Master**: `add_mastering_chain` (EQ + comp + maximizer, LUFS targeting)
- **Render**: `render_full` (auto-detect length + 4 beat tail)
- **Analysis**: `analyze_track` (BPM + key + LUFS + DR, pure Python, no external deps)
