# Scriptable Devices

5 tools for controlling user-scriptable DSP devices: Apparat (instrument), Werkstatt (audio effect), Spielwerk (MIDI effect).

## Scriptable Devices (5)

| Tool | Description |
|------|-------------|
| `set_script_device_code` | Set user JavaScript code on a scriptable device. **Compiles** via ScriptCompiler |
| `get_script_device_code` | Read the current user JavaScript code from a scriptable device |
| `list_script_params` | List `@param` declarations with full mapping info (min/max/type/unit) |
| `set_script_param` | Set a parameter value with range validation (clamps, rounds, snaps bool) |
| `list_script_samples` | List `@sample` declaration slots on a scriptable device |

## Device types

| Device | Type | Factory | Header tag |
|--------|------|---------|------------|
| **Apparat** | Instrument | `InstrumentFactories.Apparat` | `@apparat` |
| **Werkstatt** | Audio effect | `EffectFactories.Werkstatt` | `@werkstatt` |
| **Spielwerk** | MIDI effect | `EffectFactories.Spielwerk` | `@spielwerk` |

## How it works

`set_script_device_code` doesn't just write the code string — it **compiles** it:

1. **Parse `@param` declarations** → create `WerkstattParameterBox` for each (label, index, value, defaultValue)
2. **Parse `@sample` declarations** → create `WerkstattSampleBox` for each (label, index, file slot)
3. **Validate JavaScript** via `new Function()`
4. **Register AudioWorklet** through ScriptCompiler
5. All within a single `editing.modify()` transaction

### Script header format

```javascript
// @werkstatt myEffect 1 1
// @param {float} gain 0.5 0 1 "Gain"
// @param {float} drive 0.3 0 1 "Drive"
// @param {bool} bypass false "Bypass"
// @sample kick "Kick drum"
// @sample snare "Snare drum"

function processAudio(inputs, outputs, parameters) {
    // DSP code here
    // inputs: Float32Array[][], outputs: Float32Array[][]
    // parameters: { name: Float32Array }
}
```

### `@param` syntax

```
// @param {type} name defaultValue min max "label"
```

| Type | Behavior |
|------|----------|
| `float` | Continuous 0..1 (or min..max) |
| `int` | Integer, rounded |
| `bool` | Boolean, snapped to true/false |

### `@sample` syntax

```
// @sample name "label"
```

Creates a sample slot that can be loaded with audio files via the UI or `list_script_samples`.

## Processor API

Werkstatt (audio effect) processors implement:

| Method | Description |
|---------|-------------|
| `processAudio(inputs, outputs, parameters)` | Audio processing callback |
| `paramChanged(name, value)` | Called when a parameter changes |
| `this.sampleRate` | Audio sample rate (44100 or 48000) |
| `this.blockSize` | Audio processing block size (128) |

## Example: tape saturation

```python
# Read a DSP script
with open("scripts/werkstatt_darksat.js") as f:
    code = f.read()

# Add a Werkstatt effect and load the script
await server.mcp_opendaw_add_effect(unit_index=0, effect_type="Werkstatt")

# Compile the code into the device
await server.mcp_opendaw_set_script_device_code(
    unit_index=0, effect_index=0, code=code
)

# List created parameters
params = await server.mcp_opendaw_list_script_params(
    unit_index=0, effect_index=0
)
# [
#   {"name": "drive", "value": 0.0, "default": 0.0, "min": 0, "max": 1},
#   {"name": "bias",  "value": 0.0, "default": 0.0, "min": -0.5, "max": 0.5},
#   {"name": "tone",  "value": 0.5, "default": 0.5, "min": 0, "max": 1},
#   {"name": "mix",   "value": 1.0, "default": 1.0, "min": 0, "max": 1},
#   {"name": "output","value": 0.0, "default": 0.0, "min": -24, "max": 6}
# ]

# Tweak parameters
await server.mcp_opendaw_set_script_param(
    unit_index=0, effect_index=0, param_name="drive", value=0.7
)
await server.mcp_opendaw_set_script_param(
    unit_index=0, effect_index=0, param_name="tone", value=0.3
)
```

→ See [DSP Scripts](../dsp-scripts.md) for the full collection of 26 ready-made scripts.
