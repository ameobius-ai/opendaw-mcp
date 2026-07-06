---
name: opendaw-composition-patterns
description: "When and how to use openDAW MCP orchestration tools for musical composition. 509 MCP tools: drum patterns, fills, melodies, basslines, arpeggios, harmony, counterpoint, ostinato, crescendo, swing, polyrhythm, scale runs, call-response, walking bass, sidechain, ghost notes, velocity curves, articulation, chord progressions, genre templates, song structure, automation, mastering chains, mix presets, humanize, pitch-based dynamics, cross-track balance, MIDI echo, scale detection, riffs, hooks, licks, turnarounds, solos, etudes, world rhythms, DSP chains, stem splitting, offline render. Decision tree: which tool for which musical goal. v1.336.0"
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
├── Stutter edit (evolving repetition) → create_stutter (accelerate/decelerate/ping_pong/random, accent patterns, velocity ramps, gate, pitch jitter)
├── Phase shifting (Reich) → create_phase (2-4 voices, forward/backward/diverge drift, phase_rate, phase_amount reset, per-voice velocity decay)
├── Trill (ornament) → create_trill (two-note alternation, 32nd/16th/8th/triplet rates, baroque accent)
├── Mordent (ornament) → create_mordent (main→neighbor→main, upper/lower, Bach/Mozart)
├── Turn (ornament) → create_turn (main→up→main→down→main, gruppetto, Mozart/Beethoven/Bach)
├── Appoggiatura (ornament) → create_appoggiatura (approach→main, tension→release, Bach/Mozart/Chopin)
│   └── **Ornaments set complete: trill + mordent + turn + appoggiatura**
├── Glissando (scale run) → create_glissando (chromatic/diatonic/pentatonic, any direction, velocity curves)
├── Sequence (transposed repeat) → create_sequence (up/down/alternating, baroque/jazz/film score builds)
├── Pedal point (sustained bass) → create_pedal_point (bass drone under changing chords, film/organ/rock)
├── Chorale (SATB voice leading) → create_chorale (4-voice harmony with parallel fifth detection, Bach/vocal/strings)
├── Fugue (subject + answer + countersubject) → create_fugue (tonal/real answer, stretto, 2-5 voices, Bach WTC)
├── Bordun (drone chord) → create_bordun (sustained chord layer, open fifths/octaves, bagpipes/tanpura/ambient)
├── Canon (imitation) → create_canon (same melody in 2-6 voices with delayed entry + transposition, Pachelbel/rounds/fugues)
├── Comping (rhythmic chords) → create_comping (chord progression × rhythm grid, jazz/funk/reggae/country/neo-soul)
├── Hocket (interlock) → create_hocket (melody split between 2-4 voices, alternate/pairs/phrase, medieval/African/gamelan)
├── Isorhythm (talea×color) → create_isorhythm (independent rhythm×pitch cycles, phase shift at LCM, Machaut/Messiaen)
├── Hemiola (cross-rhythm) → create_hemiola (3:2 rhythmic displacement, Afro-Cuban/jazz/minimalism)
├── Passacaglia (bass ostinato + harmonies) → create_passacaglia (repeating bass + block/arpeggiated/melodic variations, Bach/film/metal)
├── Ground bass (basso ostinato) → create_ground_bass (repeating bass + developing melody, 5 styles: baroque/modal/minimalist/film_tension/folk)
├── Chaconne (bass + chords + variations) → create_chaconne (repeating bass AND chord progression + variation melody, 5 styles: baroque/romantic/jazz/minimalist/contemporary)
├── Soli (ensemble unison) → create_soli (all voices same melody in rhythmic unison, 2-5 voices, octave doublings, 14 scales, jazz big band/orchestral tutti/rock riffs)
├── Rondo (ABACA form) → create_rondo (recurring theme + contrasting episodes, 5 forms: simple ABA / classical ABACA / seven_part ABACABA / pop_rock ABABCB / jazz ABAC, Mozart/Beethoven/pop/jazz)
├── Call-and-response → create_call_and_response (leader phrase + response, 5 types: echo/transpose/variation/complementary/fill, blues/gospel/African/jazz/hip-hop)
├── Binary form (AB) → create_binary_form (two contrasting sections, optional AABB repeats, 5 modulation types: dominant/relative/subdominant/parallel/no_modulation, Bach/folk/early jazz)
├── Sonata form → create_sonata_form (exposition: theme 1 tonic + transition + theme 2 dominant/relative; development: fragmentation + sequence + modulation + dominant pedal; recapitulation: both themes in tonic; Haydn-Mozart-Beethoven classical structure)
├── Ternary form (ABA) → create_ternary_form (A-B-A' with contrasting middle, 5 B contrast types: trio/dominant/relative/episode/development, optional A' ornamentation, minuet & trio / da capo aria / Chopin nocturne / pop ABA)
├── Ghost notes (groove) → create_ghost_notes (after creating main pattern)
├── Swing (groove) → apply_swing (after creating pattern, 0.58 = hip-hop)
├── Groove transfer (feel cloning) → groove_transfer (source drum groove → destination programmed track, timing + velocity feel)
├── Time warp (half-time/double-time) → time_warp_notes (0.5× spread = half-time, 2.0× compress = double-time, moves both position + duration)
├── Force scale (harmonic snap) → force_scale_notes (out-of-scale notes → nearest in-scale pitch, 13 scales, nearest/up/down)
├── Identify chords (analysis) → identify_chords (read notes, group by overlap, match pitch-class sets → chord names with positions)
├── Diatonic transpose (scale steps) → diatonic_transpose_notes (up/down by N steps within scale, preserves key, skips out-of-scale)
│
├── Melody → create_melody (scale-based, pattern notation 1-7)
├── Riff (song identity) → create_riff (5 styles: rock/funk/metal/blues/hip_hop, power chords, gallop, shuffle)
├── Hook (earworm) → create_hook (5 styles: pop/rock/dance/rnb/country, singable, climax leap)
├── Lick (vocabulary) → create_lick (5 styles: bebop/blues/funk/rock/jazz_minor, enclosures, blue notes)
├── Turnaround (resolution) → create_turnaround (5 styles: jazz/blues/gospel/rock/pop, I-vi-ii-V, axis)
├── Solo (melodic) → create_solo (5 styles: bebop/blues/rock/jazz_swing/fusion, chromatic approaches)
├── Drum solo → create_drum_solo (5 styles: rock/jazz/funk/latin/marching, rudimental vocabulary)
├── Etude (technical study) → create_etude (5 types: scale/arpeggio/interval/rhythm/chromatic, Czerny/Chopin)
├── Bassline (static) → create_bassline (root-fifth, octave, walk-up)
├── Bassline (walking jazz) → create_walking_bass (chord progression input)
├── Arpeggio → create_arpeggio (up/down/updown/random, octaves)
├── Ostinato (repeating) → create_ostinato (short pattern × N repeats)
│
├── Chords → create_chord_progression (2-5 chords, scale-aware)
├── Chord inversion → invert_chord_notes (1st-6th inversion, drop voicing)
├── Harmony (parallel) → create_harmony (thirds/fifths/sixths above melody)
├── Doubling → double_melody (octave/fifth/fourth/third/sixth, diatonic or chromatic, same-region or cross-track)
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
├── Pitch humanize → humanize_pitch (micro-detune cents, intonation drift)
├── Reverse → reverse_notes (mirror note order)
├── Invert → invert_notes (mirror pitches around axis)
├── Transpose → transpose_notes (shift all pitches by N semitones)
├── Quantize → quantize_notes (snap to grid, adjustable strength)
├── Velocity accent → accent_beats (beat-aware: 4/4, backbeat, 3/4, 6/8, off_beat, four_on_floor)
├── Note filter → filter_notes (pitch/velocity/time range, list/delete/keep)
├── Region split → split_note_region (divide at beat point)
├── Region merge → merge_note_regions (join two into one)
├── Note stats → note_stats (pitch/velocity/duration/density/histogram)
├── Melody analysis → analyze_melody (contour, intervals, climax, step/leap)
├── Scale detection → detect_scale_from_notes (15 scales, Pearson correlation)
├── Chord identification → identify_chords (reverse-engineer harmony)
├── Harmonic rhythm → analyze_harmonic_rhythm (chord change rate, stable/active sections)
├── Rhythm analysis → extract_rhythm (onset grid, syncopation, swing, IOI)
├── Rhythm apply → apply_rhythm_pattern (stamp pattern onto notes, inverse of extract)
├── Pitch-based dynamics → map_velocity_by_pitch (higher_quieter/lower_quieter/bell_curve)
├── Velocity quantize → quantize_velocities (MPC 16-level, stepped dynamics, 2-128 levels)
├── Velocity LFO → apply_velocity_lfo (sine/triangle/saw/square/random, cyclic pumping)
├── Cross-track balance → balance_track_velocities (5 presets, MIDI mix leveling)
├── MIDI echo → create_midi_echo (decaying repeats, pitch shift, 4 feedback modes)
├── Ratchet → create_ratchet (accelerando/decelerando repeat, Bach cadences, build-ups)
├── Repeat → repeat_notes (repeat existing notes N times with transpose/velocity/gap, sequences, motivic development)
├── Subdivide → subdivide_notes (split each note into N parts, diminution, fragmentation, pitch/velocity patterns)
├── Merge → merge_consecutive_notes (combine same-pitch consecutive notes into sustained, cleanup)
├── Rotate → rotate_notes (cyclic permutation, 3 axes: position/pitch/both, serialism, jazz rotation)
├── RandDur → randomize_note_durations (generative duration variation, 5 distributions, seeded PRNG)
├── Expand → expand_intervals (widen/compress melodic intervals, 3 anchors, scale snapping, motivic development)
├── Rests → insert_rests (positional rest insertion, 3 modes: delete/truncate/shorten, syncopation/space)
├── Shuffle → shuffle_notes (random permutation, 4 modes: pitches/rhythm/full/within_groups, seeded, generative variation)
├── Merge → merge_note_tracks (combine two tracks into one, 6 overlap strategies, transpose, delete_source)
├── Contour → apply_contour (reshapes melody direction: ascending/descending/arch/inverted_arch/wave/escalating, scale snapping)
├── Explode → explode_chords (chord track → individual voice tracks, 3 directions, 4 velocity modes, 2-8 voices, orchestration)
├── PassTones → add_passing_tones (diatonic passing tones between notes, 12 scales, 4 directions, counterpoint smoothing)
├── Suspension → add_suspension (preparation→suspension→resolution on strong beats, 10 scales, 3 resolution modes, Bach/jazz)
├── Neighbor → add_neighbor_tones (upper/lower neighbor embellishment, 12 scales, 3 directions, note splitting, Bach/jazz ornaments)
├── Anticipation → add_anticipation (notes before strong beats, forward rhythmic motion, 12 scales, 4 directions, jazz/pop/salsa/funk)
├── Sequence → repeat_phrase (repeat phrase N times with transposition, diatonic/chromatic, 5 velocity patterns, time_stretch)
├── Clone → clone_track (full track duplication, transpose/velocity_scale/time_offset, new_unit option)
├── Polyrhythm → create_melodic_polyrhythm (N notes across M beats, 3:4/5:4/7:4, scale-based or custom, 4 velocity patterns)
├── Phasing → create_phase_shift (Steve Reich phasing, gradual cumulative drift per bar, forward/backward, 2-16 bars)
├── Metric Modulation → create_metric_modulation (note-value equivalence tempo change, 12 note values, direct ratio "N:M", optional time signature)
├── Additive Rhythm → create_additive_rhythm (unequal groupings within a bar, "3+2+2" etc., 4 note values, 5 pitch modes, group_start/group_end accents, velocity decay)
├── Modal Transformation → shift_mode (shift notes from one scale/mode to another preserving tonic, 14 scales, only changed degrees move)
├── Microtonal Control → set_note_cents (deterministic cent offsets, 7 targeting modes: all/pitch/beats/indices/alternating/gradient/scale_degree, -100 to +100 cents)
├── Stochastic Melody → create_random_walk_melody (random walk through scale, stepwise dependency, max_step/direction_bias/boundary behavior, seeded PRNG, Eno/Xenakis generative)
├── Markov Melody → create_markov_melody (Markov chain interval transitions, order 1/2, custom weights, regression to mean, stylistic memory)
├── L-system Melody → create_l_system_melody (deterministic rewriting system, 5 presets: fibonacci/cantor/dragon/koch/sierpinski, fractal self-similar structure, custom rules)
├── Montuno → create_montuno (Latin/jazz piano ostinato, 2-3/3-2 clave + guajira + charanga patterns, syncopated chord stabs + melodic passages, I-vi-IV-V auto or custom chords)
├── Voice Exchange → create_voice_exchange (imitative counterpoint, 6 modes: imitation/inversion/retrograde/retrograde-inversion/augmentation/diminution, optional swap for voice crossing)
├── Bariolage → create_bariolage (Baroque string crossing, pedal pitch + moving notes alternation, 5 patterns, 3 subdivisions, two-voice illusion)
├── Tuplet Group → create_tuplet_group (irrational rhythm subdivision, triplets/quintuplets/septuplets up to 16, 5 pitch modes, rest positions, accent first)
├── Cadenza → create_cadenza (unmeasured virtuosic solo, 6 segment types: flourish/leap/trill/fermata/cascade/climb, 4 styles, rubato rhythm, breath marks)
├── Fugato → create_fugato (fugal passage, subject + answer + countersubject + episode, 2-4 voices, real/tonal answer, custom or auto subject)
├── Colotomic → create_colotomic (gamelan gong layers, 4 structures: slendro/pelog/lancaran/ketawang, 3 densities, hierarchical cyclic grid, non-European tradition)
├── Tala → create_tala (Indian cyclic rhythm, 6 talas: teental/ektal/jhaptal/rupak/dadra/kehartwa, vibhag sections, tali/khali, tabla bols, 3 laya tempos, non-European tradition)
├── Songo → create_songo_pattern (Cuban drum-kit fusion, 4 variations: classic/modern/fusion/songo_funk, 4 voices: kick/snare/hh/tom, Los Van Van style)
├── Samba → create_samba_pattern (Brazilian bateria ensemble, 5 instruments: surdo/caixa/tamborim/chocalho/repique, 4 styles: batucada/samba_enredo/pagode/samba_funk)
├── Djembe Ensemble → create_djembe_ensemble (West African, 6 instruments: kenkeni/sangban/dundunba/bell/djembe2/djembe1, 4 rhythms: danza/kuku/djole/doundounba, cyclical ostinato + call-response)
├── Arabic Percussion → create_arabic_percussion (Middle Eastern, 3 instruments: darbuka/daf/zills, 6 rhythms: maqsum/baladi/saidi/ayoub/malfouf/chiftetelli, dum/tek/ka strokes)
├── Flamenco Compás → create_flamenco_compas (Andalusian, 4 instruments: palmas secas/sordas/cajón/golpe, 6 palos: bulerias/solea/alegrias/siguiriyas/tangos/rumba, 12-beat cyclical)
├── Balkan Meter → create_balkan_meter (additive meters 7/8/9/8/11/16/13/8, unequal groupings 2+2+3 etc, 6 meters + reversed, 3 variations: classic/modern/wedding)
├── Irish Trad → create_irish_trad (bodhrán+feet, 6 tune types: reel/jig/hornpipe/slip_jig/polka/slide, hornpipe swung, Ireland/Celtic)
├── Taiko Ensemble → create_taiko_ensemble (Japanese kumi-daiko, 4 instruments: odaiko/chu-daiko/shime/atarigane, 5 styles: miyake/yatai/edo/hachijo/omega, dramatic dynamics)
├── Korean Percussion → create_korean_percussion (nongak/samul nori, 5 instruments: janggu chwe+kyong/buk/kkwaenggwari/jing, 5 styles: nongak/samul_nori/binari/utdari_pungnyu/yeongnam_folk)
├── Second Line → create_second_line (New Orleans street parade, 5 instruments: bass/snare/hi-hat/tom/cymbal, 5 styles: traditional/brass_band/mardi_gras_indian/jazz_funeral/bounce)
├── Reggae percussion → create_reggae_percussion (Jamaican drum patterns, 6 styles: one_drop/rockers/steppers/ska/rocksteady/dancehall, GM percussion, swing)
├── Konokol (solkattu) → create_konokol (Indian Carnatic vocal percussion, 6 talas: adi_tala/roopaka/khanda_chapu/mishra_chapu/triputa/jhampa, syllable→pitch mapping)
│
├── Multi-track genre arrangement → create_XXX_arrangement (32 genres)
│   ├── dnb/liquid_dnb/neurofunk/house/trap/techno/dubstep (3-4 tracks: drums+bass+pad+stabs)
│   ├── synthwave/trance/disco/afrobeat/rock/jazz/pop/funk/reggae (4 tracks)
│   └── soul/rnb/blues/country/metal/gospel/edm/hardstyle/garage/acid/psytrance/breakbeat/downtempo/ambient (4-5 tracks)
│
├── Genre-aware mix → apply_genre_mix (14 genres: comp/EQ/sat/reverb/sidechain)
├── Genre-aware humanize → apply_genre_humanization (14 genres: jazz=loose, techno=tight)
├── Song structure (DJ) → create_genre_sections (8 electronic: intro→buildup→drop→breakdown→outro)
├── Section variation → create_arrangement_variation (14 genres: drum density/bass octave/melody transform)
├── Full song builder → create_song_with_variations (14 genres: 12 presets, one call)
├── Chord pads (string) → create_chord_pads ("Am-F-C-G", 10 chord types)
├── Arpeggiated progression → create_arpeggiated_progression ("Am-F-C-G", 5 arp patterns)
├── Bass from progression → create_bass_from_progression ("Am-F-C-G", 6 bass patterns)
├── Melody from progression → create_melody_from_progression ("Am-F-C-G", 5 melody patterns)
├── Harmonic arrangement → create_harmonic_arrangement ("Am-F-C-G", all 5 layers in one call)
├── Counter-melody → create_counter_melody_from_progression ("Am-F-C-G", 5 contrapuntal patterns)
├── Modulation → modulate_progression ("Am-F-C-G", target_key="C") — key change for bridge/chorus
├── Modulated song → create_modulated_song (multi-section: verse→chorus→bridge→outro with key changes)
├── Full pipeline → create_full_genre_pipeline (15 genres, optional harmonic layers via progression param)
└── Render entire song → render_full_song (auto-detect length, export WAV)
```

## Full production pipeline

```
0. ANALYSIS (optional, understand existing MIDI)
   ├── Note stats?         → note_stats (pitch/velocity/density/histogram)
   ├── Melody contour?     → analyze_melody (shape, climax, step/leap)
   ├── Scale/key?          → detect_scale_from_notes (15 scales, MIDI-based)
   ├── Chords?             → identify_chords (reverse-engineer harmony)
   ├── Harmonic rhythm?    → analyze_harmonic_rhythm (chord change rate, sections)
   ├── Rhythm pattern?     → extract_rhythm (onset grid, syncopation, swing)
   ├── Apply rhythm?       → apply_rhythm_pattern (stamp groove onto notes)
   ├── Pitch dynamics?     → map_velocity_by_pitch (natural velocity by register)
   ├── Balance tracks?     → balance_track_velocities (5 mix presets)
   ├── MIDI echo?          → create_midi_echo (decaying repeats, pitch shift)
   └── Chord identification? → identify_chords (reverse-engineer harmony)

1. CREATE
   ├── Loop-based?          → create_XXX_arrangement (14 genres)
   ├── Song structure?      → create_genre_sections (8 electronic)
   ├── Varied sections?     → create_arrangement_variation (14 genres)
   ├── Full song w/ vars?   → create_song_with_variations (12 presets, one call)
   └── One-call?            → create_full_genre_pipeline (all steps)

1b. EDIT (refine created content)
   ├── Split regions?      → split_note_region (divide at bar boundaries)
   ├── Merge regions?      → merge_note_regions (consolidate sections)
   ├── Filter notes?       → filter_notes (cleanup pitch/velocity/time)
   └── Accent dynamics?    → accent_beats (beat-aware velocity)

2. HARMONY (optional, adds chord movement)
   ├── Sustained pads?      → create_chord_pads ("Am-F-C-G", bars_per_chord=4)
   ├── Arp movement?        → create_arpeggiated_progression ("Am-F-C-G", pattern="up")
   └── Bass from chords?    → create_bass_from_progression ("Am-F-C-G", pattern="walking")

3. MIX
   └── apply_genre_mix (14 genres: per-track comp/EQ/sat/reverb/sidechain)

4. HUMANIZE
   └── apply_genre_humanization (14 genres: timing/velocity/swing per genre)

5. MASTER
   └── add_mastering_chain (LUFS: -14 Spotify, -10 loud, -16 Apple)

6. RENDER
   └── render_full_song (auto-detect length + tail, export WAV)
```

### Harmonic trio — same progression string

All three take "Am-F-C-G":
- **create_chord_pads** → sustained harmony (track 2)
- **create_arpeggiated_progression** → melodic movement (track 3, 5 patterns: up/down/updown/random/bass)
- **create_bass_from_progression** → bass foundation (track 1, 6 patterns: root/root_fifth/walking/pedal/octave/root_octave)
- **create_melody_from_progression** → lead melody (track 3, 5 patterns: chord_tones/sustained/syncopated/triadic/stepwise)

### Quick recipes

**Minimal (2 calls):**
```python
await mcp_opendaw_create_song_with_variations("dnb")
await mcp_opendaw_render_full_song(filename="my_dnb_track")
```

**Full production (4 calls):**
```python
await mcp_opendaw_create_song_with_variations("house", apply_mix=True, apply_humanize=True, apply_master=True)
await mcp_opendaw_create_chord_pads("Cm-Gm-Ab-Bb", bars_per_chord=4, track_index=2)
await mcp_opendaw_render_full_song(filename="house_with_chords")
```

**Harmonic trio (5 calls):**
```python
await mcp_opendaw_create_song_with_variations("synthwave")
await mcp_opendaw_create_chord_pads("Am-F-C-G", bars_per_chord=4, track_index=2)
await mcp_opendaw_create_arpeggiated_progression("Am-F-C-G", pattern="up", octave=4, step_duration=0.25, track_index=3)
await mcp_opendaw_create_bass_from_progression("Am-F-C-G", pattern="root", octave=2, track_index=1)
await mcp_opendaw_render_full_song(filename="synthwave_harmonic")
```

**Jazz walking bass (3 calls):**
```python
await mcp_opendaw_create_chord_pads("Dm7-G7-Cmaj7-Am7", bars_per_chord=2, octave=3, track_index=2)
await mcp_opendaw_create_bass_from_progression("Dm7-G7-Cmaj7-Am7", pattern="walking", octave=2, track_index=1)
await mcp_opendaw_render_full_song(filename="jazz_walking")
```

**Custom sections (6 calls):**
```python
await mcp_opendaw_create_arrangement_variation("dnb", section_name="intro", bars=4, velocity=0.5, drum_density=0.3, include_bass=False)
await mcp_opendaw_create_arrangement_variation("dnb", section_name="verse", bars=8, velocity=0.8, start_beat=16)
await mcp_opendaw_create_arrangement_variation("dnb", section_name="chorus", bars=8, velocity=1.0, start_beat=48, drum_density=1.5, bass_octave_shift=1)
await mcp_opendaw_create_arrangement_variation("dnb", section_name="bridge", bars=4, velocity=0.6, start_beat=80, melody_transform="invert")
await mcp_opendaw_create_arrangement_variation("dnb", section_name="outro", bars=8, velocity=0.4, start_beat=96, drum_density=0.5, include_melody=False)
await mcp_opendaw_render_full_song(filename="custom_dnb")
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
