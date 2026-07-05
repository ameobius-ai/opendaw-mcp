// @werkstatt autowah 1 1
// @label Autowah
// @param mode 0 0 2 linear
// @param base_freq 300 80 2000 exp
// @param sweep_range 1200 200 4000 linear
// @param sensitivity 0.6 0 1 linear
// @param attack 0.005 0.001 0.1 exp
// @param release 0.08 0.01 0.5 exp
// @param resonance 4 0.5 15 linear
// @param direction 0 0 1 linear
// @param smooth 0.3 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 0 1 linear

class Processor {
  p = {
    mode: 0, base_freq: 300, sweep_range: 1200, sensitivity: 0.6,
    attack: 0.005, release: 0.08, resonance: 4, direction: 0,
    smooth: 0.3, mix: 1, output: 0,
  }
  sr = 44100
  bs = 128

  env = 0
  smoothCutoff = 300
  x1L = 0; x2L = 0; y1L = 0; y2L = 0
  x1R = 0; x2R = 0; y1R = 0; y2R = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  _biquadCoeffs(cutoff, Q, mode) {
    const w0 = 2 * Math.PI * cutoff / this.sr
    const cosW = Math.cos(w0)
    const sinW = Math.sin(w0)
    const alpha = sinW / (2 * Q)
    let b0, b1, b2, a0, a1, a2
    if (mode === 0) {
      b0 = alpha; b1 = 0; b2 = -alpha
      a0 = 1 + alpha; a1 = -2 * cosW; a2 = 1 - alpha
    } else if (mode === 1) {
      b0 = 1 + alpha; b1 = -2 * cosW; b2 = 1 - alpha
      a0 = 1 + alpha; a1 = -2 * cosW; a2 = 1 - alpha
    } else {
      b0 = (1 - cosW) / 2; b1 = 1 - cosW; b2 = (1 - cosW) / 2
      a0 = 1 + alpha; a1 = -2 * cosW; a2 = 1 - alpha
    }
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    const numFrames = output[0].length
    const numCh = output.length

    const atkCoef = 1 - Math.exp(-1 / (this.p.attack * this.sr))
    const relCoef = 1 - Math.exp(-1 / (this.p.release * this.sr))
    const smoothCoef = 1 - this.p.smooth * 0.9
    const outGain = Math.pow(10, this.p.output / 20)
    const mode = Math.round(this.p.mode)

    for (let i = 0; i < numFrames; i++) {
      let inSample = 0
      if (input && input.length > 0) {
        for (let c = 0; c < input.length; c++) inSample += input[c][i] || 0
        inSample /= input.length
      }

      const abs = Math.abs(inSample)
      const coef = abs > this.env ? atkCoef : relCoef
      this.env = this.env + coef * (abs - this.env)

      let envNorm = Math.min(1, this.env * this.p.sensitivity * 3)
      let targetCutoff
      if (this.p.direction === 0) {
        targetCutoff = this.p.base_freq + this.p.sweep_range * envNorm
      } else {
        targetCutoff = this.p.base_freq + this.p.sweep_range * (1 - envNorm)
      }
      targetCutoff = Math.max(50, Math.min(this.sr * 0.45, targetCutoff))

      this.smoothCutoff = this.smoothCutoff + smoothCoef * (targetCutoff - this.smoothCutoff)
      const c = this._biquadCoeffs(this.smoothCutoff, this.p.resonance, mode)

      const dryL = (input && input[0]) ? input[0][i] : 0
      const dryR = (input && input[1]) ? input[1][i] : dryL

      const oL = c[0] * dryL + c[1] * this.x1L + c[2] * this.x2L - c[3] * this.y1L - c[4] * this.y2L
      this.x2L = this.x1L; this.x1L = dryL
      this.y2L = this.y1L; this.y1L = oL

      const oR = c[0] * dryR + c[1] * this.x1R + c[2] * this.x2R - c[3] * this.y1R - c[4] * this.y2R
      this.x2R = this.x1R; this.x1R = dryR
      this.y2R = this.y1R; this.y1R = oR

      output[0][i] = (dryL * (1 - this.p.mix) + oL * this.p.mix) * outGain
      if (numCh > 1) output[1][i] = (dryR * (1 - this.p.mix) + oR * this.p.mix) * outGain
    }
  }

  reset() {
    this.env = 0
    this.smoothCutoff = 300
    this.x1L = 0; this.x2L = 0; this.y1L = 0; this.y2L = 0
    this.x1R = 0; this.x2R = 0; this.y1R = 0; this.y2R = 0
  }
}
