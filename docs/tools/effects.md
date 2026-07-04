# Effects & MIDI Effects

32 tools for audio effects, MIDI effects, and device-specific parameters.

## Audio Effects (17)

| Tool | Description |
|------|-------------|
| `add_effect` | Add an audio effect to an AU's effect chain |
| `clone_effect_chain` | Copy all effects from one AU to another, including parameters |
| `connect_sidechain` | Connect one AU's output as sidechain source to a Compressor/Gate |
| `duplicate_effect` | Duplicate a single effect within an AU's chain |
| `export_effect_chain` | Export an effect chain as base64 preset |
| `get_effect_chain` | Get the full effect chain for an AU |
| `get_effect_state` | Full state of an effect: enabled, minimized, sidechain, all parameters |
| `list_effect_parameters` | List all parameters of an effect with current values |
| `list_effects` | List all available audio and MIDI effect types |
| `move_effect` | Reorder an effect within an AU's chain |
| `remove_effect` | Remove an audio effect from an AU's chain |
| `set_device_label` | Rename an effect or MIDI effect device |
| `set_effect_enabled` | Enable or bypass a specific effect |
| `set_effect_parameter` | Set a parameter on an audio effect |
| `set_effect_parameter_bool` | Set a boolean parameter on an audio effect |
| `set_effect_parameter_int` | Set an integer parameter on an audio effect |
| `set_effect_parameter_string` | Set a string parameter (e.g. Waveshaper equation) |

## MIDI Effects (6)

| Tool | Description |
|------|-------------|
| `add_midi_effect` | Add a MIDI effect to an AU's MIDI effect chain |
| `get_midi_effect_chain` | Get the MIDI effect chain for an AU |
| `list_midi_effect_params` | List all parameters of a MIDI effect with current values |
| `list_midi_effects` | List all available MIDI effect types |
| `remove_midi_effect` | Remove a MIDI effect from an AU's MIDI chain |
| `set_midi_effect_param` | Set a parameter on a MIDI effect |

### Available MIDI effects

- **Arpeggio** — Arpeggiator
- **Pitch** — Pitch shifter
- **Spielwerk** — Scriptable MIDI effect
- **Velocity** — Velocity processor
- **Zeitgeist** — Time manipulation

## Device-Specific Parameters (14)

| Tool | Description |
|------|-------------|
| `list_vaporisateur_params` | Full Vaporisateur state: oscillators, LFO, noise, main params |
| `set_crusher_bits` | Set bit depth on a Crusher (bitcrusher) |
| `set_crusher_crush` | Set sample-rate reduction (0=clean, 1=max) |
| `set_fold_oversampling` | Set oversampling level on a Fold (wavefolding) |
| `set_stereo_tool_panning` | Set panning mode on a StereoTool |
| `set_waveshaper_equation` | Set transfer function (hardclip/cubicSoft/tanh/sigmoid/arctan/asymmetric) |
| `set_revamp_filter` | Configure a filter on Revamp EQ (highpass/lowshelf/lowbell/midbell/highbell/highshelf/lowpass) |
| `set_tidal_rate` | Set Tidal LFO rate using musical fraction (1/1, 1/2, 1/4, 1/8, 1/16) |
| `set_delay_sync` | Set Delay synced time (off, 1/128, 1/16, 1/8, 1/4, 1/2, 1/1) |
| `set_time_stretch_cents` | Set pitch shift (cents) on a time-stretched audio region |
| `set_vaporisateur_osc_param` | Set a parameter on a Vaporisateur oscillator |
| `set_vocoder_band_count` | Set band count on a Vocoder (8-32) |
| `set_vocoder_modulator_source` | Set modulator source on a Vocoder |

### Waveshaper equations

```
hardclip      — hard clipping distortion
cubicSoft     — soft cubic saturation
tanh          — hyperbolic tangent
sigmoid       — sigmoid curve
arctan        — arctangent curve
asymmetric    — asymmetric clipping
```

### Available audio effects

Delay, Dattorro (reverb), Compressor, Waveshaper, Fold, Crusher, StereoTool,
Revamp (EQ), Tidal (LFO), Vocoder, Modulator, NeuralAmp, Maximizer, Modular,
Werkstatt, and more. Use `list_effects` to see all available types.
