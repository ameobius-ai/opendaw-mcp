---
name: opendaw-track-architecture
description: "openDAW track structure, regions, clips, tempo, markers, groove, song form. How to build the skeleton of a track with MCP tools. Covers 50+ tools across track/region/clip/marker/tempo/groove/note categories."
tags: [opendaw, mcp, tracks, regions, clips, tempo, markers, song-structure]
---

# openDAW Track Architecture

Скелет трека: треки, регионы, клипы, ноты, темпо, сигнатуры, маркеры, грув.
Это первый слой — до эффектов и инструментов. Структура = основа.

## Когда использовать

- Юзер просит "сделай трек", "создай бит", "набросай структуру"
- Нужно создать song structure (intro/verse/chorus/bridge/outro)
- Нужно расставить маркеры, темпо-изменения, time signature
- Нужно создать клипы в session view
- Нужно управлять нотами (pitch/velocity/duration/position)

## Track Types

| Type | MCP tool | What it holds |
|------|----------|---------------|
| Audio track | `create_audio_track` | Audio regions (WAV clips) |
| Note track | `create_note_track` | MIDI regions (note events) |
| Automation track | `create_automation_track` | Value regions (parameter automation) |

### Creating tracks

```python
# Audio track (for WAV stems, samples)
await mcp_opendaw_create_audio_track()  # returns track index

# Note track (for MIDI, synths)
await mcp_opendaw_create_note_track(unit_index)

# Automation track (for parameter sweeps)
await mcp_opendaw_create_automation_track(unit_index, parameter_name)
```

**Pitfall:** `create_audio_track()` has NO arguments. It creates on the primary AU.
**Pitfall:** `create_note_track(unit_index)` — unit_index REQUIRED (which AU owns the track).

## Regions

Regions are containers on tracks that hold content.

| Region type | MCP tool | Content |
|-------------|----------|---------|
| Note region | `create_note_region` | Note events (MIDI) |
| Audio region | `create_audio_region` | Audio clip reference |
| Value region | `create_value_region` | Automation events |

```python
# Note region on a note track
await mcp_opendaw_create_note_region(unit_index, track_index, position, duration, name)

# Audio region (stretched or not)
await mcp_opendaw_create_audio_region(unit_index, track_index, sample_id, position, duration)

# Time-stretched audio region
await mcp_opendaw_create_time_stretched_region(unit_index, track_index, sample_id, position, duration, playback_rate, transient_mode)

# Pitch-shifted audio region
await mcp_opendaw_create_pitch_stretched_region(unit_index, track_index, sample_id, position, duration, pitch_shift)
```

### Region operations

```python
await mcp_opendaw_delete_region(unit_index, track_index, region_index)
await mcp_opendaw_duplicate_region(unit_index, track_index, region_index, find_free_space=True)
await mcp_opendaw_transfer_region(src_unit, src_track, region_index, dst_unit, dst_track, position, delete_source=False)
await mcp_opendaw_copy_region_to_track(src_unit, src_track, src_region, dst_unit, dst_track, position)
await mcp_opendaw_set_region_color(unit_index, track_index, region_index, hue)  # 0-360
await mcp_opendaw_set_audio_region_fade(unit_index, track_index, region_index, fade_in, fade_out, in_slope, out_slope)
await mcp_opendaw_set_audio_region_gain(unit_index, track_index, region_index, gain_db)
```

## Clips (Session View)

Clips are session-view containers — alternative to timeline regions for live performance.

```python
await mcp_opendaw_create_audio_clip(sample_id, unit_index, clip_index, track_index, bpm)
await mcp_opendaw_create_note_clip(unit_index, clip_index, track_index)
await mcp_opendaw_create_value_clip(unit_index, clip_index, track_index)
await mcp_opendaw_set_clip_playback(unit_index, clip_index, track_index, loop=True, reverse=False, speed=1.0, quantise=True, trigger="default")
await mcp_opendaw_set_clip_color(unit_index, clip_index, track_index, hue)
await mcp_opendaw_set_clip_label(unit_index, clip_index, track_index, label)
await mcp_opendaw_set_clip_mute(unit_index, clip_index, track_index, muted)
await mcp_opendaw_set_clip_duration(unit_index, clip_index, track_index, duration)
await mcp_opendaw_list_clips(unit_index)
```

## Notes (MIDI Events)

### Creating notes

```python
# Single note
await mcp_opendaw_create_note(unit_index, track_index, region_index, pitch, position, duration, velocity, cent)

# Batch (orchestration tool — up to 500 notes)
await mcp_opendaw_create_notes_batch(unit_index, track_index, region_index, notes_json)
# notes_json = [{"pitch": 60, "start": 0.0, "duration": 0.25, "velocity": 0.8}, ...]
```

### Note parameters

| Param | Range | Default | Meaning |
|-------|-------|---------|---------|
| pitch | 0-127 | 60 (C4) | MIDI note number |
| position | beats (float) | 0.0 | Start position |
| duration | beats (float) | 0.25 | Length |
| velocity | 0.0-1.0 | 0.787 | Loudness |
| cent | -50..+50 | 0 | Pitch bend (cents) |
| chance | 0-100 | 100 | Probability of playing |

### Note editing

```python
await mcp_opendaw_set_note_velocity(unit_index, track_index, region_index, note_index, velocity)
await mcp_opendaw_set_note_pitch(unit_index, track_index, region_index, note_index, pitch)
await mcp_opendaw_set_note_duration(unit_index, track_index, region_index, note_index, duration)
await mcp_opendaw_set_note_position(unit_index, track_index, region_index, note_index, position)
await mcp_opendaw_delete_note(unit_index, track_index, region_index, note_index)
await mcp_opendaw_duplicate_note_event(unit_index, track_index, region_index, note_index, position_offset=0, pitch_offset=0)
```

### Drum patterns (orchestration)

```python
# Compact step-sequencer notation
await mcp_opendaw_create_drum_pattern(unit_index, track_index, region_index, pattern_json)
# pattern_json = {"kick": "x...x...x...x...", "snare": "....x.......x...", "hihat": "o.o.o.o.o.o.o.o."}
# x=hit(0.9), o=soft(0.5), .=rest, X=accent(1.0)
# Lanes: kick(36), snare(38), hihat(42), clap(39), perc(47)
```

### Chord progressions (orchestration)

```python
await mcp_opendaw_create_chord_progression(unit_index, track_index, region_index, chords_json, bpm)
# chords_json = [["A", "min"], ["F", "maj7"], ["C", "maj"], ["G", "dom7"]]
# Types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug
# Voicing centered around C4 (60), root pitched down if > F# for compact voicing
```

## Tempo

```python
await mcp_opendaw_set_bpm(bpm)  # 60-240
await mcp_opendaw_get_bpm()
await mcp_opendaw_add_tempo_change(unit_index, position, bpm)  # tempo automation
```

**Pitfall:** BPM normalized 0..1 internally. `h.api.setBpm(bpm)` handles conversion. Never set raw tempo field.
**Pitfall:** TempoTrack BPM range: min=60, max=240. Values outside are clamped.

## Time Signature

```python
await mcp_opendaw_add_signature_change(unit_index, position, numerator, denominator)
await mcp_opendaw_list_signature_changes()
await mcp_opendaw_delete_signature_change(unit_index, event_index)
```

**Pitfall:** SignatureEventBox is lazy-loaded. Position in PPQN.

## Markers

```python
await mcp_opendaw_add_marker(position, name, hue)
await mcp_opendaw_set_marker_position(marker_index, new_position)
await mcp_opendaw_list_markers()
```

**Pitfall:** `p.api.addMarker` does NOT exist. Uses `MarkerBox.create()` directly.
**Pitfall:** Marker position in PPQN: `Math.round(position_beats * h.ppqn.Quarter)`. PPQN.Quarter = 960.
**Pitfall:** `box.track.refer(markerTrack.markers)`, not `box.markers`.

### Song structure (orchestration)

```python
await mcp_opendaw_create_song_structure(sections_json)
# sections_json = [{"name": "Intro", "bars": 4}, {"name": "Verse", "bars": 8}, ...]
# Creates markers at section boundaries. Position = accumulated beats (bars × 4).
```

## Groove

```python
await mcp_opendaw_set_groove_shuffle(shuffle_amount)  # 0-1
await mcp_opendaw_set_groove_timing(timing_amount)    # 0-1
```

GrooveShuffleBox — affects swing/timing feel across the project.

## Warp Markers (for stretched audio)

```python
await mcp_opendaw_create_warp_marker(unit_index, track_index, region_index, position, bpm)
await mcp_opendaw_delete_warp_marker(unit_index, track_index, region_index, marker_index)
await mcp_opendaw_update_warp_marker(unit_index, track_index, region_index, marker_index, new_bpm)
```

## Quantization

```python
await mcp_opendaw_quantize_notes(unit_index, track_index, region_index, division, strength, swing)
# division: "1/4", "1/8", "1/16", "1/32"
# strength: 0.0-1.0 (1.0 = full quantize, 0.5 = 50% pull)
# swing: 0.0-1.0
```

## Track operations

```python
await mcp_opendaw_list_tracks()
await mcp_opendaw_delete_track(unit_index, track_index)
await mcp_opendaw_move_region_to_track(src_unit, src_track, region_index, dst_unit, dst_track, position)
await mcp_opendaw_set_track_volume(unit_index, track_index, volume_db)
await mcp_opendaw_set_track_pan(unit_index, track_index, pan)  # -1.0..+1.0
await mcp_opendaw_set_track_color(unit_index, track_index, hue)  # 0-360
await mcp_opendaw_set_track_enabled(unit_index, track_index, enabled)  # mute toggle
```

**Pitfall:** Pan is `auBox.panning.setValue(-1.0..+1.0)`, NOT `trackBox.pan`. 0=center.

## Genre presets (orchestration)

```python
await mcp_opendaw_create_genre_track(genre, bpm=None)
# Genres: house, techno, lofi, dnb, trap, ambient
# Creates: 2 synth AUs (Vaporisateur), chord notes, bass notes, drum pattern
# Each genre has hardcoded: BPM, drum pattern, bass line, chord progression
```

## Decision points for agents

### "Create a track" → what type?

| User wants | Track type | Tool chain |
|------------|-----------|------------|
| Drums | Note track + Playfield | `create_note_track` → `create_drum_pattern` |
| Synth melody | Note track + Vaporisateur | `create_note_track` → `create_note` × N |
| Audio sample | Audio track | `create_audio_track` → `load_audio` → `create_audio_clip` |
| Parameter automation | Automation track | `create_automation_track` → `automation_sweep` |
| Full song | Multiple tracks + markers | `create_song_structure` → tracks → notes → effects |

### "How many tracks?"

| Genre | Typical layout |
|-------|---------------|
| Electronic (techno/house) | drums + bass + 2 synths + pad = 5 tracks |
| Hip-hop | drums + 808 + sample + vocal = 4 tracks |
| Coldwave | drums + bass + 2 vocals + 2 synths = 7 tracks |
| Ambient | pad + texture + field = 3 tracks |
| Rock | drums + bass + vocal + 2 guitars = 5 tracks |

Start minimal — add tracks as needed. Don't over-architect before the user hears anything.

## Related skills
- `opendaw-automation` — 258 MCP tools full API reference + pitfalls
- `opendaw-sound-design` — instruments + scriptable DSP
- `opendaw-effect-routing` — effect chains, sends, buses, sidechain
- `adaptive-mix-mastering` — full mix→master pipeline with decision points
