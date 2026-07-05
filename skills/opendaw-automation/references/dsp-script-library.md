# DSP Script Library — 26 scripts

All scripts live in `opendaw-mcp/scripts/` and `openDAW/examples/{werkstatt,apparat,spielwerk}/`. Each compiles via `ScriptCompiler` and exposes `@param` declarations with mapping metadata. 11 scripts cover open upstream issues (#91, #133, #138, #139, #188, #195, #201, #209, #241, #277 — see `references/upstream-issue-coverage.md`).

## Werkstatt (audio effects — 15 scripts)

| Script | File | Params | Mapping types | Upstream issue |
|--------|------|--------|---------------|----------------|
| Dark Saturation | `werkstatt_darksat.js` | drive, bias, tone, mix, output | linear, linear, linear, linear, linear | #91 (DC blocker) |
| Cold Fold | `werkstatt_coldfold.js` | drive, fold, crush, slew, mix | linear, linear, linear, linear, linear | |
| Plate Reverb | `werkstatt_reverb.js` | decay, predelay, damping, width, mix | linear, linear, linear, linear, linear | |
| Stereo Chorus | `werkstatt_chorus.js` | rate, depth, center, feedback, mix | exp, linear, linear, linear, linear | #195 |
| Phaser | `werkstatt_phaser.js` | rate, depth, feedback, stages, mix | exp, linear, linear, int, linear | #133 (allpass) |
| Lookahead Comp | `werkstatt_lookahead.js` | threshold, ratio, attack, release, knee, makeup, mix | linear, linear, exp, exp, linear, linear, linear | |
| Shimmer Delay | `werkstatt_shimmer.js` | time, feedback, pitch, shimmer, damping, mix | exp, linear, int, linear, linear, linear | |
| Paulstretch | `werkstatt_paulstretch.js` | stretch, window, mix | linear, linear, linear | #209 |
| Envelope Follower | `werkstatt_envfollower.js` | attack, release, depth, threshold, invert, makeup | linear, linear, linear, linear, bool, linear | #139 |
| ADSR Trim | `werkstatt_adsr_trim.js` | attack, decay, sustain, release, threshold, mix | exp, exp, linear, exp, linear, linear | #241 |
| Granular Stretch | `werkstatt_granular_stretch.js` | stretch, grain, overlap, pitch, mix | exp, linear, linear, int, linear | #201 |
| Pitch Shift | `werkstatt_pitch_shift.js` | semitones, cents, latency, mix | linear, linear, exp, linear | #188 |
| DC Remover | `werkstatt_dcremover.js` | dc_freq, width, balance, mix | exp, linear, linear, linear | #91 |
| Allpass Filter | `werkstatt_allpass.js` | freq, stages, invert, feedback, mix | exp, int, bool, linear, linear | #133 |
| Ring Mod + Env Follow | `werkstatt_ringmod_env.js` | freq, modDepth, modRange, attack, release, threshold, mix, output | exp, linear, linear, linear, linear, linear, linear, linear | #277 |

## Apparat (instruments — 5 scripts)

| Script | File | Params | Upstream issue |
|--------|------|--------|----------------|
| Dark Bass | `apparat_darkbass.js` | waveform, cutoff, resonance, attack, decay, subOsc, volume | |
| Cold Lead | `apparat_coldlead.js` | waveform, cutoff, resonance, attack, decay, glide, volume | |
| Sub Crusher | `apparat_subcrusher.js` | waveform, cutoff, resonance, drive, sub, volume | |
| Ring Modulator | `apparat_ringmod.js` | frequency, waveform, attack, decay, sustain, release, adsrAmount, subOsc, volume | #277 |
| FM Synth | `apparat_fm.js` | carrier, ratio, mod_depth, waveform, attack, decay, sustain, release, volume | #138 |

## Spielwerk (MIDI effects — 6 scripts)

| Script | File | Params |
|--------|------|--------|
| Arpeggiator | `spielwerk_arpeggiator.js` | rate, mode, octaves, gate |
| Powerchord | `spielwerk_powerchord.js` | interval, interval2, velScale, detune |
| Chord Memory | `spielwerk_chordmemory.js` | chord, octave, velocity |
| Strummer | `spielwerk_strum.js` | speed, direction, spread, velocity |
| Velocity Scaler | `spielwerk_velocity.js` | scale, offset, curve, min_vel, max_vel |
| MIDI Delay | `spielwerk_mididelay.js` | time, feedback, repeats, transpose, decay |

**CRITICAL: Spielwerk `block` uses `from`/`to`, NOT `p0`/`p1`.** The Spielwerk `UserBlock` interface (`SpielwerkDeviceProcessor.ts` line 57) is `{from, to, bpm, s0, s1, flags}` — `from`/`to` are ppqn positions. This is different from Werkstatt/Apparat's `Block` type which uses `{p0, p1, s0, s1, bpm, flags, index}`. CodeRabbit caught this in `spielwerk_arpeggiator.js` where `block.p0`/`block.p1` were used instead of `block.from`/`block.to`. Always use `block.from`/`block.to` in Spielwerk scripts.

## DSP implementation patterns

All Werkstatt scripts use the correct `process(io, block)` + `paramChanged(label, value)` API (rewritten v1.11.1 after discovering the original scripts used the wrong `processAudio(inputs, outputs, parameters)` contract).

### Werkstatt pattern (audio effect)
```javascript
class Processor {
  constructor() {
    this.sr = sampleRate  // globalThis in worklet
    // allocate buffers, init state
    this.p = {param1: default1, param2: default2}  // param store
  }
  paramChanged(label, value) { this.p[label] = value }
  process(io, block) {
    // io.src[0/1] = input, io.out[0/1] = output
    for (let i = block.s0; i < block.s1; i++) {
      io.out[0][i] = /* DSP on io.src[0][i] */
      io.out[1][i] = /* DSP on io.src[1][i] */
    }
  }
}
```

### Apparat pattern (instrument — generates audio, NO input)
```javascript
class Processor {
  constructor() { this.sr = sampleRate; /* init oscillators, envelopes */ }
  paramChanged(label, value) { this[label] = value }
  process(output, block) {
    // output = [Float32Array, Float32Array] — write only, no input
    for (let i = block.s0; i < block.s1; i++) {
      output[0][i] = /* generate sample */
      output[1][i] = /* generate sample */
    }
  }
}
```

### Spielwerk pattern (MIDI effect — generator function, yields notes)
```javascript
class Processor {
  paramChanged(label, value) { this[label] = value }
  *process(block, events) {  // MUST be generator — yield note events
    for (const ev of events) {
      if (ev.gate) {
        yield { position: ev.position, duration: ev.duration, pitch: ev.pitch, velocity: ev.velocity }
      }
    }
  }
  reset() {}  // optional
}
// PITFALL: add semicolon after last class field before *process to avoid ASI bug
```

### Schroeder reverb (werkstatt_reverb.js)
**Separate L/R comb banks** with decorrelated delay times (L: 29.7/37.1/41.1/43.7ms, R: 30.1/36.5/41.7/43.3ms) + separate L/R allpass (L: 5.0/1.7ms, R: 4.8/1.9ms). Per-channel predelay buffers. Per-comb damping state. Comb indices advance each sample. **M/S stereo width decode on the REVERB TAIL** (not dry signal): `mid = (wetL+wetR)*0.5; side = (wetL-wetR)*0.5*width; wL = mid+side; wR = mid-side`. CodeRabbit caught that the original mono comb bank + dry-signal side chain meant `width` controlled dry channel balance, not reverb spread. Fix: separate stereo comb/allpass banks with decorrelated times → true stereo reverb tail → M/S width operates on wet signal. Extracted comb/allpass processing into `_combProcess()` and `_apProcess()` helper methods to avoid code duplication across L/R banks.

### Stereo chorus (werkstatt_chorus.js)
Two LFOs 90° apart. Fractional delay read via linear interpolation. Circular buffer maxDelay = **sr*0.15** (increased from sr*0.1 after CodeRabbit found depth modulation at max center=0.05s could exceed the buffer — delay = center*(1+depth) = 0.05*44100*2 = 4411 = old buffer size exactly, zero headroom). Safe modulo: `((idx - delay) % maxDelay + maxDelay) % maxDelay` for negative indices.

### Phaser (werkstatt_phaser.js)
**1st-order allpass** cascade (2-8 stages). LFO sweeps 200-8000 Hz. CodeRabbit caught that the original 2nd-order allpass recurrence was not standard and could become unstable, tripping the host's output protection. Switched to stable 1st-order allpass: `tanw = tan(π*freq/sr); a = (1-tanw)/(1+tanw); y = -a*x + z1; z1 = x + a*y`. Stereo with per-channel state arrays. Feedback loop via `this.fb[c]`.

### Lookahead compressor (werkstatt_lookahead.js)
Peak envelope detector with attack/release coefficients (`exp(-1/(time*sr))`). Soft knee: quadratic transition between kneeStart and kneeEnd. Gain reduction in dB domain. Makeup gain in linear. Lookahead buffer = sr*0.01. **Gain reduction applies to the delayed signal** (true lookahead — CodeRabbit caught that the original applied gain to the non-delayed input, making the "lookahead" label a lie).

### Shimmer delay (werkstatt_shimmer.js)
Granular pitch shift via circular buffer resampling (write at 1x, read at ratio speed). Crossfade via linear interp. Delay buffer maxLen=sr (1s). **Per-channel pitch shifter state** — CodeRabbit caught that shared `pitchBuf`/`pWriteIdx`/`pitchPhase` caused stereo crosstalk and doubled pitch ratio. Each channel gets its own `Float32Array(4096)` + write index + read phase. Per-channel damping state in feedback path.

### Reverb (werkstatt_reverb.js)
Schroeder plate: 4 comb filters (29.7/37.1/41.1/43.7ms) + 2 allpass (5.0/1.7ms). **Per-comb damping state** (CodeRabbit caught shared damping across all combs). **Comb indices advance** each sample (original was stuck on same slot). **M/S stereo width decode**: `mid = wet*0.707; side = (dryL-dryR)*0.707*width; wL = mid+side; wR = mid-side` (original used channel balance, not true width).

### CodeRabbit DSP review patterns (recurring issues)

When writing Werkstatt/Apparat/Spielwerk DSP scripts, watch for these patterns that CodeRabbit consistently catches:

1. **Undefined variable from typo** — `outR` vs `outGain`, `outL` vs `outGain`. Name gain variables explicitly (`outGain`, not channel-specific names).
2. **Delay buffer too small** — modulation (depth, LFO) can push delay time beyond buffer size. Size for max excursion, typically 2× the max center delay.
3. **Negative modulo** — JavaScript `%` operator returns negative for negative operands. Use `((x % n) + n) % n` for circular buffer indices.
4. **Shared state across channels** — stereo processing needs per-channel buffers/phases for pitch shifters, comb filters, envelope followers.
5. **Parameter scaling disconnect** — `@param slew 0 0 1 linear` gives 0–1, but `/100` in process() makes it 0–0.01 (disabled). Don't add arbitrary scaling.
6. **Lookahead not actually looking ahead** — envelope must track current input, gain reduction must apply to delayed signal.
7. **Unstable filter topologies** — non-standard allpass recursions can blow up. Use well-known 1st/2nd-order forms.
8. **Swing/grid dropping notes at block boundaries** — in Spielwerk generators, don't `break` on `notePos >= to`; yield the note anyway so the engine schedules it next block.
9. **Spielwerk `block.from`/`block.to` vs Werkstatt `block.p0`/`block.p1`** — the two device types have DIFFERENT block interfaces. Spielwerk `UserBlock` is `{from, to, bpm, s0, s1, flags}` (line 57 of `SpielwerkDeviceProcessor.ts`). Werkstatt/Apparat `Block` is `{p0, p1, s0, s1, bpm, flags, index}`. Using `block.p0` in a Spielwerk script silently produces `undefined` → notes never generate. CodeRabbit caught this in `spielwerk_arpeggiator.js`.
10. **Chorus delay buffer zero headroom** — if max delay = center*(1+depth) exactly equals buffer size, edge-case modulation produces NaN. Size buffer at 1.5× or 2× the max theoretical delay, not exactly the max.
11. **Reverb `width` controlling dry signal, not wet** (reverb) — M/S width decode must operate on the reverb tail (wetL/wetR), not on the dry input (dryL/dryR). If `side = (dryL-dryR)*width`, you're panning the dry signal, not controlling reverb spread. Fix: separate L/R comb banks with decorrelated delay times → true stereo wet signal → `side = (wetL-wetR)*0.5*width`.
12. **Paulstretch cursor coupling** (paulstretch) — if `processFrame()` advances `inputPos` by `hopSize` AND the sample loop advances it by 1 per sample, playback and synthesis cursors are coupled → frames fire at wrong times. Fix: separate `inputWritePos` (playback, +1 per sample) from `overlapReadPos` (synthesis, +1 per sample). `processFrame()` reads from `inputWritePos` but does NOT advance it. Frame emission gated by `samplesAccumulated >= hopSize`, not by `inputSize` buffer check (which is always true for a full buffer).

### Paulstretch (werkstatt_paulstretch.js — issue #209)
Paul Nasca's extreme time-stretch algorithm. FFT → randomize phase (keep magnitude) → IFFT → overlap-add. Hann window applied both before FFT and after IFFT. Radix-2 Cooley-Tukey FFT in-place. Window size maps 0→1024, 1→16384 samples. Stretch factor 0→1x (passthrough), 1→100x. Hop size = windowSize / stretchFactor. Input circular buffer 2×window, output overlap buffer 1×window. Mono-summed input (L+R)/2. **Separate read/write cursors**: `inputWritePos` (playback — advances per input sample) and `overlapReadPos` (synthesis — advances per output sample). CodeRabbit caught that the original shared a single `inputPos`/`overlapPos` between playback and synthesis, and `processFrame()` mutated `inputPos` by `hopSize`, causing cursor coupling. Fix: `processFrame()` reads from `inputWritePos` (lookback `windowSize` samples) but does NOT advance it — frame emission is gated by `samplesAccumulated >= hopSize` counter, not `inputSize` buffer check. `overlapReadPos` advances independently in the sample loop. NOTE: computationally heavy — FFT per frame in JS worklet, not optimized. Good for demonstration; real-time use may xrun on long windows.

### Envelope follower (werkstatt_envfollower.js — issue #139)
Tracks input amplitude and applies as gain modulation (sidechain-style). Attack/release coefficients via `exp(-1/(time*sr))`. Attack maps 0→500ms, 1→0.5ms. Release maps 0→2000ms, 1→2ms. Invert param: 0=boosting (loud→louder), 1=ducking (loud→quieter, expander behavior). Threshold gate: envelope below threshold → zero modulation. Makeup gain: 0→-12dB, 0.5→0dB, 1→+12dB (via `pow(4, (makeup-0.5)*2)`). Useful as DIY sidechain compressor without needing a sidechain input.

### ADSR trim (werkstatt_adsr_trim.js — issue #241)
Gates sustained samples by detecting envelope state. State machine: idle→attack→decay→sustain→release→idle. Attack/decay/release are exp time constants. Threshold triggers state transitions. When envelope drops below threshold after release, output is silenced. Useful for trimming long-sustained Soundfont samples that don't naturally fade out. Mix param blends gated vs original.

### Granular time-stretch (werkstatt_granular_stretch.js — issue #201)
Granular synthesis for time-stretching: Hann-windowed grains read from circular input buffer at 1/stretch speed. Two overlapping grains with configurable overlap ratio. Pitch shift via `pow(2, semitones/12)` ratio applied to grain read position. Grain size configurable (20–500ms). Buffer size = 4 seconds. Normalization factor 0.5 for two-grain overlap.

### Pitch shifter (werkstatt_pitch_shift.js — issue #188)
Classic delay-line pitch shift with crossfading read taps. Two read heads sweep a delay buffer (0.5s) at `|ratio-1|/sweepRange` rate. Delay sweeps linearly 0→latencySamps (pitch down: delay grows; pitch up: delay shrinks). Crossfade via complementary raised-cosine windows (`0.5*(1-cos(2π*phase))`), taps offset by half cycle. Linear-interpolated buffer reads. Ratio = `pow(2, (semitones + cents/100)/12)`. Latency param trades smoothness vs delay (10–200ms). PITFALL: delay sweep must be LINEAR (not cosine) to maintain constant pitch — a cosine sweep creates warble. The crossfade window is cosine, not the delay itself.

### Ring modulator synth (apparat_ringmod.js — issue #277)
Apparat instrument with MIDI-triggered ADSR + ring modulation. Carrier oscillator (sine/triangle/saw/square) at `frequency` param. Sub-oscillator one octave down acts as ring modulator: `sample = carrier * (1 - subLevel + subLevel * sub)`. ADSR envelope (attack/decay/sustain/release) modulates carrier frequency via `adsrAmount`: `modFreq = baseFreq * (1 + adsrAmt * env * 0.5)`. State machine: idle→attack→decay→sustain→release→idle. `noteOn(freq, velocity)` and `noteOff()` methods called by engine on MIDI events. This addresses #277 (MIDI input for Werkstatt) by using Apparat instead — Apparat is an instrument that natively receives MIDI, while Werkstatt is an audio effect that cannot. PITFALL: Apparat E2E testing requires complex AU setup (CaptureAudioBox + AudioUnitBox + InstrumentFactories.Apparat) — simpler to validate JS syntax via `node -e 'new Function(code)'` and rely on the same Processor API pattern as other Apparat scripts.

### DC remover + stereo tool (werkstatt_dcremover.js — issue #91)
One-pole highpass DC blocker at configurable cutoff (0.5–20 Hz, default 2 Hz). DC tracking: `this.dcL = inL + (this.dcL - inL) * dcCoef` where `dcCoef = exp(-2π*freq/sr)`. Highpassed output = `inL - this.dcL`. After DC removal, M/S stereo width control: `mid = (hpL+hpR)*0.5; side = (hpL-hpR)*0.5*width; wL = mid+side; wR = mid-side`. Balance param attenuates one channel (positive→attenuate L, negative→attenuate R). Mix blends processed vs original. Addresses #91 (DC remove button / stereo tool) — while the issue asks for a UI button on the native Stereo Tool, this Werkstatt script provides the same functionality as a scriptable effect.

### Allpass filter (werkstatt_allpass.js — issue #133)
1st-order allpass cascade (1–8 stages, same stable `_ap1` topology as phaser). Frequency param sweeps 20–20000 Hz. `invert` bool flips output phase. Feedback loop via `this.fb[c]`. Addresses #133 by providing the allpass filter with frequency, invert, and iteration count (stages) controls requested in the issue. The `stages` knob maps directly to "how many iterations the effect is used" (1–8 cascade depth).

### FM synth (apparat_fm.js — issue #138)
2-operator FM synthesis: carrier phase modulated by modulator output. `modSig = _wave(modPhase, wave) * mod_depth * env; sample = _wave(phase + modSig, wave) * env * vol`. Modulator frequency = `carrier * ratio` (0.25–16). 4 waveforms: sine/triangle/saw/square. ADSR envelope (state machine: attack→decay→sustain→release→idle). Addresses #138 (FM/PM synth request) — while not a full Sytrus-style routing matrix, demonstrates the core FM concept as an Apparat script. The `mod_depth` param controls FM intensity (0 = pure carrier, higher = more harmonic content). Both carrier and modulator use the same waveform selection.

### Ring modulator with envelope following (werkstatt_ringmod_env.js — issue #277)
Werkstatt audio effect: ring modulator where **input audio amplitude** triggers an ADSR-style envelope that modulates the carrier frequency. This is the workaround for #277 (MIDI input for Werkstatt — see `references/werkstatt-midi-limitation-and-release-pitfalls-2026-07-04.md`). Since Werkstatt is an audio effect without `noteOn`/`noteOff`, routing rhythmic audio (drums) into the input simulates MIDI-triggered behavior. State machine: 0=idle, 1=attack, 2=release. Attack: `aCoeff = exp(-1/(sr*attackMs*0.001))`, env rises to ~1.0, then transitions to release. Modulated frequency: `freq * (1 + modDepth * env * (modRange - 1))`. Carrier is sine wave. Mix blends dry + wet (ring-modulated) signal. Output gain: `pow(4, (output-0.5)*2)` for -12..+12 dB range.

## Testing

All scripts verified end-to-end via bridge:
```python
# Load and compile
await mcp_opendaw_set_script_device_code('Werkstatt', 0, werk_idx, code)
# Verify params with mapping info
await mcp_opendaw_list_script_params('Werkstatt', 0, werk_idx)
# Test param setting with clamping
await mcp_opendaw_set_script_param('Werkstatt', 0, werk_idx, 'cutoff', 99999)  # → clamped to 20000
```

Maximizer is at effect index 0 — always find Werkstatt by class name, not hardcoded index.
