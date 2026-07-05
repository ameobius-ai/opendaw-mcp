// @werkstatt multiband_comp 1 1
// @label Multiband Compressor
// @param crossover1 200 50 2000 exp Hz
// @param crossover2 2000 200 8000 exp Hz
// @param low_threshold 0.7 0 1 linear
// @param low_ratio 3 1 20 linear
// @param low_attack 0.003 0.001 0.1 linear sec
// @param low_release 0.15 0.01 1 linear sec
// @param low_gain 0 -12 12 linear dB
// @param mid_threshold 0.6 0 1 linear
// @param mid_ratio 3 1 20 linear
// @param mid_attack 0.005 0.001 0.1 linear sec
// @param mid_release 0.2 0.01 1 linear sec
// @param mid_gain 0 -12 12 linear dB
// @param high_threshold 0.5 0 1 linear
// @param high_ratio 4 1 20 linear
// @param high_attack 0.002 0.001 0.1 linear sec
// @param high_release 0.1 0.01 1 linear sec
// @param high_gain 0 -12 12 linear dB
// @param mix 1 0 1 linear

class Processor {
  p = {crossover1: 200, crossover2: 2000,
       low_threshold: 0.7, low_ratio: 3, low_attack: 0.003, low_release: 0.15, low_gain: 0,
       mid_threshold: 0.6, mid_ratio: 3, mid_attack: 0.005, mid_release: 0.2, mid_gain: 0,
       high_threshold: 0.5, high_ratio: 4, high_attack: 0.002, high_release: 0.1, high_gain: 0,
       mix: 1}
  sr = 44100
  bs = 128

  // Linkwitz-Riley crossover states (4th order = 24dB/oct)
  // LP for low band, HP for mid+high
  // Second crossover: LP for mid, HP for high
  // Each filter needs state per channel: [x1,x2,y1,y2,y3,y4]
  lpStateL = [0,0,0,0,0,0]
  hpStateL = [0,0,0,0,0,0]
  lp2StateL = [0,0,0,0,0,0]
  hp2StateL = [0,0,0,0,0,0]
  lpStateR = [0,0,0,0,0,0]
  hpStateR = [0,0,0,0,0,0]
  lp2StateR = [0,0,0,0,0,0]
  hp2StateR = [0,0,0,0,0,0]

  // Envelope followers per band
  envLow = 0
  envMid = 0
  envHigh = 0

  // Cached coefficients
  coeff1LP = null
  coeff1HP = null
  coeff2LP = null
  coeff2HP = null

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this._updateCoeffs()
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "crossover1" || name === "crossover2") {
      this._updateCoeffs()
    }
  }

  // 2nd-order Butterworth coefficients (used twice for LR4)
  _butterworthLP(freq) {
    const sr = this.sr
    const wc = 2 * Math.PI * freq / sr
    const cosw = Math.cos(wc)
    const sinw = Math.sin(wc)
    const alpha = sinw / Math.sqrt(2)
    const b0 = (1 - cosw) / 2
    const b1 = 1 - cosw
    const b2 = (1 - cosw) / 2
    const a0 = 1 + alpha
    return [b0/a0, b1/a0, b2/a0, -2*cosw/a0, (1-alpha)/a0]
  }

  _butterworthHP(freq) {
    const sr = this.sr
    const wc = 2 * Math.PI * freq / sr
    const cosw = Math.cos(wc)
    const sinw = Math.sin(wc)
    const alpha = sinw / Math.sqrt(2)
    const b0 = (1 + cosw) / 2
    const b1 = -(1 + cosw)
    const b2 = (1 + cosw) / 2
    const a0 = 1 + alpha
    return [b0/a0, b1/a0, b2/a0, -2*cosw/a0, (1-alpha)/a0]
  }

  _updateCoeffs() {
    this.coeff1LP = this._butterworthLP(this.p.crossover1)
    this.coeff1HP = this._butterworthHP(this.p.crossover1)
    this.coeff2LP = this._butterworthLP(this.p.crossover2)
    this.coeff2HP = this._butterworthHP(this.p.crossover2)
  }

  // Process one sample through a 2nd-order biquad
  _biquad(x, s, c) {
    const y = c[0]*x + c[1]*s[0] + c[2]*s[1] - c[3]*s[2] - c[4]*s[3]
    s[1] = s[0]; s[0] = x; s[3] = s[2]; s[2] = y
    return y
  }

  // Linkwitz-Riley 4th order = two cascaded biquads
  _lr4(x, s1, s2, c) {
    const y1 = this._biquad(x, s1, c)
    return this._biquad(y1, s2, c)
  }

  // Compressor gain calculation
  _compressGain(env, threshold, ratio, attack, release) {
    const sr = this.sr
    const atkCoeff = Math.exp(-1 / (sr * attack))
    const relCoeff = Math.exp(-1 / (sr * release))

    if (env > threshold) {
      const over = env - threshold
      const reduction = over * (1 - 1/ratio)
      const targetGain = 1 - reduction / env
      // Attack: move toward target
      return targetGain
    }
    return 1.0
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const mix = this.p.mix
    const stereo = out.length > 1

    // Compressor params per band
    const bands = [
      {thr: this.p.low_threshold, ratio: this.p.low_ratio, atk: this.p.low_attack, rel: this.p.low_release, gain: this.p.low_gain},
      {thr: this.p.mid_threshold, ratio: this.p.mid_ratio, atk: this.p.mid_attack, rel: this.p.mid_release, gain: this.p.mid_gain},
      {thr: this.p.high_threshold, ratio: this.p.high_ratio, atk: this.p.high_attack, rel: this.p.high_release, gain: this.p.high_gain},
    ]

    // Attack/release coefficients
    const atkCoeff = bands.map(b => Math.exp(-1 / (sr * b.atk)))
    const relCoeff = bands.map(b => Math.exp(-1 / (sr * b.rel)))
    const gainLin = bands.map(b => Math.pow(10, b.gain / 20))

    // Envelope followers
    let envLow = this.envLow
    let envMid = this.envMid
    let envHigh = this.envHigh

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0][i]
      const inR = stereo ? (inp.length > 1 ? inp[1][i] : inp[0][i]) : inL

      // Crossover: split into low, mid, high
      const lowL = this._lr4(inL, this.lpStateL, [this.lpStateL[2],this.lpStateL[3],this.lpStateL[4],this.lpStateL[5]], this.coeff1LP)
      const hp1L = this._lr4(inL, this.hpStateL, [this.hpStateL[2],this.hpStateL[3],this.hpStateL[4],this.hpStateL[5]], this.coeff1HP)
      const midL = this._lr4(hp1L, this.lp2StateL, [this.lp2StateL[2],this.lp2StateL[3],this.lp2StateL[4],this.lp2StateL[5]], this.coeff2LP)
      const highL = this._lr4(hp1L, this.hp2StateL, [this.hp2StateL[2],this.hp2StateL[3],this.hp2StateL[4],this.hp2StateL[5]], this.coeff2HP)

      let lowR = lowL, midR = midL, highR = highL
      if (stereo) {
        lowR = this._lr4(inR, this.lpStateR, [this.lpStateR[2],this.lpStateR[3],this.lpStateR[4],this.lpStateR[5]], this.coeff1LP)
        const hp1R = this._lr4(inR, this.hpStateR, [this.hpStateR[2],this.hpStateR[3],this.hpStateR[4],this.hpStateR[5]], this.coeff1HP)
        midR = this._lr4(hp1R, this.lp2StateR, [this.lp2StateR[2],this.lp2StateR[3],this.lp2StateR[4],this.lp2StateR[5]], this.coeff2LP)
        highR = this._lr4(hp1R, this.hp2StateR, [this.hp2StateR[2],this.hp2StateR[3],this.hp2StateR[4],this.hp2StateR[5]], this.coeff2HP)
      }

      // Envelope detection (use max of L/R)
      const absLow = Math.max(Math.abs(lowL), Math.abs(lowR))
      const absMid = Math.max(Math.abs(midL), Math.abs(midR))
      const absHigh = Math.max(Math.abs(highL), Math.abs(highR))

      // Update envelopes
      const envs = [absLow, absMid, absHigh]
      const curEnv = [envLow, envMid, envHigh]
      for (let b = 0; b < 3; b++) {
        if (envs[b] > curEnv[b]) {
          curEnv[b] = atkCoeff[b] * curEnv[b] + (1 - atkCoeff[b]) * envs[b]
        } else {
          curEnv[b] = relCoeff[b] * curEnv[b] + (1 - relCoeff[b]) * envs[b]
        }
      }
      envLow = curEnv[0]; envMid = curEnv[1]; envHigh = curEnv[2]

      // Compress each band
      let gLow = 1, gMid = 1, gHigh = 1
      for (let b = 0; b < 3; b++) {
        if (curEnv[b] > bands[b].thr) {
          const over = curEnv[b] - bands[b].thr
          const reduction = over * (1 - 1/bands[b].ratio)
          const g = [gLow, gMid, gHigh]
          g[b] = Math.max(0, 1 - reduction / Math.max(0.001, curEnv[b]))
          gLow = g[0]; gMid = g[1]; gHigh = g[2]
        }
      }

      // Apply gain + makeup + recombine
      const outL = (lowL * gLow * gainLin[0] + midL * gMid * gainLin[1] + highL * gHigh * gainLin[2]) / 3
      if (stereo) {
        const outR = (lowR * gLow * gainLin[0] + midR * gMid * gainLin[1] + highR * gHigh * gainLin[2]) / 3
        out[0][i] = inL * (1 - mix) + outL * mix
        out[1][i] = inR * (1 - mix) + outR * mix
      } else {
        out[0][i] = inL * (1 - mix) + outL * mix
      }
    }

    this.envLow = envLow
    this.envMid = envMid
    this.envHigh = envHigh
  }
}
