// @werkstatt freq_shifter 1 1
// @label Frequency Shifter (SSB)
// @param shift 200 -2000 2000 linear Hz
// @param direction 0 0 1 bool
// @param feedback 0 0 0.9 linear
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {shift: 200, direction: 0, feedback: 0, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Hilbert transform filter state (90-degree phase shifter)
  // Using 2nd-order allpass pair approximation (Pirkle)
  // a0-a2 for I (delayed) and Q (90° shifted)
  xaL = [0,0,0]; yaL = [0,0,0]
  xbL = [0,0,0]; ybL = [0,0,0]
  xaR = [0,0,0]; yaR = [0,0,0]
  xbR = [0,0,0]; ybR = [0,0,0]

  // Carrier oscillator state
  carrierPhase = 0

  // Feedback buffer
  fbL = 0; fbR = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // 2nd-order allpass for Hilbert pair
  // Phase difference ~90° across audio band
  _allpass(x, xs, ys, coeffs) {
    const y = coeffs[0] * x + coeffs[1] * xs[0] + coeffs[2] * xs[1] - coeffs[1] * ys[0] - coeffs[2] * ys[1]
    xs[1] = xs[0]
    xs[0] = x
    ys[1] = ys[0]
    ys[0] = y
    return y
  }

  // Compute allpass coefficients for given center frequency
  _apCoeffs(fc) {
    const wc = 2 * Math.PI * fc / this.sr
    const tan_w = Math.tan(wc / 2)
    const a1 = (1 - tan_w) / (1 + tan_w)
    const a2 = 0  // 1st-order allpass, used in pair
    return [a1, a1, a2]
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
    const shiftHz = this.p.shift * (this.p.direction >= 0.5 ? -1 : 1)
    const carrierInc = 2 * Math.PI * Math.abs(shiftHz) / sr
    const fbAmt = this.p.feedback

    // Allpass coefficients for Hilbert pair
    // Two allpasses at different frequencies create ~90° phase difference
    const cA = this._apCoeffs(sr * 0.001)  // very low freq
    const cB = this._apCoeffs(sr * 0.001)

    for (let i = 0; i < numFrames; i++) {
      // Input with feedback
      const inL = (inp[0] ? inp[0][i] : 0) + this.fbL * fbAmt
      const inR = (inp.length > 1 && inp[1] ? inp[1][i] : inL) + this.fbR * fbAmt

      // Hilbert transform: two allpass branches
      // Branch A → ~0° (in-phase), Branch B → ~90° (quadrature)
      const phaseI_L = this._allpass(inL, this.xaL, this.yaL, cA)
      const phaseQ_L = this._allpass(inL, this.xbL, this.ybL, cB)
      const phaseI_R = this._allpass(inR, this.xaR, this.yaR, cA)
      const phaseQ_R = this._allpass(inR, this.xbR, this.ybR, cB)

      // Carrier oscillator (complex: cos + sin)
      const cosC = Math.cos(this.carrierPhase)
      const sinC = Math.sin(this.carrierPhase)

      // SSB: shift up = (I*cos - Q*sin), shift down = (I*cos + Q*sin)
      // Upper sideband: I*cos - Q*sin
      // Lower sideband: I*cos + Q*sin
      const upper_L = phaseI_L * cosC - phaseQ_L * sinC
      const lower_L = phaseI_L * cosC + phaseQ_L * sinC
      const upper_R = phaseI_R * cosC - phaseQ_R * sinC
      const lower_R = phaseI_R * cosC + phaseQ_R * sinC

      // Select sideband based on direction
      const shiftedL = (shiftHz >= 0) ? upper_L : lower_L
      const shiftedR = (shiftHz >= 0) ? upper_R : lower_R

      // Feedback
      this.fbL = shiftedL
      this.fbR = shiftedR

      // Advance carrier
      this.carrierPhase += carrierInc
      if (this.carrierPhase > 2 * Math.PI) this.carrierPhase -= 2 * Math.PI

      // Dry/wet
      const dryL = inp[0] ? inp[0][i] : 0
      const dryR = (inp.length > 1 && inp[1]) ? inp[1][i] : dryL
      const wetL = shiftedL * mix
      const wetR = shiftedR * mix
      const dryGain = 1.0 - mix * 0.5

      if (numCh > 0) out[0][i] = (dryL * dryGain + wetL) * og
      if (numCh > 1) out[1][i] = (dryR * dryGain + wetR) * og
    }
  }

  reset() {
    this.xaL = [0,0,0]; this.yaL = [0,0,0]
    this.xbL = [0,0,0]; this.ybL = [0,0,0]
    this.xaR = [0,0,0]; this.yaR = [0,0,0]
    this.xbR = [0,0,0]; this.ybR = [0,0,0]
    this.carrierPhase = 0
    this.fbL = 0; this.fbR = 0
  }
}
