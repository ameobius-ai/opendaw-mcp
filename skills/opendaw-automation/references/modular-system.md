# Modular System — openDAW's Patchable Modular Synthesizer

## Overview

openDAW has a built-in modular synthesizer system (`ModularDeviceBox`) that lives inside an audio effect slot. It's marked "inaudible yet" in EffectFactories (defaultName: "🔇 Create New Modular Audio Effect (inaudible yet)") — the DSP layer is not yet wired to produce sound, but the entire adapter/box layer is fully functional for patch construction, parameter control, and connection management.

**E2E verified 2026-07-03**: AU+Modular created, gain+delay modules added, input→gain→delay patched, gain set to -6dB, delay set to 250ms, delay module removed. All 7 MCP tools pass.

## Architecture

```
ModularDeviceBox (audio effect)
  └─ modularSetup → ModularBox
       ├─ modules (PointerHub, Pointers.ModuleCollection)
       │    ├─ ModuleGainBox       — VCA, gain param (dB)
       │    ├─ ModuleDelayBox      — delay, time param (ms, 1-10000)
       │    ├─ ModuleMultiplierBox — X × Y → Result, 2 inputs
       │    ├─ ModularAudioInputBox  — entry point, 0 inputs → 1 output
       │    └─ ModularAudioOutputBox — exit point, 1 input → 0 outputs
       └─ connections (PointerHub, Pointers.ConnectionCollection)
            └─ ModuleConnectionBox — source field → target field
```

## Module connector specs

| Module | Inputs | Outputs | Parameters |
|--------|--------|---------|------------|
| Gain | Input (voltageInput) | Output (voltageOutput) | gain (dB, ValueMapping.DefaultDecibel) |
| Delay | Input (voltageInput) | Output (voltageOutput) | time (ms, exponential 1-10000) |
| Multiplier | X (voltageInputX), Y (voltageInputY) | Result (voltageOutput) | none |
| AudioInput | none | Output | none |
| AudioOutput | Input | none | none |

## Key adapter classes

- `ModularDeviceBoxAdapter` — `effects[j].modular()` returns `ModularAdapter`. Check via `effects[j].box instanceof ModularDeviceBox`.
- `ModularAdapter` — `.modules` (ReadonlyArray<ModuleAdapter>), `.connections` (ReadonlyArray<ModuleConnectionAdapter>), `.box.modules` / `.box.connections` (PointerHubs for refer).
- `ModuleAdapter` (abstract) — `.attributes` (label, x, y), `.namedParameter` (params dict, **may be undefined** — see pitfalls), `.inputs` / `.outputs` (ModuleConnectorAdapter[]).
- `ModuleConnectorAdapter` — `.name` ("Output", "Input", "X", "Y", "Result"), `.field` (the PointerField to connect), `.address`.
- `ModuleConnectionAdapter` — `.source` (Vertex), `.target` (Vertex).

## Creating modules (JS pattern)

```javascript
const BoxClass = window.DAW_ModuleGainBox; // or DAW_ModuleDelayBox, etc.
const graph = p.boxGraph;  // NOT p.project.boxGraph — p.project is undefined!
const uuid = window.DAW_UUID.generate();
p.editing.modify(() => {
    BoxClass.create(graph, uuid, (box) => {
        box.attributes.collection.refer(modular.box.modules);
        box.attributes.label.setValue("My Gain");
        box.attributes.x.setValue(0);
        box.attributes.y.setValue(0);
    });
});
```

## Creating connections (JS pattern)

```javascript
const srcOutput = srcMod.outputs.find(c => c.name === "Output");
const tgtInput = tgtMod.inputs.find(c => c.name === "Input");
p.editing.modify(() => {
    window.DAW_ModuleConnectionBox.create(graph, uuid, (box) => {
        box.collection.refer(modular.box.connections);
        box.source.refer(srcOutput.field);
        box.target.refer(tgtInput.field);
    });
});
```

## Setting module parameters — THREE fallback strategies

**CRITICAL: `m.namedParameter` is undefined on ModuleGainAdapter/ModuleDelayAdapter.** The `namedParameter` property exists on AudioUnit/Effect adapters but NOT on module adapters. Use one of these three fallbacks in order:

### Strategy 1: Direct box field (most reliable)
```javascript
const gainField = module.box.gain;  // Float32Field
const oldVal = gainField.getValue();  // 0 (default)
p.editing.modify(() => {
    gainField.setValue(-6.0);  // -6 dB
});
// gainField.getValue() → -6, gainField.unit → "dB"
```

### Strategy 2: Adapter getter (parameterGain, parameterTime)
```javascript
const param = module.parameterGain;  // AutomatableParameterFieldAdapter
p.editing.modify(() => {
    param.field.setValue(-6.0);
});
```

### Strategy 3: namedParameter (works on some adapters, NOT modules)
```javascript
const np = module.namedParameter;
if (np && np["gain"]) {
    p.editing.modify(() => { np["gain"].field.setValue(-6.0); });
}
```

The MCP tool `set_modular_module_param` tries all three in order: namedParameter → adapter getter (`parameterGain`) → direct box field (`m.box.gain`).

## Adding a Modular effect to an AU

**CRITICAL: `api.insertEffect` takes a FIELD, not a box.** And Modular is NOT in `AudioNamed`:

```javascript
// WRONG — gives "has no index field" error:
p.api.insertEffect(au.box, window.DAW_EffectFactories.Modular);

// WRONG — Modular not in AudioNamed:
const factory = window.DAW_EffectFactories.AudioNamed["Modular"]; // undefined!

// CORRECT:
const au = p.rootBoxAdapter.audioUnits.adapters()[0];
p.editing.modify(() => {
    p.api.insertEffect(au.box.audioEffects, window.DAW_EffectFactories.Modular);
});
```

## Auto-created on Modular device creation

When `EffectFactories.Modular.create()` runs, it automatically creates:
1. `ModularBox` (the modular setup)
2. `ModularAudioInputBox` (at x=-256, y=32, label "Modular Input")
3. `ModularAudioOutputBox` (at x=256, y=32, label "Modular Output")
4. `ModuleConnectionBox` connecting AudioInput.output → AudioOutput.input

So a fresh Modular device has 2 modules (input + output) and 1 connection.

**Module order is NOT guaranteed** — modules may appear in any order in `modular.modules`. Always find by type/name, don't assume index:
```javascript
const gainMod = modular.modules.find(m => m.box.name === "ModuleGainBox");
const inMod = modular.modules.find(m => m.box.name === "ModularAudioInputBox");
```

## Globals needed in headless-daw/src/main.ts

Box classes (from `@opendaw/studio-boxes`):
- `DAW_ModularBox`, `DAW_ModularDeviceBox`
- `DAW_ModuleGainBox`, `DAW_ModuleDelayBox`, `DAW_ModuleMultiplierBox`
- `DAW_ModuleConnectionBox`
- `DAW_ModularAudioInputBox`, `DAW_ModularAudioOutputBox`

Adapter classes (from `@opendaw/studio-adapters`):
- `DAW_ModularDeviceBoxAdapter`, `DAW_ModularAdapter`
- `DAW_ModuleConnectionAdapter`
- `DAW_ModuleGainAdapter`, `DAW_ModuleDelayAdapter`, `DAW_ModuleMultiplierAdapter`
- `DAW_ModularAudioInputAdapter`, `DAW_ModularAudioOutputAdapter`
- `DAW_Modules` (namespace with `adapterFor` and `isVertexOfModule`)

## MCP tools (185→192, session 2026-07-03)

| # | Tool | Purpose | E2E |
|---|------|---------|-----|
| 186 | list_modular_devices | Find all Modular effects in project | ✅ |
| 187 | list_modular_modules | List modules with type/label/position/inputs/outputs/params | ✅ 4 modules |
| 188 | list_modular_connections | List patch cables with source→target | ✅ 3 connections |
| 189 | add_modular_module | Add gain/delay/multiplier/audio-input/audio-output module | ✅ gain+delay added |
| 190 | connect_modular_modules | Connect output→input between modules | ✅ input→gain→delay |
| 191 | set_modular_module_param | Set module parameter (dB for gain, ms for delay) | ✅ -6dB, 250ms |
| 192 | remove_modular_module | Delete module + its connections | ✅ 4→3 modules |

## E2E test recipe

```python
# 1. Create AU (Vaporisateur synth)
p.editing.modify(() => {
    const cap = CaptureAudioBox.create(p.boxGraph, UUID.generate());
    const au = AudioUnitBox.create(p.boxGraph, UUID.generate(), (box) => {
        box.type.setValue(AudioUnitType.Instrument);
        box.collection.refer(p.rootBox.audioUnits);
        box.output.refer(p.primaryAudioBusBox.input);
        box.capture.refer(cap);
        box.index.setValue(0);
        box.volume.setValue(0.767835);
    });
    InstrumentFactories.Vaporisateur.create(p.boxGraph, au.input, "Synth", IconSymbol.Piano);
    p.api.createNoteTrack(au);
});

# 2. Add Modular effect
const au0 = p.rootBoxAdapter.audioUnits.adapters()[0];
p.editing.modify(() => {
    p.api.insertEffect(au0.box.audioEffects, EffectFactories.Modular);
});

# 3. Add Gain + Delay modules
# 4. Connect: AudioInput.Output → Gain.Input, Gain.Output → Delay.Input
# 5. Set gain to -6dB, delay to 250ms
# 6. Remove delay module
```

## Pitfalls

- **`m.namedParameter` is undefined on module adapters** — use `m.box.gain` / `m.box.time` (direct box fields) or `m.parameterGain` / `m.parameterTime` (adapter getters) instead.
- **`p.project` does not exist** — use `p.boxGraph` directly, not `p.project.boxGraph`.
- **`api.insertEffect` takes a field** — `au.box.audioEffects`, not `au.box`. Passing a box gives "has no index field" error.
- **Modular NOT in `AudioNamed`** — access via `EffectFactories.Modular` directly.
- **Module order not guaranteed** — always find by `m.box.name`, don't assume index 0 = audio-input.
- **`m.namedParameter` may be undefined** for modules without params (Multiplier, AudioInput, AudioOutput). Always check before accessing.
- **Module type string parsing** — `m.box.name` returns "ModuleGainBox" etc. Strip "Module"/"Modular"/"Box" and lowercase for clean type names.
