# Mixing and Rendering via MCP (verified July 2026)

## Track Volume and Panning

```python
# Volume in dB (VolumeMapper.decibel(-96, -9, +6) powerByCenter)
await mcp_opendaw_set_track_volume(unit_index=0, volume_db=-3.0)

# Panning: -1.0 = full left, 0.0 = center, 1.0 = full right
await mcp_opendaw_set_track_panning(unit_index=0, panning=-0.2)  # L20
```

## Built-in Effect Parameter Names (verified July 2026)

### Delay (DelayDeviceBox)
| Parameter | Type | Default | Unit | Scaling |
|-----------|------|---------|------|---------|
| `delayMusical` | float | 13 | — | any (musical time) |
| `feedback` | float | 0.5 | % | unipolar |
| `cross` | float | 1 | % | unipolar |
| `filter` | float | 0 | % | bipolar |
| `wet` | float | -6 | dB | decibel |

**PITFALL**: Parameter is `delayMusical`, NOT `time`. Wet is in dB, NOT `mix` (0-1). Use `wet=-9` for ~30% mix.

### DattorroReverb (DattorroReverbDeviceBox)
| Parameter | Type | Default | Unit | Scaling |
|-----------|------|---------|------|---------|
| `preDelay` | float | 0 | ms | linear (0-1000) |
| `bandwidth` | float | 0.9999 | % | unipolar |
| `inputDiffusion1` | float | 0.75 | % | unipolar |
| `inputDiffusion2` | float | 0.625 | % | unipolar |
| `decay` | float | 0.5 | % | unipolar |
| `decayDiffusion1` | float | 0.7 | % | unipolar |
| `decayDiffusion2` | float | 0.5 | % | unipolar |
| `damping` | float | 0.999 | % | unipolar |
| `wet` | float | -6 | dB | decibel |

**PITFALL**: `wet` is in dB (not 0-1 mix). `decay=0.7` for long darksynth tail.

### Usage
```python
await mcp_opendaw_add_effect(effect_type="Delay", unit_index=lead_u)
await mcp_opendaw_set_effect_parameter(
    unit_index=lead_u, effect_index=1,  # after werkstatt at index 0
    parameter_name="delayMusical", value=13
)
await mcp_opendaw_set_effect_parameter(
    unit_index=lead_u, effect_index=1,
    parameter_name="feedback", value=0.35
)
await mcp_opendaw_set_effect_parameter(
    unit_index=lead_u, effect_index=1,
    parameter_name="wet", value=-9  # ~30% wet in dB
)
```

**PITFALL**: `set_effect_parameter` uses `parameter_name` (NOT `param_name`). Effect index is 0-based in the audio effects chain (excluding MIDI effects).

## Vaporisateur as Drum Synth

Vaporisateur can serve as kick/hat synth via `set_instrument_param` with `param_index`:

| Field Index | Parameter | For Kick | For Hat |
|-------------|-----------|----------|---------|
| 99 | osc1Waveform | 0 (sine) | 3 (square) |
| 23 | osc2Volume | 0.0 (off) | 0.0 (off) |
| 10 | volume (dB) | -3 | -18 |
| 14 | cutoff | 8000 (default) | 8000 |

```python
# Kick: sine wave, low pitch (C1=24), short notes
await mcp_opendaw_set_instrument_param(unit_index=kick_u, param_index=99, value=0)  # sine
await mcp_opendaw_set_instrument_param(unit_index=kick_u, param_index=23, value=0.0)  # osc2 off

# 4-on-floor pattern
for bar in range(8):
    if bar in [4, 5]:  # breakdown drop
        continue
    for beat in range(4):
        await mcp_opendaw_create_note(
            unit_index=kick_u, track_index=kick_t,
            pitch=24, start_beat=bar*4+beat,
            duration_beats=0.5, velocity=0.9
        )
```

**PITFALL**: `set_instrument_param` accepts `param_name` (string) OR `param_index` (int). Vaporisateur fields are numbered, not named — use `param_index` with values from `list_instrument_params`.

## New Upstream Effects (verified July 2026 post-sync)

### StereoTool (StereoToolDeviceBox)
| Parameter | Type | Default | Unit | Scaling |
|-----------|------|---------|------|---------|
| `volume` | float | 0 | dB | decibel (-72..+12) |
| `panning` | float | 0 | % | bipolar |
| `stereo` | float | 0 | % | bipolar (stereo width) |
| `invertL` | bool | false | — | — |
| `invertR` | bool | false | — | — |
| `swap` | bool | false | — | swap L/R |
| `panningMixing` | float | 1 | — | Linear=0, EqualPower=1 |

```python
await mcp_opendaw_add_effect(unit_index=0, effect_type='StereoTool')
await mcp_opendaw_set_effect_parameter(unit_index=0, effect_index=0, parameter_name='stereo', value=0.8)
```

### Waveshaper (WaveshaperDeviceBox)
| Parameter | Type | Default | Unit | Scaling |
|-----------|------|---------|------|---------|
| `equation` | string | "hardclip" | — | — |
| `inputGain` | float | 0 | dB | linear (0..40) |
| `outputGain` | float | 0 | dB | linear (-24..+24) |
| `mix` | float | 1 | % | unipolar |

**Equation values**: `hardclip`, `tanh`, `cubicSoft`, `sigmoid`, `arctan`, `asymmetric`. Set via `set_effect_parameter_string`:
```python
await mcp_opendaw_add_effect(unit_index=0, effect_type='Waveshaper')
await mcp_opendaw_set_effect_parameter_string(unit_index=0, effect_index=0, parameter_name='equation', string_value='tanh')
await mcp_opendaw_set_effect_parameter(unit_index=0, effect_index=0, parameter_name='inputGain', value=12.0)
```

### Vocoder (VocoderDeviceBox)
| Parameter | Type | Default | Unit | Scaling |
|-----------|------|---------|------|---------|
| `carrierMinFreq` | float | 100 | Hz | exponential (20..20000) |
| `carrierMaxFreq` | float | 12000 | Hz | exponential (20..20000) |
| `modulatorMinFreq` | float | 100 | Hz | exponential (20..20000) |
| `modulatorMaxFreq` | float | 12000 | Hz | exponential (20..20000) |
| `qMin` | float | 2 | — | exponential (1..60) |
| `qMax` | float | 20 | — | exponential (1..60) |
| `envAttack` | float | 5 | ms | exponential (0.1..100) |
| `envRelease` | float | 30 | ms | exponential (1..1000) |
| `gain` | float | 0 | dB | linear (-20..+20) |
| `mix` | float | 1 | % | unipolar |
| `bandCount` | int | 16 | — | 8..16 |
| `modulatorSource` | string | "noise-pink" | — | — |

**Modulator source values**: `noise-white`, `noise-pink`, `noise-brown`, `self`, `external`. When `external`, set sidechain via `connect_sidechain`.

**PITFALL: Box field names are camelCase, NOT kebab-case.** The schema file uses kebab-case (`carrier-min-freq`, `modulator-source`, `band-count`) but the compiled box fields are camelCase (`carrierMinFreq`, `modulatorSource`, `bandCount`). `set_effect_parameter` / `set_effect_parameter_string` access `effectBox[paramName]` directly — always use camelCase. The `list_effect_parameters` tool returns the correct camelCase names.

```python
await mcp_opendaw_add_effect(unit_index=0, effect_type='Vocoder')
await mcp_opendaw_set_effect_parameter_string(unit_index=0, effect_index=0, parameter_name='modulatorSource', string_value='noise-white')
await mcp_opendaw_set_effect_parameter(unit_index=0, effect_index=0, parameter_name='bandCount', value=12)
# External modulator: connect sidechain from another AU
await mcp_opendaw_connect_sidechain(source_unit_index=1, target_unit_index=0, effect_index=0)
```

### NeuralAmp (NeuralAmpDeviceBox — Tone3000 NAM)
| Parameter | Type | Default | Unit | Scaling |
|-----------|------|---------|------|---------|
| `modelJson` | string | "" | — | deprecated |
| `inputGain` | float | 0 | dB | decibel |
| `outputGain` | float | 0 | dB | decibel |
| `mono` | bool | true | — | — |
| `mix` | float | 1 | % | linear (0..1) |

**PITFALL: NAM model loading does NOT work in headless mode.** The Tone3000 select flow uses `window.open()` popup + localStorage events + redirect-based model browsing. In headless Chromium this is unavailable. Basic params (inputGain, outputGain, mono, mix) work fine via `set_effect_parameter`. The `model` pointer field (field 20) requires a `NeuralAmpModelBox` which can only be created through the popup flow.

## Audio Unit Duplication

```python
# Deep-copy AU: instrument + effects + notes + volume
await mcp_opendaw_duplicate_audiounit(unit_index=1)
# Returns: {success, source_unit_index, new_unit_index, instrument, effects_copied, tracks_copied, notes_copied}
```

**PITFALL**: This tool is Python-orchestrated (NOT a single JS block) because `capture.refer()` fails inside `editing.modify()`. See `references/au-duplication.md` for the full pitfall and architecture.

Effect box class → factory name mapping (used internally):
`DelayDeviceBox`→`Delay`, `ReverbDeviceBox`→`Reverb`, `CompressorDeviceBox`→`Compressor`, `DistortionDeviceBox`→`Distortion`, `ChorusDeviceBox`→`Chorus`, `PhaserDeviceBox`→`Phaser`, `NoiseGateDeviceBox`→`NoiseGate`, `TremoloDeviceBox`→`Tremolo`, `WerkstattDeviceBox`→`Werkstatt`, `SpielwerkDeviceBox`→`Spielwerk`, `StereoToolDeviceBox`→`StereoTool`, `WaveshaperDeviceBox`→`Waveshaper`, `VocoderDeviceBox`→`Vocoder`, `NeuralAmpDeviceBox`→`NeuralAmp`.

**PITFALL**: `Filter` and `Equalizer` were REMOVED from upstream `EffectFactories.AudioNamed` (verified July 2026). `VALID_EFFECTS` in server.py does NOT include them. The `fx_map` in `duplicate_audiounit` has them commented out. If you encounter `FilterDeviceBox` or `EqualizerDeviceBox` in an existing project, they will load but you cannot create new ones via `add_effect`.

## Rendering

### Mix export
```python
await mcp_opendaw_export_mix(
    filename="track_name",
    sample_rate=48000,
    method="auto"  # "offline" (fast) | "realtime" | "auto"
)
# Returns: {success, max_sample, duration_seconds, file_size_mb, saved_to, method}
```

**`max_sample` interpretation**:
- `0` = silence (check device compilation, wiring, note positions)
- `>1.0` = clipping (reduce track volumes)
- `0.85-0.95` = good headroom for mastering
- `None` = realtime render (no peak analysis)

### Stem export
```python
await mcp_opendaw_export_stems(
    filename_prefix="track_stem",
    sample_rate=48000
)
# Returns multichannel WAV: one channel per instrument AU
# File is LARGE (65MB for 5 stems × 40s @ 48kHz)
```

**PITFALL**: `export_stems` creates a single multichannel WAV (all stems in one file), NOT separate files. File size = num_stems × duration × sample_rate × 4 bytes. 5 stems × 40s = 65MB — too large for Discord (10MB limit). Use for local mixing only.

### Render silence debugging checklist
1. **Check `max_sample`** in export result — 0 means silence
2. **Apparat silence**: constructor must accept zero args → `constructor(opts)` not `constructor({sampleRate})`
3. **Werkstatt silence**: `process(io, block)` not `process(inputL, inputR, outputL, outputR, block)`
4. **Spielwerk silence**: arpeggiator must track `nextStepPos` across blocks (block ~5ppqn << rate 240ppqn)
5. **Worklet registration**: check `worklet_registered` and `worklet_error` in `set_script_device_code` result
6. **Update mismatch**: `device.code` header update number MUST match worklet registry update number
7. **Isolate**: test each device solo, then pair, then full chain to find which breaks

## Demo Track Pattern (darksynth, July 2026)

32-bar darksynth demo built entirely via MCP tools:

### Structure
| Bars | Bass | Lead | Pad | Kick | Hat |
|------|------|------|-----|------|-----|
| 1-4 | arp Cm pattern | melody phrase 1 | Cm chord sustain | 4-on-floor | off-beat 8ths |
| 5-6 | — (breakdown) | — | Cm sustain | — (drop) | — (drop) |
| 7-8 | arp return | melody phrase 2 | Cm sustain | 4-on-floor | off-beat 8ths |
| 9-16 | arp Cm pattern x2 | melody phrase 3+4 | Ab chord sustain | 4-on-floor | off-beat 8ths |

### Track chain
1. **Bass**: Apparat darkbass (saw, 150Hz, subOsc=0.8) → Spielwerk arp (1/8 up, 2 oct) → Werkstatt coldfold (drive=1.0, fold=0.4, crush=0.1, mix=0.5). -3dB center.
2. **Lead**: Apparat coldlead (triangle, 800Hz, release=0.8) → Werkstatt darksat (drive=0.4, tone=0.6, mix=0.7) → Delay (delayMusical=13, feedback=0.35, wet=-9dB). -5dB pan L20.
3. **Pad**: Vaporisateur (Cm: C3+Eb3+G3+C4, Ab: Ab2+C3+Eb3+F3) → Dattorro reverb (decay=0.7, wet=-6dB). -10dB pan R15.
4. **Kick**: Vaporisateur sine C1, 4-on-floor, dropped during breakdown. -4dB center.
5. **Hat**: Vaporisateur square C6, off-beat 8ths, dropped during breakdown. -12dB pan R30.

110 BPM, C minor. max_sample=0.871. Offline render, 48kHz stereo.
