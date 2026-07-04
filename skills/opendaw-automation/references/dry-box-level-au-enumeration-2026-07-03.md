# DRY Refactoring: Box-Level AU Enumeration → h.allAUBoxes() — 2026-07-03

## Summary

After the prior `p → h` mass conversion (91 tools, see `daw-helpers-mass-conversion-2026-07-03.md`), 113+ tools still had raw box-level AU enumeration boilerplate:

```js
const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
```

This pattern appeared 135 times in server.py. Replaced 133 of them with `h.allAUBoxes()` (2 remaining are the helper definitions themselves). Commit: `45eb15a`.

## Helpers added (server.py bridge.start())

```js
// In DAW_HELPERS:
auBox: (i) => {
    const aus = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
        .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
    return aus[i];
},
allAUBoxes: () => [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0)),
```

`h.auBox(i)` = box by index (throws "No AU at {i}" if out of range).
`h.allAUBoxes()` = sorted array of all AU boxes (sorted by index field).

## Replacement patterns (6 variants)

### Pattern 1 — `const units` with sort (79 occurrences)
```
OLD: const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
NEW: const units = h.allAUBoxes();
```

### Pattern 2 — `const allUnits` with sort (14 occurrences)
```
OLD: const allUnits = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort(...);
NEW: const allUnits = h.allAUBoxes();
```

### Pattern 3 — `const allAU` with sort (7 occurrences)
```
OLD: const allAU = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).sort(...);
NEW: const allAU = h.allAUBoxes();
```

### Pattern 4 — Multi-line `.map().sort()` (12 occurrences)
```
OLD: const units = [...h.rootBox.audioUnits.pointerHub.incoming()]
         .map(({{box}}) => box)
         .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
NEW: const units = h.allAUBoxes();
```

### Pattern 5 — `.length` queries (4 occurrences)
```
OLD: const remaining = [...h.rootBox.audioUnits.pointerHub.incoming()].length;
NEW: const remaining = h.allAUBoxes().length;

OLD: const existingCount = [...h.rootBox.audioUnits.pointerHub.incoming()].length;
NEW: const existingCount = h.allAUBoxes().length;
```

### Pattern 6 — Edge cases (for..of, find, no `h.` prefix)
```
OLD: for (const au of [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box)) {
NEW: for (const au of h.allAUBoxes()) {

OLD: const outputAU = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box).find(u => u.type.getValue() === "output");
NEW: const outputAU = h.allAUBoxes().find(u => u.type.getValue() === "output");

OLD: const allUnits = [...rootBox.audioUnits.pointerHub.incoming()].map(({{box}}) => box);  // no h. prefix
NEW: const allUnits = h.allAUBoxes();
```

## Pitfall: dangling `.sort()` lines

When replacing Pattern 4 (multi-line `.map().sort()`), the replace_all only matched the first line, leaving orphaned `.sort(...)` continuation lines:

```
// AFTER first pass (BROKEN):
const units = h.allAUBoxes();
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));  // DANGLING
```

**Fix:** Two additional `replace_all` passes to remove the dangling lines:
1. `\n            .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));` (4-space indent variant)
2. `\n            .sort((a, b) => a.index.getValue() - b.index.getValue());` (different sort comparator)

`h.allAUBoxes()` already sorts internally, so these were dead code.

## E2E verification

```python
# 5-point helper verification (run via bridge.evaluate):
# 1. allAUBoxes returns array with correct count
# 2. auBox(0) returns box with correct type
# 3. allAUBoxes().length === raw [...rootBox.audioUnits.pointerHub.incoming()].length
# 4. auBox(0).address === allAUBoxes()[0].address
# 5. auBox(999) throws "No AU at 999" (expected, not undefined)
```

## Security audit (same session, committed before DRY)

Commits `367889a` + `e0fb0f4`:
- Transport action enum validation: `("play", "stop", "toggle")`
- `duplicate_effect` chain_type enum: `("audio", "midi")`
- `_safe_filename()`: `os.path.basename()` + sanitization
- `_safe_path()`: ensures within `OPENDAW_EXPORT_DIR`
- Applied to 6 render/export locations
- `_unwrap_eval`: bare except → `except json.JSONDecodeError`
- 1 bare except remains (atexit cleanup — acceptable)

See `references/security-audit-enum-validation-path-traversal-2026-07-03.md` for details.

## Pitfall: `pkill` kills the agent process

**NEVER use `pkill -f vite`** — it kills the Hermes agent process itself (which also matches "vite" in its command tree). Use targeted kill:
```bash
kill $(pgrep -f 'vite.*5174')
# or
process(action='kill', session_id='proc_xxx')
```
