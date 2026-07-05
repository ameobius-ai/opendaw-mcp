# DSP Scripts

53 ready-made JavaScript DSP scripts for openDAW's scriptable devices.

## Werkstatt (Audio Effects) — 40 scripts

| Script | Description | Parameters |
|--------|-------------|------------|
| `werkstatt_darksat.js` | Tape saturation / drive | drive, bias, tone, mix, output |
| `werkstatt_coldfold.js` | Wavefolding + bitcrush | drive, fold, crush, slew, mix |
| `werkstatt_overdrive.js` | Asymmetric soft-clip overdrive | drive, tone, level, mix |
| `werkstatt_stereo_delay.js` | Stereo ping-pong delay | time, feedback, tone, mix |
| `werkstatt_multifilter.js` | Chamberlin SVF (LP/HP/BP/Notch) | mode, freq, resonance, mix |
| `werkstatt_compressor.js` | Soft-knee peak compressor | threshold, ratio, attack, release, makeup, mix, knee |
| `werkstatt_lookahead.js` | Lookahead compressor | threshold, ratio, attack, release, knee, makeup, mix |
| `werkstatt_limiter.js` | Brickwall limiter w/ lookahead | ceiling, release, lookahead, dither, mix |
| `werkstatt_exciter.js` | Harmonic exciter (band-split) | freq, harmonics, drive, mix, output |
| `werkstatt_deesser.js` | De-esser (dynamic HF compressor) | freq, threshold, ratio, attack, release, mix, output |
| `werkstatt_transient.js` | Transient shaper (dual envelope) | attack, sustain, mix, output |
| `werkstatt_stereowidth.js` | Stereo width (M/S processor) | width, lowTrim, lowFreq, mix, output |
| `werkstatt_paraeq.js` | 3-band parametric EQ + HP/LP | band1/2/3 freq+gain+Q, hp_freq, lp_freq, mix |
| `werkstatt_reverb.js` | Algorithmic reverb | room, decay, damp, mix |
| `werkstatt_chorus.js` | Stereo chorus | rate, depth, mix |
| `werkstatt_phaser.js` | Phaser | rate, depth, feedback, mix |
| `werkstatt_flanger.js` | Flanger | rate, depth, feedback, mix |
| `werkstatt_tremolo.js` | Tremolo | rate, depth, shape, mix |
| `werkstatt_vibrato.js` | Pitch vibrato (modulated delay) | rate, depth, shape, stereo |
| `werkstatt_shimmer.js` | Shimmer reverb (pitch-shifted tail) | pitch, decay, mix |
| `werkstatt_pitch_shift.js` | Pitch shifter | semitones, mix |
| `werkstatt_granular_stretch.js` | Granular time stretch | grain_size, density, pitch |
| `werkstatt_paulstretch.js` | Paulstretch extreme stretch | stretch, mix |
| `werkstatt_spectral_freezer.js` | Spectral freeze | freeze, mix |
| `werkstatt_allpass.js` | Allpass filter | frequency, feedback |
| `werkstatt_dcremover.js` | DC blocker | — |
| `werkstatt_envfollower.js` | Envelope follower | attack, release, threshold |
| `werkstatt_noisegate.js` | Noise gate | threshold, attack, release, range |
| `werkstatt_ringmod_env.js` | Ring modulator with envelope | frequency, depth, mix |
| `werkstatt_adsr_trim.js` | ADSR-based trim | attack, decay, sustain, release |
| `werkstatt_bitcrusher.js` | Standalone bitcrusher (quantize + rate reduce) | bits, rate, drive, offset, mix |
| `werkstatt_spring_reverb.js` | Spring reverb (dispersive, boing) | decay, damp, tension, boing, mix |
| `werkstatt_tube_saturator.js` | Tube/valve saturator (even harmonics, bias) | drive, warmth, bias, tone, output, mix |
| `werkstatt_tape_delay.js` | Tape delay (wow/flutter, feedback saturation) | time, feedback, wow, flutter, saturation, mix |
| `werkstatt_graphic_eq.js` | 10-band graphic EQ (ISO frequencies, biquad peaking) | band_32, band_64, band_125, band_250, band_500, band_1k, band_2k, band_4k, band_8k, band_16k, master |
| `werkstatt_auto_pan.js` | Auto-pan (LFO stereo positioning, waveform morph) | rate, depth, shape, phase, width, offset |
| `werkstatt_comb_filter.js` | Comb filter (delay-line feedback, polarity, damping) | freq, feedback, damping, mix, polarity |
| `werkstatt_formant_filter.js` | Formant filter (3-band vocal tract, vowel presets) | formant_a/b/c, bandwidth_a/b/c, vowel, resonance, mix |
| `werkstatt_harmonizer.js` | Dual-voice harmonizer (pitch shift + detune) | shift1/2_semi, shift1/2_cent, shift1/2_gain, detune, delay, mix |
| `werkstatt_multiband_comp.js` | 3-band multiband compressor (LR4 crossover, per-band dynamics) | crossover1/2, low/mid/high × threshold/ratio/attack/release/gain, mix |
| `werkstatt_vocoder.js` | Channel vocoder (bandpass bank, spectral envelope mapping) | bands, carrier_wave, carrier_freq, mod_response, mod_threshold, band_q, emphasis, highpass, mix, output |
| `werkstatt_reverse.js` | Real-time reverse (chunked buffer, variable speed, trigger modes) | chunk_size, feedback, speed, smooth, dry_gain, wet_gain, mix, stereo_mode, trigger_mode, output |
| `werkstatt_scratch.js` | DJ vinyl scratch (turntable physics, wow/flutter, crackle) | depth, rate, pullback, friction, wow, flutter, flutter_rate, crackle, mix, output |

## Apparat (Instruments) — 7 scripts

| Script | Description | Parameters |
|--------|-------------|------------|
| `apparat_darkbass.js` | Sub bass synthesizer | oscillator, envelope, filter |
| `apparat_coldlead.js` | Cold lead synth | oscillator, envelope, filter |
| `apparat_subcrusher.js` | Sub crusher (distorted bass) | oscillator, distortion, envelope |
| `apparat_fm.js` | FM synthesis | carrier, modulator, ratio, depth |
| `apparat_ringmod.js` | Ring modulation synth | carrier, modulator, depth |
| `apparat_pluck.js` | Karplus-Strong plucked string | decay, damping, brightness, attack, release, detune, volume |
| `apparat_wavetable.js` | Wavetable synth (8 tables, scan, unison) | pos, pos_lfo_rate, pos_lfo_depth, detune, unison, attack, decay, sustain, release, volume |

## Spielwerk (MIDI Effects) — 6 scripts

| Script | Description | Parameters |
|--------|-------------|------------|
| `spielwerk_arpeggiator.js` | Arpeggiator | rate, octave, pattern |
| `spielwerk_powerchord.js` | Powerchord generator | interval, voicing |
| `spielwerk_chordmemory.js` | Chord memory | chord_type, voicing |
| `spielwerk_mididelay.js` | MIDI delay | time, feedback, mix |
| `spielwerk_strum.js` | Strum simulator | speed, direction |
| `spielwerk_velocity.js` | Velocity processor | curve, min, max |

## Using DSP scripts

```python
# Load a Werkstatt script onto an effect
with open("scripts/werkstatt_darksat.js") as f:
    code = f.read()

await server.mcp_opendaw_add_effect(unit_index=0, effect_type="Werkstatt")
await server.mcp_opendaw_set_script_device_code(
    unit_index=0, effect_index=0, code=code
)

# Tweak parameters
await server.mcp_opendaw_set_script_param(
    unit_index=0, effect_index=0, param_name="drive", value=0.7
)
```

## Writing your own

DSP scripts use the Werkstatt/Apparat/Spielwerk processor API:

```javascript
// @werkstatt myEffect 1 1
// @param {float} gain 0.5 0 1 "Gain"
// @param {float} drive 0.3 0 1 "Drive"
// @param {bool} bypass false "Bypass"

function processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];

    for (let ch = 0; ch < input.length; ch++) {
        const inCh = input[ch];
        const outCh = output[ch];
        const gain = parameters.gain[ch];
        const drive = parameters.drive[ch];

        for (let i = 0; i < inCh.length; i++) {
            let sample = inCh[i] * gain;
            // Tanh approximation for soft clipping
            sample = Math.tanh(sample * (1 + drive * 5));
            outCh[i] = sample;
        }
    }
}
```

### Key APIs

| API | Description |
|-----|-------------|
| `processAudio(inputs, outputs, parameters)` | Audio processing callback |
| `paramChanged(name, value)` | Called when a parameter changes |
| `this.sampleRate` | Audio sample rate (44100 or 48000) |
| `this.blockSize` | Audio block size (128) |
| `inputs[ch][sample]` | Input audio (Float32Array) |
| `outputs[ch][sample]` | Output audio (Float32Array) |
| `parameters.name[ch]` | Parameter values per channel |

→ See [Scriptable Devices](tools/scriptable.md) for the full API reference.
