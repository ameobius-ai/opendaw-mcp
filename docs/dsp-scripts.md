# DSP Scripts

110 ready-made JavaScript DSP scripts for openDAW's scriptable devices.

## Werkstatt (Audio Effects) — 91 scripts

### Dynamics (13)

| Script | Description |
|--------|-------------|
| `werkstatt_compressor.js` | Compressor |
| `werkstatt_lookahead.js` | Lookahead Compressor |
| `werkstatt_limiter.js` | Brickwall Limiter |
| `werkstatt_maximizer.js` | Loudness Maximizer (lookahead limiting, ISP detection, TPDF dither, ceiling, stereo link) |
| `werkstatt_cabinet_sim.js` | Guitar Cabinet Speaker Simulator (4x12/open-back/tweed, resonance peak, speaker rolloff, cone soft clip) |
| `werkstatt_valve_preamp.js` | Valve/Tube Preamp (12AX7 triode, asymmetric waveshaper, even-order harmonics, Miller capacitance, output transformer) |
| `werkstatt_synthetic_ir_reverb.js` | Synthetic IR Reverb (algorithmic impulse response generation, exponential decay × filtered noise, early reflections, truncated convolution) |
| `werkstatt_sidechain_comp.js` | Sidechain Compressor (pump effect, envelope follower, gain smoothing, kick→bass ducking, 8 params) |
| `werkstatt_ott.js` | OTT Multiband Compressor (Xfer-style 3-band upward/downward, LR crossover 200/2000Hz, depth/time/per-band+master gain) |
| `werkstatt_soft_clipper.js` | Soft Clipper (tanh+cubic curves, ceiling/drive/curve, drum bus/mix bus/808 loudness without harshness) |
| `werkstatt_exciter.js` | Harmonic Exciter |
| `werkstatt_deesser.js` | De-Esser |
| `werkstatt_transient.js` | Transient Shaper |
| `werkstatt_noisegate.js` | Noise Gate |
| `werkstatt_multiband_comp.js` | Multiband Compressor |
| `werkstatt_bass_enhancer.js` | Bass Enhancer (Psychoacoustic) |
| `werkstatt_expander.js` | Downward Expander |
| `werkstatt_envelope_follower.js` | Envelope Follower (amplitude tracking) |
| `werkstatt_glue_comp.js` | SSL-Style Glue Compressor (auto-makeup, VCA warmth, parallel mix, true stereo peak detect) |
| `werkstatt_de_plosive.js` | De-Plosive (adaptive highpass for vocal plosive removal, envelope follower + threshold) |

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

### Filter (10)

| Script | Description |
|--------|-------------|
| `werkstatt_multifilter.js` | Multi-Mode Filter |
| `werkstatt_allpass.js` | Allpass Filter |
| `werkstatt_dcremover.js` | DC Remover + Stereo Tool |
| `werkstatt_comb_filter.js` | Comb Filter |
| `werkstatt_formant_filter.js` | Formant Filter |
| `werkstatt_moog_ladder.js` | Moog Ladder Filter |
| `werkstatt_autowah.js` | Autowah |
| `werkstatt_auto_wah.js` | Auto-Wah (envelope-driven biquad sweep, Mu-Tron III) |
| `werkstatt_svf.js` | State Variable Filter (Chamberlin) |
| `werkstatt_vowel_morph.js` | Vowel Morph (3 cascaded formant biquads, A→E→I→O→U interpolation, auto-morph LFO, spectral tilt) |

### Modulation (9)

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

### Time (4)

| Script | Description |
|--------|-------------|
| `werkstatt_granular_stretch.js` | Granular Time-Stretch |
| `werkstatt_paulstretch.js` | PaulStretch (Extreme Ambient Stretch) |
| `werkstatt_tape_stop.js` | Tape Stop |

### Stereo/Spatial (6)

| Script | Description |
|--------|-------------|
| `werkstatt_stereowidth.js` | Stereo Width (M/S) |
| `werkstatt_auto_pan.js` | Auto-Pan |
| `werkstatt_multiband_imager.js` | Multiband Stereo Imager |
| `werkstatt_binaural.js` | Binaural Spatial Panner (HRTF) |
| `werkstatt_mid_side_processor.js` | Mid/Side Processor (independent M/S gain + filters + width, mastering) |
| `werkstatt_haas_widener.js` | Haas Stereo Widener (short delay 1-30ms on one channel, precedence effect) |

### Spectral/FX (10)

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
| `werkstatt_spectral_blur.js` | Spectral Blur (STFT-based spectral smearing, freq+temporal blur, phase randomization, ambient textures) |
| `werkstatt_spectral_enhancer.js` | Spectral Enhancer (STFT-based high-freq air boost, spectral peak emphasis, transient enhancement, stereo widening on enhanced band) |

### Restoration (5)

| Script | Description |
|--------|-------------|
| `werkstatt_spectral_denoise.js` | Spectral Denoiser (Berouti spectral subtraction, noise floor learning, oversubtraction, musical noise prevention) |
| `werkstatt_dereverb.js` | De-Reverb (reverb tail suppression: per-band dual envelope followers, fast=direct/slow=tail, transient detection via ratio, tail dominance gain reduction -24 dB, decay estimation, RX De-reverb style) |
| `werkstatt_declicker.js` | De-Clicker (click & crackle removal: median filter, adaptive threshold, cubic Hermite interpolation, RX De-click style) |
| `werkstatt_decrackle.js` | De-Crackle (continuous crackle removal: adaptive crackle modeling, crackle/signal energy tracking, crackle rate estimation, RX De-crackle style) |
| `werkstatt_de_plosive.js` | De-Plosive (adaptive highpass for vocal plosive removal, one-pole LP envelope follower + threshold, transient-triggered HPF sweep) |

### Physical Modeling (3)

| Script | Description |
|--------|-------------|
| `werkstatt_modal_resonator.js` | Modal Resonator (marimba/bell/plate/string/wine glass) |
| `werkstatt_karplus_strong.js` | Karplus-Strong String (delay-line + one-pole lowpass feedback, brightness/damping/stretch controls) |
| `werkstatt_waveguide_string.js` | Waveguide String (bidirectional delay lines, bridge lowpass + nut allpass, pick position, inharmonicity) |

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

### Vocal (2)

| Script | Description |
|--------|-------------|
| `werkstatt_auto_tune.js` | Auto-Tune (autocorrelation pitch detection + snap-to-scale + time-domain pitch shift) |
| `werkstatt_formant_shifter.js` | Formant Shifter (LPC Levinson-Durbin, lattice filter, formant frequency scaling independent of pitch, gender/age/size morphing) |

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
