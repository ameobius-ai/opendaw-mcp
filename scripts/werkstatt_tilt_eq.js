// @werkstatt tilt_eq 1 1
// @label Tilt EQ
// @param tilt 0 -6 6 linear dB
// @param pivot 1000 100 8000 exp Hz
// @param steepness 0.5 0.2 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {tilt: 0, pivot: 1000, steepness: 0.5, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Biquad states for low shelf (L+R) and high shelf (L+R)
  lsL = {x1:0, x2:0, y1:0, y2:0}
  lsR = {x1:0, x2:0, y1:0, y2:0}
  hsL = {x1:0, x2:0, y1:0, y2:0}
  hsR = {x1:0, x2:0, y1:0, y2:0}

  // Cached coefficients
  lsCoeffs = null
  hsCoeffs = null
  lastTilt = 999
  lastPivot = 999
  lastSteep = 999

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._updateCoeffs()
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  _shelfLP(freq, gainDb, sr) {
    // Low shelf: boosts/cuts below freq
    const A = Math.pow(10, gainDb / 40)
    const w0 = 2 * Math.PI * freq / sr
    const cosW = Math.cos(w0)
    const sinW = Math.sin(w0)
    // S = steepness (0.5 = 1.5dB/oct, 1.0 = 3dB/oct typical)
    const S = this.p.steepness
    const alpha = sinW / 2 * Math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    const b0 = A * ((A + 1) - (A - 1) * cosW + 2 * Math.sqrt(A) * alpha)
    const b1 = 2 * A * ((A - 1) - (A + 1) * cosW)
    const b2 = A * ((A + 1) - (A - 1) * cosW - 2 * Math.sqrt(A) * alpha)
    const a0 = (A + 1) + (A - 1) * cosW + 2 * Math.sqrt(A) * alpha
    const a1 = -2 * ((A - 1) + (A + 1) * cosW)
    const a2 = (A + 1) + (A - 1) * cosW - 2 * Math.sqrt(A) * alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]
  }

  _shelfHP(freq, gainDb, sr) {
    // High shelf: boosts/cuts above freq
    const A = Math.pow(10, gainDb / 40)
    const w0 = 2 * Math.PI * freq / sr
    const cosW = Math.cos(w0)
    const sinW = Math.sin(w0)
    const S = this.p.steepness
    const alpha = sinW / 2 * Math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    const b0 = A * ((A + 1) + (A - 1) * cosW + 2 * Math.sqrt(A) * alpha)
    const b1 = -2 * A * ((A - 1) + (A + 1) * cosW)
    const b2 = A * ((A + 1) + (A - 1) * cosW - 2 * Math.sqrt(A) * alpha)
    const a0 = (A + 1) - (A - 1) * cosW + 2 * Math.sqrt(A) * alpha
    const a1 = 2 * ((A - 1) - (A + 1) * cosW)
    const a2 = (A + 1) - (A - 1) * cosW - 2 * Math.sqrt(A) * alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]
  }

  _updateCoeffs() {
    const tilt = this.p.tilt
    const pivot = this.p.pivot
    const sr = this.sr
    // Positive tilt: brighten (boost highs, cut lows)
    // Negative tilt: darken (boost lows, cut highs)
    const lsGain = -tilt  // low shelf gain (opposite of tilt)
    const hsGain = tilt   // high shelf gain (same as tilt)
    this.lsCoeffs = this._shelfLP(pivot, lsGain, sr)
    this.hsCoeffs = this._shelfHP(pivot, hsGain, sr)
  }

  _biquad(x, s, c) {
    const y = c[0]*x + c[1]*s.x1 + c[2]*s.x2 - c[3]*s.y1 - c[4]*s.y2
    s.x2 = s.x1
    s.x1 = x
    s.y2 = s.y1
    s.y1 = y
    return y
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    // Recompute coefficients if params changed
    if (this.p.tilt !== this.lastTilt || this.p.pivot !== this.lastPivot || this.p.steepness !== this.lastSteep) {
      this._updateCoeffs()
      this.lastTilt = this.p.tilt
      this.lastPivot = this.p.pivot
      this.lastSteep = this.p.steepness
    }

    const numCh = out.length
    const numFrames = out[0].length
    const og = this.outGain
    const mix = this.p.mix

    for (let i = 0; i < numFrames; i++) {
      const dryL = inp[0] ? inp[0][i] : 0
      const dryR = (inp.length > 1 && inp[1]) ? inp[1][i] : dryL

      // Low shelf (cut lows for bright, boost for dark)
      const lsOutL = this._biquad(dryL, this.lsL, this.lsCoeffs)
      const lsOutR = this._biquad(dryR, this.lsR, this.lsCoeffs)

      // High shelf (boost highs for bright, cut for dark)
      const hsOutL = this._biquad(lsOutL, this.hsL, this.hsCoeffs)
      const hsOutR = this._biquad(lsOutR, this.hsR, this.hsCoeffs)

      // Dry/wet
      const dryGain = 1.0 - mix
      if (numCh > 0) out[0][i] = (dryL * dryGain + hsOutL * mix) * og
      if (numCh > 1) out[1][i] = (dryR * dryGain + hsOutR * mix) * og
    }
  }

  reset() {
    this.lsL = {x1:0, x2:0, y1:0, y2:0}
    this.lsR = {x1:0, x2:0, y1:0, y2:0}
    this.hsL = {x1:0, x2:0, y1:0, y2:0}
    this.hsR = {x1:0, x2:0, y1:0, y2:0}
  }
}
