---
name: opendaw-composition-patterns
description: "When and how to use openDAW MCP orchestration tools for musical composition. 26 orchestration tools: drum patterns, fills, melodies, basslines, arpeggios, harmony, counterpoint, ostinato, crescendo, swing, polyrhythm, scale runs, call-response, walking bass, sidechain, ghost notes, velocity curves, articulation (staccato/legato/tenuto/accent), chord progressions, genre templates, song structure, automation sweeps, mastering chains, mix presets, humanize, reverse/invert/transpose. Decision tree: which tool for which musical goal. Not theory — concrete tool calls and parameter values."
---

# openDAW Composition Patterns

## When to use which orchestration tool

### Decision tree by musical goal

```
What do you want to create?
│
├── Full genre track → create_genre_track (house/techno/lofi/dnb/trap/ambient/coldwave/hiphop)
│
├── Drum pattern → create_drum_pattern (step-sequencer notation, x/o/.)
├── Drum fill/transition → create_drum_fill (build/break/roll/crash/tom)
├── Riser (build-up sweep) → create_riser (ascending pitch, exp/linear/log curves)
├── Stabs (house/disco/funk) → create_stab (rhythmic chord jabs, x-./. grid, ghost notes)
├── Drum break (classic) → create_break (Amen/Think/Funky Drummer/etc, variation + swing)
├── Bass drop (dubstep/EDM) → create_bass_drop (descending sweep + sustained sub bass)
├── Chop (sample flip) → create_chop (reverse/stutter/shuffle/ping-pong/gate, Dilla/Madlib/glitch)
├── Trill (ornament) → create_trill (two-note alternation, 32nd/16th/8th/triplet rates, baroque accent)
├── Mordent (ornament) → create_mordent (main→neighbor→main, upper/lower, Bach/Mozart)
├── Turn (ornament) → create_turn (main→up→main→down→main, gruppetto, Mozart/Beethoven/Bach)
├── Appoggiatura (ornament) → create_appoggiatura (approach→main, tension→release, Bach/Mozart/Chopin)
│   └── **Ornaments set complete: trill + mordent + turn + appoggiatura**
├── Glissando (scale run) → create_glissando (chromatic/diatonic/pentatonic, any direction, velocity curves)
├── Sequence (transposed repeat) → create_sequence (up/down/alternating, baroque/jazz/film score builds)
├── Pedal point (sustained bass) → create_pedal_point (bass drone under changing chords, film/organ/rock)
├── Bordun (drone chord) → create_bordun (sustained chord layer, open fifths/octaves, bagpipes/tanpura/ambient)
├── Canon (imitation) → create_canon (same melody in 2-6 voices with delayed entry + transposition, Pachelbel/rounds/fugues)
├── Comping (rhythmic chords) → create_comping (chord progression × rhythm grid, jazz/funk/reggae/country/neo-soul)
├── Hocket (interlock) → create_hocket (melody split between 2-4 voices, alternate/pairs/phrase, medieval/African/gamelan)
├── Isorhythm (talea×color) → create_isorhythm (independent rhythm×pitch cycles, phase shift at LCM, Machaut/Messiaen)
├── Hemiola (cross-rhythm) → create_hemiola (3:2 rhythmic displacement, Afro-Cuban/jazz/minimalism)
├── Ghost notes (groove) → create_ghost_notes (after creating main pattern)
├── Swing (groove) → apply_swing (after creating pattern, 0.58 = hip-hop)
│
├── Melody → create_melody (scale-based, pattern notation 1-7)
├── Bassline (static) → create_bassline (root-fifth, octave, walk-up)
├── Bassline (walking jazz) → create_walking_bass (chord progression input)
├── Arpeggio → create_arpeggio (up/down/updown/random, octaves)
├── Ostinato (repeating) → create_ostinato (short pattern × N repeats)
│
├── Chords → create_chord_progression (2-5 chords, scale-aware)
├── Harmony (parallel) → create_harmony (thirds/fifths/sixths above melody)
├── Counter-melody → create_counterpoint (contrary motion, mirror around center)
│
├── Scale run (fill) → create_scale_run (up/down, 1-4 octaves)
├── Drum fill (alt) → create_drum_fill (build/break/roll/crash/tom)
│
├── Call-and-response → create_call_response (antecedent/consequent, repeats)
├── Polyrhythm → create_polyrhythm (3:4, 2:3, 5:7 cross-rhythms)
├── Crescendo/decrescendo → create_crescendo (velocity ramp, linear/exp/log)
├── Velocity curve (envelope) → apply_velocity_curve (ramp_up/ramp_down/arc/trough/power)
│
├── Articulation → apply_articulation (staccato/legato/tenuto/accent)
│   ├── Staccato (crisp, detached) → amount=0.3
│   ├── Legato (smooth, connected) → amount=0.95
│   ├── Tenuto (full slot, no gap) → (amount unused)
│   └── Accent (downbeat boost) → amount=0.8
│
├── Sidechain (pump) → apply_sidechain (house/techno/EDM ducking)
├── Automation sweep → automation_sweep (filter/volume/parameter ramp)
├── Mix preset → apply_mix_preset (lofi/house/balanced/wide)
├── Mastering chain → add_mastering_chain (balanced/warm/loud/transparent)
│
├── Song structure → create_song_structure (intro/verse/chorus/bridge/outro markers)
├── Humanize → humanize_notes (velocity/timing/duration/swing variation)
├── Reverse → reverse_notes (mirror note order)
├── Invert → invert_notes (mirror pitches around axis)
├── Transpose → transpose_notes (shift all pitches by N semitones)
└── Quantize → quantize_notes (snap to grid, adjustable strength)
```

## Genre-specific tool recipes

### Hip-hop / lofi (BPM 80-95)
1. `create_genre_track("hiphop")` → base track
2. `apply_swing(swing_amount=0.58, grid="16th")` → laid-back groove
3. `create_ghost_notes(density=0.3, velocity=0.25)` → funk feel
4. `humanize_notes(velocity_amount=0.12, timing_amount=0.10)` → natural feel
5. `apply_mix_preset("lofi")` → warm, narrow stereo

### House / techno (BPM 120-135)
1. `create_genre_track("house")` → base track
2. `apply_sidechain(depth=0.7, release=0.25, kick_interval=1.0)` → pump
3. `create_ostinato("minor", "C", "1 5 3 5", repeats=8)` → riff
4. `add_mastering_chain("loud")` → club-ready

### Jazz (BPM 120-180)
1. `create_walking_bass(chords='[["C","maj7"],["A","min7"],["D","min7"],["G","dom7"]]')` → walking bass
2. `create_call_response("blues", "C", "1 3 5 3", "5 4 3 2", repeats=4)` → melody
3. `create_chord_progression("C", "major", ["maj7","min7","dom7","maj7"])` → comping
4. `apply_swing(0.62, "8th")` → jazz swing

### Drum & bass (BPM 170-180)
1. `create_genre_track("dnb")` → base track
2. `create_drum_fill(fill_type="roll", bars=2, density="dense")` → build-up
3. `create_riser(start_pitch=36, end_pitch=84, steps=32, curve="exp", length_beats=4)` → ascending pitch sweep before drop
4. `create_polyrhythm(3, 4, bars=2)` → cross-rhythm layer
5. `add_mastering_chain("loud")` → loud

### Ambient (BPM 60-80)
1. `create_genre_track("ambient")` → base track
2. `create_ostinato("major", "C", "1 3 5 3 1", repeats=16, step_duration=0.5)` → evolving pad
3. `automation_sweep("filter_cutoff", 0, 32, 200, 8000, steps=64)` → slow filter open
4. `create_crescendo(start_velocity=0.1, end_velocity=0.7, curve="exp")` → slow build

## Parameter guidelines

### Swing amounts
- 0.50 = light swing (pop)
- 0.55-0.66 = classic hip-hop/lofi
- 0.62 = jazz swing (8th grid)
- 0.75 = strong shuffle
- 1.00 = full triplet

### Sidechain depths
- 0.3 = subtle (techno, minimal)
- 0.5 = moderate (house, pop)
- 0.7 = pronounced (EDM, festival)
- 0.8+ = extreme (big room)

### Ghost note densities
- 0.15 = sparse (subtle groove)
- 0.30 = moderate (funk, hip-hop)
- 0.45 = busy (R&B, neo-soul)
- 0.60+ = chaotic (jazz fusion)

### Crescendo curves
- linear = steady build (classical)
- exp = slow start, fast end (tension release)
- log = fast start, slow end (impact fade)

### Velocity curve types (apply_velocity_curve)
- ramp_up = linear increase (build-up, snare roll)
- ramp_down = linear decrease (fade-out, decrescendo)
- arc = peak in middle (expressive phrase, rises then falls)
- trough = dip in middle (quiet middle, loud edges)
- power = exponential curve via `power` param (2.0 = sharp attack, 0.5 = slow swell)

### Articulation amounts (apply_articulation)
- staccato: 0.3 = very short (pizzicato), 0.5 = moderate, 0.7 = light detachment
- legato: 0.5 = half-fill, 0.9 = near-full, 0.95 = smooth connected
- accent: 0.3 = subtle, 0.5 = moderate, 0.8 = strong, 1.0 = maximum boost
- tenuto: amount unused — always fills to nearest 16th grid slot

### Scale run step durations
- 0.0625 = 32nd notes (fast run, fill)
- 0.125 = 16th triplet (smooth run)
- 0.25 = 16th notes (moderate run)
- 0.5 = 8th notes (slow walk)

## Common pitfalls

1. **Call before response**: `create_call_response` requires both patterns to produce notes. Pattern "0 0 0 0" (all rests) will error.
2. **Walking bass octave**: Default octave=2 (C2=36). Use octave=3 for higher bass, octave=1 for sub-bass.
3. **Polyrhythm requires different counts**: `create_polyrhythm(4, 4)` errors — that's not a polyrhythm.
4. **Ghost notes need existing notes**: `create_ghost_notes` uses nearest note's pitch. Empty region = default pitch 38 (snare).
5. **Sidechain doesn't create kick**: `apply_sidechain` only automates volume. You need a separate kick drum track.
6. **Swing before quantize**: If you quantize after swing, you undo the swing. Apply swing last.
7. **Scale degrees 1-7**: `parse_melody_pattern` uses scale degrees, not MIDI notes. "1" = root, "5" = fifth.
8. **Chord progression needs valid chords**: Use chord types from CHORD_INTERVALS: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug.
9. **Velocity curve vs humanize**: `apply_velocity_curve` is deterministic (mathematical curve), `humanize_notes` is random. Use curve for build-ups, humanize for natural feel. They can be combined: curve first, then light humanize.
10. **Articulation modifies existing notes**: `apply_articulation` doesn't create notes — it reshapes durations/velocities of notes already in the region. Create your pattern first, then articulate.
11. **Velocity curve normalizes by position**: The curve maps 0..1 across the note range in the region. If notes are unevenly spaced, the curve still maps linearly by position, not by time.

## Tool chain examples

### Full hip-hop beat
```python
# 1. Base track
await mcp_opendaw_create_genre_track("hiphop")

# 2. Add swing to hi-hats
await mcp_opendaw_apply_swing(unit_index=0, track_index=0, swing_amount=0.58)

# 3. Add ghost notes for groove
await mcp_opendaw_create_ghost_notes(unit_index=0, density=0.3, velocity=0.25, seed=42)

# 4. Humanize for natural feel
await mcp_opendaw_humanize_notes(velocity_amount=0.12, timing_amount=0.10, swing=0.0)

# 5. Sample flip — Dilla-style chop on melody track
await mcp_opendaw_create_chop(
    pitches="60,62,64,67,69,71,72,74",
    chop_mode="shuffle",
    segment_beats=0.375,
    velocity_variation=0.15,
    seed=1337,
    unit_index=1,  # melody/synth track
)

# 6. Mix preset
await mcp_opendaw_apply_mix_preset("lofi")
```

### Full house track
```python
# 1. Base track
await mcp_opendaw_create_genre_track("house")

# 2. Sidechain the bass/pad
await mcp_opendaw_apply_sidechain(unit_index=1, bars=16, depth=0.7, release=0.25)

# 3. Off-beat stabs — Cm7 on the "and" of each beat
await mcp_opendaw_create_stab(
    chords='[["C","min7"]]',
    rhythm="x-x-x-x-",
    unit_index=1,
    octave=4,
    velocity=0.85,
    stab_duration=0.5
)

# 4. Ostinato riff
await mcp_opendaw_create_ostinato("minor", "F", "1 5 3 5", repeats=16, octave=4)

# 5. Mastering
await mcp_opendaw_add_mastering_chain("loud")
```

### Expressive MIDI lead (build-up + articulation)
```python
# 1. Create synth track with notes
await mcp_opendaw_create_synth_track(name="Lead", synth_type="vaporisateur")
notes = [{"pitch": 60 + (i % 4) * 12, "start": i * 0.25, "duration": 0.25, "velocity": 0.5} for i in range(16)]
await mcp_opendaw_create_notes_batch(notes_json=notes, unit_index=0, track_index=0)

# 2. Apply velocity ramp-up (build-up from quiet to loud)
await mcp_opendaw_apply_velocity_curve(curve_type="ramp_up", start_velocity=0.2, end_velocity=1.0)

# 3. Apply staccato (crisp, detached feel)
await mcp_opendaw_apply_articulation(articulation="staccato", amount=0.4)

# 4. Light humanize for natural timing
await mcp_opendaw_humanize_notes(velocity_amount=0.05, timing_amount=0.08, swing=0.0)
```

### Funk groove (articulation + ghost notes + accent)
```python
# 1. Base drum pattern
await mcp_opendaw_create_drum_pattern("x..x..x.", unit_index=0)  # kick
await mcp_opendaw_create_drum_pattern("..x...x", unit_index=0)   # snare

# 2. Ghost notes for funk feel
await mcp_opendaw_create_ghost_notes(density=0.3, velocity=0.25, seed=42)

# 3. Accent the downbeats
await mcp_opendaw_apply_articulation(articulation="accent", amount=0.7)

# 4. Swing for groove
await mcp_opendaw_apply_swing(swing_amount=0.58, grid="16th")
```
