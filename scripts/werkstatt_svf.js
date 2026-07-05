// @werkstatt svf 1 1
// @label State Variable Filter (Chamberlin)
// @param cutoff 1000 20 20000 exp Hz
// @param resonance 0.5 0 1 linear
// @param morph 0 0 1 linear
// @param output_mode 0 0 2 linear
// @param drive 0 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {cutoff: 1000, resonance: 0.5, morph: 0, output_mode: 0, drive: 0, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // SVF state (Chamberlin topology): LP and BP integrators
  lpL = 0; bpL = 0
  lpR = 0; bpR = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const numCh = out.length
    const numFrames = out[0].length
    const sr = this.sr
    const og = this.outGain
    const mix = this.p.mix

    // Chamberlin SVF coefficients
    // f = 2 * sin(pi * cutoff / sr) — frequency coefficient
    // q = 2 - 2 * resonance (damping, 0=max resonance, 2=no resonance)
    const fc = this.p.cutoff
    const f = 2 * Math.sin(Math.PI * Math.min(fc, sr * 0.49) / sr)
    const res = this.p.resonance
    // Damping: res=0 → q=2 (no resonance), res=1 → q≈0 (self-oscillation)
    const q = 2 - 2 * res * 0.99  // cap at 0.99 to prevent runaway

    // Morph: 0=LP, 0.25=BP, 0.5=notch, 0.75=HP, 1=HP (or continuous blend)
    const morph = this.p.morph
    // Blend weights for LP, BP, HP
    // morph=0 → [1,0,0] (LP), morph=0.5 → [0,0,1] (HP), morph=0.25 → [0,1,0] (BP)
    // Continuous morph: LP→BP→HP
    let wLP, wBP, wHP
    if (morph <= 0.5) {
      // LP → BP
      const t = morph * 2  // 0..1
      wLP = 1 - t
      wBP = t
      wHP = 0
    } else {
      // BP → HP
      const t = (morph - 0.5) * 2  // 0..1
      wLP = 0
      wBP = 1 - t
      wHP = t
    }

    // Output mode override: 0=morph blend, 1=notch (LP-HP), 2=allpass
    const outMode = Math.round(this.p.output_mode)
    if (outMode === 1) {
      // Notch = LP - BP*q + HP = input - BP*q (simplified)
      wLP = 1; wBP = -q * 0.5; wHP = 1
    }

    // Drive
    const drv = 1 + this.p.drive * 2
    const dryGain = 1.0 - mix

    for (let i = 0; i < numFrames; i++) {
      const dryL = inp[0] ? inp[0][i] : 0
      const dryR = (inp.length > 1 && inp[1]) ? inp[1][i] : dryL

      // Drive input
      const inL = dryL * drv
      const inR = dryR * drv

      // Chamberlin SVF (per channel)
      // HP = input - LP - q * BP
      // BP = BP + f * HP
      // LP = LP + f * BP

      // Left channel
      const hpL = inL - this.lpL - q * this.bpL
      this.bpL += f * hpL
      this.lpL += f * this.bpL

      // Right channel
      const hpR = inR - this.lpR - q * this.bpR
      this.bpR += f * hpR
      this.lpR += f * this.bpR

      // Blend outputs
      let filtL, filtR
      if (outMode === 2) {
        // Allpass: input - 2 * q * BP
        filtL = inL - 2 * q * this.bpL
        filtR = inR - 2 * q * this.bpR
      } else {
        filtL = wLP * this.lpL + wBP * this.bpL + wHP * hpL
        filtR = wLP * this.lpR + wBP * this.bpR + wHP * hpR
      }

      // Soft clip to prevent runaway at high resonance
      filtL = Math.tanh(filtL * 0.5) * 2
      filtR = Math.tanh(filtR * 0.5) * 2

      // Dry/wet
      if (numCh > 0) out[0][i] = (dryL * dryGain + filtL * mix) * og
      if (numCh > 1) out[1][i] = (dryR * dryGain + filtR * mix) * og
    }
  }

  reset() {
    this.lpL = 0; this.bpL = 0
    this.lpR = 0; this.bpR = 0
  }
}
