# Render Phase — Agent Guide

## When to use this phase
```
OPENDAW_MCP_MODE=phase
switch_phase("render")
```

## Core workflow

### 1. Render full mix
```
render_full()
```
Renders the complete project to WAV (48kHz, 32-bit float).

### 2. Export stems
```
export_stems()
```
Exports each track as a separate WAV file.

### 3. Export single region
```
export_region_audio(unit_index=0, region_index=0)
```

### 4. Audio I/O
```
load_audio(file_path="/path/to/drum_loop.wav")
place_audio_region(unit_index=0, file_path="/path/to/bass.wav", start_beat=0)
```

### 5. Audio region editing
```
set_audio_region_fade(unit_index=0, region_index=0, fade_in=2.0, fade_out=4.0)
set_audio_region_gain(unit_index=0, region_index=0, gain_db=-3.0)
```

### 6. Time/pitch stretch
```
create_time_stretched_clip(unit_index=0, file_path="...", stretch_ratio=1.5)
create_pitch_stretched_clip(unit_index=0, file_path="...", pitch_shift=2)
```

### 7. Presets
```
save_preset(file_path="/path/to/preset.opb")
load_preset(file_path="/path/to/preset.opb")
```

## Render targets
- **WAV 48kHz 32-bit float** (default)
- Offline renderer with full DSP chain
- Timeout: 1200s (Hermes config)
- Render time: ~234s for 6 stems, 272.8s duration

## Stem separation
7 SOTA models available (separate from phase system):
- BS-Roformer, HTDemucs FT, SCNet, MelBand Roformer
- Modes: 2-stem, 4-stem, 6-stem, karaoke, denoise

## One-call pipeline
For complete production + mastering + render + verification:
```
switch_phase("compose")
produce_and_master(
    structure="intro:4,verse:8,prechorus:2,chorus:8,verse:8,prechorus:2,chorus:8,bridge:4,chorus:8,outro:4",
    key_root="C",
    scale_type="minor",
    genre="house",
    bpm=128,
    platform="spotify",
    master_style="balanced",
    render=True
)
```
10 steps: BPM → arrange → drums → bass → melody → chords → genre FX → master → render → verify
