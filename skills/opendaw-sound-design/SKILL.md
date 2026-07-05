---
name: opendaw-sound-design
description: "openDAW instruments (Vaporisateur, Playfield, Nano, Tape, Soundfont, MIDIOutput) + scriptable DSP (Werkstatt audio effects, Apparat instruments, Spielwerk MIDI effects). 43 DSP scripts. How to synthesize and shape sound with MCP tools."
tags: [opendaw, mcp, sound-design, instruments, synth, dsp, werkstatt, apparat, spielwerk, scriptable]
---

# openDAW Sound Design

Инструменты и саунд-дизайн. Два слоя: встроенные инструменты (Vaporisateur/Playfield/Nano/Tape/Soundfont) и scriptable devices (Werkstatt/Apparat/Spielwerk — пользовательский JS DSP).

## Когда использовать

- Юзер просит синт, бас, лид, drum machine
- Нужно запрограммировать MIDI для конкретного инструмента
- Нужно создать кастомный DSP эффект/инструмент через scriptable device
- Нужно загрузить sample в Playfield (drum machine)
- Нужно управлять параметрами инструмента (cutoff, resonance, ADSR)

## Built-in Instruments

### Vaporisateur (polysynth)

Основной синтезатор. 2 осциллятора + LFO + noise + filter + ADSR.

```python
# Create
await mcp_opendaw_create_synth(unit_index, "Vaporisateur")
# or via create_instrument:
await mcp_opendaw_create_instrument(unit_index, "Vaporisateur")

# Oscillator params (per-osc: 0, 1)
await mcp_opendaw_set_osc_param(unit_index, osc_index, "waveform", value)  # 0=Sine, 1=Triangle, 2=Saw, 3=Square
await mcp_opendaw_set_osc_param(unit_index, osc_index, "volume", value)    # 0-1
await mcp_opendaw_set_osc_param(unit_index, osc_index, "octave", value)    # -2..+2
await mcp_opendaw_set_osc_param(unit_index, osc_index, "tune", value)      # -1..+1 (semitones)

# LFO/noise
await mcp_opendaw_list_osc_params(unit_index)
# Returns: oscillator params + LFO rate/depth + noise volume/color
```

| Waveform | Value | Character |
|----------|-------|-----------|
| Sine | 0 | Pure, soft, sub-bass |
| Triangle | 1 | Warm, flute-like |
| Saw | 2 | Bright, buzzy, leads |
| Square | 3 | Hollow, reedy, chiptune |

### Playfield (drum machine)

Sample-based drum sampler. Each pitch = a different sample slot.

```python
# Create with attachment (sample mapping)
await mcp_opendaw_create_instrument(unit_index, "Playfield", attachment_json)
# attachment_json = [{"pitch": 36, "file": "kick.wav"}, {"pitch": 38, "file": "snare.wav"}, ...]

# Or create empty and load samples individually
await mcp_opendaw_create_instrument(unit_index, "Playfield")
await mcp_opendaw_load_audio("kick.wav", "kick")
# Then attach to Playfield via bridge
```

**Pitfall:** `api.createInstrument(IF.Playfield, {attachment: [...]})` format. SampleClass.create() for each sample.

### Nano (basic synth)

Simple synth with volume + release.

```python
await mcp_opendaw_create_instrument(unit_index, "Nano")
await mcp_opendaw_set_instrument_param(unit_index, "volume", value)
await mcp_opendaw_set_instrument_param(unit_index, "release", value)
```

### Tape (tape playback)

Sample player with tape character (flutter, wow, noise, saturation).

```python
await mcp_opendaw_create_instrument(unit_index, "Tape")
await mcp_opendaw_set_instrument_param(unit_index, "flutter", value)   # 0-1
await mcp_opendaw_set_instrument_param(unit_index, "wow", value)       # 0-1
await mcp_opendaw_set_instrument_param(unit_index, "noise", value)     # 0-1
await mcp_opendaw_set_instrument_param(unit_index, "saturation", value) # 0-1
```

### Soundfont (SF2 player)

Loads SF2 soundfonts. Preset selection via index.

```python
await mcp_opendaw_create_instrument(unit_index, "Soundfont")
await mcp_opendaw_set_instrument_param(unit_index, "presetIndex", value)  # int
```

### MIDIOutput (external MIDI)

Routes MIDI to external devices.

```python
await mcp_opendaw_create_instrument(unit_index, "MIDIOutput")
await mcp_opendaw_set_instrument_param(unit_index, "channel", value)  # 0-15
```

### Universal instrument params

```python
# List all params for any instrument
await mcp_opendaw_list_instrument_params(unit_index)
# Returns: parameter names, current values, min/max, units

# Set any instrument param
await mcp_opendaw_set_instrument_param(unit_index, param_name, value)
```

| Instrument | Params |
|------------|--------|
| Vaporisateur | 23 fields (osc×2, LFO, noise, filter, ADSR) |
| Tape | flutter, wow, noise, saturation |
| Nano | volume, release |
| Soundfont | presetIndex |
| MIDIOutput | channel |

## Scriptable Devices (DSP Scripts)

Три типа устройств с пользовательским JS кодом:

| Device | Type | Input | Output | MIDI? |
|--------|------|-------|--------|-------|
| Werkstatt | Audio effect | Audio in | Audio out | NO |
| Apparat | Instrument | None (generates) | Audio out | YES (noteOn/noteOff) |
| Spielwerk | MIDI effect | MIDI in | MIDI out (yields) | YES (processes) |

### Creating scriptable devices

```python
# Add Werkstatt (audio effect)
await mcp_opendaw_add_effect(unit_index, "Werkstatt")

# Add Apparat (instrument)
await mcp_opendaw_create_instrument(unit_index, "Apparat")

# Add Spielwerk (MIDI effect)
await mcp_opendaw_add_midi_effect(unit_index, "Spielwerk")

# Load script code (compiles: parses @param, creates parameter boxes, validates JS)
await mcp_opendaw_set_script_device_code(device_type, unit_index, device_index, code)
# device_type: "Werkstatt", "Apparat", or "Spielwerk"

# Read code back
code = await mcp_opendaw_get_script_device_code(device_type, unit_index, device_index)

# List parameters (from @param declarations)
await mcp_opendaw_list_script_params(device_type, unit_index, device_index)

# Set parameter (validates + clamps)
await mcp_opendaw_set_script_param(device_type, unit_index, device_index, param_name, value)

# List sample slots (from @sample declarations)
await mcp_opendaw_list_script_samples(device_type, unit_index, device_index)
```

### @param format

```text
// @param <name> <default> <min> <max> <type> [unit]
```

Types: `linear`, `exp`, `int`, `bool`. Default is MANDATORY.

```javascript
// @param cutoff 1000 20 20000 exp Hz
// @param resonance 0.3 0 1 linear
// @param drive 0.5 0 2 linear
// @param enabled 1 0 1 bool
// @param voices 4 1 16 int
```

### Script APIs

**Werkstatt (audio effect):**
```javascript
class Processor {
  constructor() { this.sr = sampleRate; /* init */ }
  paramChanged(label, value) { this[label] = value }
  process(io, block) {
    // io.src[0/1] = input, io.out[0/1] = output
    // block.s0, block.s1 = sample range
    for (let i = block.s0; i < block.s1; i++) {
      io.out[0][i] = /* DSP */
      io.out[1][i] = /* DSP */
    }
  }
}
```

**Apparat (instrument — NO input, HAS MIDI):**
```javascript
class Processor {
  constructor() { this.sr = sampleRate; /* init oscillators */ }
  paramChanged(label, value) { this[label] = value }
  process(output, block) {
    // output[0/1] = output channels (write only)
    // NO input — generates audio
    for (let i = block.s0; i < block.s1; i++) {
      output[0][i] = /* generate */
      output[1][i] = /* generate */
    }
  }
  noteOn(pitch, velocity, cent, id) { /* MIDI note on */ }
  noteOff(id) { /* MIDI note off */ }
}
```

**Spielwerk (MIDI effect — generator, yields notes):**
```javascript
class Processor {
  paramChanged(label, value) { this[label] = value }
  ;*process(block, events) {  // MUST be generator — semicolon before * to avoid ASI bug
    // block.from, block.to = ppqn range (NOT p0/p1!)
    for (const ev of events) {
      if (ev.gate) {
        yield { position: ev.position, duration: ev.duration, pitch: ev.pitch, velocity: ev.velocity }
      }
    }
  }
  reset() {}
}
```

### CRITICAL pitfalls

1. **Spielwerk uses `block.from`/`block.to`, NOT `block.p0`/`block.p1`.** Different interface from Werkstatt/Apparat.
2. **ASI bug:** add `;` after last class field before `*process` to prevent `field = value * process(...)` misparse.
3. **Werkstatt has NO MIDI input.** Implements `AudioEffectDeviceProcessor`, not `NoteEventTarget`. Use envelope following from input audio as workaround (see `werkstatt_ringmod_env.js`).
4. **Apparat is the ONLY scriptable device with MIDI.** `noteOn`/`noteOff` in UserProcessor interface.
5. **Maximizer at effect index 0.** Find Werkstatt by class name: `fx.findIndex(b => b.constructor.name === 'WerkstattDeviceBox')`.

## DSP Script Library (47 scripts)

### Werkstatt (34 audio effects)

| Script | Effect | Key params | Issue |
|--------|--------|------------|-------|
| `werkstatt_darksat.js` | Tape saturation | drive, bias, tone, mix, output | #91 |
| `werkstatt_coldfold.js` | Wavefolding + bitcrush | drive, fold, crush, slew, mix | |
| `werkstatt_reverb.js` | Stereo plate reverb | decay, predelay, damping, width, mix | |
| `werkstatt_chorus.js` | Stereo chorus | rate, depth, center, feedback, mix | #195 |
| `werkstatt_phaser.js` | Allpass cascade phaser | rate, depth, feedback, stages, mix | #133 |
| `werkstatt_flanger.js` | Stereo flanger | rate, depth, center, feedback, mix | |
| `werkstatt_tremolo.js` | Tremolo | rate, depth, shape (sine→square), phase | |
| `werkstatt_vibrato.js` | Pitch vibrato (modulated delay) | rate, depth, shape (sine→tri), stereo | |
| `werkstatt_stereo_delay.js` | Stereo delay w/ ping-pong | time_l, time_r, feedback, tone, mix, pingpong | |
| `werkstatt_overdrive.js` | Asymmetric soft-clip overdrive | drive, tone, level, bias, dry | |
| `werkstatt_multifilter.js` | Multi-mode SVF (LP/HP/BP/Notch) | mode, cutoff, resonance, drive, mix | |
| `werkstatt_compressor.js` | Soft-knee peak compressor | threshold, ratio, attack, release, makeup, mix, knee | |
| `werkstatt_paraeq.js` | 3-band parametric EQ + HP/LP | band1/2/3 freq+gain+Q, hp_freq, lp_freq, mix | |
| `werkstatt_limiter.js` | Brickwall limiter w/ lookahead | ceiling, release, lookahead, dither, mix | |
| `werkstatt_exciter.js` | Harmonic exciter (band-split) | freq, harmonics, drive, mix, output | |
| `werkstatt_deesser.js` | De-esser (dynamic HF compressor) | freq, threshold, ratio, attack, release, mix, output | |
| `werkstatt_transient.js` | Transient shaper (dual envelope) | attack, sustain, mix, output | |
| `werkstatt_stereowidth.js` | Stereo width (M/S processor) | width, lowTrim, lowFreq, mix, output | |
| `werkstatt_lookahead.js` | Lookahead compressor | threshold, ratio, attack, release, knee, makeup, mix | |
| `werkstatt_shimmer.js` | Pitch-shift delay | time, feedback, pitch, shimmer, damping, mix | |
| `werkstatt_paulstretch.js` | Extreme time-stretch | stretch, window, mix | #209 |
| `werkstatt_envfollower.js` | Envelope follower | attack, release, depth, threshold, invert, makeup | #139 |
| `werkstatt_adsr_trim.js` | ADSR envelope trim | attack, decay, sustain, release, threshold, mix | #241 |
| `werkstatt_granular_stretch.js` | Granular time-stretch | stretch, grain, overlap, pitch, mix | #201 |
| `werkstatt_bitcrusher.js` | Standalone bitcrusher (quantize + rate reduce) | bits, rate, drive, offset, mix | |
| `werkstatt_spring_reverb.js` | Spring reverb (dispersive, boing) | decay, damp, tension, boing, mix | |
| `werkstatt_tube_saturator.js` | Tube/valve saturator (even harmonics, bias) | drive, warmth, bias, tone, output, mix | |
| `werkstatt_tape_delay.js` | Tape delay (wow/flutter, feedback saturation) | time, feedback, wow, flutter, saturation, mix | |
| `werkstatt_graphic_eq.js` | 10-band graphic EQ (ISO freqs, biquad peaking) | band_32..band_16k (10 bands), master | |
| `werkstatt_auto_pan.js` | Auto-pan (LFO stereo positioning, waveform morph) | rate, depth, shape, phase, width, offset | |
| `werkstatt_comb_filter.js` | Comb filter (delay-line feedback, polarity, damping) | freq, feedback, damping, mix, polarity | |
| `werkstatt_formant_filter.js` | Formant filter (3-band vocal tract, vowel presets) | formant_a/b/c, bandwidth_a/b/c, vowel, resonance, mix | |
| `werkstatt_harmonizer.js` | Dual-voice harmonizer (pitch shift + detune) | shift1/2_semi, shift1/2_cent, shift1/2_gain, detune, delay, mix | |
| `werkstatt_multiband_comp.js` | 3-band multiband compressor (LR4, per-band dynamics) | crossover1/2, low/mid/high × thr/ratio/atk/rel/gain, mix | |
| `werkstatt_pitch_shift.js` | Real-time pitch shift | semitones, cents, latency, mix | #188 |
| `werkstatt_dcremover.js` | DC remover + stereo width | dc_freq, width, balance, mix | #91 |
| `werkstatt_allpass.js` | Allpass filter + cascade | freq, stages, invert, feedback, mix | #133 |
| `werkstatt_noisegate.js` | Noise gate | threshold, attack, hold, release, range | |
| `werkstatt_spectral_freezer.js` | Spectral freeze | freeze, position, mix | |
| `werkstatt_ringmod_env.js` | Ring mod + env follower | freq, modDepth, modRange, attack, release, threshold, mix, output | #277 |

### Apparat (5 instruments)

| Script | Instrument | Key params | Issue |
|--------|-----------|------------|-------|
| `apparat_darkbass.js` | Mono subtractive bass | waveform, cutoff, resonance, ADSR, subOsc, detune, volume | |
| `apparat_subcrusher.js` | Sub-bass with sub-osc | waveform, cutoff, resonance, drive, sub, volume | |
| `apparat_coldlead.js` | Lead synth with glide | waveform, cutoff, resonance, ADSR, glide, volume | |
| `apparat_ringmod.js` | Ring modulator synth | frequency, waveform, ADSR, adsrAmount, subOsc, volume | #277 |
| `apparat_fm.js` | 2-operator FM synth | carrier, ratio, mod_depth, waveform, ADSR, volume | #138 |
| `apparat_pluck.js` | Karplus-Strong plucked string | decay, damping, brightness, attack, release, detune, volume | |
| `apparat_wavetable.js` | Wavetable synth (8 tables, scan, unison) | pos, pos_lfo_rate, pos_lfo_depth, detune, unison, ADSR, volume | |

### Spielwerk (6 MIDI effects)

| Script | Effect | Key params |
|--------|--------|------------|
| `spielwerk_arpeggiator.js` | Arpeggiator with swing | rate, mode, octaves, gate |
| `spielwerk_powerchord.js` | Power chord generator | interval, interval2, velScale, detune |
| `spielwerk_chordmemory.js` | Chord memory (7 shapes) | chord (0-6), octave, velocity |
| `spielwerk_strum.js` | Strummer | speed, direction, spread, velocity |
| `spielwerk_velocity.js` | Velocity scaler | scale, offset, curve, min_vel, max_vel |
| `spielwerk_mididelay.js` | MIDI delay + feedback | time, feedback, repeats, transpose, decay |

### Choosing a script

| Need | Script | Device |
|------|--------|--------|
| Tape warmth/saturation | `werkstatt_darksat.js` | Werkstatt |
| Overdrive/distortion | `werkstatt_overdrive.js` | Werkstatt |
| Reverb (plate) | `werkstatt_reverb.js` | Werkstatt |
| Reverb (shimmer) | `werkstatt_shimmer.js` | Werkstatt |
| Reverb (spring) | `werkstatt_spring_reverb.js` | Werkstatt |
| Delay (stereo) | `werkstatt_stereo_delay.js` | Werkstatt |
| Delay (tape, wow/flutter) | `werkstatt_tape_delay.js` | Werkstatt |
| Delay (MIDI) | `spielwerk_mididelay.js` | Spielwerk |
| Saturation (tube/valve) | `werkstatt_tube_saturator.js` | Werkstatt |
| Bitcrusher (lo-fi) | `werkstatt_bitcrusher.js` | Werkstatt |
| Filter (LP/HP/BP/Notch) | `werkstatt_multifilter.js` | Werkstatt |
| EQ (parametric, 3-band) | `werkstatt_paraeq.js` | Werkstatt |
| EQ (graphic, 10-band) | `werkstatt_graphic_eq.js` | Werkstatt |
| Auto-pan (LFO) | `werkstatt_auto_pan.js` | Werkstatt |
| Comb filter | `werkstatt_comb_filter.js` | Werkstatt |
| Formant filter (vocal) | `werkstatt_formant_filter.js` | Werkstatt |
| Harmonizer (dual-voice) | `werkstatt_harmonizer.js` | Werkstatt |
| Multiband compressor | `werkstatt_multiband_comp.js` | Werkstatt |
| Compressor (peak, soft-knee) | `werkstatt_compressor.js` | Werkstatt |
| Compressor (lookahead) | `werkstatt_lookahead.js` | Werkstatt |
| Limiter (brickwall) | `werkstatt_limiter.js` | Werkstatt |
| Exciter (harmonic) | `werkstatt_exciter.js` | Werkstatt |
| De-esser (dynamic HF) | `werkstatt_deesser.js` | Werkstatt |
| Transient shaper | `werkstatt_transient.js` | Werkstatt |
| Stereo width (M/S) | `werkstatt_stereowidth.js` | Werkstatt |
| Chorus/width | `werkstatt_chorus.js` | Werkstatt |
| Phaser | `werkstatt_phaser.js` | Werkstatt |
| Flanger | `werkstatt_flanger.js` | Werkstatt |
| Tremolo | `werkstatt_tremolo.js` | Werkstatt |
| Vibrato | `werkstatt_vibrato.js` | Werkstatt |
| Noise gate | `werkstatt_noisegate.js` | Werkstatt |
| Time-stretch (extreme) | `werkstatt_paulstretch.js` | Werkstatt |
| Time-stretch (granular) | `werkstatt_granular_stretch.js` | Werkstatt |
| Pitch shift | `werkstatt_pitch_shift.js` | Werkstatt |
| Spectral freeze | `werkstatt_spectral_freezer.js` | Werkstatt |
| DC/stereo tool | `werkstatt_dcremover.js` | Werkstatt |
| Sidechain ducking | `werkstatt_envfollower.js` | Werkstatt |
| Bass synth | `apparat_darkbass.js` | Apparat |
| Sub-bass | `apparat_subcrusher.js` | Apparat |
| Lead synth | `apparat_coldlead.js` | Apparat |
| FM synth | `apparat_fm.js` | Apparat |
| Wavetable synth | `apparat_wavetable.js` | Apparat |
| Ring mod (MIDI) | `apparat_ringmod.js` | Apparat |
| Plucked string (KS) | `apparat_pluck.js` | Apparat |
| Ring mod (audio) | `werkstatt_ringmod_env.js` | Werkstatt |
| Arpeggiator | `spielwerk_arpeggiator.js` | Spielwerk |
| Power chords | `spielwerk_powerchord.js` | Spielwerk |
| Chord memory | `spielwerk_chordmemory.js` | Spielwerk |
| Strumming | `spielwerk_strum.js` | Spielwerk |
| Velocity control | `spielwerk_velocity.js` | Spielwerk |

### Writing custom DSP scripts

**Werkstatt pattern (audio effect):**
```javascript
// @werkstatt myeffect 1 1
// @param drive 0.5 0 2 linear

class Processor {
  p = {drive: 0.5}
  sr = sampleRate
  
  constructor() { /* allocate buffers */ }
  
  paramChanged(label, value) { this.p[label] = value }
  
  process(io, block) {
    const drive = this.p.drive
    for (let i = block.s0; i < block.s1; i++) {
      io.out[0][i] = Math.tanh(io.src[0][i] * drive)
      io.out[1][i] = Math.tanh(io.src[1][i] * drive)
    }
  }
}
```

**Validate before commit:** `node --check script.js` then bridge compile test.

## MIDI Effects Chain

MIDI effects process MIDI before it reaches the instrument. Chain order matters.

```python
# Add MIDI effect (before instrument)
await mcp_opendaw_add_midi_effect(unit_index, effect_type)
# Types: Arpeggio, Pitch, Spielwerk, Velocity, Zeitgeist

# List MIDI effects on a unit
await mcp_opendaw_list_midi_effects(unit_index)
```

**Pitfall:** `au.midiEffects` is field 21 on AudioUnitBox. `api.insertEffect` for MIDI effects uses same API but different field.

## Instrument replacement

```python
# Replace instrument (keeps MIDI/effect chain)
await mcp_opendaw_replace_instrument(unit_index, new_instrument_type)
```

## Preset export/import

```python
# Export instrument preset (base64)
preset = await mcp_opendaw_export_preset(unit_index)

# Import preset
await mcp_opendaw_replace_from_preset(unit_index, preset_b64, keep_midi_effects=False, keep_audio_effects=False, keep_timeline=False)
```

## Related skills
- `opendaw-automation` — 263 MCP tools full API reference + pitfalls
- `opendaw-track-architecture` — tracks, regions, clips, notes, tempo, markers
- `opendaw-effect-routing` — effect chains, sends, buses, sidechain
- `adaptive-mix-mastering` — full mix→master pipeline with decision points
