# Drums & Modular

12 tools for the Playfield drum machine and the Modular system.

## Playfield / Drum Machine (5)

| Tool | Description |
|------|-------------|
| `copy_playfield_sample` | Copy a Playfield drum pad sample to a new index slot |
| `create_playfield_sample` | Add a drum pad to a Playfield drum machine |
| `list_playfield_samples` | List all drum pads (samples) on a Playfield |
| `reset_playfield_params` | Reset all parameters of a Playfield drum sample to defaults |
| `set_playfield_sample_enabled` | Enable/disable a drum pad on a Playfield |

### Creating a drum machine

```python
# Create a Playfield instrument
result = await server.mcp_opendaw_create_synth_track(name="Drums")
au_index = result["unit_index"]

# Replace the default instrument with Playfield
await server.mcp_opendaw_replace_instrument(
    unit_index=au_index, instrument_type="Playfield"
)

# Add drum pads
await server.mcp_opendaw_create_playfield_sample(
    unit_index=au_index, sample_index=0, name="Kick"
)
await server.mcp_opendaw_create_playfield_sample(
    unit_index=au_index, sample_index=1, name="Snare"
)
```

### Orchestration shortcut

Use `create_drum_pattern` for a full beat in one call:

```python
# x = hit, o = accent, . = rest, X = ghost
await server.mcp_opendaw_create_drum_pattern(
    pattern="x...x...x...x...|o.......o.....o.|..x...x...x...x.",
    unit_index=0
)
# Lanes: kick | snare | hihat
# Returns: {"total_notes": 10, "lanes": ["kick", "snare", "hihat"]}
```

## Modular System (7)

| Tool | Description |
|------|-------------|
| `add_modular_module` | Add a module to a Modular device |
| `connect_modular_modules` | Connect two modules (create a patch cable) |
| `list_modular_connections` | List all connections (patch cables) in a Modular device |
| `list_modular_devices` | List all Modular audio effect devices in the project |
| `list_modular_modules` | List all modules in a Modular device |
| `remove_modular_module` | Remove a module from a Modular device |
| `set_modular_module_param` | Set a parameter on a module in a Modular device |

### Modular workflow

```python
# Add a Modular effect to an AU
await server.mcp_opendaw_add_effect(unit_index=0, effect_type="Modular")

# Add modules
await server.mcp_opendaw_add_modular_module(
    unit_index=0, effect_index=0, module_type="Oscillator"
)
await server.mcp_opendaw_add_modular_module(
    unit_index=0, effect_index=0, module_type="Filter"
)

# Connect them: Oscillator output → Filter input
await server.mcp_opendaw_connect_modular_modules(
    unit_index=0, effect_index=0,
    source_module=0, source_port="output",
    dest_module=1, dest_port="input"
)

# Set filter cutoff
await server.mcp_opendaw_set_modular_module_param(
    unit_index=0, effect_index=0,
    module_index=1, param="cutoff", value=0.7
)
```

## Piano Mode (6)

| Tool | Description |
|------|-------------|
| `get_piano_mode` | Get piano roll view settings |
| `set_piano_keyboard` | Set the piano roll keyboard type |
| `set_piano_note_labels` | Toggle note labels (C, C#, D) in the piano roll |
| `set_piano_note_scale` | Set the piano roll note scale (vertical zoom) |
| `set_piano_time_range` | Set the piano roll time range (horizontal width in quarters) |
| `set_transpose` | Set global transpose for piano roll view (does not affect audio) |

## NeuralAmp (2)

| Tool | Description |
|------|-------------|
| `get_neuralamp_model` | Get the NeuralAmp (Tone3000) model JSON |
| `set_neuralamp_model` | Load a NAM/Tone3000 model JSON into a NeuralAmp effect |
