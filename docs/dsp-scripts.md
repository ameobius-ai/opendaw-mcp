# DSP Scripts

26 ready-made JavaScript DSP scripts for openDAW's scriptable devices.

## Werkstatt (Audio Effects) — 15 scripts

| Script | Description | Parameters |
|--------|-------------|------------|
| `werkstatt_darksat.js` | Tape saturation / drive | drive, bias, tone, mix, output |
| `werkstatt_coldfold.js` | Wavefolding + bitcrush | drive, fold, crush, slew, mix |
| `werkstatt_reverb.js` | Algorithmic reverb | room, decay, damp, mix |
| `werkstatt_chorus.js` | Stereo chorus | rate, depth, mix |
| `werkstatt_phaser.js` | Phaser | rate, depth, feedback, mix |
| `werkstatt_shimmer.js` | Shimmer reverb (pitch-shifted tail) | pitch, decay, mix |
| `werkstatt_pitch_shift.js` | Pitch shifter | semitones, mix |
| `werkstatt_granular_stretch.js` | Granular time stretch | grain_size, density, pitch |
| `werkstatt_paulstretch.js` | Paulstretch extreme stretch | stretch, mix |
| `werkstatt_allpass.js` | Allpass filter | frequency, feedback |
| `werkstatt_dcremover.js` | DC blocker | — |
| `werkstatt_envfollower.js` | Envelope follower | attack, release, threshold |
| `werkstatt_ringmod_env.js` | Ring modulator with envelope | frequency, depth, mix |
| `werkstatt_lookahead.js` | Lookahead limiter | threshold, release, makeup |
| `werkstatt_adsr_trim.js` | ADSR-based trim | attack, decay, sustain, release |

## Apparat (Instruments) — 5 scripts

| Script | Description | Parameters |
|--------|-------------|------------|
| `apparat_darkbass.js` | Sub bass synthesizer | oscillator, envelope, filter |
| `apparat_coldlead.js` | Cold lead synth | oscillator, envelope, filter |
| `apparat_subcrusher.js` | Sub crusher (distorted bass) | oscillator, distortion, envelope |
| `apparat_fm.js` | FM synthesis | carrier, modulator, ratio, depth |
| `apparat_ringmod.js` | Ring modulation synth | carrier, modulator, depth |

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
