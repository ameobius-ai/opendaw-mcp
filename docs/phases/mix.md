# Mix Phase — Agent Guide

## When to use this phase
```
OPENDAW_MCP_MODE=phase
switch_phase("mix")
```

## Core workflow

### 1. Genre effects (one call)
```
add_genre_effects(genre="house", unit_index=-1)
```
37 genres with character-appropriate effect chains. Applies to all units if -1.

### 2. Individual effects
```
add_effect(effect_type="Compressor", unit_index=0)
set_effect_parameter(unit_index=0, effect_index=0, param_name="threshold", value=-20)
add_effect(effect_type="Reverb", unit_index=2)
add_effect(effect_type="Delay", unit_index=2)
```

### 3. Mixing
```
set_track_volume(unit_index=0, volume_db=-3.0)
set_track_panning(unit_index=2, pan=0.3)
apply_mix_preset(preset="balanced")
create_send(source_unit=2, dest_bus=0, amount=0.3)
```

### 4. Mastering chain
```
add_mastering_chain(style="balanced")
```
Styles: balanced, warm, loud, transparent

### 5. Adaptive mastering (one call)
```
auto_master(platform="spotify", style="balanced")
```
Platforms: spotify (-14 LUFS), apple (-16), youtube (-14), tidal (-14), soundcloud (-14), club (-8)
Chains: analyze → mastering chain → auto_gain → LUFS meter placement

### 6. Automation
```
add_automation(unit_index=0, param_name="volume", points=[[0,-3],[4,0],[8,-6]])
add_automation(unit_index=2, param_name="cutoff", points=[[0,200],[8,8000]])
```

### 7. Effect chains (genre-specific presets)
```
add_drum_chain(unit_index=0)      # comp + EQ + saturation
add_bass_chain(unit_index=1)      # comp + EQ + sub boost
add_vocal_chain(unit_index=3)     # comp + reverb + delay + de-esser
add_instrument_chain(unit_index=2)  # EQ + reverb + stereo widen
```

### 8. MIDI effects
```
add_midi_effect(effect_type="Arpeggio", unit_index=2)
add_midi_effect(effect_type="Spielwerk", unit_index=2)
```

### 9. Instrument parameters
```
list_instrument_params(unit_index=0)
set_instrument_param(unit_index=0, param_name="cutoff", value=0.7)
set_osc_param(unit_index=0, osc_index=0, param="waveform", value=2)
```

## Mastering chain
```
EQ → multiband_comp → SSL bus comp → true_peak_limiter → aire (air+width)
```

## Verification (after mastering)
Switch to inspect phase to read meters:
```
switch_phase("inspect")
read_meter()  # read LUFS from output
```

## Next phase
After mixing is done, switch to render:
```
switch_phase("render")
```
