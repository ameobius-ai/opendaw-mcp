# DSP Scripts

95 ready-made JavaScript DSP scripts for openDAW's scriptable devices.

## Werkstatt (Audio Effects) — 76 scripts

### Dynamics (10)

| Script | Description |
|--------|-------------|
| `werkstatt_compressor.js` | Compressor |
| `werkstatt_lookahead.js` | Lookahead Compressor |
| `werkstatt_limiter.js` | Brickwall Limiter |
| `werkstatt_exciter.js` | Harmonic Exciter |
| `werkstatt_deesser.js` | De-Esser |
| `werkstatt_transient.js` | Transient Shaper |
| `werkstatt_noisegate.js` | Noise Gate |
| `werkstatt_multiband_comp.js` | Multiband Compressor |
| `werkstatt_bass_enhancer.js` | Bass Enhancer (Psychoacoustic) |
| `werkstatt_expander.js` | Downward Expander |

### Saturation/Distortion (8)

| Script | Description |
|--------|-------------|
| `werkstatt_darksat.js` | Dark Saturation |
| `werkstatt_overdrive.js` | Overdrive |
| `werkstatt_coldfold.js` | Cold Fold Distortion |
| `werkstatt_bitcrusher.js` | Bitcrusher |
| `werkstatt_tube_saturator.js` | Tube Saturator |
| `werkstatt_waveshaper.js` | Waveshaper |
| `werkstatt_fuzz.js` | Fuzz (Big Muff Pi / Fuzz Face style) |
| `werkstatt_multiband_saturator.js` | Multiband Saturator |

### EQ (5)

| Script | Description |
|--------|-------------|
| `werkstatt_paraeq.js` | Parametric EQ |
| `werkstatt_graphic_eq.js` | Graphic EQ |
| `werkstatt_dynamic_eq.js` | Dynamic EQ |
| `werkstatt_tilt_eq.js` | Tilt EQ |
| `werkstatt_matching_eq.js` | Matching EQ (Spectral Balance Corrector) |

### Filter (8)

| Script | Description |
|--------|-------------|
| `werkstatt_multifilter.js` | Multi-Mode Filter |
| `werkstatt_allpass.js` | Allpass Filter |
| `werkstatt_dcremover.js` | DC Remover + Stereo Tool |
| `werkstatt_comb_filter.js` | Comb Filter |
| `werkstatt_formant_filter.js` | Formant Filter |
| `werkstatt_moog_ladder.js` | Moog Ladder Filter |
| `werkstatt_autowah.js` | Autowah |
| `werkstatt_svf.js` | State Variable Filter (Chamberlin) |

### Modulation (8)

| Script | Description |
|--------|-------------|
| `werkstatt_chorus.js` | Stereo Chorus |
| `werkstatt_flanger.js` | Stereo Flanger |
| `werkstatt_phaser.js` | Phaser |
| `werkstatt_tremolo.js` | Tremolo |
| `werkstatt_vibrato.js` | Pitch Vibrato |
| `werkstatt_rotary_speaker.js` | Rotary Speaker (Leslie) |
| `werkstatt_dimension_chorus.js` | Dimension Chorus |
| `werkstatt_harmonic_tremolo.js` | Harmonic Tremolo (Fender) |

### Reverb (5)

| Script | Description |
|--------|-------------|
| `werkstatt_reverb.js` | Plate Reverb |
| `werkstatt_shimmer.js` | Shimmer Delay |
| `werkstatt_spring_reverb.js` | Spring Reverb |
| `werkstatt_convolution_reverb.js` | Convolution Reverb |
| `werkstatt_gated_reverb.js` | Gated Reverb (80s Drum) |

### Delay (5)

| Script | Description |
|--------|-------------|
| `werkstatt_stereo_delay.js` | Stereo Delay |
| `werkstatt_tape_delay.js` | Tape Delay |
| `werkstatt_multitap_delay.js` | Multitap Delay |
| `werkstatt_reverse_delay.js` | Reverse Delay |
| `werkstatt_grain_delay.js` | Grain Delay |

### Pitch (5)

| Script | Description |
|--------|-------------|
| `werkstatt_pitch_shift.js` | Pitch Shifter |
| `werkstatt_ringmod_env.js` | Ring Modulator (Envelope-Followed) |
| `werkstatt_harmonizer.js` | Harmonizer |
| `werkstatt_octaver.js` | Octaver (Sub-Octave Generator) |
| `werkstatt_freq_shifter.js` | Frequency Shifter (SSB) |

### Time (3)

| Script | Description |
|--------|-------------|
| `werkstatt_granular_stretch.js` | Granular Time-Stretch |
| `werkstatt_paulstretch.js` | PaulStretch (Extreme Ambient Stretch) |
| `werkstatt_tape_stop.js` | Tape Stop |

### Stereo/Spatial (4)

| Script | Description |
|--------|-------------|
| `werkstatt_stereowidth.js` | Stereo Width (M/S) |
| `werkstatt_auto_pan.js` | Auto-Pan |
| `werkstatt_multiband_imager.js` | Multiband Stereo Imager |
| `werkstatt_binaural.js` | Binaural Spatial Panner (HRTF) |

### Spectral/FX (8)

| Script | Description |
|--------|-------------|
| `werkstatt_spectral_freezer.js` | Spectral Freeze (Sustain a spectral frame) |
| `werkstatt_reverse.js` | Reverse |
| `werkstatt_scratch.js` | Scratch |
| `werkstatt_looper.js` | Looper |
| `werkstatt_spectral_gate.js` | Spectral Gate |
| `werkstatt_vinyl.js` | Vinyl Simulator |
| `werkstatt_spectral_compressor.js` | Spectral Compressor (STFT) |
| `werkstatt_spectral_denoise.js` | Spectral Denoiser (Noise Floor Subtraction) |

### Restoration (1)

| Script | Description |
|--------|-------------|
| `werkstatt_spectral_denoise.js` | Spectral Denoiser (Berouti spectral subtraction, noise floor learning, oversubtraction, musical noise prevention) |

### Physical Modeling (1)

| Script | Description |
|--------|-------------|
| `werkstatt_modal_resonator.js` | Modal Resonator (marimba/bell/plate/string/wine glass) |

### Vocoder (1)

| Script | Description |
|--------|-------------|
| `werkstatt_vocoder.js` | Vocoder |

### Phase Vocoder / Pitch-Shifting (2)

| Script | Description |
|--------|-------------|
| `werkstatt_phase_vocoder.js` | Phase Vocoder (FFT Pitch Shifter — Élastique/Melodyne quality) |
| `werkstatt_time_stretch.js` | Phase Vocoder Time Stretch (preserves pitch, transient detection) |

### Utility (4)

| Script | Description |
|--------|-------------|
| `werkstatt_adsr_trim.js` | ADSR Envelope Trim |
| `werkstatt_envfollower.js` | Envelope Follower (with sidechain ducking) |
| `werkstatt_auto_tune.js` | Auto-Tune (Pitch Correction — Cher/T-Pain style) |

### Vocal (1)

| Script | Description |
|--------|-------------|
| `werkstatt_auto_tune.js` | Auto-Tune (autocorrelation pitch detection + snap-to-scale + time-domain pitch shift) |

## Apparat (Instruments) — 9 scripts

| Script | Description |
|--------|-------------|
| `apparat_darkbass.js` | Dark Bass (waveform, cutoff, resonance, envelope) |
| `apparat_coldlead.js` | Cold Lead (subtractive synth) |
| `apparat_subcrusher.js` | SubCrusher Bass (distorted sub bass) |
| `apparat_pluck.js` | Plucked String (Karplus-Strong) |
| `apparat_fm.js` | FM Synth (2-operator) |
| `apparat_ringmod.js` | Ring Modulator Synth |
| `apparat_wavetable.js` | Wavetable Synth (8 tables, scan + LFO, unison) |
| `apparat_supersaw.js` | Supersaw (7 detuned saws, JP-8000 style) |
| `apparat_bowed_string.js` | Bowed String (waveguide + Stribeck bow friction) |

## Spielwerk (MIDI Effects) — 10 scripts

| Script | Description |
|--------|-------------|
| `spielwerk_arpeggiator.js` | Arpeggiator (rate, octave, pattern) |
| `spielwerk_chordmemory.js` | Chord Memory (hold chords) |
| `spielwerk_mididelay.js` | MIDI Delay (echo MIDI notes) |
| `spielwerk_powerchord.js` | Power Chord (root + fifth) |
| `spielwerk_strum.js` | Strummer (simulate guitar strumming) |
| `spielwerk_velocity.js` | Velocity Scaler (adjust note velocities) |
| `spielwerk_scale_quantizer.js` | Scale Quantizer (14 scales, 12 roots, snap direction) |
| `spielwerk_harmonizer.js` | MIDI Harmonizer (3 voices, 14 scales) |
| `spielwerk_prob_gate.js` | Probability Gate (subtractive MIDI — random note removal) |
| `spielwerk_chorder.js` | Chorder (13 chord types, 5 voicing modes, 4 inversions, strum delay) |

## Using DSP scripts

```python
# Load a DSP script into a Werkstatt device
import json
code = open("scripts/werkstatt_compressor.js").read()
await mcp.call("set_script_device_code", {
    "device_type": "werkstatt",
    "unit_index": 0,
    "device_index": 0,
    "code": code
})

# Set a parameter
await mcp.call("set_script_param", {
    "device_type": "werkstatt",
    "unit_index": 0,
    "device_index": 0,
    "param_label": "threshold",
    "value": 0.5
})
```

DSP scripts use the Werkstatt/Apparat/Spielwerk processor API:

```javascript
// @werkstatt my_effect 1 1
// @param gain 0.5 0 1 linear

class Processor {
  p = {gain: 0.5}
  sr = sampleRate

  paramChanged(name, value) {
    this.p[name] = value
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0]
      const outCh = output[ch]
      for (let i = 0; i < outCh.length; i++) {
        outCh[i] = inCh[i] * this.p.gain
      }
    }
  }

  reset() {
    // Clear state
  }
}
```
