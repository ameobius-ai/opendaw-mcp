# DRY Refactoring: Effect Enumeration → h.effectBoxes() — 2026-07-03

## Summary

After box-level AU enumeration DRY (see `dry-box-level-au-enumeration-2026-07-03.md`), 24 occurrences of raw effect chain enumeration remained:

```js
const effects = [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue());
```

Added `h.effectBoxes(au)` and `h.midiEffectBoxes(au)` helpers. Migrated 12 tools (3 single-line + 9 multi-line). Commit: `ee5ce6e`.

## Helpers added (server.py bridge.start(), DAW_HELPERS block)

```js
// Get effect boxes for an AU (sorted by index)
effectBoxes: (au) => [...au.audioEffects.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue()),
// Get MIDI effect boxes for an AU (sorted by index)
midiEffectBoxes: (au) => [...au.midiEffects.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => a.index.getValue() - b.index.getValue()),
```

## Replacement patterns

### Pattern 1 — single-line with sort (3 occurrences)
```
OLD: const effects = [...au.audioEffects.pointerHub.incoming()].map(({{box}}) => box).sort((a, b) => a.index.getValue() - b.index.getValue());
NEW: const effects = h.effectBoxes(au);
```

### Pattern 2 — multi-line .map().sort() (9 occurrences)
```
OLD: const effects = [...au.audioEffects.pointerHub.incoming()]
         .map(({{box}}) => box)
         .sort((a, b) => a.index.getValue() - b.index.getValue());
NEW: const effects = h.effectBoxes(au);
```

## Remaining (NOT migrated — different patterns)

13 occurrences remain, all edge cases that don't fit the helper:
- `.forEach()` loops (1) — different iteration pattern
- `.length` queries (1) — `h.effectBoxes(au).length` works but minimal gain
- `.map(({box}) => box)` without `.sort()` (5) — unsorted access, helper sorts
- `.find()` calls (1) — `h.effectBoxes(au).find(...)` works but only 1 occurrence
- Custom `.map(({box}) => ({...}))` with transform (1) — different shape
- `const fx = [...].map(({box}) => box)` without sort (5) — unsorted, different var name

These are low-frequency patterns (1-5 occurrences each). Migration would add complexity without significant boilerplate reduction.

## Post-v1.9.2 DRY continuation

After v1.9.2 release, DRY refactoring continued with 3 more helpers:

| Commit | Helper | Replacements | Pattern |
|--------|--------|-------------|---------|
| `ef167e0` | `h.midiEffectBoxes()` / `h.trackBoxes()` | 33 | MIDI effects + track enumeration |
| `f00c1b7` | `h.regionBoxes()` | 29 | Region enumeration (unsorted) |
| `b785df4` | `h.eventBoxes()` | 15 | Note events + signature events (unsorted) |
| `0018386` | `h.inputBoxes()` | 18 | Device input enumeration (unsorted) |

Total post-v1.9.2: 95 additional replacements. Grand total: 220 across 8 helpers.

**Key lesson: unsorted helpers.** regionBoxes, eventBoxes, and inputBoxes are intentionally unsorted (insertion order). The original code didn't sort these, and adding sort would silently change index semantics. Only add sort to a helper if the original pattern included `.sort()`.
