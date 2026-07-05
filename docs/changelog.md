# Changelog

## v1.45.0 (2026-07-05)

- **`create_turn` orchestration tool (297 MCP tools)** — circular ornament (gruppetto): main → upper → main → lower → main. Third of four essential baroque ornaments (trill ✅, mordent ✅, turn ✅, appoggiatura ❌). Upper/lower direction, adjustable interval. Mozart piano concertos, Beethoven sonatas, Bach partitas. One call replaces 5 manual note creations. Completes ornaments set: trill + mordent + turn
- **E2E verified**: upper turn (5 notes), lower turn, half-step, bad direction/interval/pitch/velocity/duration — 8/8 tests passed
- **+10 unit tests** for turn note order, timing, velocity, clamping (364 total)
- **Example script**: `create_turn.py` — upper + lower turn
- **297 MCP tools** (259 low-level + 40 orchestration + 3 melodic)
- ruff clean, CI green

## v1.44.0 (2026-07-05)

- **`create_mordent` orchestration tool (296 MCP tools)** — classical baroque ornament: main note → neighbor → main. One of the four essential ornaments (trill, mordent, turn, appoggiatura). Upper mordent flicks up, lower flicks down. Adjustable interval (1-7 semitones), timing split (40%/20%/40%). Bach two-part inventions, Mozart sonatas. One call replaces 3 manual note creations. Completes the ornaments set alongside create_trill
- **E2E verified**: upper mordent (3 notes), lower mordent, half-step, bad direction/interval/pitch/velocity, clamped neighbor — 8/8 tests passed
- **+10 unit tests** for mordent neighbor direction, timing split, velocity, clamping (354 total)
- **Example script**: `create_mordent.py` — upper + lower mordent
- **296 MCP tools** (258 low-level + 39 orchestration + 3 melodic)
- ruff clean, CI green

## v1.43.0 (2026-07-05)

- **`create_comping` orchestration tool (295 MCP tools)** — rhythmic chordal accompaniment: the most common accompaniment style in modern music. Play chords in a rhythmic pattern rather than sustained blocks. Jazz piano comping, funk guitar chops, reggae skanks, country boom-chick, neo-soul. Rhythm grid (x=play, -=rest, .=ghost), syncopation, chord JSON parsing, multi-chord progression. One call replaces 20-80 manual note creations. Unlike create_chord_progression (sustained blocks) or create_stab (house stabs), comping gives each chord a rhythmic identity
- **E2E verified**: jazz comping (64 notes, 4 chords), funk with ghosts, reggae skank 16 steps, syncopation, bad JSON/rhythm/velocity/chord type — 8/8 tests passed
- **+10 unit tests** for comping note generation, ghost velocity, rhythm parsing, syncopation (344 total)
- **Example script**: `create_comping.py` — jazz ii-V-I with syncopation
- **295 MCP tools** (257 low-level + 38 orchestration + 3 melodic)
- ruff clean, CI green

## v1.42.0 (2026-07-05)

- **`augment_notes` transformation tool (294 MCP tools)** — augmentation/diminution: the fourth classical motivic transformation. Multiplies note durations by a factor (0.25-4.0). Combined with transpose, reverse, and invert, completes the set of four fundamental transformations used by Bach, Beethoven, and every composition teacher. Two modes: "scale" (multiply both duration AND position — phrase slows down/speeds up) and "stretch" (multiply only duration, positions unchanged). Think Beethoven 5th: opening motif returns augmented (twice as slow) in recapitulation. Essential for: motivic development, fugue subjects, theme variations, rhythmic transformation
- **E2E verified**: augmentation x2 (5 notes), diminution x0.5 (8 notes), stretch mode, factor=1.0 no-op, bad factor/mode rejection, non-existent AU — 8/8 tests passed
- **+10 unit tests** for factor validation, duration math, mode logic (334 total)
- **Example script**: `augment_notes.py` — augmentation + diminution on C major scale
- **294 MCP tools** (256 low-level + 37 orchestration + 3 melodic)
- ruff clean, CI green

## v1.41.0 (2026-07-05)

- **`create_canon` orchestration tool (293 MCP tools)** — strict melodic imitation with delayed voice entries. The foundation of contrapuntal music: Pachelbel's Canon, "Row Row Row Your Boat", Bach fugue subjects, film score layering. Unlike create_counterpoint (generates a new line), a canon copies the SAME melody into each voice — just shifted in time and pitch. 2-6 voices, per-voice transposition, velocity decay, up/down entry order. One call replaces 16-48 manual note creations. Essential for: rounds, fugues, film scores, call-and-response layering, minimalism
- **+10 unit tests** for canon voice generation + transposition + direction + clamping (324 total)
- **293 MCP tools** (255 low-level + 35 orchestration + 3 melodic)

## v1.40.0 (2026-07-05)

- **`create_pedal_point` orchestration tool (292 MCP tools)** — sustained bass note under changing chords. The foundational technique in film scoring (Hans Zimmer drones), organ preludes (Bach), and rock ballads. Retrigger or sustained pedal mode. Full chord name parsing (maj/min/m7/maj7/dom7/sus2/sus4/dim/aug + implicit major). Adjustable time signatures (3/4, 4/4, 6/8). One call replaces 13-34 manual note creations. Essential for: film scoring, organ music, rock ballads, ambient drones, harmonic tension
- **+10 unit tests** for pedal point generation + chord parsing (314 total)
- **292 MCP tools** (254 low-level + 35 orchestration + 3 melodic)

## v1.35.0 (2026-07-05)

- **`create_bass_drop` orchestration tool (287 MCP tools)** — descending pitch sweep into sustained sub bass for dubstep/EDM/trap. Two phases: sweep (16th-note resolution pitch glide) + hold (sustained landing note). 3 curves (linear/exp/log), adjustable sweep (0.25-8 beats) and hold (0-16 beats). Complement to `create_riser` — riser builds up, bass drop lands. One call replaces 10-65 manual note creations. Essential for: dubstep drops, EDM build-and-drop, trap bass falls, impact transitions
- **E2E verified**: default drop (33 notes, 32 sweep + 1 hold), sweep-only (64 notes), short aggressive (9 notes), error handling
- **287 MCP tools** (254 low-level + 30 orchestration + 3 melodic)
- ruff clean, CI green

## v1.34.0 (2026-07-05)

- **`create_break` orchestration tool (286 MCP tools)** — classic drum break patterns for jungle/DnB/hip-hop/breakbeat. 6 presets: Amen Break, Think Break, Ashanti, Funky Drummer, When the Levee, Synthetic. 1-8 bars with variation modes (none/fill/humanize/drop) and swing. One call replaces 15-120 manual note creations. Essential for: breakbeat-based genres, sampling workflows, drum programming
- **E2E verified**: Amen (14 notes), Think 2-bar fill (26 notes), Funky Drummer humanized (22 notes), Amen 2-bar drop (25 notes), Synthetic with swing (14 notes), error handling
- **286 MCP tools** (254 low-level + 29 orchestration + 3 melodic)
- ruff clean, CI green

## v1.33.0 (2026-07-05)

- **`create_stab` orchestration tool (285 MCP tools)** — rhythmic chord stabs for house/disco/funk. Grid pattern with 'x' (stab), '-' (rest), '.' (ghost). Cycles through chord progressions. Adjustable octave, velocity, stab duration, pattern length. Ghost stabs use 45% velocity and shorter duration. One call replaces 20-60 manual note creations. Essential for: house off-beat stabs, funk syncopated punches, garage/shuffle patterns
- **E2E verified**: house Cm7 off-beat (16 notes, 4 stabs), funky F7/Cm7 with ghost notes (28 notes, 7 hits), all-rests error, invalid rhythm error
- **285 MCP tools** (254 low-level + 28 orchestration + 3 melodic)
- ruff clean, CI green

## v1.32.0 (2026-07-05)

- **`create_riser` orchestration tool (284 MCP tools)** — ascending pitch sweep for build-up transitions. 3 curves (linear, exp, log). Adjustable pitch range (MIDI 0-127), step count (8-128), length (0.25-16 beats). Velocity ramps up proportionally. One call replaces 10-50 manual note creations. Essential for: build-ups before drops, section transitions, tension creation
- **E2E verified**: 32 notes, pitch 36→84, exp curve ascending, linear curve 16 notes, error handling
- **284 MCP tools** (254 low-level + 27 orchestration + 3 melodic)
- ruff clean, CI green

## v1.31.0 (2026-07-05)

- **`werkstatt_stereowidth.js`** — M/S stereo width processor. 5 params: width (0=mono, 0.5=neutral, 1.5=wide), lowTrim (mono bass below crossover), lowFreq (50-500Hz crossover), mix, output. M/S encode → width scaling on side → low-freq trim → M/S decode. Essential for mastering: wide highs, mono bass
- **41 DSP scripts** (29 Werkstatt + 6 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, width 0.5→1.2, lowTrim 0→0.7

## v1.30.0 (2026-07-05)

- **`apparat_pluck.js`** — Karplus-Strong plucked string synth. 7 params: decay (string decay rate), damping (lowpass strength), brightness (noise burst spectral content), attack, release, detune, volume. Noise burst excites delay line, averaging filter creates natural string decay. Unique physical modeling sound unavailable in other Apparat scripts
- **40 DSP scripts** (28 Werkstatt + 6 Apparat + 6 Spielwerk)
- **E2E verified**: compiled via ScriptCompiler, 7 params, brightness 0.7→0.9, code header readback OK

## v1.29.0 (2026-07-05)

- **`werkstatt_transient.js`** — transient shaper with dual envelope followers. 4 params: attack (±12 dB transient boost/cut), sustain (±12 dB sustain boost/cut), mix, output. Fast envelope (~5ms) detects transients, slow envelope (~80ms) detects sustain, independent gain on each component. No threshold needed — works on any material. Essential for drum mixing
- **39 DSP scripts** (28 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 4 params, attack 0.5→0.8, sustain 0.5→0.3

## v1.28.0 (2026-07-05)

- **`werkstatt_deesser.js`** — dynamic de-esser, band-split architecture. 7 params: freq (2-12kHz crossover), threshold (-40..0 dB), ratio (1:1..10:1), attack, release, mix, output. 2nd-order Linkwitz-Riley HPF isolates sibilance, envelope-followed gain reduction on high band only. Completes vocal chain: EQ → compressor → de-esser → exciter → limiter
- **38 DSP scripts** (27 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 7 params, threshold 0.5→0.65, freq 0.4→0.8

## v1.27.0 (2026-07-05)

- **`werkstatt_exciter.js`** — harmonic exciter, band-split architecture. 5 params: freq (800Hz-12kHz crossover), harmonics, drive, mix, output. Cascaded one-pole HPF + cubic nonlinearity, parallel wet/dry. Completes mastering chain: EQ → compressor → exciter → limiter
- **37 DSP scripts** (26 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, freq 0.3→0.75, harmonics 0.5→0.85

## v1.26.0 (2026-07-05)

- **`werkstatt_limiter.js`** — brickwall limiter w/ lookahead + TPDF dither. 5 params: ceiling, release, lookahead, dither, mix. Instant attack, smooth release, circular buffer
- **`werkstatt_exciter.js`** — harmonic exciter, band-split architecture. 5 params: freq (800Hz-12kHz crossover), harmonics, drive, mix, output. Cascaded one-pole HPF + cubic nonlinearity, parallel wet/dry. Completes mastering chain: EQ → compressor → exciter → limiter
- **37 DSP scripts** (26 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, freq 0.3→0.75, harmonics 0.5→0.85

## v1.25.1 (2026-07-05)

- **+31 unit tests** for music_theory functions — parse_melody_pattern (11), scale_to_pitches (6), chord_to_pitches (8), GENRE_PRESETS (6)
- **272 unit tests** total (was 241), all passing
- ruff clean, CI green

## v1.25.0 (2026-07-05)

- **`werkstatt_paraeq.js`** — 3-band parametric EQ + HP/LP. 12 params: 3 × (freq, gain, Q) + hp_freq + lp_freq + mix. Biquad (RBJ cookbook), signal chain HP→B1→B2→B3→LP
- **35 DSP scripts** (24 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 12 params, band1_gain 0→6, band2_q 1→3.5

## v1.24.0 (2026-07-05)

- **`werkstatt_compressor.js`** — soft-knee peak compressor. 7 params: threshold, ratio, attack, release, makeup, mix, knee. Peak detection, one-pole envelope, stereo-linked
- **Integration test fix** — skips when Playwright chromium unavailable instead of failing
- **34 DSP scripts** (23 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 7 params, threshold/ratio set, code readback OK

## v1.23.3 (2026-07-05)

- **`werkstatt_multifilter.js`** — multi-mode SVF filter (LP/HP/BP/Notch). 5 params: mode, cutoff, resonance, drive, mix. Chamberlin topology
- **33 DSP scripts** (22 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, mode switching, resonance cranked

## v1.23.2 (2026-07-05)

- **`werkstatt_overdrive.js`** — asymmetric soft-clip overdrive. 5 params: drive, tone, level, bias, dry. Even harmonics for warmth, dry blend for parallel
- **32 DSP scripts** (21 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 5 params, set_param works

## v1.23.1 (2026-07-05)

- **`werkstatt_stereo_delay.js`** — stereo delay with ping-pong, feedback, tone filter. 6 params. Fills delay gap in DSP library
- **31 DSP scripts** (20 Werkstatt + 5 Apparat + 6 Spielwerk)
- **E2E verified**: compiled, 6 params, set_param works

## v1.23.0 (2026-07-05)

- **`apply_articulation`** — staccato/legato/tenuto/accent for existing notes. Duration reshaping for phrasing. Accent boosts velocity on downbeats
- **13 unit tests** — 228→241 total
- **E2E verified**: staccato (240→120), legato (240→228), accent (beats=0.9, off-beats=0.5)
- **55 examples** (added apply_articulation.py)
- **283 MCP tools**, **26 orchestration tools**

## v1.22.0 (2026-07-05)

- **`apply_velocity_curve`** — deterministic velocity envelope across notes (ramp_up/ramp_down/arc/trough/power). Unlike humanize (random), applies mathematical curve shape — build-ups, fade-ins, crescendo rolls, expressive phrasing. Power exponent for exponential curves
- **15 unit tests** — 213→228 total
- **E2E verified**: ramp_up (0.2→1.0, 16 notes), arc (peak=0.95), power=2.0 (slow rise)
- **54 examples** (added apply_velocity_curve.py)
- **282 MCP tools**, **25 orchestration tools**

## v1.21.0 (2026-07-05)

- **`apply_sidechain`** — new orchestration tool: sidechain ducking via volume automation. Classic pumping/breathing effect for house/techno/EDM. Adjustable depth, attack, release, kick interval
- **`create_ghost_notes`** — new orchestration tool: ghost notes (quiet grace notes) for funk/R&B/neo-soul/hip-hop drumming. Seeded reproducibility, avoids occupied positions
- **12 unit tests** for sidechain ducking curve and ghost note placement logic — 201→212 total
- **E2E test** for sidechain (272 events, 16 kicks, error handling) and ghost_notes (4 added, error handling)
- **53 examples** (added apply_sidechain.py, create_ghost_notes.py)
- **281 MCP tools**, **24 orchestration tools**, ruff clean, CI green

## v1.20.0 (2026-07-05)

- **`create_call_response`** — new orchestration tool: call-and-response patterns (antecedent/consequent phrases). Foundation of blues, jazz, hip-hop, electronic. Alternates call → response with adjustable repeats
- **`create_walking_bass`** — new orchestration tool: walking bass lines over chord progressions. Beat 1=chord root, beat 2=chord tone, beat 3=passing tone, beat 4=approach note. Jazz/blues/swing
- **11 unit tests** for call_response (interleave, timing, velocity) and walking_bass (beat positions, approach notes, bass range) — 190→201 total
- **E2E test** for call_response (blues ×4, 1 repeat, error handling) and walking_bass (ii-V-I, 2 bars/chord, error handling)
- **51 examples** (added create_call_response.py, create_walking_bass.py)
- **279 MCP tools**, **22 orchestration tools**, ruff clean, CI green

## v1.19.1 (2026-07-05)

- **`create_scale_run`** — new orchestration tool: ascending/descending scale sequences for fills and transitions. 14 scales, 1-4 octaves, adjustable step duration
- **8 unit tests** for scale run generation (ascending/descending, multi-octave, blues/chromatic/pentatonic) — 182→190 total
- **E2E test** for scale_run (C minor up 1 oct, A blues down 2 oct, error handling)
- **49 examples** (added create_scale_run.py)
- **277 MCP tools**, **20 orchestration tools**, ruff clean, CI green

## v1.19.0 (2026-07-05)

- **`apply_swing`** — new orchestration tool: pure swing feel for existing notes, deterministic, no randomness. 16th/8th grid, 0-1 depth. 0.58 = classic hip-hop/lofi swing
- **`create_polyrhythm`** — new orchestration tool: polyrhythms with two streams of different subdivision counts (3:4, 2:3, 5:7, 7:8). Jazz, electronic, progressive, math rock
- **12 unit tests** for swing offset logic and polyrhythm generation (170→182 total)
- **E2E test** for apply_swing (0.5/0.0/8th grid) and create_polyrhythm (3:4, 2:3, error handling)
- Bugfix: swing=0.0 no longer increments shift counter
- **276 MCP tools**, **19 orchestration tools**, ruff clean, CI green

## v1.18.1 (2026-07-05)

- **3 new Werkstatt DSP scripts**: `werkstatt_flanger.js` (stereo flanger with LFO delay + feedback), `werkstatt_noisegate.js` (noise gate with threshold/hold/release/range), `werkstatt_tremolo.js` (tremolo with sine→square shape)
- E2E verified: all 3 compile, params created, set_param works
- **30 DSP scripts** total (19 Werkstatt + 5 Apparat + 6 Spielwerk)

## v1.18.0 (2026-07-05)

- **`create_drum_fill`** — new orchestration tool: drum fills/transitions with 5 types (build, break, roll, crash, tom). Adjustable density and bar length. One call replaces 10-30 note creations.
- **`create_ostinato`** — new orchestration tool: repeating melodic/rhythmic pattern as foundation layer. Scale-based, 1-16 repeats. Common in minimalism, electronic, and film music.
- **`create_crescendo`** — new orchestration tool: apply crescendo/decrescendo to existing notes. Linear, exponential, or logarithmic velocity curves.
- **E2E verified**: drum_fill (build 7 notes, roll 45 notes), ostinato (C minor 1-5-3-5 ×4 = 16 notes), crescendo (exp 0.2→0.9, 23 notes modified)
- **17 orchestration tools** total, **274 MCP tools**, ruff clean, CI green

## v1.17.0 (2026-07-05)

- **`create_counterpoint`** — new orchestration tool: generate counter-melody in contrary motion. Mirrors melody around center pitch. Auto-creates target track.
- **`humanize_notes`** — new orchestration tool: velocity/timing/duration variation + swing. Seeded mulberry32 PRNG for reproducibility.
- **`create_harmony`** — new orchestration tool: generate harmony from existing notes. 8 intervals (diatonic thirds/fifths/sixths + chromatic). Up/down direction.
- **`reverse_notes`** — melodic variation: retrograde (reverse note order in region)
- **`invert_notes`** — melodic variation: mirror inversion around axis pitch (newPitch = 2*axis - oldPitch)
- **`suno-prompt-engineering` skill** — concentrated Suno prompt engineering guide from 20+ KB files
- **7 new examples**: create_melody, create_bassline, create_arpeggio, humanize_notes, create_harmony, create_counterpoint, reverse_invert_notes
- **TOOL_CATALOG**: all 27 DSP scripts documented (was 7)
- **KB index sync**: 31→33 entries (all files covered)
- **bridge.py**: `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` env var for system chromium
- **271 MCP tools**, **43 examples**, **9 skills**, ruff clean, CI green

## v1.16.1 (2026-07-05)

- **`create_melody`** — new orchestration tool: generate melodies from scale + rhythmic pattern using scale degrees (1-7). Supports 14 scales, rests (0), sustains (-), octave shifts (+). One call replaces 10-30 `create_note` calls.
- **`create_bassline`** — new orchestration tool: generate basslines from root + rhythmic pattern. Low octave default (C2=36), high velocity (0.9), octave up/down (+/_). One call replaces 8-20 `create_note` calls.
- **`create_arpeggio`** — new orchestration tool: generate arpeggios from chord name with 6 patterns (up/down/updown/downup/random/chord) and 6 rates (32/16/8/4/16t/32t). One call replaces 8-32 `create_note` calls.
- **`humanize_notes`** — new orchestration tool: add human-like velocity, timing, duration variation and swing to existing notes. Seeded mulberry32 PRNG for reproducibility. Makes programmed MIDI feel less robotic.
- **`create_harmony`** — new orchestration tool: generate harmony parts from existing notes. Diatonic (thirds/fifths/sixths) and chromatic (octave/fifth/fourth/major-minor third) intervals. Up/down direction. Auto-creates target track.
- **`create_counterpoint`** — new orchestration tool: generate counter-melody in contrary motion. Mirrors melody around center pitch. Adjustable interval. Auto-creates target track.
- **`reverse_notes`** — new melodic variation tool: reverse note order in a region (retrograde). Positions mirrored, durations/velocities preserved.
- **`invert_notes`** — new melodic variation tool: invert melody around a pitch axis (mirror reflection). newPitch = 2*axis - oldPitch.
- **`opendaw_mcp/music_theory.py`** — shared music theory module: `NOTE_TO_PITCH`, `CHORD_INTERVALS`, `SCALE_INTERVALS`, `GENRE_PRESETS`, `chord_to_pitches()`, `scale_to_pitches()`
- **DRY refactor**: `create_chord_progression` and `create_genre_track` now import from `music_theory` instead of duplicating dicts inline
- **2 new genres**: `coldwave` (110 BPM, dark bass) and `hiphop` (90 BPM, boom bap) — `create_genre_track` now supports 8 genres
- **14 scale types**: major, minor, harmonic minor, melodic minor, dorian, phrygian, lydian, mixolydian, locrian, pentatonic major/minor, blues, chromatic
- **38 new unit tests** (test_music_theory.py) — 150 total
- ruff clean, 271 MCP tools, no regressions

## v1.16.0 (2026-07-05)

- **Modular architecture** — infrastructure extracted from 13K-line `server.py` into `opendaw_mcp/` package:
  - `constants.py` — lookup tables (TIDAL_RATE_MAP, DELAY_SYNC_MAP, WAVESHAPER_FUNCS, REVAMP_SECTIONS)
  - `bridge.py` — `HeadlessDawBridge` class (Playwright bridge, DAW_HELPERS injection)
  - `utils.py` — pure-Python helpers (`_parse_wav`, `_compute_lufs`, `_ok`, `_err`, `_safe_filename`, `_safe_path`, `_clamp_script_param`)
  - `__init__.py` — public API, all symbols re-exported for backward compat
- **`OpendawServer` facade** — class providing `bridge` + all `mcp_opendaw_*` tools as methods. Framework wrappers (LangChain, AutoGen, CrewAI) now work via this single interface.
- **server.py: 13244 → 12955 lines** (infrastructure moved to package modules)
- **0 regressions** — 93 unit tests pass, ruff clean, all framework wrappers functional, 263 MCP tools intact

## v1.15.2 (2026-07-04)

- **CrewAI toolkit** — `opendaw_mcp/crewai_tools.py` wraps 27 tools for CrewAI. Custom `OpendawCrewAITool` class, category filtering, shared server instance.
- **GitHub Discussions seeded** — 5 discussions: release announcement, 3 FAQ (bridge, GPU, MCP clients), genre showcase
- **33 examples total** (added `crewai_integration.py`)

## v1.15.1 (2026-07-04)

- **AutoGen toolkit** — `opendaw_mcp/autogen_tools.py` wraps 27 tools for Microsoft AutoGen. Category filtering, shared server instance.
- **Framework integration docs page** — LangChain + AutoGen + MCP direct + Hermes, with comparison table
- **32 examples total** (added `autogen_integration.py`)

## v1.15.0 (2026-07-04)

- **LangChain toolkit** — `opendaw_mcp/langchain_tools.py` wraps 30+ tools as LangChain `StructuredTool` objects. Category filtering, auto bridge start. Use with any LangChain agent.
- **Docs site** — mkdocs-material at https://ameobius.github.io/opendaw-mcp/ — 21 pages, dark mode, search, auto-deploy via GitHub Actions
- **PR template** — structured checklist for contributors
- **PyPI metadata** — Documentation, Issues, Changelog URLs pointing to docs site
- **dev.to article** — "Controlling a DAW with AI Agents via MCP" (in `promotion/`)
- **32 examples total** (added `langchain_integration.py`, `autogen_integration.py`)

## v1.14.4 (2026-07-04)

- **Final 2 genre examples (E2E verified)**: `genre_lofi.py` (82 BPM, swung drums, jazzy ii-V-I, warm) and `genre_trap.py` (145 BPM, fast hi-hat rolls, gliding 808, dark minor). **All 8 genres from the skill now covered with E2E examples.** 30 examples total.

## v1.14.3 (2026-07-04)

- **3 more genre examples (E2E verified)**: `genre_hiphop.py` (85 BPM, boom bap, 808 Ab minor), `genre_dnb.py` (174 BPM, Amen break, reese+sub F minor), `genre_house.py` (124 BPM, 4-on-floor, off-beat chord stabs). 28 examples total, 6 genres covered.

## v1.14.2 (2026-07-04)

- **2 new genre examples (E2E verified)**: `genre_coldwave.py` (100 BPM, Am-Fmaj7-Cmaj-Gdom7, 4 tracks, Dattorro+Waveshaper) and `genre_ambient.py` (70 BPM, Cmaj7-Amin7-Fmaj7-Gmaj7, pad+bell+texture, long reverbs). 25 examples total.
- Fixed return key names in genre examples (`notes_created` / `total_notes` / `lanes`)

## v1.14.1 (2026-07-04)

- **`opendaw-genres` skill** — 8 genre templates with concrete parameters: techno, coldwave, hip-hop, ambient, DnB, house, lofi, trap. BPM, track layout, drum patterns, bass lines, chord progressions, effect chains, pan, LUFS targets. 8 skills total.

## v1.14.0 (2026-07-04)

- **2 new agent skills**: `suno-to-opendaw` (6-stage Suno→stems→openDAW→mix→master→export pipeline) and `dsp-script-authoring` (custom Werkstatt/Apparat/Spielwerk DSP script writing guide). 7 skills total.
- `set_marker_repeat` MCP tool — marker repeat count control (0=infinite)
- **263 MCP tools** (254 low-level + 8 orchestration)

## v1.13.0 (2026-07-04)

- **Preset Management**: 2 new MCP tools for openDAW preset format (.opb). `save_effect_preset` encodes any audio effect chain into a shareable .opb bundle. `load_effect_preset` decodes .opb and applies it to a project.
- 5 Werkstatt presets published to upstream (PR #284): Dark Saturation, Plate Reverb, Cold Fold Distortion, Stereo Phaser, Stereo Chorus.

## v1.12.1 (2026-07-04)

- **Stem Splitter**: 2 new MCP tools for SOTA open-source source separation. `split_stems` runs 7 modes locally on GPU (ensemble, scnet, bs6, polarformer, dereverb, drumsep, denoise). Optional auto-import into DAW.

## v1.12.0 (2026-07-04)

- **Agent Skills**: 8 structured skill files in `skills/` directory — adaptive mix→master, suno-to-opendaw, dsp-script-authoring, opendaw-genres, opendaw-automation, track architecture, sound design, effect routing. Decision points for genre-adaptive workflows. Agent-agnostic.
- **26 DSP scripts total** (15 Werkstatt + 5 Apparat + 6 Spielwerk)

## v1.11.9 (2026-07-04)

- **CodeRabbit fixes**: reverb stereo width (separate L/R comb banks, M/S width on reverb tail), paulstretch cursor split (independent read/write cursors, proper frame emission gating)

## v1.11.8 (2026-07-04)

- **New Werkstatt script**: ring modulator with envelope-followed frequency modulation — workaround for MIDI input limitation in Werkstatt audio effects

## v1.11.7 (2026-07-04)

- **Suno→openDAW pipeline example**: import AI-generated track, add mastering chain (tape sat + lookahead comp), reverb send bus, MIDI arp layer, render + stems + LUFS

## v1.11.6 (2026-07-04)

- **4 new Spielwerk MIDI effect scripts**: chord memory, strummer, velocity scaler, MIDI delay
- **1 new Python example**: Suno→openDAW pipeline

## v1.11.5 (2026-07-04)

- **7 new DSP scripts**: DC remover + stereo width, allpass filter, 2-operator FM synth, chord memory, strummer, velocity scaler, MIDI delay
- **Coldfold fix**: removed unused `range` variable (CodeRabbit review)

## v1.11.4 (2026-07-04)

- **1 new Apparat script**: ring modulator synth with ADSR and sub-oscillator

## v1.11.3 (2026-07-04)

- **1 new Werkstatt script**: real-time pitch shifter via delay-line sweep
- **Ruff lint fixes**: removed unused imports/variables

## v1.11.2 (2026-07-04)

- **10 DSP bug fixes** synced from upstream PR #283 CodeRabbit review: darksat DC blocker, chorus delay buffer, coldfold slew scaling, lookahead gain reduction, reverb comb filter indices, shimmer per-channel pitch shifter, phaser stable allpass topology, subcrusher bidirectional glide, arpeggiator block boundaries
- **2 new Werkstatt scripts**: ADSR trim + granular time-stretch

## v1.11.1 (2026-07-04)

- **Scriptable device mapping info** — `list_script_params` now returns full `@param` mapping metadata (min, max, mapping type, unit)
- **Range validation** — `set_script_param` validates values against `@param` declarations: bool snaps, int rounds+clamps, linear/exp clamps
- **+15 unit tests** (93 total) — TestScriptParamClamping
- **+6 integration E2E tests** — bridge startup, globals, track ops, scriptable compile, param clamping, latency benchmark (avg 4ms round-trip)
- **5 new Werkstatt DSP scripts** — reverb, chorus, phaser, lookahead compressor, shimmer delay

## v1.11.0 (2026-07-04)

- **`apply_mix_preset`** — 8th orchestration tool: batch volume/pan/mute/solo across all tracks. Named presets (lofi, house, balanced, wide) or custom JSON

## v1.10.0–v1.10.2 (2026-07-04)

- **7 orchestration tools** — high-level composers for agents: `create_notes_batch`, `create_drum_pattern`, `create_chord_progression`, `add_mastering_chain`, `create_genre_track`, `create_song_structure`, `automation_sweep`
- **Official ScriptCompiler migration** — `set_script_device_code` now uses the real ScriptCompiler from `@opendaw/studio-adapters`
- **Stems export fix** — `useInstrumentOutput` changed from True→False. Stems now route through channel strip
- **`export_dry_stem`** — new tool for freeze/flatten/re-amp workflows
- **Device-specific parameter tools** — Waveshaper equations, Crusher bits/crush, Revamp EQ sections, Tidal LFO rate, Delay sync
- **+23 new unit tests** (54 total)

## v1.9.x (2026-07-03)

- **DRY refactoring: 17 DAW_HELPERS** — ~295 replacements, 0 raw enumeration patterns
- **CLI commands** — `--version`, `--list-tools`, `--help`
- **93 unit tests** — pytest covering helpers, WAV parsing, LUFS computation
- **Security hardening** — path traversal fixes, case-sensitive extension stripping
- **PEP 561** — `py.typed` marker for type checker support
- **Social preview banner** — custom OpenGraph image

---

For the full changelog including v1.0–v1.8, see the [GitHub releases page](https://github.com/ameobius/opendaw-mcp/releases).
