// @werkstatt paraeq 1 1
// @label Parametric EQ
// @param band1_freq 200 20 20000 exp Hz
// @param band1_gain 0 -18 18 linear dB
// @param band1_q 1 0.1 6 linear
// @param band2_freq 1000 20 20000 exp Hz
// @param band2_gain 0 -18 18 linear dB
// @param band2_q 1 0.1 6 linear
// @param band3_freq 5000 20 20000 exp Hz
// @param band3_gain 0 -18 18 linear dB
// @param band3_q 1 0.1 6 linear
// @param hp_freq 20 20 20000 exp Hz
// @param lp_freq 20000 20 20000 exp Hz
// @param mix 1 0 1 linear

class Processor {
  p = {
    band1_freq: 200, band1_gain: 0, band1_q: 1,
    band2_freq: 1000, band2_gain: 0, band2_q: 1,
    band3_freq: 5000, band3_gain: 0, band3_q: 1,
    hp_freq: 20, lp_freq: 20000, mix: 1,
  }
  sr = sampleRate

  // Peaking filter state (biquad, per-band, per-channel)
  // Each band: {x1, x2, y1, y2} for L and R
  _initState() {
    this.b1L = {x1:0, x2:0, y1:0, y2:0}
    this.b1R = {x1:0, x2:0, y1:0, y2:0}
    this.b2L = {x1:0, x2:0, y1:0, y2:0}
    this.b2R = {x1:0, x2:0, y1:0, y2:0}
    this.b3L = {x1:0, x2:0, y1:0, y2:0}
    this.b3R = {x1:0, x2:0, y1:0, y2:0}
    this.hpL = {x1:0, x2:0, y1:0, y2:0}
    this.hpR = {x1:0, x2:0, y1:0, y2:0}
    this.lpL = {x1:0, x2:0, y1:0, y2:0}
    this.lpR = {x1:0, x2:0, y1:0, y2:0}
  }

  constructor() {
    this._initState()
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Compute biquad coefficients for a peaking EQ filter
  // Reference: Robert Bristow-Johnson "Audio EQ Cookbook"
  _peakCoeffs(freq, gainDb, q, sr) {
    const A = Math.pow(10, gainDb / 40)  // sqrt of linear gain
    const w0 = 2 * Math.PI * freq / sr
    const cosW = Math.cos(w0)
    const sinW = Math.sin(w0)
    const alpha = sinW / (2 * Math.max(q, 0.1))

    const b0 = 1 + alpha * A
    const b1 = -2 * cosW
    const b2 = 1 - alpha * A
    const a0 = 1 + alpha / A
    const a1 = -2 * cosW
    const a2 = 1 - alpha / A

    return {b0: b0/a0, b1: b1/a0, b2: b2/a0, a1: a1/a0, a2: a2/a0}
  }

  // Highpass biquad (12 dB/oct)
  _hpCoeffs(freq, sr) {
    const w0 = 2 * Math.PI * freq / sr
    const cosW = Math.cos(w0)
    const sinW = Math.sin(w0)
    const alpha = sinW / Math.sqrt(2)  // Q=0.707 = Butterworth

    const b0 = (1 + cosW) / 2
    const b1 = -(1 + cosW)
    const b2 = (1 + cosW) / 2
    const a0 = 1 + alpha
    const a1 = -2 * cosW
    const a2 = 1 - alpha

    return {b0: b0/a0, b1: b1/a0, b2: b2/a0, a1: a1/a0, a2: a2/a0}
  }

  // Lowpass biquad (12 dB/oct)
  _lpCoeffs(freq, sr) {
    const w0 = 2 * Math.PI * freq / sr
    const cosW = Math.cos(w0)
    const sinW = Math.sin(w0)
    const alpha = sinW / Math.sqrt(2)

    const b0 = (1 - cosW) / 2
    const b1 = 1 - cosW
    const b2 = (1 - cosW) / 2
    const a0 = 1 + alpha
    const a1 = -2 * cosW
    const a2 = 1 - alpha

    return {b0: b0/a0, b1: b1/a0, b2: b2/a0, a1: a1/a0, a2: a2/a0}
  }

  // Apply biquad to single sample
  _biquad(x, st, c) {
    const y = c.b0 * x + c.b1 * st.x1 + c.b2 * st.x2 - c.a1 * st.y1 - c.a2 * st.y2
    st.x2 = st.x1
    st.x1 = x
    st.y2 = st.y1
    st.y1 = y
    return y
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr

    // Compute all coefficients
    const c1 = this._peakCoeffs(p.band1_freq, p.band1_gain, p.band1_q, sr)
    const c2 = this._peakCoeffs(p.band2_freq, p.band2_gain, p.band2_q, sr)
    const c3 = this._peakCoeffs(p.band3_freq, p.band3_gain, p.band3_q, sr)
    const chp = this._hpCoeffs(p.hp_freq, sr)
    const clp = this._lpCoeffs(p.lp_freq, sr)

    const stereo = output.length > 1
    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]

    for (let i = 0; i < inL.length; i++) {
      let s = inL[i]

      // HP → Band1 → Band2 → Band3 → LP
      s = this._biquad(s, this.hpL, chp)
      s = this._biquad(s, this.b1L, c1)
      s = this._biquad(s, this.b2L, c2)
      s = this._biquad(s, this.b3L, c3)
      s = this._biquad(s, this.lpL, clp)

      outL[i] = inL[i] * (1 - p.mix) + s * p.mix

      if (stereo) {
        let sR = inR[i]
        sR = this._biquad(sR, this.hpR, chp)
        sR = this._biquad(sR, this.b1R, c1)
        sR = this._biquad(sR, this.b2R, c2)
        sR = this._biquad(sR, this.b3R, c3)
        sR = this._biquad(sR, this.lpR, clp)
        outR[i] = inR[i] * (1 - p.mix) + sR * p.mix
      }
    }
  }
}
