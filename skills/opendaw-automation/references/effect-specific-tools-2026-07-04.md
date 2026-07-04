# Effect-Specific Tools + ScriptCompiler Migration (2026-07-04)

Session findings from researching naomiaro/opendaw-test (543 commits, 17 SDK doc chapters) and adding 4 new MCP tools (244→247).

## New tools added

1. **`export_dry_stem(unit_index, filename, sample_rate=48000)`** — Captures raw instrument output before effects/channel strip. `useInstrumentOutput: True`, `includeAudioEffects: False`, `includeSends: False`. For freeze/flatten/re-amp workflows. Uses `OfflineEngineRenderer.start(project.copy(), Option.wrap(exportConfig), ...)`.

2. **`set_waveshaper_equation(unit_index, effect_index, equation)`** — Sets transfer function on Waveshaper effect. 6 equations: hardclip, cubicSoft, tanh, sigmoid, arctan, asymmetric. `box.equation.setValue("tanh")` inside `editing.modify()`. E2E: hardclip→tanh ✅.

3. **`set_crusher_crush(unit_index, effect_index, crush)`** — Sample-rate reduction. Crush value 0-1 is inverted internally (`setCrush(1.0 - value)`). 0.0=clean 20kHz, 0.25=AM radio 3.5kHz, 0.55=glitchy 500Hz, 1.0=inaudible 20Hz. E2E: 0→0.25 ✅.

4. **`set_revamp_filter(unit_index, effect_index, section, enabled, frequency, gain, q, order)`** — Configure 7 EQ sections: highpass, lowshelf, lowbell, midbell, highbell, highshelf, lowpass. E2E: HPF 80Hz order 2, midbell 2kHz -3dB Q1.5, lowshelf 120Hz +2dB, lowpass 8kHz order 3 — all ✅.

## Critical: adapter vs box access for effect-specific tools

`au.audioEffects.adapters()` (adapter-level) does NOT see effects created in previous `evaluate()` calls — Yjs sync doesn't refresh adapter collections across evaluate boundaries.

**Use box-level access instead:**
```javascript
const au = h.auBox(unit_index);    // box, not adapter
const fx = h.effectBoxes(au);      // box-level effect list
const box = fx[effect_index];      // direct box access
box.equation.setValue("tanh");     // works across evaluate calls
```

**DO NOT use adapter-level for effect tools:**
```javascript
const au = h.au(unit_index);              // adapter
const fx = au.audioEffects.adapters();    // STALE — doesn't see new effects
const box = fx[effect_index].box;         // undefined if effect was added in prev eval
```

The pre-existing `set_crusher_bits` tool used adapter-level access and only worked when tested in a single evaluate block. All 3 new effect tools (`set_waveshaper_equation`, `set_crusher_crush`, `set_revamp_filter`) use box-level access from the start.

## Critical: Revamp box field names are camelCase

The forge-boxes schema defines RevampDeviceBox sections with kebab-case names:
```typescript
10: {type: "object", name: "high-pass", class: Pass},
11: {type: "object", name: "low-shelf", class: Shelf},
// ...
```

But the generated box class exposes them as **camelCase** on the prototype:
```javascript
Object.getPrototypeOf(rvBox).getOwnPropertyNames(proto)
// → ["highPass", "lowShelf", "lowBell", "midBell", "highBell", "highShelf", "lowPass", ...]
```

Access pattern:
```javascript
const hpf = box.highPass;    // ✓ camelCase
const hpf = box["high-pass"]; // ✗ undefined
```

Each section sub-object has:
- `.enabled` (BooleanField)
- `.frequency` (Float32Field, 20-20000 Hz, exponential)
- `.gain` (Float32Field, -24 to 24 dB) — shelves and bells only
- `.q` (Float32Field, 0.01-10) — bells and LPF only
- `.order` (Int32Field, 1-4) — HPF and LPF only

Section type mapping:
| Section name | Box field | Type | Has gain? | Has q? | Has order? |
|---|---|---|---|---|---|
| highpass | highPass | Pass | no | no | yes |
| lowshelf | lowShelf | Shelf | yes | no | no |
| lowbell | lowBell | Bell | yes | yes | no |
| midbell | midBell | Bell | yes | yes | no |
| highbell | highBell | Bell | yes | yes | no |
| highshelf | highShelf | Shelf | yes | no | no |
| lowpass | lowPass | Pass | no | no | yes |

## ScriptCompiler @param mapping values

Official `ScriptCompiler` from `@opendaw/studio-adapters` accepts these mappings in `@param` declarations:

- `linear` — linear scaling
- `exp` — exponential (for frequency/time)
- `int` — integer
- `bool` — boolean

**`unipolar` is NOT a valid explicit mapping.** It's the DEFAULT when only name+value are given:
- `// @param gain` → unipolar 0-1, default 0
- `// @param gain 0.5` → unipolar 0-1, default 0.5
- `// @param gain 0.5 0 1 unipolar` → **THROWS**: `unknown mapping 'unipolar'`
- `// @param gain 0.5 0 1 linear` → ✓ correct for 0-1 range

Source: `ScriptDeclaration.ts` line 43: `VALID_MAPPINGS = ["linear", "exp", "int", "bool"]`

## ScriptCompiler.compile() calls editing.modify() internally

The official `ScriptCompiler.create(config).compile(ctx, editing, box, source)` handles BOTH the `editing.modify()` transaction AND worklet registration in one call.

**Do NOT wrap compile() in your own editing.modify()** — it does that internally (ScriptCompiler.ts line 196: `editing.modify(modifier)`).

Compile flow:
1. `parseHeader(source)` → strips `// @werkstatt js 1 N` header
2. `ScriptDeclaration.parseParams(userCode)` → param declarations
3. `ScriptDeclaration.parseSamples(userCode)` → sample declarations
4. `wrapCode(config, uuid, newUpdate, userCode)` → IIFE wrapper
5. `validateCode(wrappedCode)` → `new Function(wrappedCode)` syntax check
6. `editing.modify(modifier)` — sets code + reconciles params/samples
7. `registerWorklet(audioContext, wrappedCode)` — blob URL + `audioWorklet.addModule`

Config per device type:
```javascript
const configs = {
    werkstatt: {headerTag: "werkstatt", registryName: "werkstattProcessors", functionName: "werkstatt"},
    apparat: {headerTag: "apparat", registryName: "apparatProcessors", functionName: "apparat"},
    spielwerk: {headerTag: "spielwerk", registryName: "spielwerkProcessors", functionName: "spielwerk"},
};
```

DAW_ScriptCompiler global added to headless-daw/main.ts: `w.DAW_ScriptCompiler = adapters.ScriptCompiler`

## Stems export useInstrumentOutput fix

`useInstrumentOutput` semantics (confirmed by naomiaro/opendaw-test docs):

- **`false`** = route through channel strip (effects, sends, volume, pan all applied) — THIS IS WHAT YOU WANT for stems with effects
- **`true`** = tap dry instrument output before any effects/channel strip — for freeze/flatten/re-amp

Previous code had `useInstrumentOutput: True` in `export_stems` and `export_single_stem` — stems were rendering DRY despite docstring saying "effects included". Fixed to `False`. New `export_dry_stem` tool added for the dry use case.

## naomiaro/opendaw-test as SDK reference

URL: `https://github.com/naomiaro/opendaw-test` (543 commits)

17 documentation chapters in `documentation/`:
- quick-start, 00-system-architecture, 01-introduction, 02-timing-and-tempo, 03-animation-frame, 04-box-system-and-reactivity, 05-samples-peaks-and-looping, 06-timeline-and-rendering, 07-building-a-complete-app, 08-recording, 09-editing-fades-and-automation, 10-export, 11-effects, 12-browser-compat, 13-troubleshooting, 14-glossary, 15-performance-debugging, 16-midi, 17-modular-devices, 18-time-and-pitch

Plus: demo code for each concept (`src/demos/`), SDK changelogs (`changelogs/`), Claude `audio-verify` skill (`.claude/skills/audio-verify/`).

**This is the best reference for openDAW SDK patterns** — better than reading source code alone. Key reference files: `src/lib/projectSetup.ts` (initialization), `src/lib/audioUtils.ts` (format detection, file loading), `src/demos/effects/werkstatt-demo.tsx` (ScriptCompiler usage), `src/demos/export/export-demo.tsx` (OfflineEngineRenderer patterns).

## Effect factory case-insensitive lookup

`EffectFactories.AudioNamed` uses PascalCase keys: `Werkstatt`, `Compressor`, `DattorroReverb`, etc. The `add_effect` tool now accepts case-insensitive input via fallback: `ef.AudioNamed[effectType] || ef.AudioNamed[effectType.charAt(0).toUpperCase() + effectType.slice(1)]`. So both `werkstatt` and `Werkstatt` work.

## naomiaro upstream plans of interest

André Michelle's plans (in openDAW `plans/` directory, 60 files) that could become future MCP tools:
- **flatten-audio-regions** — consolidate audio regions via offline render + sample import
- **freeze-audiounit** — already covered by our freeze/unfreeze tools
- **match-tempo** — `/tap` page, sliding-window OLS BPM estimation
- **waveshaper-device** — already implemented upstream, we have `set_waveshaper_equation`
- **vocoder** — already implemented upstream, accessible via generic effect params
- **code-fx** — scriptable FX chain, future scriptable device
