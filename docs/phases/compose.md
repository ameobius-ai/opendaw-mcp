# Compose Phase — Agent Guide

## When to use this phase
```
OPENDAW_MCP_MODE=phase
switch_phase("compose")
```

## Core workflow

### 1. Set tempo
```
set_bpm(bpm=128)
```

### 2. Create tracks
```
create_note_track(name="Lead")       # melody/synth
create_note_track(name="Bass")
create_note_track(name="Chords")
create_audio_track(name="Drums")     # audio drum loop
```

### 3. Arrange song structure
```
arrange_full_song(structure="intro:4,verse:8,prechorus:2,chorus:8,verse:8,prechorus:2,chorus:8,bridge:4,chorus:8,outro:4", key_root="C", scale_type="minor")
```
Creates markers + MIDI regions for all sections automatically.

### 4. Build compositional layers
```
create_drum_pattern(genre="house", unit_index=0)    # genre drums
create_bassline(genre="house", unit_index=1)         # genre bass
create_melody(scale_type="minor", key_root="C", pattern="1 2 3 4 5 4 3 2 1 7 6 5 4 3 2 1", unit_index=2)
create_chord_progression(chords="Am7,Fmaj7,Cmaj7,G7", unit_index=3)
```

### 5. Section generators (optional, for custom sections)
```
create_intro(type="ambient", key_root="C", scale_type="minor", bars=4)
create_verse(type="narrative", key_root="C", scale_type="minor", bars=8)
create_prechorus(type="build", key_root="C", scale_type="minor", bars=2)
create_chorus(type="anthemic", key_root="C", scale_type="minor", bars=8)
create_bridge(type="breakdown", key_root="C", scale_type="minor", bars=4)
create_outro(type="fade", key_root="C", scale_type="minor", bars=4)
```

### 6. Advanced composition
```
create_arpeggio(chord="Cmin7", rate="1/8", steps=8)
create_harmony(intervals="3,5", unit_index=2)
create_descant(type="soaring", key_root="C", scale_type="minor", bars=4)
create_counter_melody(type="contrary", key_root="C", scale_type="minor", bars=8)
create_riff(type="rock", key_root="C", scale_type="minor", bars=2)
create_hook(type="pop", key_root="C", scale_type="minor", bars=4)
```

### 7. Note editing
```
humanize_notes(unit_index=2, track_index=0, amount=0.15)
transposenotes(unit_index=2, track_index=0, semitones=12)
quantize_notes(unit_index=2, track_index=0, grid="1/16")
```

### 8. Scriptable devices (DSP synthesis)
```
set_script_device_code(device_type="apparat", unit_index=4, device_index=0, code="...")
set_script_param(device_type="apparat", unit_index=4, device_index=0, param_name="cutoff", value=0.7)
```

## Key-aware chord progressions
Use `_build_chord_prog(key_root, scale_type)` logic:
- **Major**: I-V-vi-IV (e.g. Cmaj7,G7,Am7,Fmaj7)
- **Minor**: i-VI-III-VII (e.g. Am7,Fmaj7,Cmaj7,G7)
- **Harmonic minor**: i-iv-V-i (e.g. Em7,Am7,B7,Em7)

## 37 genre arrangements available
house, techno, dnb, liquid_dnb, neurofunk, trap, dubstep, synthwave, trance, disco,
afrobeat, rock, jazz, pop, funk, reggae, lofi, soul, rnb, blues, country, metal,
gospel, edm, hardstyle, garage, acid, psytrance, breakbeat, downtempo, ambient,
phonk, future_bass, harmonic, industrial, kpop, jpop

## Next phase
After composition is done, switch to mix:
```
switch_phase("mix")
```
