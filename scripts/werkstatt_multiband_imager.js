// @werkstatt multiband_imager 1 1
// @label Multiband Stereo Imager
// @param crossover1 200 50 2000 exp Hz
// @param crossover2 2000 200 8000 exp Hz
// @param low_width 0 0 1.5 linear
// @param mid_width 0.5 0 1.5 linear
// @param high_width 1.0 0 1.5 linear
// @param bypass_low 0 0 1 bool
// @param link 0 0 1 bool
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {
    crossover1: 200, crossover2: 2000,
    low_width: 0, mid_width: 0.5, high_width: 1.0,
    bypass_low: 0, link: 0,
    mix: 1, output: 0,
  }
  sr = 44100
  outGain = 1

  // LR4 crossover states per channel: [x1,x2,y1,y2,y3,y4]
  lpStateL = [0,0,0,0,0,0]
  hpStateL = [0,0,0,0,0,0]
  lp2StateL = [0,0,0,0,0,0]
  hp2StateL = [0,0,0,0,0,0]
  lpStateR = [0,0,0,0,0,0]
  hpStateR = [0,0,0,0,0,0]
  lp2StateR = [0,0,0,0,0,0]
  hp2StateR = [0,0,0,0,0,0]

  coeff1LP = null
  coeff1HP = null
  coeff2LP = null
  coeff2HP = null

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._updateCoeffs()
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
    if (name === "crossover1" || name === "crossover2") {
      this._updateCoeffs()
    }
  }

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

  _biquad(x, s, c) {
    const y = c[0]*x + c[1]*s[0] + c[2]*s[1] - c[3]*s[2] - c[4]*s[3]
    s[1] = s[0]
    s[0] = x
    s[3] = s[2]
    s[2] = y
    return y
  }

  // LR4 = two cascaded biquads
  _lr4(x, s1, s2, c) {
    const y1 = this._biquad(x, s1, c)
    return this._biquad(y1, s2, c)
  }

  // Apply M/S width to a stereo band sample pair
  _applyWidth(l, r, width) {
    const mid = (l + r) * 0.5
    const side = (l - r) * 0.5
    const wSide = side * width
    return [mid + wSide, mid - wSide]
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out || inp.length < 2) return

    const inL = inp[0]
    const inR = inp[1]
    const outL = out[0]
    const outR = out[1]
    const len = inL.length

    const og = this.outGain
    const mix = this.p.mix
    const bypassLow = this.p.bypass_low >= 0.5
    const link = this.p.link >= 0.5

    const lowW = this.p.low_width
    const midW = link ? this.p.low_width : this.p.mid_width
    const highW = this.p.high_width

    for (let i = 0; i < len; i++) {
      const dryL = inL[i]
      const dryR = inR[i]

      // Split into 3 bands per channel via LR4 crossovers
      const lowL = this._lr4(dryL, this.lpStateL, [this.lpStateL[2],this.lpStateL[3],this.lpStateL[4],this.lpStateL[5]], this.coeff1LP)
      const hp1L = this._lr4(dryL, this.hpStateL, [this.hpStateL[2],this.hpStateL[3],this.hpStateL[4],this.hpStateL[5]], this.coeff1HP)
      const midL = this._lr4(hp1L, this.lp2StateL, [this.lp2StateL[2],this.lp2StateL[3],this.lp2StateL[4],this.lp2StateL[5]], this.coeff2LP)
      const highL = this._lr4(hp1L, this.hp2StateL, [this.hp2StateL[2],this.hp2StateL[3],this.hp2StateL[4],this.hp2StateL[5]], this.coeff2HP)

      const lowR = this._lr4(dryR, this.lpStateR, [this.lpStateR[2],this.lpStateR[3],this.lpStateR[4],this.lpStateR[5]], this.coeff1LP)
      const hp1R = this._lr4(dryR, this.hpStateR, [this.hpStateR[2],this.hpStateR[3],this.hpStateR[4],this.hpStateR[5]], this.coeff1HP)
      const midR = this._lr4(hp1R, this.lp2StateR, [this.lp2StateR[2],this.lp2StateR[3],this.lp2StateR[4],this.lp2StateR[5]], this.coeff2LP)
      const highR = this._lr4(hp1R, this.hp2StateR, [this.hp2StateR[2],this.hp2StateR[3],this.hp2StateR[4],this.hp2StateR[5]], this.coeff2HP)

      // Apply M/S width per band
      let procLowL, procLowR
      if (bypassLow) {
        procLowL = lowL
        procLowR = lowR
      } else {
        [procLowL, procLowR] = this._applyWidth(lowL, lowR, lowW)
      }
      const [procMidL, procMidR] = this._applyWidth(midL, midR, midW)
      const [procHighL, procHighR] = this._applyWidth(highL, highR, highW)

      // Sum bands back
      const wetL = procLowL + procMidL + procHighL
      const wetR = procLowR + procMidR + procHighR

      // Dry/wet
      outL[i] = (dryL + (wetL - dryL) * mix) * og
      outR[i] = (dryR + (wetR - dryR) * mix) * og
    }
  }
}
