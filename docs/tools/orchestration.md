# Orchestration Tools

8 high-level composers that combine multiple low-level operations into a single call.
Designed for agents — reduce token usage and round-trips when building musical structures.

## Orchestration Tools (8)

| Tool | Description |
|------|-------------|
| `create_notes_batch` | Create multiple MIDI notes from a JSON array in one call |
| `create_drum_pattern` | Create a drum beat from compact step-sequencer notation |
| `create_chord_progression` | Create chords from names (Cm, Fm7, Gdom7) — auto-voiced |
| `create_melody` | Create a melody from scale + rhythmic pattern using scale degrees (1-7) |
| `create_bassline` | Create a bassline from root + rhythmic pattern with low octave and high velocity |
| `create_arpeggio` | Create an arpeggio from chord name — 6 patterns (up/down/updown/downup/random/chord) |
| `add_mastering_chain` | Add EQ + Compressor + Maximizer to output bus with genre presets |
| `create_genre_track` | Create a full genre starting point in one call |
| `create_song_structure` | Create arrangement markers from JSON section list |
| `automation_sweep` | Create smooth automation ramps with linear/exp/log curves |
| `apply_mix_preset` | Apply volume/pan/mute/solo to all units from JSON or named preset |

## create_notes_batch

Replaces 10-50 `create_note` calls with one:

```python
await server.mcp_opendaw_create_notes_batch(
    notes=[
        {"pitch": 60, "position": 0,    "duration": 480},
        {"pitch": 64, "position": 480,  "duration": 480},
        {"pitch": 67, "position": 960,  "duration": 480},
        {"pitch": 72, "position": 1440, "duration": 960},
    ],
    unit_index=0,
    track_index=0
)
# Returns: {"notes_created": 4}
```

## create_drum_pattern

Compact step-sequencer notation. One call = full beat.

Notation:

| Symbol | Meaning |
|--------|---------|
| `x` | Hit (normal velocity) |
| `o` | Accent (high velocity) |
| `.` | Rest |
| `X` | Ghost (low velocity) |

Lanes separated by `|`:

```python
await server.mcp_opendaw_create_drum_pattern(
    pattern="x...x...x...x...|o.......o.....o.|..x...x...x...x.",
    unit_index=0
)
# Returns: {"total_notes": 10, "lanes": ["kick", "snare", "hihat"]}
```

Each lane is 16 steps (one bar of 16th notes). First lane = kick, second = snare, third = hihat.

## create_chord_progression

Create chords from names — auto-voiced, positioned, batched:

```python
await server.mcp_opendaw_create_chord_progression(
    chords=["Cm", "Fm7", "Gdom7", "Cm"],
    unit_index=1,
    track_index=0,
    duration=1920  # 2 bars per chord
)
```

Supported chord types: maj, min, dim, aug, sus2, sus4, dom7, maj7, min7, m7b5, etc.

## create_melody

Create a melody from a scale + rhythmic pattern using scale degrees:

```python
await server.mcp_opendaw_create_melody(
    scale="minor",
    root="A",
    pattern="1 0 3 0 5 - 4 3 2 0 1 + 1",
    unit_index=1,
    track_index=0,
    start_beat=0,
    octave=4,
    velocity=0.75
)
```

Pattern syntax (space-separated, each step = one 16th note):

| Symbol | Meaning |
|--------|---------|
| `1`-`7` | Scale degree (1 = root) |
| `0` | Rest |
| `-` | Sustain previous note (extend by one step) |
| `+` | Octave up (applies to next note only) |

Supports 14 scales: major, minor, harmonic_minor, melodic_minor, dorian, phrygian, lydian, mixolydian, locrian, pentatonic_major, pentatonic_minor, blues, chromatic.

## create_bassline

Create a bassline from root + rhythmic pattern with low octave and high velocity:

```python
await server.mcp_opendaw_create_bassline(
    root="A",
    pattern="1 - - - 5 - - - 1 - - - 4 - - -",
    unit_index=2,
    track_index=0,
    octave=2,       # A2 = 45
    velocity=0.9,
    scale="minor"
)
```

Same pattern syntax as `create_melody`, plus:

| Symbol | Meaning |
|--------|---------|
| `_` | Octave down (applies to next note only) |

Default octave is 2 (C2=36) for bass range. Default velocity is 0.9 for strong bass.

## create_arpeggio

Create an arpeggio from a chord name with 6 patterns and 6 rates:

```python
await server.mcp_opendaw_create_arpeggio(
    chord="Cmin7",
    pattern="up",       # up, down, updown, downup, random, chord
    rate="16",          # 32, 16, 8, 4, 16t, 32t
    steps=16,           # number of steps (16 = one bar of 16ths)
    unit_index=1,
    track_index=0,
    octave=4,
    velocity=0.65
)
```

| Pattern | Description |
|---------|-------------|
| `up` | Bottom to top, repeat |
| `down` | Top to bottom, repeat |
| `updown` | Up then down (ping-pong) |
| `downup` | Down then up |
| `random` | Random chord tones |
| `chord` | Full chord on each step (block chords) |

## add_mastering_chain

Add EQ + Compressor + Maximizer to the output bus:

```python
await server.mcp_opendaw_add_mastering_chain(style="balanced")
# Styles: balanced, warm, loud, transparent
```

| Style | EQ | Compressor | Maximizer |
|-------|-----|------------|-----------|
| balanced | gentle tilt | 2:1, -18 dB threshold | -0.3 dB ceiling |
| warm | low shelf boost | 3:1, softer attack | -1 dB ceiling |
| loud | aggressive tilt | 4:1, -14 dB threshold | -0.1 dB ceiling |
| transparent | subtle correction | 1.5:1, -20 dB | -0.5 dB ceiling |

## create_genre_track

Create a full genre starting point — synth, drums, bass, chords, BPM in one call:

```python
await server.mcp_opendaw_create_genre_track(genre="house")
# Genres: house, techno, lofi, dnb, trap, ambient
```

Each genre template sets appropriate BPM, instrument types, and initial patterns.
See the [Examples](../examples.md) page for full genre templates.

## create_song_structure

Create arrangement markers from a JSON section list:

```python
await server.mcp_opendaw_create_song_structure(
    sections=[
        {"name": "Intro",   "length": 8},
        {"name": "Verse 1", "length": 16},
        {"name": "Chorus",  "length": 16},
        {"name": "Bridge",  "length": 8},
        {"name": "Outro",   "length": 8},
    ]
)
```

Enables agents to reason about song form — sections become navigable landmarks.

## automation_sweep

Create smooth automation ramps in one call:

```python
await server.mcp_opendaw_automation_sweep(
    unit_index=0, effect_index=0, param_name="frequency",
    start_position=0, end_position=3840,
    start_value=0.1, end_value=0.9,
    curve="log"  # or: linear, exp
)
```

Replaces 10-30 `create_automation_event` calls with a single smooth ramp.

## apply_mix_preset

Apply volume/pan/mute/solo to all units from JSON or named preset:

```python
# Named preset
await server.mcp_opendaw_apply_mix_preset(preset="lofi")

# Custom JSON
await server.mcp_opendaw_apply_mix_preset(
    preset_json={
        "0": {"volume": -3, "pan": -0.3},
        "1": {"volume": -6, "pan": 0.0},
        "2": {"volume": -8, "pan": 0.3, "mute": True},
    }
)
```

Named presets: `lofi`, `house`, `balanced`, `wide`.
