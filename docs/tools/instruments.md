# Instruments & Synths

4 tools for instrument parameter management.

## Instruments (4)

| Tool | Description |
|------|-------------|
| `list_automatable_fields` | List all automatable parameter fields on an instrument (or Playfield sample) |
| `list_instrument_params` | List all parameters of the instrument connected to an AU |
| `replace_instrument` | Replace the instrument on an AU with a different MIDI instrument |
| `set_instrument_param` | Set a parameter on the instrument connected to an AU |

## Available instruments

| Instrument | Description |
|------------|-------------|
| **Vaporisateur** | Subtractive synthesizer — 3 oscillators, LFO, noise, filter, envelope |
| **Tape** | Tape-based sampling instrument |
| **Soundfont** | SoundFont playback — preset selection by index |
| **Playfield** | Drum machine — sample pads, sequencing |
| **Apparat** | Scriptable instrument — custom JS audio synthesis |

## Vaporisateur parameters

The Vaporisateur synth has 23 controllable parameters across oscillators, LFO, noise, and main section:

- **Oscillators (per-osc):** waveform (0=Sine, 1=Triangle, 2=Saw, 3=Square), volume, octave, tune
- **LFO:** rate, depth, target
- **Noise:** volume, type
- **Main:** volume, glide, filter cutoff, filter resonance, attack, decay, sustain, release

Use `list_instrument_params` to see all available parameters for the current instrument.
Use `set_instrument_param` or `set_vaporisateur_osc_param` to modify them.

## Example

```python
# Create a synth and tweak it
result = await server.mcp_opendaw_create_synth_track(name="Pad")
au = result["unit_index"]

# List available params
params = await server.mcp_opendaw_list_instrument_params(unit_index=au)

# Set filter cutoff
await server.mcp_opendaw_set_instrument_param(
    unit_index=au, param_name="filterCutoff", value=0.7
)

# Change oscillator 1 waveform to saw
await server.mcp_opendaw_set_vaporisateur_osc_param(
    unit_index=au, osc_index=1, param="waveform", value=2
)
```
