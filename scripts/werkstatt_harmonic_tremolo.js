// @werkstatt harmonic_tremolo 1 1
// @label Harmonic Tremolo (Fender)
// @param rate 0.3 0 1 linear
// @param depth 0.7 0 1 linear
// @param crossover 800 100 4000 exp Hz
// @param shape 0 0 1 linear
// @param phase_offset 0.5 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {rate: 0.3, depth: 0.7, crossover: 800, shape: 0, phase_offset: 0.5, mix: 1, output: 0}
  sr = 44100
  outGain = 1
  phase = 0

  // LR4 crossover state — 4 cascaded one-poles for LP, subtract for HP
  // LP: 4x one-pole (z1..z4)
  // HP = input - LP
  lpL_z1 = 0; lpL_z2 = 0; lpL_z3 = 0; lpL_z4 = 0
  lpR_z1 = 0; lpR_z2 = 0; lpR_z3 = 0; lpR_z4 = 0

  // Smoothing for LFO gain to avoid clicks at high depth
  gainLowL = 0; gainHighL = 0
  gainLowR = 0; gainHighR = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // LR4 one-pole cascade: 4 passes of first-order LP
  _lr4LP(input, z) {
    // First-order LP: y = z + a * (input - z)
    // a = 1 - exp(-2*pi*fc/sr)
    // Stored in z[0..3]
    let s = input
    for (let i = 0; i < 4; i++) {
      s = z[i] + this._lpCoeff * (s - z[i])
      z[i] = s
    }
    return s
  }

  _lpCoeff = 0

  _updateCoeff() {
    const fc = Math.min(this.p.crossover, this.sr * 0.45)
    this._lpCoeff = 1 - Math.exp(-2 * Math.PI * fc / this.sr)
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const og = this.outGain

    // Update crossover coefficient
    this._updateCoeff()

    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]
    const numFrames = inL.length
    const isMono = input.length <= 1

    // LFO rate: 0→0.1Hz, 1→20Hz (logarithmic)
    const rateHz = 0.1 + Math.pow(p.rate, 3) * 19.9
    const phaseInc = 2 * Math.PI * rateHz / this.sr
    const depth = p.depth
    const phaseOff = p.phase_offset * Math.PI // 0..PI offset between low and high

    // Shape: 0=sine (smooth), 1=square (choppy), blend between
    const shapeAmt = p.shape

    // LFO gain smoothing coefficient
    const smoothCoeff = 1 - Math.exp(-1 / (this.sr * 0.005)) // 5ms smoothing

    for (let i = 0; i < numFrames; i++) {
      const dryL = inL[i]
      const dryR = isMono ? inL[i] : inR[i]

      // --- 1. LR4 crossover: split into low and high bands ---
      const lpL = this._lr4LP(dryL, [this.lpL_z1, this.lpL_z2, this.lpL_z3, this.lpL_z4])
      this.lpL_z1 += this._lpCoeff * (dryL - this.lpL_z1)
      // Actually, _lr4LP already updates z[] in place via reference...
      // Let me do it properly:
      let sL = dryL
      sL = this.lpL_z1 + this._lpCoeff * (sL - this.lpL_z1); this.lpL_z1 = sL
      sL = this.lpL_z2 + this._lpCoeff * (sL - this.lpL_z2); this.lpL_z2 = sL
      sL = this.lpL_z3 + this._lpCoeff * (sL - this.lpL_z3); this.lpL_z3 = sL
      sL = this.lpL_z4 + this._lpCoeff * (sL - this.lpL_z4); this.lpL_z4 = sL
      const lowL = sL
      const highL = dryL - lowL

      let sR = dryR
      sR = this.lpR_z1 + this._lpCoeff * (sR - this.lpR_z1); this.lpR_z1 = sR
      sR = this.lpR_z2 + this._lpCoeff * (sR - this.lpR_z2); this.lpR_z2 = sR
      sR = this.lpR_z3 + this._lpCoeff * (sR - this.lpR_z3); this.lpR_z3 = sR
      sR = this.lpR_z4 + this._lpCoeff * (sR - this.lpR_z4); this.lpR_z4 = sR
      const lowR = sR
      const highR = dryR - lowR

      // --- 2. LFO: two oscillators 180° out of phase ---
      // Low band: gain = (1 + sin(phase)) / 2 → 0..1
      // High band: gain = (1 + sin(phase + PI)) / 2 → 0..1 (inverted)
      // phase_offset controls how much offset (PI = classic, 0 = both same)
      let lfoLow = Math.sin(this.phase)
      let lfoHigh = Math.sin(this.phase + phaseOff + Math.PI)

      // Shape: blend sine toward square
      if (shapeAmt > 0) {
        // Square-ish: sign function with blend
        const sqLow = lfoLow >= 0 ? 1 : -1
        const sqHigh = lfoHigh >= 0 ? 1 : -1
        lfoLow = lfoLow * (1 - shapeAmt) + sqLow * shapeAmt
        lfoHigh = lfoHigh * (1 - shapeAmt) + sqHigh * shapeAmt
      }

      // Map to gain: center at 1, depth controls excursion
      // gainLow = 1 - depth * (1 - (lfoLow + 1) / 2)
      // gainHigh = 1 - depth * (1 - (lfoHigh + 1) / 2)
      const targetGainLowL = 1 - depth * (1 - (lfoLow + 1) * 0.5)
      const targetGainHighL = 1 - depth * (1 - (lfoHigh + 1) * 0.5)
      const targetGainLowR = targetGainLowL // same LFO for both channels (stereo linked)
      const targetGainHighR = targetGainHighL

      // Smooth gain changes
      this.gainLowL += (targetGainLowL - this.gainLowL) * smoothCoeff
      this.gainHighL += (targetGainHighL - this.gainHighL) * smoothCoeff
      this.gainLowR += (targetGainLowR - this.gainLowR) * smoothCoeff
      this.gainHighR += (targetGainHighR - this.gainHighR) * smoothCoeff

      // --- 3. Apply modulated gains to each band ---
      const modLowL = lowL * this.gainLowL
      const modHighL = highL * this.gainHighL
      const modLowR = lowR * this.gainLowR
      const modHighR = highR * this.gainHighR

      // --- 4. Recombine bands ---
      const wetL = modLowL + modHighL
      const wetR = modLowR + modHighR

      // --- 5. Dry/wet + output gain ---
      outL[i] = (dryL * (1 - p.mix) + wetL * p.mix) * og
      outR[i] = (dryR * (1 - p.mix) + wetR * p.mix) * og

      // Advance LFO phase
      this.phase += phaseInc
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI
    }
  }

  reset() {
    this.phase = 0
    this.lpL_z1 = 0; this.lpL_z2 = 0; this.lpL_z3 = 0; this.lpL_z4 = 0
    this.lpR_z1 = 0; this.lpR_z2 = 0; this.lpR_z3 = 0; this.lpR_z4 = 0
    this.gainLowL = 0; this.gainHighL = 0
    this.gainLowR = 0; this.gainHighR = 0
  }
}
