// @werkstatt spectral_gate 1 1
// @label Spectral Gate
// @param bands 8 4 16 linear count
// @param threshold 0.05 0 0.5 linear
// @param reduction 0 0 1 linear
// @param attack 0.005 0.001 0.1 linear sec
// @param release 0.1 0.01 1 linear sec
// @param min_freq 80 20 500 exp Hz
// @param max_freq 8000 1000 16000 exp Hz
// @param tilt 0 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 12 linear dB

class Processor {
  p = {bands: 8, threshold: 0.05, reduction: 0, attack: 0.005,
       release: 0.1, min_freq: 80, max_freq: 8000, tilt: 0,
       mix: 1, output: 0}
  sr = 44100
  bs = 128

  MAX_BANDS = 16
  // Per-band biquad state [x1,x2,y1,y2] for L and R
  bpStateL = null
  bpStateR = null
  // Per-band envelope
  env = null
  // Cached coefficients
  coeffs = null
  // Output HP state
  hpState = [0, 0, 0, 0]
  hpCoeff = null

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.bpStateL = new Array(this.MAX_BANDS)
    this.bpStateR = new Array(this.MAX_BANDS)
    this.env = new Float32Array(this.MAX_BANDS)
    for (let i = 0; i < this.MAX_BANDS; i++) {
      this.bpStateL[i] = [0, 0, 0, 0]
      this.bpStateR[i] = [0, 0, 0, 0]
    }
    this._updateCoeffs()
    this._updateHp()
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "min_freq" || name === "max_freq" || name === "bands") {
      this._updateCoeffs()
    }
    if (name === "min_freq") {
      this._updateHp()
    }
  }

  _bandFreq(i, n) {
    const t = i / Math.max(1, n - 1)
    return this.p.min_freq * Math.pow(this.p.max_freq / this.p.min_freq, t)
  }

  _bandpassCoeffs(freq, q) {
    const sr = this.sr
    const w0 = 2 * Math.PI * freq / sr
    const cosw = Math.cos(w0)
    const sinw = Math.sin(w0)
    const alpha = sinw / (2 * q)
    const b0 = alpha
    const b1 = 0
    const b2 = -alpha
    const a0 = 1 + alpha
    return [b0/a0, b1/a0, b2/a0, -2*cosw/a0, (1-alpha)/a0]
  }

  _updateCoeffs() {
    this.coeffs = new Array(this.MAX_BANDS)
    for (let i = 0; i < this.MAX_BANDS; i++) {
      const f = this._bandFreq(i, this.MAX_BANDS)
      this.coeffs[i] = this._bandpassCoeffs(f, 4)
    }
  }

  _updateHp() {
    const sr = this.sr
    const w0 = 2 * Math.PI * Math.max(20, this.p.min_freq * 0.5) / sr
    const cosw = Math.cos(w0)
    const sinw = Math.sin(w0)
    const alpha = sinw / Math.sqrt(2)
    const b0 = (1 + cosw) / 2
    const b1 = -(1 + cosw)
    const b2 = (1 + cosw) / 2
    const a0 = 1 + alpha
    this.hpCoeff = [b0/a0, b1/a0, b2/a0, -2*cosw/a0, (1-alpha)/a0]
  }

  _biquad(x, s, c) {
    const y = c[0]*x + c[1]*s[0] + c[2]*s[1] - c[3]*s[2] - c[4]*s[3]
    s[1] = s[0]; s[0] = x; s[3] = s[2]; s[2] = y
    return y
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const nBands = Math.min(this.MAX_BANDS, Math.floor(this.p.bands))
    const mix = this.p.mix
    const stereo = out.length > 1
    const threshold = this.p.threshold
    const reductionAmt = this.p.reduction
    const tilt = this.p.tilt
    const outGain = Math.pow(10, this.p.output / 20)
    const atkCoeff = Math.exp(-1 / (sr * this.p.attack))
    const relCoeff = Math.exp(-1 / (sr * this.p.release))

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0] ? inp[0][i] : 0
      const inR = stereo && inp.length > 1 && inp[1] ? inp[1][i] : inL

      let sumL = 0, sumR = 0

      for (let b = 0; b < nBands; b++) {
        const c = this.coeffs[b]

        // Bandpass filter
        const bandL = this._biquad(inL, this.bpStateL[b], c)
        const bandR = this._biquad(inR, this.bpStateR[b], c)

        // Envelope follower (use max of L/R)
        const bandAbs = Math.max(Math.abs(bandL), Math.abs(bandR))

        if (bandAbs > this.env[b]) {
          this.env[b] = atkCoeff * this.env[b] + (1 - atkCoeff) * bandAbs
        } else {
          this.env[b] = relCoeff * this.env[b]
        }

        // Spectral gate: if band envelope below threshold, reduce
        let gain = 1
        if (this.env[b] < threshold) {
          gain = 1 - reductionAmt
        }

        // Tilt: boost high bands, cut low bands (spectral tilt)
        const tiltGain = 1 + tilt * (b / nBands - 0.5) * 2

        sumL += bandL * gain * tiltGain
        sumR += bandR * gain * tiltGain
      }

      // Normalize by band count
      const norm = 1 / Math.max(1, nBands) * 3
      sumL *= norm
      sumR *= norm

      // Output highpass
      sumL = this._biquad(sumL, this.hpState, this.hpCoeff)

      const wetL = sumL * outGain
      const wetR = sumR * outGain

      out[0][i] = inL * (1 - mix) + wetL * mix
      if (stereo) {
        out[1][i] = inR * (1 - mix) + wetR * mix
      }
    }
  }
}
