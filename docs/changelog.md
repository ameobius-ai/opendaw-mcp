# Changelog

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
