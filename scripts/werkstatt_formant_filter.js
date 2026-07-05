// @werkstatt formant_filter 1 1
// @label Formant Filter
// @param formant_a 800 100 5000 exp Hz
// @param formant_b 1200 100 5000 exp Hz
// @param formant_c 2800 100 5000 exp Hz
// @param bandwidth_a 0.06 0.01 0.5 linear
// @param bandwidth_b 0.06 0.01 0.5 linear
// @param bandwidth_c 0.06 0.01 0.5 linear
// @param vowel 0 0 4 linear
// @param resonance 0.8 0 1 linear
// @param mix 0.7 0 1 linear

class Processor {
  p = {formant_a: 800, formant_b: 1200, formant_c: 2800,
       bandwidth_a: 0.06, bandwidth_b: 0.06, bandwidth_c: 0.06,
       vowel: 0, resonance: 0.8, mix: 0.7}
  sr = 44100
  bs = 128

  // Vowel presets: [F1, F2, F3] in Hz
  vowels = [
    [800, 1200, 2800],   // 0: neutral/a
    [730, 1090, 2440],   // 1: /a/ (father)
    [270, 2290, 3010],   // 2: /i/ (heed)
    [530, 1840, 2480],   // 3: /u/ (who)
    [570, 840, 2410],    // 4: /o/ (hoe)
  ]

  // 3 bandpass filter states: x1,x2,y1,y2 per formant, per channel
  stateLa = [0,0,0,0]
  stateLb = [0,0,0,0]
  stateLc = [0,0,0,0]
  stateRa = [0,0,0,0]
  stateRb = [0,0,0,0]
  stateRc = [0,0,0,0]

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Bandpass biquad coefficients
  // Returns [b0, b1, b2, a1, a2] (normalized by a0)
  _bpCoeff(freq, bw) {
    const sr = this.sr
    const w0 = 2 * Math.PI * freq / sr
    const cosw = Math.cos(w0)
    const sinw = Math.sin(w0)
    // Q from bandwidth: Q = w0 / (bw * w0) = 1/bw roughly
    // alpha = sin(w0) * sinh(ln(2)/2 * BW * w0/sin(w0))
    const alpha = sinw * Math.sinh(Math.LN2 / 2 * bw * w0 / sinw)

    const b0 = alpha
    const b1 = 0
    const b2 = -alpha
    const a0 = 1 + alpha
    const a1 = -2 * cosw
    const a2 = 1 - alpha

    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]
  }

  // Process one sample through one bandpass
  _bp(x, s, c) {
    const y = c[0] * x + c[1] * s[0] + c[2] * s[1] - c[3] * s[2] - c[4] * s[3]
    s[1] = s[0]
    s[0] = x
    s[3] = s[2]
    s[2] = y
    return y
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    // Get formant frequencies: use vowel preset if vowel > 0, else manual
    let f1, f2, f3
    const vIdx = Math.floor(this.p.vowel)
    if (vIdx >= 0 && vIdx < this.vowels.length && this.p.vowel > 0) {
      // Interpolate between vowels for smooth morphing
      const t = this.p.vowel - vIdx
      const cur = this.vowels[vIdx]
      const next = this.vowels[Math.min(vIdx + 1, this.vowels.length - 1)]
      f1 = cur[0] * (1 - t) + next[0] * t
      f2 = cur[1] * (1 - t) + next[1] * t
      f3 = cur[2] * (1 - t) + next[2] * t
    } else {
      f1 = this.p.formant_a
      f2 = this.p.formant_b
      f3 = this.p.formant_c
    }

    // Scale bandwidths by resonance (higher resonance = narrower = more vocal)
    const resScale = 1 - this.p.resonance * 0.7
    const ca = this._bpCoeff(f1, this.p.bandwidth_a * resScale)
    const cb = this._bpCoeff(f2, this.p.bandwidth_b * resScale)
    const cc = this._bpCoeff(f3, this.p.bandwidth_c * resScale)

    const mix = this.p.mix
    const stereo = out.length > 1

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0][i]
      const inR = stereo ? (inp.length > 1 ? inp[1][i] : inp[0][i]) : inL

      // Three bandpass filters in parallel
      const ya = this._bp(inL, this.stateLa, ca)
      const yb = this._bp(inL, this.stateLb, cb)
      const yc = this._bp(inL, this.stateLc, cc)
      const sumL = (ya + yb + yc) / 3

      if (stereo) {
        const yaR = this._bp(inR, this.stateRa, ca)
        const ybR = this._bp(inR, this.stateRb, cb)
        const ycR = this._bp(inR, this.stateRc, cc)
        const sumR = (yaR + ybR + ycR) / 3

        out[0][i] = inL * (1 - mix) + sumL * mix
        out[1][i] = inR * (1 - mix) + sumR * mix
      } else {
        out[0][i] = inL * (1 - mix) + sumL * mix
      }
    }
  }
}
