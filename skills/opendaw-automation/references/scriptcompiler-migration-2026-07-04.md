# ScriptCompiler Migration + Stems Fix (2026-07-04)

## Context

Discovered via studying `naomiaro/opendaw-test` (543 commits, 17 SDK doc chapters) that our `set_script_device_code` tool was using a hand-rolled regex parser for `@param`/`@sample` declarations instead of the official SDK `ScriptCompiler`. Also found that `export_stems` and `export_single_stem` had `useInstrumentOutput: True` which rendered DRY stems (no effects) despite docstrings saying "effects included".

## ScriptCompiler Migration

### What changed

`set_script_device_code` rewritten to use `ScriptCompiler` from `@opendaw/studio-adapters` (exposed as `DAW_ScriptCompiler` global in `headless-daw/main.ts`).

### Config per device type

```js
const configs = {
  werkstatt: {headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"},
  apparat:   {headerTag: "apparat",   registryName: "apparatProcessors",   functionName: "apparat"},
  spielwerk: {headerTag: "spielwerk", registryName: "spielwerkProcessors", functionName: "spielwerk"},
};
```

### Usage in evaluate

```js
const compiler = ScriptCompiler.create(config);
await compiler.compile(ctx, editing, device, source);
// compile() calls editing.modify() internally + registers worklet
```

### `@param` mapping types — CRITICAL

ONLY these explicit mapping tokens are accepted: `linear`, `exp`, `int`, `bool`.

`unipolar` is the DEFAULT mapping when only name+value given (`// @param gain 0.5`), but passing `unipolar` as explicit 5th token THROWS:
```
Malformed @param: '// @param gain 0.5 0 1 unipolar' — unknown mapping 'unipolar' (expected: linear, exp, int, bool)
```

For 0-1 ranges with explicit bounds, use `linear`:
```
// @param gain 0.5 0 1 linear    ← correct
// @param gain 0.5 0 1 unipolar  ← THROWS
// @param gain 0.5               ← correct (unipolar default)
```

### Processor class format

State variables must be **class fields**, NOT standalone `let`:

```js
// CORRECT
class Processor {
  gain = 0.5
  drive = 0.3
  paramChanged(name, value) { if (name === "gain") this.gain = value }
  processAudio(inputs, outputs) { /* ... */ }
}

// WRONG — "Unexpected identifier" error
class Processor { /* ... */ }
let gn = 0.5;  // ← crashes: unreachable after IIFE return
```

### Advantages over custom parser

1. **Declaration caching** (WeakMap) — identical `@param` blocks don't recreate WerkstattParameterBox
2. **Proper sample cleanup** — orphaned AudioFileBox references cleaned correctly
3. **Label parsing** — `// @label My Effect` sets device label
4. **Correct worklet wrapping** — uses exact same `wrapCode()` + `registerWorklet()` as studio app
5. **Internal editing.modify()** — compiler scopes mutations correctly

### E2E verified 2026-07-04

3 params (gain=0.5, drive=0.3, tone=0.8) created, `set_script_param("gain", 0.85)` works, `get_script_device_code` returns code with `// @werkstatt js 1 1` header.

---

## Stems Export Fix

### Bug

`export_stems` and `export_single_stem` had `useInstrumentOutput: True`. This rendered DRY stems (raw instrument output, no effects/channel strip) despite docstrings saying "effects included".

### Root cause confusion

naomiaro/opendaw-test documentation clarifies:
- `useInstrumentOutput: false` → routes through **channel strip** (effects, sends, volume/pan all reach render) — this is what "stems with effects" means
- `useInstrumentOutput: true` → taps **dry instrument output** BEFORE effects/channel strip

### Fix

Changed `True → False` in both `export_stems` and `export_single_stem`.

### New tool: `export_dry_stem` (#244)

For freeze/flatten/re-amp workflows that specifically need raw instrument signal:
```python
stems_map[uuid] = {
    "includeAudioEffects": False,
    "includeSends": False,
    "useInstrumentOutput": True,   # dry instrument output
    "fileName": filename
}
```

---

## add_effect case-insensitive

`EffectFactories.AudioNamed` keys are Capitalized (`Werkstatt`, `Compressor`). Lowercase input (`"werkstatt"`) returned "factory not found". Fix:

```js
const factory = ef.AudioNamed[effectType] 
  || ef.AudioNamed[effectType.charAt(0).toUpperCase() + effectType.slice(1)];
```

Error message now lists available factories.

---

## naomiaro/opendaw-test as SDK reference

`github.com/naomiaro/opendaw-test` (543 commits) is the most comprehensive SDK documentation:

- **17 chapters**: Quick Start → System Architecture → Timing → AnimationFrame → Box System → Samples → Timeline → Building App → Recording → Editing → Export → Effects → MIDI → Modular → Time & Pitch → Browser Compat → Troubleshooting → Performance → Glossary
- **Demo code**: `src/demos/` — every concept has a runnable demo
- **CLAUDE.md**: SDK patterns, pitfalls, workflow conventions, PR review checklist
- **Key files**: `src/lib/projectSetup.ts` (init template), `src/lib/audioUtils.ts`, `documentation/10-export.md`, `documentation/11-effects.md`
- **Claude skill**: `.claude/skills/audio-verify/` — automated offline render + beat alignment testing

When in doubt about an SDK API, check naomiaro first.
