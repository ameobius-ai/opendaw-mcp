---
name: suno-to-opendaw
description: "End-to-end pipeline: Suno AI generation → SOTA stem separation → openDAW import → mix/master → export. The killer workflow that no other MCP server offers. 7 stem-split modes, 263 DAW tools, adaptive mastering. From prompt to finished track."
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
# Download audio_url → WAV/MP3 for next stage
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

Stems → openDAW tracks. `split_stems(import_to_daw=True)` auto-imports.

### Manual import (if split was done CLI)

```python
# Load each stem
sample_ids = []
for stem in ["bass", "drums", "vocals", "other"]:
    sid = await mcp_opendaw_load_audio(f"stems/{stem}.wav", stem)
    sample_ids.append(sid)

# Create audio tracks
for i, stem in enumerate(["bass", "drums", "vocals", "other"]):
    track_idx = await mcp_opendaw_create_audio_track()
    await mcp_opendaw_create_audio_region(0, track_idx, sample_ids[i], position=0, duration=...)
```

### Auto-import (preferred)

```python
result = await mcp_opendaw_split_stems("track.wav", mode="bs6", import_to_daw=True)
# Returns: {stems: [{name, path, sample_id}], ...}
# Each stem already loaded as audio region on a new track
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

```python
import asyncio
from server import HeadlessDawBridge

async def suno_to_opendaw():
    bridge = HeadlessDawBridge()
    await bridge.start()

    # S1: Generate (or user provides Suno URL)
    # ... download Suno audio to /tmp/suno_track.wav ...

    # S2: Split — 6 stems, auto-import to DAW
    split = await bridge.evaluate(f"""
        () => {{
            // Use MCP split_stems tool logic
            return {{stems: 6, modes: "bs6"}};
        }}
    """)
    # Or call mcp_opendaw_split_stems directly

    # S3: Import — already done by import_to_daw=True
    # Stems loaded as tracks 0-5

    # S4: Arrange — set BPM, add markers
    await bridge.evaluate("""
        () => {
            const h = window.DAW_HELPERS;
            h.api.setBpm(128);
            return {bpm: 128};
        }
    """)

    # S5: Mix — pan, levels, effects
    # ... see adaptive-mix-mastering skill ...

    # S6: Master + Export
    # ... render_audio, measure LUFS, adjust ...

    await bridge.stop()

asyncio.run(suno_to_opendaw())
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
- `opendaw-automation` — 263 MCP tools full API reference

## Tooling

- **Suno**: `chirp_generate` (7 models, simple/custom mode)
- **Stem splitter**: `mcp_opendaw_split_stems` (7 modes, GPU local)
- **openDAW MCP**: 263 tools (v1.13.1)
- **Analysis**: pyloudnorm + librosa (LUFS, BPM, spectral)
- **DSP scripts**: 26 scripts (15 Werkstatt + 5 Apparat + 6 Spielwerk)
