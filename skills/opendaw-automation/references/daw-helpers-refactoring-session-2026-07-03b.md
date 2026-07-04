# DAW_HELPERS Refactoring — Session 2026-07-03b (56 tools converted)

## Summary

Continued the incremental `const p = window.DAW;` → `const h = window.DAW_HELPERS;` refactoring. Progress: 40→56 tools converted (16 in this session), 124 remaining. 3 new pre-existing `.sort()` bugs found and fixed. 7 commits pushed, CI green.

## Packages converted this session

### Package 9: Effect params + MIDI effects (9 tools)
- `get_effect_details` (list_effect_parameters variant)
- `set_effect_parameter` — missing `.sort()` on AU list, fixed
- `set_effect_parameter_string` — missing `.sort()` on AU list, fixed
- `remove_effect` — missing `.sort()` on AU list, fixed
- `add_midi_effect` — already had `.sort()`
- `remove_midi_effect` — already had `.sort()`
- `get_midi_effect_chain` — already had `.sort()`
- `list_midi_effect_params` — already had `.sort()`
- `set_midi_effect_param` — already had `.sort()`
- Commit: `6f2b22f`

### Package 10: Vaporisateur + instrument params (3 tools)
- `list_vaporisateur_params` — auto-detect pattern (unitIdx >= 0 / else)
- `set_vaporisateur_osc_param` — auto-detect pattern + `p.editing.modify()` → `h.modify()`
- `list_instrument_params` — auto-detect pattern
- Commit: `959a02a`

### Package 11: Set instrument param + Playfield (4 tools)
- `set_instrument_param` — auto-detect pattern, `h.modify()` for field.setValue
- `list_playfield_samples` — Playfield auto-detect (find "PlayfieldDeviceBox")
- `set_playfield_sample_enabled` — Playfield auto-detect + `h.modify()`
- `create_playfield_sample` — Playfield auto-detect + `h.modify()` + `h.uuid.generate()` + `h.boxGraph`
- Commit: `5506294`

## Auto-detect pattern conversion

Many instrument-param tools use an "auto-detect" pattern where `unit_index: int = -1` means "find the first AU with this instrument type". The conversion is straightforward:

```js
// OLD:
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box).sort(...);
if (unitIdx >= 0) {
    const au = units[unitIdx];
    const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
    vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
} else {
    for (const au of units) {
        const incoming = [...au.input.pointerHub.incoming()].map(({box}) => box);
        vap = incoming.find(b => b.constructor.name === "VaporisateurDeviceBox");
        if (vap) break;
    }
}

// NEW: just p → h
const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box).sort(...);
// ... same logic, just h instead of p
```

The only changes needed:
1. `const p = window.DAW;` → `const h = window.DAW_HELPERS;`
2. `p.rootBox` → `h.rootBox`
3. `p.editing.modify()` → `h.modify()`
4. `window.DAW_UUID` → `h.uuid` (remove `const UUID = window.DAW_UUID;` line)
5. `p.boxGraph` → `h.boxGraph`

## `.sort()` bug pattern — systematic exposure during refactoring

The AU ordering bug (SKILL.md pattern #41) was fixed in 80+ sites in a prior session. However, refactoring continues to expose tools that were MISSED in that original fix. The pattern is always the same:

```js
// BUG: no .sort() — AU order is arbitrary (insertion order)
const units = [...p.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box);

// FIX: add .sort() by index field
const units = [...h.rootBox.audioUnits.pointerHub.incoming()].map(({box}) => box)
    .sort((a, b) => (a.index?.getValue?.() ?? 0) - (b.index?.getValue?.() ?? 0));
```

**7 additional missing-sort bugs found across sessions 2026-07-03a + 2026-07-03b:**
1. `set_track_volume` — missing `.sort()`
2. `set_track_panning` — missing `.sort()`
3. `set_track_mute` — missing `.sort()`
4. `set_track_solo` — missing `.sort()`
5. `add_effect` — missing `.sort()`
6. `list_effect_parameters` — missing `.sort()`
7. `set_effect_parameter` — missing `.sort()`
8. `set_effect_parameter_string` — missing `.sort()`
9. `remove_effect` — missing `.sort()`

**Rule**: When converting ANY tool that uses `pointerHub.incoming()` for AU access, ALWAYS verify `.sort()` is present. If absent, add it. This is not optional — without `.sort()`, `units[1]` may return undefined or the wrong AU.

## Patch tool pitfall — duplicate return

When patching large evaluate blocks (50+ lines like `create_send`), the `old_string`/`new_string` boundary can accidentally introduce a duplicate `return _wrap_eval(result)` line. Always check lint status after patching large blocks — the linter catches this as unreachable code.

## Remaining roadmap (124 tools)

| Package | Est. count | Priority |
|---------|-----------|----------|
| Notes | ~12 | P1 (next) |
| Regions | ~10 | P1 |
| Clips | ~11 | P1 |
| Automation | ~8 | P2 |
| Export/Render | ~7 | P2 |
| MIDI | ~2 | P2 |
| MIDI Effects (remaining) | ~3 | P3 |
| Modular | ~7 | P3 |
| PianoMode | ~6 | P3 |
| Scriptable Devices | ~5 | P3 |
| Transfer | ~2 | P3 |
| Presets | ~5 | P3 |
| Device Mgmt | ~4 | P3 |
| Note Advanced | ~4 | P3 |
| Musical Grid | ~7 | P3 |
| Inspection | ~3 | P3 (some already on DAW_HELPERS) |
| Transients/Warp/Content | ~6 | P3 |
| Tempo/Mixer/Region | ~7 | P3 |
| Debugging | ~3 | P3 (already on DAW_HELPERS) |

## CI status

All 7 commits pushed to `main` on GitHub. CI green (syntax check + AST tool count >=211 + DSP scripts + hardcoded paths). No regressions.
