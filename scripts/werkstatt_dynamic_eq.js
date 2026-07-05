// @werkstatt dynamic_eq 1 1
// @label Dynamic EQ
// @param band1_freq 200 20 20000 exp Hz
// @param band1_gain -6 -18 18 linear dB
// @param band1_q 1.5 0.1 6 linear
// @param band1_threshold 0.06 0 0.5 linear
// @param band1_range 6 0 18 linear dB
// @param band2_freq 1000 20 20000 exp Hz
// @param band2_gain 0 -18 18 linear dB
// @param band2_q 1.5 0.1 6 linear
// @param band2_threshold 0.08 0 0.5 linear
// @param band2_range 6 0 18 linear dB
// @param band3_freq 5000 20 20000 exp Hz
// @param band3_gain 0 -18 18 linear dB
// @param band3_q 1.5 0.1 6 linear
// @param band3_threshold 0.05 0 0.5 linear
// @param band3_range 6 0 18 linear dB
// @param attack 0.005 0.001 0.1 linear sec
// @param release 0.1 0.01 1 linear sec
// @param mix 1 0 1 linear
// @param output 0 -12 12 linear dB

class Processor {
  p = {
    band1_freq: 200, band1_gain: -6, band1_q: 1.5, band1_threshold: 0.06, band1_range: 6,
    band2_freq: 1000, band2_gain: 0, band2_q: 1.5, band2_threshold: 0.08, band2_range: 6,
    band3_freq: 5000, band3_gain: 0, band3_q: 1.5, band3_threshold: 0.05, band3_range: 6,
    attack: 0.005, release: 0.1, mix: 1, output: 0,
  }
  sr = sampleRate

  // per-band state: detection biquad + processing biquad (L+R) + envelope
  st = []
  _initState() {
    this.st = []
    for (let b = 0; b < 3; b++) {
      this.st.push({
        dL: {x1:0, x2:0, y1:0, y2:0}, dR: {x1:0, x2:0, y1:0, y2:0},
        pL: {x1:0, x2:0, y1:0, y2:0}, pR: {x1:0, x2:0, y1:0, y2:0},
        env: 0,
      })
    }
  }

  constructor() {
    this._initState()
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  _peakCoeffs(freq, gainDb, q, sr) {
    const A = Math.pow(10, gainDb / 40)
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

  _biquad(x, s, c) {
    const y = c.b0 * x + c.b1 * s.x1 + c.b2 * s.x2 - c.a1 * s.y1 - c.a2 * s.y2
    s.x2 = s.x1
    s.x1 = x
    s.y2 = s.y1
    s.y1 = y
    return y
  }

  _db2gain(db) {
    return Math.pow(10, db / 20)
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const atkCoef = Math.exp(-1 / (this.p.attack * sr))
    const relCoef = Math.exp(-1 / (this.p.release * sr))
    const outGain = this._db2gain(this.p.output)
    const mix = this.p.mix

    const bands = [
      {freq: this.p.band1_freq, gain: this.p.band1_gain, q: this.p.band1_q,
       thresh: this.p.band1_threshold, range: this.p.band1_range},
      {freq: this.p.band2_freq, gain: this.p.band2_gain, q: this.p.band2_q,
       thresh: this.p.band2_threshold, range: this.p.band2_range},
      {freq: this.p.band3_freq, gain: this.p.band3_gain, q: this.p.band3_q,
       thresh: this.p.band3_threshold, range: this.p.band3_range},
    ]

    // detection coeffs (0 dB gain peaking — isolates band)
    const detCoeffs = bands.map(b => this._peakCoeffs(b.freq, 0, b.q, sr))

    for (let i = 0; i < out[0].length; i++) {
      const dryL = inp[0] ? inp[0][i] : 0
      const dryR = inp[1] ? inp[1][i] : 0

      let procL = dryL
      let procR = dryR

      for (let b = 0; b < 3; b++) {
        const s = this.st[b]
        const band = bands[b]

        // detection: isolate band energy
        const detL = this._biquad(dryL, s.dL, detCoeffs[b])
        const detR = this._biquad(dryR, s.dR, detCoeffs[b])
        const detLevel = Math.abs(detL) * 0.5 + Math.abs(detR) * 0.5

        // envelope follower
        const coef = detLevel > s.env ? atkCoef : relCoef
        s.env = s.env * coef + detLevel * (1 - coef)

        // dynamic gain: above threshold → reduce
        let dynGainDb = band.gain
        if (s.env > band.thresh && band.range > 0) {
          const over = (s.env - band.thresh) / (1 - band.thresh)
          dynGainDb = band.gain - Math.min(over, 1) * band.range
        }

        // processing filter with dynamic gain
        const pc = this._peakCoeffs(band.freq, dynGainDb, band.q, sr)
        procL = this._biquad(procL, s.pL, pc)
        procR = this._biquad(procR, s.pR, pc)
      }

      out[0][i] = (dryL * (1 - mix) + procL * mix) * outGain
      out[1][i] = (dryR * (1 - mix) + procR * mix) * outGain
    }
  }
}
