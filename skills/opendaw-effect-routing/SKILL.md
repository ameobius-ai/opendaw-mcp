---
name: opendaw-effect-routing
description: "openDAW effect chains, sends/returns, sidechain, buses, mixing, mastering chain, render/export. How to route audio through effects and deliver final output with MCP tools."
tags: [opendaw, mcp, effects, routing, sends, sidechain, buses, mixing, mastering, render, export]
---

# openDAW Effect Routing

Роутинг аудио: effect chains, send/return topology, sidechain, buses, рендер.
Третий слой — после структуры (track-architecture) и звука (sound-design).

## Когда использовать

- Нужно добавить эффекты (reverb, delay, compression, EQ, saturation)
- Нужно создать send/return (reverb bus, delay bus)
- Нужно настроить sidechain (drums→bass ducking)
- Нужно создать bus routing (subgroups, parallel chains)
- Нужно отрендерить трек (WAV, stems, LUFS targeting)
- Нужно создать mastering chain

## Effect Chain

### Adding effects

```python
# Add effect to audio unit
await mcp_opendaw_add_effect(unit_index, effect_type)
# effect_index = return value

# Available effects (15):
# Compressor, Crusher, DattorroReverb, Delay, Fold, Gate, Maximizer,
# NeuralAmp, Reverb, Revamp, StereoTool, Tidal, Vocoder, Waveshaper, Werkstatt
```

**Pitfall:** Maximizer auto-added at index 0 on Output unit. Find effects by class name:
```javascript
const fx = h.effectBoxes(au);
const compIdx = fx.findIndex(b => b.constructor.name === 'CompressorDeviceBox');
```

### Setting effect parameters

```python
# Set single param
await mcp_opendaw_set_effect_parameter(unit_index, effect_index, param_name, value)

# Get all params
await mcp_opendaw_list_effect_parameters(unit_index, effect_index)

# Get current state (all param values)
await mcp_opendaw_get_effect_state(unit_index, effect_index)
```

### Effect parameter reference

| Effect | Key params | Range |
|--------|-----------|-------|
| Compressor | threshold, ratio, attack, release, knee, makeup | -60..0 dB, 1..20, s, s, dB, dB |
| DattorroReverb | decay, predelay, damping, wet | 0..1, s, 0..1, dB |
| Delay | time, feedback, wet, sync | s, 0..0.95, dB, bool |
| Revamp (EQ) | sections (highShelf, lowShelf, bell, highpass, lowpass) | freq, gain, Q per section |
| Waveshaper | inputGain, mix, curve | dB, 0..1, enum |
| Maximizer | ceiling, release | dB, ms |
| Gate | threshold, attack, hold, release | dB, ms, ms, ms |
| NeuralAmp | model, bandCount, modulatorSource, overSampling | path, int, enum, bool |
| StereoTool | width, balance, pan | 0..2, -1..1, -1..1 |
| Vocoder | bandCount, input, modulator | int, enum, enum |
| Tidal | rate, sync, feedback | Hz, bool, 0..0.95 |
| Fold | drive, threshold | 0..2, dB |
| Crusher | bits, rate | 1..16, Hz |

### Effect operations

```python
# Duplicate effect (with all params)
await mcp_opendaw_clone_effect(src_unit, src_effect, dst_unit, dst_position)

# Delete effect
await mcp_opendaw_delete_effect(unit_index, effect_index)

# Move effect within chain
await mcp_opendaw_move_effect(unit_index, effect_index, new_position)

# Copy effect chain from one AU to another
await mcp_opendaw_clone_effect_chain(src_unit, dst_unit)
```

### Effect ordering (decision point)

| Genre | Chain order (top→bottom) |
|-------|--------------------------|
| Coldwave | EQ → Saturation → Comp → Reverb (send) |
| Techno | EQ → Comp → Saturation → Delay (send) → Reverb (send) |
| Hip-hop | EQ → Comp → Saturation → Reverb (send) |
| Rock | EQ → Amp → Comp → Reverb (send) |
| Pop | EQ → Comp → Saturation → Reverb (send) → Delay (send) |

**Principle:** Reverb and delay usually go on sends, not inserts. Inserts = EQ, comp, saturation.

## Sends / Returns

Send topology: FX unit → primary bus, FX bus → FX unit input, send → FX bus input.

```python
# Create send/return routing
await mcp_opendaw_create_send(src_unit_index, dst_bus_index, send_amount_db)

# Manage sends
await mcp_opendaw_list_sends(unit_index)
await mcp_opendaw_set_send_amount(src_unit, send_index, amount_db)
await mcp_opendaw_delete_send(src_unit, send_index)
```

### Typical send topology

```
Drums AU ──send──→ Reverb Bus ──→ DattorroReverb FX ──→ Output
Bass AU  ──send──→ Reverb Bus
Vocal AU ──send──→ Reverb Bus ──→ DattorroReverb FX
Vocal AU ──send──→ Delay Bus  ──→ Delay FX
```

### Reverb send (genre-dependent)

| Genre | Reverb type | Send level | Damping | Decay |
|-------|------------|------------|---------|-------|
| Coldwave | DattorroReverb | -10 dB | 0.2 | 0.7 |
| Pop | DattorroReverb | -6 dB | 0.5 | 0.5 |
| Hip-hop | DattorroReverb | -14 dB | 0.6 | 0.3 |
| Rock | DattorroReverb | -8 dB | 0.3 | 0.8 |
| Ambient | DattorroReverb | -4 dB | 0.4 | 0.9 |

## Sidechain

```python
# Create sidechain (drums → bass compressor)
await mcp_opendaw_create_sidechain(src_unit_index, dst_unit_index, dst_effect_index)
```

**Bridge implementation:** `p.boxGraph.registerEdge(sourceAu.audioEffects.output, compEffect.sideChain)`

**Pitfall:** Connect sidechain AFTER all stems loaded. ProcessPhase bug = first block only (~0.01s), inaudible.

### Sidechain decision point

| When | How | Settings |
|------|-----|----------|
| Electronic with kick+bass | drums→bass comp | threshold -20, ratio 4, attack 5ms, release 80ms |
| Hip-hop with 808 | 808→bass or EQ carve | sidechain or 80Hz cut on bass |
| No kick-bass conflict | skip | — |
| Vocal needs ducking | music→vocal comp | gentle, ratio 2:1 |

## Buses

```python
# Create audio bus
await mcp_opendaw_create_audio_bus(name)

# Route AU to bus
await mcp_opendaw_route_to_bus(unit_index, bus_index)

# Bus operations
await mcp_opendaw_set_bus_volume(bus_index, volume_db)
await mcp_opendaw_list_buses()
```

### Bus topology (decision point)

| Setup | Buses | When |
|-------|-------|------|
| Simple (3-4 tracks) | none (all → Output) | small project |
| Drum subgroup | drums bus → Output | need drum bus comp |
| Vocal subgroup | vocals bus → Output | need vocal bus comp |
| Full mix | drums + instruments + vocals → master bus | 8+ tracks |

## Mixing

### Track levels

```python
await mcp_opendaw_set_track_volume(unit_index, track_index, volume_db)
await mcp_opendaw_set_track_pan(unit_index, track_index, pan)  # -1.0..+1.0
await mcp_opendaw_set_track_enabled(unit_index, track_index, enabled)  # mute
```

### Mix presets (orchestration)

```python
await mcp_opendaw_apply_mix_preset(unit_index, preset_name)
# Presets: balanced, vocal_forward, bass_heavy, ambient, aggressive
```

### Volume calibration

| Platform | Target LUFS | How |
|----------|-------------|-----|
| Spotify | -14 | measure after mix, adjust master |
| Apple Music | -16 | quieter, more dynamic |
| YouTube | -14 | same as Spotify |
| Club | -8 to -10 | loud, compressed |
| SoundCloud | -10 to -12 | louder OK |

**Pitfall:** Volume field uses powerByCenter(-96, -9, +6) — dB scale. `field.setValue(value)` directly in dB.

## Mastering Chain (orchestration)

```python
# One-call mastering chain
await mcp_opendaw_add_mastering_chain(target_lufs=-14, style="balanced")
# Adds: Revamp EQ → Compressor → Maximizer on output bus
# Styles: balanced, warm, loud, transparent
# target_lufs: -14 (Spotify), -16 (Apple), -10 (loud)
```

**Pitfall:** `add_mastering_chain` does NOT set EQ params (Revamp has complex section-based params). EQ is a shell — configure separately.

## Render / Export

### Full render

```python
await mcp_opendaw_render_audio(output_path, duration_beats=None, sample_rate=44100)
# duration_beats: None = entire project, or specific length
```

### Stem export

```python
await mcp_opendaw_export_stems(output_dir, stems="all")
# stems: "all" or list of track indices
# Exports each track as separate WAV
```

### Region export

```python
await mcp_opendaw_export_region_audio(unit_index, track_index, region_index, output_path)
```

### Render with LUFS targeting

```python
# Render → measure → adjust → re-render
await mcp_opendaw_render_audio("/tmp/mix.wav")
# Then measure with pyloudnorm:
# python3 -c "import pyloudnorm as pyln; ..."
# Adjust master gain, re-render
```

**Pitfall:** `api.exportAudio` uses Files.save (file dialog), doesn't work in headless mode. Use `render_audio` instead.
**Pitfall:** AudioContext 44100 Hz in headless Chromium. OfflineEngineRenderer uses 48000.

### Render decision points

| Need | Tool | Output |
|------|------|--------|
| Final master | `render_audio` | single WAV |
| Stems for mixing | `export_stems` | per-track WAVs |
| Region preview | `export_region_audio` | single region WAV |
| MIDI export | `export_midi` | .mid file |

## Transport

```python
await mcp_opendaw_start_engine()
await mcp_opendaw_stop_engine()
await mcp_opendaw_play()
await mcp_opendaw_stop()
await mcp_opendaw_set_position(beats)
```

## Project management

```python
await mcp_opendaw_save_project(path)
await mcp_opendaw_load_project(path)
await mcp_opendaw_get_project_state()
```

**Pitfall:** `DAW_loadProject` hack: override `toArrayBuffer` → `copy()` → restore.

## Copy/move operations

```python
# Copy entire AU (instrument + effects + tracks)
await mcp_opendaw_copy_audiounit(src_unit, dst_position)

# Move AU
await mcp_opendaw_move_audio_unit(src_unit, new_position)

# Delete AU
await mcp_opendaw_delete_track(unit_index, track_index)
await mcp_opendaw_delete_audio_unit(unit_index)

# Transfer AU (copy + optional delete source)
await mcp_opendaw_transfer_audiounit(unit_index, delete_source=False, insert_index=-1)
```

## Automation

```python
# Create automation track for a parameter
await mcp_opendaw_create_automation_track(unit_index, parameter_name)

# Add automation events
await mcp_opendaw_create_automation_event(unit_index, track_index, region_index, position, value)
await mcp_opendaw_duplicate_automation_event(unit_index, track_index, region_index, event_index, position_offset=0, value_override=None)

# Sweep (orchestration — smooth ramp)
await mcp_opendaw_automation_sweep(unit_index, parameter_name, start_beat, end_beat, start_value, end_value, steps=16, curve="linear")
# curve: linear, exp, log
```

## Offline render verification

**All effects work in offline render** (code-audited July 2026):

| Effect | Status | Notes |
|--------|--------|-------|
| Gain/Volume/Pan | ✅ | Basic mixing |
| Revamp (EQ) | ✅ | highShelf/highBell on master |
| DattorroReverb | ✅ | Plate reverb, damping for character |
| Waveshaper | ✅ | hardclip on bass = roar, tanh on melodic = sand |
| Compressor | ✅ | Sidechain works, ProcessPhase bug = first block only |
| Delay | ✅ | Needs sync fraction + wet/dry |
| Tidal | ✅ | Audio loop unconditional |
| Maximizer | ✅ | Auto on Output unit |

## Related skills
- `opendaw-automation` — 391 MCP tools full API reference + pitfalls
- `opendaw-track-architecture` — tracks, regions, clips, notes, tempo, markers
- `opendaw-sound-design` — instruments + scriptable DSP (Werkstatt/Apparat/Spielwerk)
- `adaptive-mix-mastering` — full mix→master pipeline with decision points
- `coldwave-mix-mastering` — coldwave-specific session log (F01→F12)
