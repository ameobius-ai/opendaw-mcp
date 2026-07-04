# openDAW Effect Parameter Reference

## How Parameters Work

Effect parameters are `Float32Field` / `StringField` / `BooleanField` on the effect Box.
Adapter layer wraps them in `AutomatableParameterFieldAdapter` with `ValueMapping` (min/max/unit) and `StringMapping`.

Set values: `p.editing.modify(() => { effectBox.inputGain.setValue(12.0); })`
Get values: `effectBox.inputGain.getValue()`

## MCP Tools (server.py)

| Tool | Purpose |
|------|---------|
| `mcp_opendaw_add_effect(unit_idx, effect_type)` | Add effect, returns effect_index |
| `mcp_opendaw_list_effect_parameters(unit_idx, effect_idx)` | Discover all params |
| `mcp_opendaw_set_effect_parameter(unit_idx, effect_idx, name, value)` | Set numeric param |
| `mcp_opendaw_set_effect_parameter_string(unit_idx, effect_idx, name, str)` | Set string param |
| `mcp_opendaw_remove_effect(unit_idx, effect_idx)` | Remove effect |
| `mcp_opendaw_get_effect_chain(unit_idx)` | List full chain |

## Parameters by Effect Type

### Waveshaper
| Param | Type | Range | Default | Notes |
|-------|------|-------|---------|-------|
| equation | string | hardclip/tanh/cubicSoft/sigmoid/arctan/asymmetric | hardclip | ⚠️ hardclip at 0dB inputGain = no-op on sub-0dBFS audio |
| inputGain | float | 0-40 dB | 0 | Set +6 to +12 for distortion |
| outputGain | float | -24 to 24 dB | 0 | |
| mix | float | 0-1 (unipolar) | 1 | 1=100% wet |

### Tidal (tremolo/panner)
| Param | Type | Range | Default |
|-------|------|-------|---------|
| depth | float | 0-1 | 1.0 |
| slope | float | 0-1 | 0.0 |
| symmetry | float | 0-1 | 0.0 |
| rate | int | index into RateFractions | 0 |
| offset | float | 0-360° | 0 |
| channelOffset | float | 0-360° | 0 |

### Delay
| Param | Type | Range | Default |
|-------|------|-------|---------|
| delay | int | fraction index | 0 |
| millisTime | float | ms | 0 |
| preSyncTimeLeft/Right | int | fraction index | 0 |
| preMillisTimeLeft/Right | float | ms | 0 |
| feedback | float | 0-1 | 0 |
| cross | float | 0-1 | 0 |
| lfoSpeed | float | Hz | 0 |
| lfoDepth | float | ms | 0 |
| filter | float | -1 to 1 | 0 |
| wet | float | dB | -inf |
| dry | float | dB | 0 |

### DattorroReverb
| Param | Type | Range | Default |
|-------|------|-------|---------|
| preDelay | float | 0.001-0.5 s | |
| bandwidth | float | 0-1 | |
| inputDiffusion1 | float | 0-1 | |
| inputDiffusion2 | float | 0-1 | |
| decay | float | 0-1 | |
| decayDiffusion1 | float | 0-1 | |
| decayDiffusion2 | float | 0-1 | |
| damping | float | 0-1 | |
| excursionRate | float | 0-1 | |
| excursionDepth | float | 0-1 | |
| wet | float | dB | |
| dry | float | dB | |

### Revamp (7-band EQ)
7 bands: highPass, lowShelf, lowBell, midBell, highBell, highShelf, lowPass
Each band has: `enabled` (bool), `frequency` (Hz), `gain` (dB, where applicable), `q` (where applicable), `order` (int, HP/LP only)

### Compressor
| Param | Type | Range | Default |
|-------|------|-------|---------|
| threshold | float | dB | -10 |
| ratio | float | 1-∞ | 2.0 |
| knee | float | dB | 6.0 |
| attack | float | ms | 2.0 |
| release | float | ms | 140.0 |
| makeup | float | dB | 0.0 |
| mix | float | 0-1 | 1.0 |
| inputgain | float | dB | 0.0 |
| lookahead | bool | | false |
| automakeup | bool | | false |
| autoattack | bool | | false |
| autorelease | bool | | false |

## Parameter Architecture (Deep)

```
EffectBox (e.g. WaveshaperDeviceBox)
  └── Float32Field (e.g. inputGain)
       └── getValue() / setValue() — direct field access

WaveshaperDeviceBoxAdapter
  └── namedParameter = {
      inputGain: ParameterAdapterSet.createParameter(
          box.inputGain,
          ValueMapping.linear(0.0, 40.0),   // unitValue ↔ dB
          StringMapping.decible,              // display format
          "Input"                             // UI label
      )
  }

AutomatableParameterFieldAdapter
  ├── getValue() / setValue(value)     — direct
  ├── getUnitValue() / setUnitValue(0-1) — mapped
  ├── getPrintValue() / setPrintValue(text) — string
  └── valueAt(position) — with automation track
```
