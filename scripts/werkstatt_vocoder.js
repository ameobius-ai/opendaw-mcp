// @werkstatt vocoder 1 1
// @label Vocoder
// @param bands 16 8 24 linear count
// @param carrier_wave 0 0 2 linear type
// @param carrier_freq 120 50 500 exp Hz
// @param mod_response 0.3 0.05 1 linear sec
// @param mod_threshold 0.02 0 0.2 linear
// @param band_q 6 2 20 linear
// @param emphasis 0.5 0 2 linear
// @param highpass 80 20 500 exp Hz
// @param mix 1 0 1 linear
// @param output 0 -12 12 linear dB

class Processor {
  p = {bands: 16, carrier_wave: 0, carrier_freq: 120,
       mod_response: 0.3, mod_threshold: 0.02, band_q: 6,
       emphasis: 0.5, highpass: 80, mix: 1, output: 0}
  sr = 44100
  bs = 128

  MAX_BANDS = 24
  FREQ_LO = 80
  FREQ_HI = 8000

  // Per-band filter states: [x1, x2, y1, y2] for modulator and carrier
  modState = null
  carState = null
  // Envelope per band
  env = null
  // Cached bandpass coefficients per band
  coeffs = null
  // Carrier oscillator phase
  carPhase = 0
  // HP filter state for output
  hpState = [0, 0, 0, 0]
  hpCoeff = null

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.modState = new Array(this.MAX_BANDS)
    this.carState = new Array(this.MAX_BANDS)
    this.env = new Float32Array(this.MAX_BANDS)
    for (let i = 0; i < this.MAX_BANDS; i++) {
      this.modState[i] = [0, 0, 0, 0]
      this.carState[i] = [0, 0, 0, 0]
    }
    this._updateCoeffs()
    this._updateHp()
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "band_q" || name === "bands") this._updateCoeffs()
    if (name === "highpass") this._updateHp()
  }

  _bandFreq(i, n) {
    // Logarithmic spacing
    const t = i / Math.max(1, n - 1)
    return this.FREQ_LO * Math.pow(this.FREQ_HI / this.FREQ_LO, t)
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
      this.coeffs[i] = this._bandpassCoeffs(f, this.p.band_q)
    }
  }

  _updateHp() {
    const sr = this.sr
    const w0 = 2 * Math.PI * this.p.highpass / sr
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

  _carrierSample(phase, wave) {
    if (wave < 0.5) {
      // Sawtooth
      return 2 * (phase / (2 * Math.PI)) - 1
    } else if (wave < 1.5) {
      // Square
      return phase < Math.PI ? 1 : -1
    } else {
      // Noise
      return Math.random() * 2 - 1
    }
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const nBands = Math.min(this.MAX_BANDS, Math.floor(this.p.bands))
    const mix = this.p.mix
    const stereo = out.length > 1
    const envCoeff = Math.exp(-1 / (sr * this.p.mod_response))
    const threshold = this.p.mod_threshold
    const emphasis = this.p.emphasis
    const outGain = Math.pow(10, this.p.output / 20)
    const carFreq = this.p.carrier_freq
    const carWave = this.p.carrier_wave
    const carPhaseInc = 2 * Math.PI * carFreq / sr

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0] ? inp[0][i] : 0
      const inR = stereo && inp.length > 1 && inp[1] ? inp[1][i] : inL

      // Carrier sample (mono, shared)
      const carSig = this._carrierSample(this.carPhase, carWave)
      this.carPhase += carPhaseInc
      if (this.carPhase > Math.PI * 2) this.carPhase -= Math.PI * 2

      let sumL = 0, sumR = 0

      for (let b = 0; b < nBands; b++) {
        const c = this.coeffs[b]

        // Modulator band (use mid/side = average of L/R)
        const modIn = (inL + inR) * 0.5
        const modBand = this._biquad(modIn, this.modState[b], c)
        const modAbs = Math.abs(modBand)

        // Envelope follower
        if (modAbs > this.env[b]) {
          this.env[b] = envCoeff * this.env[b] + (1 - envCoeff) * modAbs
        } else {
          this.env[b] = envCoeff * this.env[b]
        }

        // Gate
        let env = this.env[b]
        if (env < threshold) env = 0

        // Emphasis: boost high bands
        const emphGain = 1 + emphasis * (b / nBands)
        env *= emphGain

        // Carrier band
        const carBand = this._biquad(carSig, this.carState[b], c)

        // Apply modulator envelope to carrier band
        const bandOut = carBand * env
        sumL += bandOut
        sumR += bandOut
      }

      // Normalize by band count to prevent clipping
      const norm = 1 / Math.max(1, nBands) * 4
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
