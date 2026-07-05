---
name: dsp-script-authoring
description: "How to author custom DSP scripts for openDAW scriptable devices (Werkstatt audio effects, Apparat instruments, Spielwerk MIDI effects). Processor API, @param/@sample declarations, DSP patterns, validation, compilation, pitfalls. 26 example scripts as reference. For writing new DSP, not using existing."
tags: [dsp, scripting, werkstatt, apparat, spielwerk, javascript, audio-programming, custom-effects, openDAW]
---

# DSP Script Authoring

Ремесло написания кастомных DSP скриптов для openDAW scriptable devices.
Три типа устройств, три API, одна философия: чистый JS, running in AudioWorklet.

## Когда использовать

- Юзер просит кастомный эффект/инструмент которого нет в built-in
- Нужно написать DSP специфичный для трека (уникальная дисторшн, реверб, генератор)
- Юзер хочет понять как работают scriptable devices
- Нужно модифицировать существующий DSP скрипт
- Нужно создать .opb preset из кастомного скрипта

## Три типа устройств

| Device | Role | Input | Output | MIDI | Class |
|--------|------|-------|--------|------|-------|
| Werkstatt | Audio effect | Audio in | Audio out | NO | AudioEffectDeviceProcessor |
| Apparat | Instrument | None | Audio out | YES (noteOn/noteOff) | NoteEventTarget |
| Spielwerk | MIDI effect | MIDI events | MIDI events (yielded) | YES (processes) | Generator |

## Header Format

Every script starts with a header declaring the device type:

```javascript
// @werkstatt myeffect 1 1    ← type, name, version, channels
// @apparat myinstrument 1 1
// @spielwerk mymidieffect 1 1
```

## @param Declarations

Parameters are declared as comments. Parsed by ScriptDeclaration, turned into parameter boxes.

```text
// @param <name> <default> <min> <max> <type> [unit]
```

### Types (ONLY 4)

| Type | Behavior | Example |
|------|----------|---------|
| `linear` | Linear mapping, clamped to [min,max] | `// @param drive 0.5 0 2 linear` |
| `exp` | Exponential mapping, clamped | `// @param cutoff 1000 20 20000 exp Hz` |
| `int` | Integer, rounded, clamped | `// @param voices 4 1 16 int` |
| `bool` | Boolean, snaps to 0/1 | `// @param enabled 1 0 1 bool` |

**There is NO `unipolar` type.** Omitting type or writing `unipolar` → default 0-1 range.

**Default value is MANDATORY.** Without it, the param is ignored.

### @sample Declarations (Werkstatt only)

```javascript
// @sample kick 0
// @sample snare 1
```

Creates sample slots. Index must match. Samples loaded via Playfield-style audio files.

## Processor API

### Werkstatt (audio effect)

```javascript
// @werkstatt myeffect 1 1
// @param drive 0.5 0 2 linear
// @param mix 0.5 0 1 linear

class Processor {
  p = {drive: 0.5, mix: 0.5}   // param store (MUST match @param names)
  sr = sampleRate               // global, available in class body
  
  constructor() {
    // Allocate buffers, init state
    this.buffer = new Float32Array(this.sr * 0.5)  // 0.5s delay
    this.writePos = 0
  }
  
  paramChanged(label, value) {
    this.p[label] = value       // called when user changes param
  }
  
  process(io, block) {
    // io.src[0], io.src[1] = input channels (Float32Array)
    // io.out[0], io.out[1] = output channels (Float32Array, write target)
    // block.s0, block.s1 = sample range to process
    // block.p0, block.p1 = position in project (for LFO sync)
    // block.bpm = current BPM
    
    const drive = this.p.drive
    const mix = this.p.mix
    for (let i = block.s0; i < block.s1; i++) {
      const dry = io.src[0][i]
      const wet = Math.tanh(dry * drive)
      io.out[0][i] = dry * (1 - mix) + wet * mix
      io.out[1][i] = dry * (1 - mix) + wet * mix  // same for mono effect
    }
  }
}
```

### Apparat (instrument — generates audio, has MIDI)

```javascript
// @apparat mybass 1 1
// @param cutoff 1000 20 20000 exp Hz
// @param resonance 0.3 0 1 linear

class Processor {
  p = {cutoff: 1000, resonance: 0.3}
  sr = sampleRate
  phase = 0
  voices = []           // active voices
  
  constructor() {
    // init filter state, etc.
  }
  
  paramChanged(label, value) {
    this.p[label] = value
  }
  
  process(output, block) {
    // output[0], output[1] = output channels (WRITE ONLY)
    // NO input — this generates audio
    // block.s0, block.s1, block.p0, block.p1, block.bpm
    
    for (let i = block.s0; i < block.s1; i++) {
      let sum = 0
      for (const v of this.voices) {
        v.phase += v.freq / this.sr
        if (v.phase >= 1) v.phase -= 1
        sum += Math.sin(v.phase * 2 * Math.PI) * v.amp
      }
      // Simple one-pole lowpass filter
      this.lastOut = this.lastOut || 0
      const cutoff = this.p.cutoff / this.sr
      this.lastOut = this.lastOut + cutoff * (sum - this.lastOut)
      output[0][i] = this.lastOut
      output[1][i] = this.lastOut
    }
  }
  
  noteOn(pitch, velocity, cent, id) {
    // pitch = MIDI note number
    // velocity = 0..1
    // cent = pitch bend in cents
    // id = unique note ID (for matching noteOff)
    const freq = 440 * Math.pow(2, (pitch - 69 + cent/100) / 12)
    this.voices.push({freq, amp: velocity, phase: 0, id})
  }
  
  noteOff(id) {
    // Remove voice by id
    this.voices = this.voices.filter(v => v.id !== id)
  }
}
```

### Spielwerk (MIDI effect — generator, yields notes)

```javascript
// @spielwerk myarp 1 1
// @param rate 0.5 0.05 4 linear
// @param octaves 2 1 4 int

class Processor {
  p = {rate: 0.5, octaves: 2}
  step = 0
  
  paramChanged(label, value) {
    this.p[label] = value
  }
  
  ;*process(block, events) {
    // block.from, block.to = ppqn range (NOT p0/p1!)
    // events = Iterable of MIDI events with {position, duration, pitch, velocity, gate}
    // MUST be a generator — yield note events
    
    for (const ev of events) {
      if (ev.gate) {
        // Arpeggiate: yield multiple notes from one input note
        for (let oct = 0; oct < this.p.octaves; oct++) {
          yield {
            position: ev.position + this.step * this.p.rate * 960,
            duration: ev.duration * 0.5,
            pitch: ev.pitch + oct * 12,
            velocity: ev.velocity * (1 - oct * 0.15)
          }
          this.step++
        }
      }
    }
  }
  
  reset() {
    this.step = 0
  }
}
```

## DSP Patterns

### One-pole filter (lowpass/highpass)

```javascript
// Lowpass
let lp = 0
const coeff = Math.exp(-2 * Math.PI * cutoff / this.sr)
for (let i = s0; i < s1; i++) {
  lp = lp + (1 - coeff) * (input[i] - lp)
  output[i] = lp
}

// Highpass
let hp = 0, lp = 0
for (let i = s0; i < s1; i++) {
  lp = lp + (1 - coeff) * (input[i] - lp)
  hp = input[i] - lp
  output[i] = hp
}
```

### State-variable filter (LP/HP/BP simultaneously)

```javascript
let low = 0, band = 0
const f = 2 * Math.sin(Math.PI * cutoff / this.sr)
const q = 1 / resonance
for (let i = s0; i < s1; i++) {
  low += f * band
  band += f * (input[i] - low - q * band)
  // low = lowpass, band = bandpass, input - low - q*band = highpass
  output[i] = low  // or band, or highpass
}
```

### Tanh saturation (soft clip)

```javascript
// Drive parameter controls intensity
const driven = input * drive
output = Math.tanh(driven)  // soft clip
// Or polynomial approximation (faster):
// output = driven - (driven*driven*driven)/3  // cubic soft clip
```

### Wavefolding

```javascript
// fold = threshold where signal reflects back
for (let i = s0; i < s1; i++) {
  let s = input[i] * drive
  while (s > 1) s = 2 - s    // reflect
  while (s < -1) s = -2 - s
  output[i] = s * (1 - 0.3 * (1 - mix))  // attenuate slightly
}
```

### Bitcrush + sample rate reduction

```javascript
const bits = 8  // 1-16
const crush = Math.pow(2, bits) - 1
const hold = 4  // samples to hold (rate reduction)
let last = 0, counter = 0
for (let i = s0; i < s1; i++) {
  if (counter++ % hold === 0) {
    last = Math.round(input[i] * crush) / crush
  }
  output[i] = last
}
```

### Comb filter (reverb/delay building block)

```javascript
const delaySamples = Math.floor(this.sr * delayMs / 1000)
const buffer = new Float32Array(delaySamples)
let pos = 0
for (let i = s0; i < s1; i++) {
  const delayed = buffer[pos]
  buffer[pos] = input[i] + delayed * feedback
  output[i] = delayed
  pos = (pos + 1) % delaySamples
}
```

### DC blocker (one-pole highpass ~20Hz)

```javascript
let prevIn = 0, prevOut = 0
const coeff = 0.995  // ~20Hz at 44100
for (let i = s0; i < s1; i++) {
  const out = input[i] - prevIn + coeff * prevOut
  prevIn = input[i]
  prevOut = out
  output[i] = out
}
```

### LFO (sine, for modulation)

```javascript
// block.p0 = position in samples, block.bpm = tempo
const lfoFreq = 4  // Hz
const lfoPhase = (block.p0 / this.sr) * lfoFreq * 2 * Math.PI
for (let i = s0; i < s1; i++) {
  const lfo = 0.5 + 0.5 * Math.sin(lfoPhase + (i - s0) / this.sr * lfoFreq * 2 * Math.PI)
  output[i] = input[i] * (0.5 + lfo * depth)
}
```

### Envelope follower (for sidechain/ducking)

```javascript
let env = 0
const attack = 0.005  // 5ms
const release = 0.08  // 80ms
const aCoeff = Math.exp(-1 / (this.sr * attack))
const rCoeff = Math.exp(-1 / (this.sr * release))
for (let i = s0; i < s1; i++) {
  const abs = Math.abs(input[i])
  if (abs > env) env = aCoeff * env + (1 - aCoeff) * abs
  else env = rCoeff * env + (1 - rCoeff) * abs
}
// env = envelope amplitude (0..1), use for gain reduction
```

### ADSR envelope (for Apparat instruments)

```javascript
class Voice {
  constructor(freq, vel) {
    this.freq = freq
    this.vel = vel
    this.phase = 0
    this.env = 0
    this.stage = 'attack'
    this.time = 0
  }
  
  process(sr, a, d, s, r) {
    this.time += 1 / sr
    switch (this.stage) {
      case 'attack':  this.env = this.time / a; if (this.time >= a) { this.stage = 'decay'; this.time = 0 } break
      case 'decay':   this.env = 1 - (1 - s) * (this.time / d); if (this.time >= d) { this.stage = 'sustain' } break
      case 'sustain': this.env = s; break
      case 'release': this.env = s * (1 - this.time / r); if (this.time >= r) { this.env = 0; this.stage = 'done' } break
    }
    this.env = Math.max(0, Math.min(1, this.env))
    this.phase += this.freq / sr
    if (this.phase >= 1) this.phase -= 1
    return Math.sin(this.phase * 2 * Math.PI) * this.env * this.vel
  }
  
  release() { this.stage = 'release'; this.time = 0 }
}
```

## Validation Workflow

### 1. JS syntax check (local)

```bash
node --check script.js
# catches syntax errors, ASI issues, missing semicolons
```

### 2. Bridge compile test

```python
import json
from server import HeadlessDawBridge

async def test_compile():
    bridge = HeadlessDawBridge()
    await bridge.start()
    code = open("script.js").read()
    code_escaped = json.dumps(code)
    r = await bridge.evaluate(f"""
        () => {{
            try {{
                eval({code_escaped});
                return {{ok: true}};
            }} catch(e) {{
                return {{ok: false, error: e.message}};
            }}
        }}
    """)
    print(r)  # {ok: true} or {ok: false, error: "..."}
    await bridge.stop()

import asyncio
asyncio.run(test_compile())
```

### 3. Full compile via ScriptCompiler

```python
# set_script_device_code uses ScriptCompiler.compile() internally:
# - Parses @param → creates WerkstattParameterBox
# - Parses @sample → creates WerkstattSampleBox
# - Validates JS via new Function()
# - Registers worklet
# All in one editing.modify() block

await mcp_opendaw_set_script_device_code("Werkstatt", unit_index, effect_index, code)
```

### 4. Param test

```python
# List params (should match @param declarations)
await mcp_opendaw_list_script_params("Werkstatt", unit_index, effect_index)

# Set a param (validates + clamps)
await mcp_opendaw_set_script_param("Werkstatt", unit_index, effect_index, "drive", 0.85)
```

## CRITICAL Pitfalls

### 1. Spielwerk block.from/block.to ≠ Werkstatt block.p0/block.p1

```javascript
// WRONG (Werkstatt style in Spielwerk):
process(block, events) {
  for (let i = block.p0; i < block.p1; i++) { ... }  // undefined!
}

// CORRECT (Spielwerk):
;*process(block, events) {
  for (const ev of events) {
    if (ev.position >= block.from && ev.position < block.to) { ... }
  }
}
```

### 2. ASI bug — semicolon before `*process`

```javascript
class Processor {
  p = {rate: 0.5}    // last class field
  
  ;*process(block, events) {  // semicolon prevents ASI misparse
    // Without ;, JS parses as: this.p = {rate: 0.5} * process(...)
    // which is multiplication, not generator method
  }
}
```

### 3. Werkstatt has NO MIDI input

Werkstatt implements `AudioEffectDeviceProcessor`, NOT `NoteEventTarget`.
No `noteOn`/`noteOff` callbacks. The `Block` type has no MIDI events.

For MIDI-triggered behavior in an audio effect: use **envelope following** from input audio.
See `werkstatt_ringmod_env.js` as reference.

### 4. Apparat is the ONLY scriptable device with MIDI

`noteOn(pitch, velocity, cent, id)` and `noteOff(id)`.
`id` is a unique identifier — match it in `noteOff` to find the right voice.

### 5. sampleRate is globalThis, not this

```javascript
class Processor {
  sr = sampleRate   // globalThis.sampleRate — available in class body
  // NOT this.sr = sampleRate (not set at class body eval time)
}
```

### 6. No DOM access

Scripts run in AudioWorklet — no `window`, `document`, `console`, `fetch`.
Use `sampleRate` (global), `block.bpm`, `block.p0`/`block.p1` for context.

### 7. Float32Array, not regular Array

All audio buffers are `Float32Array`. Don't create regular arrays for audio:
```javascript
const buf = new Float32Array(size)  // correct
const buf = new Array(size)          // wrong — no typed array methods
```

### 8. Don't allocate in process()

```javascript
// WRONG — allocates every block, GC pressure:
process(io, block) {
  const temp = new Float32Array(block.s1 - block.s0)  // NO!
}

// CORRECT — allocate in constructor:
constructor() {
  this.temp = new Float32Array(1024)  // pre-allocate
}
process(io, block) {
  // reuse this.temp
}
```

## Example Scripts (85 in library)

### Werkstatt (67 audio effects)

| Script | Pattern | Key technique |
|--------|---------|---------------|
| `werkstatt_darksat.js` | Tape saturation | tanh + DC blocker + tone shelving |
| `werkstatt_coldfold.js` | Wavefolding | mirror reflection + bitcrush |
| `werkstatt_reverb.js` | Plate reverb | 4 comb + 2 allpass per channel |
| `werkstatt_convolution_reverb.js` | Convolution reverb | generated stereo IR + time-domain direct convolution |
| `werkstatt_dynamic_eq.js` | Dynamic EQ | peaking biquad + envelope follower per band |
| `werkstatt_multitap_delay.js` | Multitap delay | single buffer + 4 parallel taps + equal-power pan |
| `werkstatt_dimension_chorus.js` | Dimension chorus | dual detuned delay lines + independent triangle LFOs + no feedback |
| `werkstatt_autowah.js` | Autowah (env-followed) | envelope follower → biquad cutoff modulation (3 modes) |
| `werkstatt_octaver.js` | Octaver (sub-octave) | zero-crossing flip-flop /2 and /4, envelope tracking, hysteresis |
| `werkstatt_fuzz.js` | Fuzz (Big Muff) | hard clip + foldback squash + full-wave rect octave-up + Muff tone stack + noise gate |
| `werkstatt_tape_stop.js` | Tape stop | exponential speed decay to zero + pitch drop + state machine + fractional buffer read |
| `werkstatt_multiband_imager.js` | Multiband imager | LR4 crossover → 3-band M/S width control, mono bass default, link mode |
| `werkstatt_modal_resonator.js` | Modal resonator | parallel bandpass biquads at modal frequency ratios, 5 materials, inharmonicity stretch |
| `werkstatt_multiband_saturator.js` | Multiband saturator | LR4 crossover 3-band + per-band drive + 3 saturation characters (tape/tube/transistor) |
| `werkstatt_vinyl.js` | Vinyl simulator | crackle/pops via LCG envelopes + surface noise + wow/flutter pitch wobble + wear HF rolloff |
| `werkstatt_grain_delay.js` | Grain delay | Hann-windowed grains from delay buffer + pitch shift + scatter + reverse + pan + feedback |
| `werkstatt_gated_reverb.js` | Gated reverb | Schroeder plate + envelope-followed gate on dry input → hard tail cutoff, 80s drum sound |
| `werkstatt_reverse_delay.js` | Reverse delay | reads delay buffer backwards + fade ramps at boundaries + damped feedback for cascading reverse repeats |
| `werkstatt_freq_shifter.js` | Frequency shifter (SSB) | Hilbert transform allpass pair + complex carrier oscillator → shifts all frequencies by fixed Hz, breaks harmonic ratios |
| `werkstatt_bass_enhancer.js` | Bass enhancer | LPF isolates bass → full-wave rectification → sub-harmonic LPF + HPF DC removal → tanh harmonic saturation → band replacement, psychoacoustic missing fundamental |
| `werkstatt_tilt_eq.js` | Tilt EQ | low shelf (RBJ) + high shelf (RBJ) with single tilt knob, pivot freq, steepness slope, coefficient caching |
| `werkstatt_svf.js` | State variable filter | Chamberlin topology: HP=input-LP-q*BP, BP+=f*HP, LP+=f*BP, morph blend LP→BP→HP, notch/allpass modes, tanh soft-clip |
| `werkstatt_chorus.js` | Modulated delay | LFO + fractional read |
| `werkstatt_phaser.js` | Allpass cascade | 6-stage allpass + quadrature LFO |
| `werkstatt_spectral_enhancer.js` | Spectral enhancer | STFT radix-2 FFT, Hann window, high-freq air boost above crossover, spectral peak emphasis, transient enhancement, stereo widening |
| `werkstatt_formant_shifter.js` | Formant shifter | LPC Levinson-Durbin, lattice filter, formant frequency scaling independent of pitch, gender/age morphing |
| `werkstatt_lookahead.js` | Compressor | envelope follower + lookahead buffer |
| `werkstatt_shimmer.js` | Pitch-shift delay | delay buffer + pitch shift + feedback |
| `werkstatt_paulstretch.js` | Extreme stretch | FFT phase randomization |
| `werkstatt_envfollower.js` | Envelope follower | attack/release coefficients |
| `werkstatt_adsr_trim.js` | ADSR trim | envelope detection + gate |
| `werkstatt_granular_stretch.js` | Granular | grain windows + overlap |
| `werkstatt_pitch_shift.js` | Pitch shift | delay buffer + head ratio |
| `werkstatt_dcremover.js` | DC + width | one-pole HPF + M/S |
| `werkstatt_allpass.js` | Allpass filter | nested allpass stages |
| `werkstatt_ringmod_env.js` | Ring mod | env follower + sine oscillator |

### Apparat (5 instruments)

| Script | Pattern | Key technique |
|--------|---------|---------------|
| `apparat_darkbass.js` | Subtractive bass | saw + one-pole LPF + ADSR |
| `apparat_subcrusher.js` | Sub-bass | sub-osc + drive + filter |
| `apparat_coldlead.js` | Lead with glide | portamento + SVF + ADSR |
| `apparat_ringmod.js` | Ring mod synth | sine carrier × modulator |
| `apparat_fm.js` | 2-op FM | carrier + modulator + feedback |
| `apparat_supersaw.js` | Supersaw (7-voice) | 7 detuned saws + per-voice stereo pan + resonant LPF |

### Spielwerk (10 MIDI effects)

| Script | Pattern | Key technique |
|--------|---------|---------------|
| `spielwerk_arpeggiator.js` | Arp + swing | note generator + timing |
| `spielwerk_powerchord.js` | Chord gen | interval + detune |
| `spielwerk_chordmemory.js` | Chord shapes | 7 chord types + octave |
| `spielwerk_strum.js` | Strummer | staggered note timing |
| `spielwerk_velocity.js` | Vel scaler | curve + offset + clamp |
| `spielwerk_mididelay.js` | MIDI delay | feedback + transpose + decay |
| `spielwerk_scale_quantizer.js` | Scale quantizer | 14 scales + nearest-note snap |
| `spielwerk_harmonizer.js` | MIDI harmonizer | 3 voices, diatonic/fixed, 14 scales |
| `spielwerk_prob_gate.js` | Probability gate | LCG note dropping, 3 modes, hold momentum, forced pass zones |
| `spielwerk_chorder.js` | Chord voicer | 13 chord shapes, 5 voicings (close/drop2/drop3/open/spread), 4 inversions |

## Creating .opb Presets from Scripts

After writing and testing a Werkstatt script, package it as a preset:

```python
# 1. Add Werkstatt effect to a unit
await mcp_opendaw_add_effect(unit_index, "Werkstatt")

# 2. Load your script code
code = open("my_script.js").read()
await mcp_opendaw_set_script_device_code("Werkstatt", unit_index, effect_index, code)

# 3. Set params to desired preset values
await mcp_opendaw_set_script_param("Werkstatt", unit_index, effect_index, "drive", 0.7)

# 4. Save as .opb preset
await mcp_opendaw_save_effect_preset(unit_index, effect_index, "My Preset", "Description", "/tmp/my_preset.opb")
```

## Related Skills

- `opendaw-sound-design` — using existing instruments + DSP scripts (this skill is about WRITING new ones)
- `opendaw-automation` — 413 MCP tools, ScriptCompiler internals, bridge API
- `adaptive-mix-mastering` — where custom DSP fits in the mix pipeline
- `suno-to-opendaw` — full Suno→openDAW workflow
