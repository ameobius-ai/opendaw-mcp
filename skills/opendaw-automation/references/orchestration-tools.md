# Orchestration Tools — High-Level Composers for Agent-Native DAW Control

## Design Rationale

250 low-level MCP tools give agents full DAW control, but building a complete track requires 30-50 individual calls (create_synth → create_note × 20 → add_effect × 3 → set_param × 10 → create_send → render). This is token-heavy, slow, and agents lose context in the sequence.

Orchestration tools solve this by combining multiple low-level operations into a single call. They are **composers**, not replacements — each one calls the same underlying DAW APIs but batches the work into one `editing.modify()` block and one bridge round-trip.

## Tools Added (v1.10.0, 255 total → v1.32.0, 284 total)

52 orchestration tools total. First 7 documented below with full implementation details. Later tools follow the same patterns. See `skills/opendaw-composition-patterns/SKILL.md` for agent-facing decision tree and recipes.

### Full orchestration tool list (v1.70.0)
1. `create_notes_batch` — batch note creation from JSON
2. `create_drum_pattern` — step-sequencer drum notation
3. `create_chord_progression` — scale-aware chord sequences
4. `add_mastering_chain` — EQ+Comp+Maximizer on output bus
5. `create_genre_track` — full genre starting point
6. `create_song_structure` — arrangement markers
7. `automation_sweep` — smooth parameter ramps
8. `create_melody` — scale-based melodic phrases
9. `create_bassline` — root-fifth/octave/walk-up bass
10. `create_arpeggio` — up/down/updown/random arps
11. `create_harmony` — parallel harmony (thirds/fifths/sixths)
12. `create_counterpoint` — contrary motion counter-melody
13. `humanize_notes` — random velocity/timing/duration/swing
14. `create_arp_pattern` — arpeggio pattern sequencer
15. `create_drum_fill` — build/break/roll/crash/tom fills
16. `create_ostinato` — repeating pattern × N
17. `create_crescendo` — velocity ramp via automation (linear/exp/log)
18. `apply_swing` — deterministic swing (16th/8th grid)
19. `create_polyrhythm` — cross-rhythms (3:4, 2:3, 5:7)
20. `create_scale_run` — ascending/descending scale fills
21. `create_call_response` — antecedent/consequent phrases
22. `create_walking_bass` — walking bass over chord changes
23. `apply_sidechain` — volume automation ducking on kick
24. `create_ghost_notes` — quiet grace notes for groove
25. `apply_velocity_curve` — deterministic velocity envelope (ramp/arc/trough/power)
26. `apply_articulation` — staccato/legato/tenuto/accent
27. `create_riser` — ascending pitch sweep for build-up transitions (linear/exp/log curves)
28. `create_stab` — rhythmic chord stabs for house/disco/funk (grid pattern with ghost notes, chord cycling)
29. `create_break` — classic drum breaks (Amen/Think/Ashanti/Funky Drummer/When the Levee/Synthetic) with variation modes and swing
30. `create_bass_drop` — descending pitch sweep into sustained sub bass (dubstep/EDM/trap, 3 curves, sweep+hold phases)
31. `create_chop` — slice source pitches into segments and rearrange (reverse/stutter/shuffle/ping-pong/gate, Dilla/Madlib/glitch-hop)
32. `create_trill` — rapid two-note alternation ornament (5 rates, upper accent, start convention)
33. `create_glissando` — smooth scale run between two pitches (6 scale types, 5 rates, 4 velocity curves, asc/desc)
34. `create_sequence` — transposed melodic repetition (up/down/alternating, adjustable transposition, velocity decay)
35. `create_pedal_point` — sustained bass under changing chords (retrigger/sustained, chord name parsing, time signatures)
36. `create_comping` — rhythmic chordal accompaniment (chord JSON × rhythm grid, jazz/funk/reggae/country/neo-soul)
37. `create_ostinato` — repeating melodic/rhythmic pattern as foundation layer (scale-based, 1-16 repeats)
38. `create_mordent` — ornament: main→neighbor→main (upper/lower, Bach/Mozart)
39. `create_turn` — ornament: main→up→main→down→main (gruppetto, upper/lower, Mozart/Beethoven/Bach)
40. `create_appoggiatura` — ornament: approach→main (tension→release, above/below, Bach/Mozart/Chopin)
41. `create_hemiola` — 3:2 rhythmic displacement creating cross-rhythm illusion (Afro-Cuban/jazz/minimalism)
42. `create_bordun` — continuously sustained drone chord as textural layer (open fifths/octaves, bagpipes/tanpura/ambient)
43. `create_hocket` — melodic line split between 2-4 voices (alternate/pairs/phrase, medieval/African/gamelan/Reich)
44. `create_isorhythm` — repeating rhythm (talea) × repeating pitch (color) as independent cycles (phase shift at LCM, Machaut/Messiaen)
45. `create_passacaglia` — bass ostinato + evolving harmonies (block/arpeggiated/melodic variations, Bach/film/metal)
46. `create_canon` — same melody in 2-6 voices with delayed entry + transposition (Pachelbel/rounds/fugues)
47. `create_chorale` — 4-voice SATB chorale with voice-leading rules (nearest chord tone, parallel fifth detection, S/A/T/B range clamping, Bach/vocal/strings)
48. `create_fugue` — polyphonic fugue with subject, tonal/real answer, optional countersubject, stretto (voice alternation, 2-5 voices, Bach WTC/Art of Fugue)
49. `create_two_hand_piano` — two-hand piano arrangement: left hand accompaniment (block/arpeggio/Alberti/bass+chord) + right hand (chord tones/arpeggio/melody). Separate octaves, adjustable arpeggio rate (piano ballads, jazz comping, lofi piano)
50. `create_variations` — 9 transformations in one operation (transpose/invert/retrograde/augment/diminish/fragment/transpose_cadence/octave_shift/reverse)
51. `create_motif_development` — through-composed melodic development: 11 stages (statement/sequence/fragment/invert/octave/expand/compress/cadence)
52. `create_stutter` — stutter edit: rapid rhythmic repetitions with evolving rate (accelerate/decelerate/ping_pong/random), accent patterns, velocity ramps, gate, pitch jitter (BT/Imogen Heap/Deadmau5)
53. `create_phase` — Steve Reich phase shifting: 2-4 voices play same pattern, one gradually shifts in time. 3 drift directions, phase_rate, phase_amount with reset (minimalism)
54. `create_cross_rhythm` — cross-rhythm: multiple voices with independent period lengths creating shifting alignment. Unlike polyrhythm (divides one bar), cross-rhythm gives each voice its own period. Voices realign at LCM. 2-6 voices (African, Steve Reich, Talking Heads)
55. `create_clave` — Afro-Cuban clave: 5-note rhythmic skeleton across 2 bars. 6 types (son/rumba/bossa/6-8), direction 3-2 or 2-3. All rhythms align to clave
56. `create_euclidean_rhythm` — Euclidean rhythm: BJK algorithm distributes k onsets across n steps maximally evenly. E(3,8)=tresillo, E(7,16)=samba, E(7,12)=bembé. Rotation, accents, bars
57. `create_cross_rhythm` — Cross-rhythm: 2-6 voices with independent periods (not fractions of one bar). LCM alignment. Velocity attenuation per voice
58. `create_clave` — (see #55 above)
59. `create_tumbao` — Afro-Cuban conga pattern. 4 types (open/tip/heel/slap strokes). 3 conga pitches
60. `create_cascara` — Afro-Cuban cáscara: timbale shell rhythm. 4 variants (son 3-2/2-3, guaguanco, mambo). Completes trilogy with clave+tumbao
61. `create_dembow` — Reggaeton/dancehall 3-3-2 gallop. 5 variants (classic/dancehall/trap_latino/perreo/urbano)
62. `create_boom_bap` — Hip-hop boom-bap. 5 variants (classic/old_school/trap/lofi/drill). Kick on 1/3, snare on 2/4
63. `create_four_on_floor` — House/techno/disco four-on-the-floor. Kick on every quarter. 5 variants (classic_house/deep_house/techno/disco/tech_house). Open hats, claps, 16th hats

### create_notes_batch
- **Replaces:** 10-50 × `create_note`
- **Input:** JSON array of note objects `[{pitch, start, duration, velocity?}]`
- **Implementation:** Parses JSON in Python, passes to bridge as `json.dumps(note_list)`. All notes created in one `h.modify()` block. Auto-creates region if none exists. Extends region duration if notes exceed it.
- **Limit:** 500 notes per batch.
- **Token savings:** ~2000 tokens for a 20-note melody (1 call vs 20).

### create_drum_pattern
- **Replaces:** 10-20 × `create_note` for drum beats
- **Input:** JSON object with drum lanes, compact step-sequencer notation
  - `'x'` = hit (velocity 0.9), `'o'` = soft (0.5), `'.'` = rest, `'X'` = accent (1.0)
  - Lanes: kick(36), snare(38), hihat(42), clap(39), perc(47) — GM drum map pitches
- **Example:** `'{"kick":"x...x...x...x...","snare":"....x.......x...","hihat":"....o...o...o..."}'`
- **Implementation:** Each char = one 16th note step. All notes in one region, one `h.modify()`.

### create_chord_progression
- **Replaces:** 15-50 × `create_note` for chord sequences
- **Input:** JSON array of `[root_name, chord_type]` pairs
  - Roots: C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B
  - Types: maj, min, dom7, maj7, min7, sus2, sus4, add9, dim, aug
- **Music theory baked in:** Note→pitch class map, chord interval maps. Voicing centered around C4 (60), root pitched down if > F# to keep voicing compact.
- **Implementation:** Python builds note_list from chord specs, then same batch-create path as `create_notes_batch`.

### add_mastering_chain
- **Replaces:** 3 × `add_effect` + 10 × `set_effect_parameter`
- **Input:** `target_lufs` (-14 Spotify, -16 Apple, -10 loud), `style` (balanced/warm/loud/transparent)
- **Implementation:** Adds Revamp EQ → Compressor → Maximizer to the last AU (output bus). Uses `h.allAUBoxes()` (boxes, NOT `h.allAUs()` adapters) for the target AU. Each effect inserted via `p.api.insertEffect(targetAU.audioEffects, EF.Revamp)` — first arg is the `.audioEffects` field on the AU box, NOT the AU box itself. Separate `h.modify()` blocks per effect insertion (required by openDAW). Then one more `h.modify()` to set compressor/maximizer params via `record()` iteration.
- **Parameter presets:** Defined in Python dict, passed to bridge as JSON.
- **Note:** Does NOT set EQ params — Revamp has complex section-based params. EQ is added as a shell for agent to configure. Compressor and Maximizer get full param setting.
- **Pitfall:** Do NOT use `compBox._fields.entries()` — `_fields` does not exist on effect boxes. Use `compBox.record()` and iterate with `Object.entries(record)`, getting field name via `field._fieldName || field.fieldName || key`.
- **Tested:** Revamp + Compressor (threshold -20, ratio 3) + Maximizer (ceiling -1.5) ✅

### create_genre_track
- **Replaces:** 20-40 low-level calls (create AU × 2, set BPM, create notes for chords/bass/drums)
- **Input:** `genre` (house/techno/lofi/dnb/trap/ambient), optional `bpm` override
- **Implementation:**
  1. Set BPM via `h.api.setBpm(bpm)` inside `h.modify()` — NOT raw tempo field, NOT `p.rootBoxAdapter.project.tempo`
  2. Create synth AU (Vaporisateur) for chords/bass — MUST be inside `h.modify()` (see pitfall below)
  3. Add chord notes (music theory maps in JS) to first note track
  4. Add bass notes to second note track (or first if only one)
  5. Create second synth AU for drums, add drum pattern notes
  6. Each section in its own `h.modify()` block
- **Genre data:** Hardcoded in Python dict — drums (step notation), bass (note list), chords (name+type pairs), default BPM.
- **Tested:** lofi preset → 16 chord notes, 12 drum notes, 2 AUs, BPM 80 ✅

### create_song_structure
- **Replaces:** 5-10 × `add_marker` for song form layout
- **Input:** JSON array of section objects `[{"name":"Intro","bars":4},{"name":"Verse","bars":8},...]`
- **Implementation:** Python parses sections, accumulates beat positions (bars × 4), builds marker data array. For each marker: `MarkerBox.create(h.boxGraph, h.uuid.generate(), ...)` inside `h.modify()`. Uses `h.timelineBox?.markerTrack` and `box.track.refer(markerTrack.markers)`.
- **Pitfall:** `p.api.addMarker` does NOT exist. The API has no marker creation method. Must use `MarkerBox.create()` directly with the same pattern as `add_marker` tool.
- **Pitfall:** Marker position must be in PPQN: `Math.round(position_beats * h.ppqn.Quarter)`.
- **Tested:** Intro(4) + Verse(8) + Chorus(8) + Outro(4) → 4 markers, 96 beats, 24 bars ✅

### automation_sweep
- **Replaces:** 10-30 × `create_automation_event` for smooth parameter ramps
- **Input:** `unit_index`, `parameter_name` (e.g. "cutoff"), `start_beat`, `end_beat`, `start_value`, `end_value`, `steps` (default 16), `curve` (linear/exp/log)
- **Implementation:** Python passes params to bridge. JS interpolates points based on curve type:
  - linear: `startVal + (endVal - startVal) * t`
  - exp: `startVal + (endVal - startVal) * (Math.exp(t * 3) - 1) / (Math.exp(3) - 1)` — slow start, fast end. Good for filter sweeps.
  - log: `startVal + (endVal - startVal) * Math.log(1 + t * (Math.E - 1))` — fast start, slow end.
- **Auto-creates automation track:** Uses `h.api.createAutomationTrack(au, field)` + `h.api.createValueClip(autoTrack, 0, {name})` + `ValueEventBox.create()` for each point. All in one `h.editing.modify()` block.
- **Pitfall:** Original design took `track_index` and required a pre-existing value track. Redesigned to take `parameter_name` instead — the tool finds the instrument field, creates the automation track, and populates it in one call. Much more useful for agents.
- **Pitfall:** Must find instrument box via `h.inputBoxes(au)` → filter out AudioBusBox. Same pattern as `add_instrument_automation` tool.
- **Pitfall:** `ValueEventBox.create()` needs `box.interpolation.setValue(1)` for linear interpolation between points (0=none/step, 1=linear).
- **Tested:** cutoff sweep 0.1→0.9 over 16 beats, 8 steps, exp curve ✅. Values correctly interpolated (0.1, 0.122, 0.157, 0.21, ...).

## Key Implementation Patterns

1. **Python-side validation:** All JSON parsing and parameter validation happens in Python before the bridge call. Returns error strings immediately without touching the DAW.

2. **One bridge round-trip:** Each orchestration tool makes exactly one `bridge.evaluate()` call. All DAW mutations happen inside that call's JS execution.

3. **Multiple `h.modify()` blocks:** Within a single `evaluate()`, multiple `h.modify()` blocks are used for logically separate operations (e.g., separate blocks for chords, bass, drums in `create_genre_track`). This matches openDAW's requirement for atomic box operations.

4. **`json.dumps()` for data passing:** Python data structures (note lists, genre configs) are serialized via `json.dumps()` and interpolated into the JS template string. This handles escaping correctly — `_escape_js` was a dead function, replaced with `json.dumps()`.

5. **Auto-region creation:** If no region exists on the target track, one is created with `NoteEventCollectionBox` + `NoteRegionBox`. If a region exists, notes are appended to its event collection.

6. **Region duration extension:** After adding notes, if any note extends beyond the current region duration, the duration (and loopDuration) are extended.

## CI Threshold

CI assertion updated: `assert count >= 284` (was 258, 260, 263, 283, etc.). AST count verified via `python3 -c "import ast; ..."`. The AST counts ALL async functions including non-tool helpers (`start`, `stop`, `evaluate`), so the threshold should be set to the exact `mcp_opendaw_` prefix count. Use the prefix filter for accurate count: `[n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith('mcp_opendaw_')]`.

## Runtime Pitfalls (discovered during end-to-end testing)

### 1. `p.api.createInstrument()` MUST be inside `h.modify()`

`createInstrument` calls `CaptureMidiBox.create()` → `BoxGraph.stageBox()` which requires a transaction. Calling it outside `h.modify()` throws:
```
Error: Modification only prohibited in transaction mode.
    at #assertTransaction
    at BoxGraph.stageBox
    at CaptureMidiBox.create
    at #trackTypeToCapture
    at ProjectApi.createInstrument
```

**Fix:** Wrap in `h.modify()`:
```javascript
let synthAU;
h.modify(() => {
    const result = p.api.createInstrument(IF.Vaporisateur, {});
    synthAU = result.audioUnitBox;  // NOTE: returns {audioUnitBox, instrumentBox, trackBox}
});
```

### 2. `createInstrument` return value is NOT the AU box

`p.api.createInstrument()` returns an object `{audioUnitBox, instrumentBox, trackBox}`, not the AU box directly. Using the return value as a box (e.g. `h.noteTrackBoxes(result)`) throws `Cannot read properties of undefined (reading 'pointerHub')`.

**Fix:** Extract `.audioUnitBox` from the return value.

### 3. `insertEffect` argument: `au.audioEffects` field, not the AU box

`p.api.insertEffect(targetAU, factory)` with the AU box directly throws `VaporisateurDeviceBox ... has no index field`. The first argument must be the `.audioEffects` field on the AU box.

**Fix:** `p.api.insertEffect(targetAU.audioEffects, EF.Revamp)` — use `h.allAUBoxes()` (boxes), then access `.audioEffects` on the box.

### 4. Effect field access: `record()`, not `_fields.entries()`

Effect boxes do NOT have a `_fields` Map. Use `box.record()` which returns a `Record<fieldKey, Field>` object.

**Fix:**
```javascript
const record = compBox.record();
for (const [key, field] of Object.entries(record)) {
    const fname = field._fieldName || field.fieldName || key;
    if (fname === 'threshold') field.setValue(params.comp_threshold);
}
```

### 5. BPM: use `h.api.setBpm()`, never raw tempo field

`p.rootBoxAdapter.project.tempo` is undefined. Accessing `.tempo` throws `Cannot read properties of undefined (reading 'tempo')`.

**Fix:** `h.modify(() => h.api.setBpm(bpm));` — the API handles normalization internally.

## Adding New Orchestration Tools

When adding a new orchestration tool:
1. Define input validation in Python (JSON parsing, enum checks, range checks)
2. Build the data structure in Python (note lists, config dicts)
3. Pass to bridge via `json.dumps()` interpolation in f-string
4. Use multiple `h.modify()` blocks for separate logical operations
5. Update: TOOL_CATALOG.md, README.md, pyproject.toml, server.json, CI threshold
6. Run: `python3 -c "import ast; ..."` to verify AST tool count
7. Run: `python -m pytest tests/ -q` to verify no regressions
8. Commit with `feat: N orchestration tools — ...` message

## PyPI Publishing Workflow

When ready to publish a new version:

1. Bump version in `pyproject.toml`
2. Update all tool count references: README.md badge, README.md body, TOOL_CATALOG.md header + total, server.json description, pyproject.toml description, `main()` version string, `main()` help string, CI threshold in `.github/workflows/ci.yml`
3. Build: `pip install build twine` (one-time), then `rm -rf dist && python3 -m build`
4. Upload: `TWINE_PASSWORD="<token>" TWINE_USERNAME="__token__" python3 -m twine upload dist/opendaw_mcp-<version>*`
5. GitHub Release: `gh release create v<version> --title "v<version> — ..." --notes "..."`
6. Verify: `pip index versions opendaw-mcp`
7. Store token in credentials: `python3 credentials/credman.py add-account pypi __token__ --password "<token>" --notes "PyPI API token for opendaw-mcp"`

**AST count note:** `ast.walk` counting `AsyncFunctionDef` includes helper functions (`start`, `stop`, `evaluate`) that are NOT MCP tools. Real tool count = AST count - 3 (roughly). Use the `mcp_opendaw_` prefix filter for accurate count: `[n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith('mcp_opendaw_')]`.

## Patch Release Pattern (v1.10.1)

When orchestration tools have runtime bugs caught during bridge testing (not unit tests):

1. Fix the JS code in `server.py` (e.g. `p.api.addMarker` → `MarkerBox.create()`)
2. Bump patch version: `1.10.0` → `1.10.1` in `pyproject.toml`, `server.json`, `server.py` main() version string
3. Do NOT bump tool count (same 260 tools, just fixed)
4. Rebuild: `rm -rf dist && python3 -m build`
5. Republish: `TWINE_PASSWORD=... TWINE_USERNAME=__token__ python3 -m twine upload dist/opendaw_mcp-<patch>*`
6. GitHub Release with fix notes
7. Comment on all open catalog PRs/issues (punkpeye/awesome-mcp-servers#9133, chatmcp/mcpso#3003, YuzeHao2023/Awesome-MCP-Servers#338)
8. Update memory with new version

**Token location:** `python3 credentials/credman.py search pypi` → pypi/__token__ account.
