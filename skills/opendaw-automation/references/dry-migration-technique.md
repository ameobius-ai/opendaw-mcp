# DRY Migration Technique — Bulk replace_all for Enumeration Boilerplate

## Problem

server.py (11,800+ lines) had 196 `pointerHub.incoming()` calls, many with identical `[...X.pointerHub.incoming()].map(({box})=>box).sort(...)` boilerplate. Manual tool-by-tool migration would take hours.

## Technique: replace_all with exact string matching

### Step 1: Count exact patterns

```bash
# Count exact string occurrences (use -F for literal, not regex)
grep -cF 'const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));' server.py
```

Note: f-string `{{}}` braces must be included in the search string — they're literal in the .py file.

### Step 2: replace_all via patch tool

```
patch(mode='replace', replace_all=true, old_string='<exact pattern>', new_string='<helper call>')
```

### Step 3: Handle multi-line patterns

Multi-line patterns need exact whitespace matching. Use `grep -n -A2` to see continuation lines:

```bash
grep -n -A2 'const units = [...h.rootBox.audioUnits.pointerHub.incoming()]$' server.py
```

Then replace the full multi-line block including continuation lines.

### Step 4: Clean up dangling .sort() lines

When replacing `[...raw...].map().sort()` with `h.allAUBoxes()` (which already sorts), the `.sort()` continuation line becomes orphaned. Replace the two-line pattern:

```
# Before:
const units = h.allAUBoxes();
    .sort((a, b) => ...);

# After:
const units = h.allAUBoxes();
```

Use `replace_all=true` for each dangling `.sort()` variant.

### Step 5: Verify after each batch

```bash
# Syntax check
python3 -W error -c "import py_compile; py_compile.compile('server.py', doraise=True)"

# Tool count (must stay 245)
python3 -c "import ast; tree=ast.parse(open('server.py').read()); tools=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.decorator_list]; print(f'OK: {len(tools)} tools')"

# Residual count
grep -c 'pointerHub.incoming()' server.py
```

## Pattern priority (by frequency)

1. `const units = [...h.rootBox.audioUnits...].sort(...)` → `h.allAUBoxes()` (79 occurrences)
2. `const allUnits = [...h.rootBox.audioUnits...].sort(...)` → `h.allAUBoxes()` (14)
3. Multi-line `.map().sort()` → single helper call (12)
4. `.length` queries → `h.allAUBoxes().length` (4)
5. `for (const au of [...raw...])` → `for (const au of h.allAUBoxes())` (1)
6. `const allUnits = [...rootBox...]` (no `h.` prefix) → `h.allAUBoxes()` (2)

## Key decisions

- **regionBoxes is unsorted** — original code didn't sort regions by position. Adding sort would change region index semantics. Helper returns insertion order.
- **trackBoxes is sorted by index** — original code always sorted tracks by index field. Safe to sort.
- **effectBoxes/midiEffectBoxes sorted by index** — original code always sorted effects by index. Safe.
- **auBox(i) throws Error** — not undefined, for out-of-range. This is intentional — tools catch it.
- **eventBoxes is unsorted** — note events and signature events weren't sorted in original code. Helper preserves insertion order.
- **inputBoxes is unsorted** — device input enumeration (instruments, effects) wasn't sorted. Helper preserves insertion order.
- **Sort decision rule: check original code before adding sort to helper.** If the original pattern included `.sort()`, the helper sorts. If not, the helper preserves insertion order. Adding sort to an unsorted helper silently changes index semantics for all migrated tools.

## Commits (2026-07-03)

| Commit | Helper | Replacements | Delta lines |
|--------|--------|-------------|-------------|
| `45eb15a` | `h.allAUBoxes()` / `h.auBox()` | 133 | -36 |
| `ee5ce6e` | `h.effectBoxes()` | 12 | -12 |
| `ef167e0` | `h.midiEffectBoxes()` / `h.trackBoxes()` | 33 | -27 |
| `f00c1b7` | `h.regionBoxes()` | 29 | +2 |
| `b785df4` | `h.eventBoxes()` | 15 | +9 |
| `0018386` | `h.inputBoxes()` | 18 | +2 |
| `cf52904` | `h.markerBoxes()` / `h.sendBoxes()` / `h.busBoxes()` / `h.sampleBoxes()` / `h.noteTrackBoxes()` / `h.clipBoxes()` | 83 | -12 |
| `72cd457` | `h.rootClipBoxes()` / `h.scriptParams()` / `h.scriptSamples()` / `h.chainBoxes()` + edge cases | ~32 | -10 |

Total: ~295 replacements across 17 helpers. (Earlier counts of ~418 were inflated by double-counting multi-line replacements.)

## Round 2 (2026-07-03)

After round 1 (220 replacements, 8 helpers), 136 `pointerHub.incoming()` remained. This session added 6 more helpers and migrated 83 more (303 total):

### New helpers added

| Helper | Pattern | Replacements | Sort? |
|--------|---------|-------------|-------|
| `h.markerBoxes(mt)` | `[...mt.markers.pointerHub.incoming()].map(({box})=>box)` | 6 | No |
| `h.sendBoxes(au)` | `[...au.auxSends.pointerHub.incoming()].map(({box})=>box).sort(index)` | 7 | Yes (index) |
| `h.busBoxes()` | `[...p.rootBox.audioBusses.pointerHub.incoming()].map(({box})=>box)` | 4 | No |
| `h.sampleBoxes(pf)` | `[...pf.samples.pointerHub.incoming()].map(({box})=>box)` | 3 | No |
| `h.noteTrackBoxes(au)` | `[...au.tracks...].map().sort(index).filter(type===1)` | 10 | Yes (index) + filter |
| `h.clipBoxes(track)` | `[...track.clips.pointerHub.incoming()].map(({box})=>box)` | 3 | No |

### Additional replacements via existing helpers

| Existing helper | New replacements | Context |
|----------------|-----------------|---------|
| `h.trackBoxes()` | 12 | 9 single-line `.map()`, 2 `.length`, 1 filter `type===2` ×2 |
| `h.effectBoxes()` | 13 | 5 scriptable `fx`, 5 various single-line, 3 `.find()` / `.length` |
| `h.midiEffectBoxes()` | 6 | 5 ternary `au.midiEffects ? h.midiEffectBoxes(au) : []`, 1 sort |
| `h.inputBoxes()` | 6 | 5 ternary `au.input ? h.inputBoxes(au) : []`, 1 direct |
| `h.eventBoxes()` | 5 | 3 direct, 2 `.length` |
| `h.regionBoxes()` | 5 | 3 `.length`, 2 direct |

### CRITICAL PITFALL: wrong field for clips

**Mistake:** Used `h.regionBoxes(track)` to replace `[...track.clips.pointerHub.incoming()].map(({box})=>box)` — this is WRONG. `regionBoxes` accesses `track.regions`, not `track.clips`. Clips and regions are different collections on a track box.

**Fix:** Created separate `h.clipBoxes(track)` helper that accesses `track.clips.pointerHub.incoming()`.

**Lesson:** Always verify the field name in the helper matches the field name in the original code. `regionBoxes` → `track.regions`, `clipBoxes` → `track.clips`. Similar names, different fields. A `replace_all` with the wrong helper silently corrupts every clips call.

### Ternary pattern migration

Many scriptable device tools use ternary guards:
```js
const me = au.midiEffects ? [...au.midiEffects.pointerHub.incoming()].map(({box})=>box) : [];
const incoming = au.input ? [...au.input.pointerHub.incoming()].map(({box})=>box) : [];
```

These migrate cleanly to:
```js
const me = au.midiEffects ? h.midiEffectBoxes(au) : [];
const incoming = au.input ? h.inputBoxes(au) : [];
```

5 occurrences each — `replace_all=true` handles them in one patch.

### `.map(({box}) => box)` vs `.map(({{box}}) => box)` in f-strings

In Python f-strings, `{box}` becomes a format placeholder. The JS code uses `{{box}}` in the f-string which renders as `{box}` in the actual JS. When writing helper definitions (NOT inside f-strings), use single braces `{box}`. When writing tool code inside f-strings, use double braces `{{box}}`. The helpers themselves are defined in the DAW_HELPERS injection block which IS an f-string, so they use `({box})`.

## Round 3 — edge case migration (2026-07-03, same session)

After round 2 (303 replacements, 14 helpers), 53 `pointerHub.incoming()` remained (40 working + 13 helper defs). Round 3 tackled the "edge cases" and migrated ~32 more, bringing total to ~295 replacements:

### New helpers added

| Helper | Pattern | Replacements | Sort? |
|--------|---------|-------------|-------|
| `h.rootClipBoxes()` | `[...p.rootBox.clips.pointerHub.incoming()].map(({box})=>box)` | 1 | No |
| `h.scriptParams(device)` | `[...device.parameters.pointerHub.incoming()].map(({box})=>box)` | 2 | No |
| `h.scriptSamples(device)` | `[...device.samples.pointerHub.incoming()].map(({box})=>box)` | 1 | No |
| `h.chainBoxes(field)` | `[...field.pointerHub.incoming()].map(({box})=>box)` | 3 | No |

### Edge cases successfully migrated

| Pattern | Helper used | Count | Notes |
|---------|------------|-------|-------|
| `[...chainField.pointerHub.incoming()].map(({{box}})=>box)` | `h.chainBoxes(chainField)` | 3 | Dynamic field (audio or midi effects) |
| `[...field.pointerHub.incoming()].map(({{box}})=>box)` | `h.chainBoxes(field)` | 1 | Same dynamic pattern, different var name |
| `[...device.parameters.pointerHub.incoming()].map(({box})=>box)` | `h.scriptParams(device)` | 2 | Scriptable device internal params |
| `[...device.samples.pointerHub.incoming()].map(({box})=>box)` | `h.scriptSamples(device)` | 1 | Scriptable device internal samples |
| `[...rootBox.clips.pointerHub.incoming()].map(({{box}})=>box)` | `h.rootClipBoxes()` | 1 | Root-level clips (not track clips) |
| Multi-line `[...srcAU.audioEffects...].map().sort()` | `h.effectBoxes(srcAU)` | 3 | srcEffects, dstEffects, newOrder |
| Multi-line `[...instrumentAU.tracks...].map().filter(type===2)` | `h.trackBoxes(instrumentAU).filter(...)` | 1 | audioTracks filter |
| Multi-line `[...instrumentAU.tracks...].map().filter(type===1)` | `h.noteTrackBoxes(instrumentAU)` | 1 | noteTracks filter |
| Multi-line `[...au.tracks...].map().filter(type===3)` | `h.trackBoxes(au).filter(...)` | 2 | valueTracks (automation) ×2 |
| `noteTracks.push(...[...au.tracks...].map().filter(type===1))` | `noteTracks.push(...h.noteTrackBoxes(au))` | 1 | Spread into push |
| `[...au.audioEffects...].forEach(({{box}})=>{...})` | `h.effectBoxes(au).forEach((box)=>{...})` | 1 | forEach loop |
| `[...au.tracks...].map(({{box}})=>({{...}}))` (object map) | `h.trackBoxes(au).map((box)=>({{...}}))` | 1 | Object literal map |
| `[...events.events.pointerHub.incoming()].map().sort()` | `h.eventBoxes(events).sort(...)` | 2 | Adapter-level events access |
| `[...instBox.samples...].map()` (sort continuation) | `h.sampleBoxes(instBox)` | 2 | Playfield samples on instBox |
| `[...inst.box.samples...].map()` (ternary) | `inst.box.samples ? h.sampleBoxes(inst.box) : []` | 2 | Ternary with inst.box |
| `[...outputAU.input...].map()[0]` | `h.inputBoxes(outputAU)[0]?.box \|\| h.inputBoxes(outputAU)[0]` | 2 | First input box access |
| `targetAU.input...length > 0 ? [...targetAU.input...][0].box` | `h.inputBoxes(targetAU).length > 0 ? h.inputBoxes(targetAU)[0]` | 1 | Inline conditional access |
| `[...tbox.regions...].length` / `[...tbox.clips...].length` | `h.regionBoxes(tbox).length` / `h.clipBoxes(tbox).length` | 2 | Count queries |
| `[...track.regions...].map().sort(position)` | `h.regionBoxes(track).sort(position)` | 1 | Sort by position explicitly |
| `[...au.audioEffects...].find(constructor.name)` | `h.effectBoxes(au).find(...)` | 1 | Maximizer find |
| `[...srcAU.tracks...].map().sort(index)` | `h.trackBoxes(srcAU).sort(index)` | 1 | Already-sorted helper, redundant sort OK |

### Techniques used for edge cases

1. **Dynamic field access** — `const field = kind === 0 ? au.midiEffects : au.audioEffects; [...field.pointerHub.incoming()]` → `h.chainBoxes(field)`. Generic helper accepts any field with pointerHub.

2. **Scriptable device internals** — `device.parameters` and `device.samples` are NOT the same as Playfield's `pf.samples`. Separate helpers `h.scriptParams(device)` and `h.scriptSamples(device)` avoid confusion.

3. **Root-level clips** — `rootBox.clips` is different from `track.clips`. `h.rootClipBoxes()` vs `h.clipBoxes(track)`. Different collections on different objects.

4. **Multi-line with filter** — `.map(({box})=>box).filter(t => t.type === 3)` → `h.trackBoxes(au).filter(t => t.type === 3)`. Helper already maps+sorts, just chain the filter.

5. **forEach loops** — `[...au.audioEffects...].forEach(({{box}}) => {{...}})` → `h.effectBoxes(au).forEach((box) => {{...}})`. Same API, just swap the enumeration source.

6. **Object literal maps** — `.map(({{box}}) => ({{name: ...}}))` → `.map((box) => ({{name: ...}}))`. The `{{}}` in f-string becomes `{}` in JS. Helper returns boxes directly, so `(box)` not `({box})`.

7. **First-element access** — `[...outputAU.input.pointerHub.incoming()].map(({box})=>box)[0]` → `h.inputBoxes(outputAU)[0]`. May return adapter not box — add `?.box` fallback if needed.

8. **Spread into push** — `noteTracks.push(...[...au.tracks...].map().filter())` → `noteTracks.push(...h.noteTrackBoxes(au))`. Helper returns array, spread works directly.

### Final state after round 3

- **20 total `pointerHub.incoming()` occurrences** (down from 136 at round 2 start):
  - 17 — helper definitions (the helpers themselves contain `pointerHub.incoming()`)
  - 1 — comment (`// Get InstrumentBox via au.input.pointerHub.incoming()`)
  - 1 — `s.file.pointerHub.incoming().length > 0` — field existence check (not enumeration)
  - 1 — `[...chainField.pointerHub.incoming()]` — missed one, fixed after count check

- **0 raw enumeration patterns remain** — every `[...X.pointerHub.incoming()].map(({box})=>box)` working pattern has been migrated to a helper.

- **17 helpers total:**
  `auBox`, `allAUBoxes`, `effectBoxes`, `midiEffectBoxes`, `trackBoxes`, `regionBoxes`, `eventBoxes`, `inputBoxes`, `markerBoxes`, `sendBoxes`, `busBoxes`, `sampleBoxes`, `noteTrackBoxes`, `clipBoxes`, `rootClipBoxes`, `scriptParams`, `scriptSamples`, `chainBoxes`

- **~295 total DRY replacements** across 3 rounds, 8 commits. Final commit `848e72e` (v1.9.3 release).

## Verification after each round

```bash
# 1. Python syntax
python3 -c "import py_compile; py_compile.compile('server.py', doraise=True); print('syntax OK')"

# 2. AST tool count (must be 245)
python3 -c "import ast; tree=ast.parse(open('server.py').read()); tools=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.decorator_list]; print(f'OK: {len(tools)} tools')"

# 3. Residual count (track progress)
grep -c 'pointerHub.incoming()' server.py

# 4. Category breakdown of residuals
grep -n 'pointerHub.incoming()' server.py | head -60

# 5. CI green
gh run list --limit 1
```
