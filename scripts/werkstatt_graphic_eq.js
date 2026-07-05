// @werkstatt graphic_eq 1 1
// @label Graphic EQ
// @param band_32 0 -12 12 linear dB
// @param band_64 0 -12 12 linear dB
// @param band_125 0 -12 12 linear dB
// @param band_250 0 -12 12 linear dB
// @param band_500 0 -12 12 linear dB
// @param band_1k 0 -12 12 linear dB
// @param band_2k 0 -12 12 linear dB
// @param band_4k 0 -12 12 linear dB
// @param band_8k 0 -12 12 linear dB
// @param band_16k 0 -12 12 linear dB
// @param master 0 -6 6 linear dB

class Processor {
  p = {band_32: 0, band_64: 0, band_125: 0, band_250: 0, band_500: 0,
       band_1k: 0, band_2k: 0, band_4k: 0, band_8k: 0, band_16k: 0, master: 0}
  sr = 44100
  bs = 128

  // 10-band ISO frequencies
  freqs = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
  // Peaking filter coefficients per band: b0, b1, b2, a1, a2
  coeffs = []
  // Per-band state: x1, x2, y1, y2
  stateL = []
  stateR = []

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this._calcCoeffs()
  }

  paramChanged(name, value) {
    this.p[name] = value
    this._calcCoeffs()
  }

  // Biquad peaking filter coefficients
  // A = 10^(gain/40), w0 = 2*pi*f/sr, Q = 1.41 (approx 2/3 octave)
  _peakCoeff(f, gainDb) {
    const sr = this.sr
    const w0 = 2 * Math.PI * f / sr
    const cosw = Math.cos(w0)
    const sinw = Math.sin(w0)
    const A = Math.pow(10, gainDb / 40)
    const Q = 1.41
    const alpha = sinw / (2 * Q)

    const b0 = 1 + alpha * A
    const b1 = -2 * cosw
    const b2 = 1 - alpha * A
    const a0 = 1 + alpha / A
    const a1 = -2 * cosw
    const a2 = 1 - alpha / A

    // Normalize by a0
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]
  }

  _calcCoeffs() {
    const bandKeys = ['band_32', 'band_64', 'band_125', 'band_250', 'band_500',
                      'band_1k', 'band_2k', 'band_4k', 'band_8k', 'band_16k']
    this.coeffs = []
    for (let i = 0; i < 10; i++) {
      this.coeffs.push(this._peakCoeff(this.freqs[i], this.p[bandKeys[i]]))
    }
    // Reset state arrays
    this.stateL = []
    this.stateR = []
    for (let i = 0; i < 10; i++) {
      this.stateL.push([0, 0, 0, 0])
      this.stateR.push([0, 0, 0, 0])
    }
  }

  // Process one sample through all 10 bands in series
  _processSample(x, states) {
    let y = x
    for (let i = 0; i < 10; i++) {
      const c = this.coeffs[i]
      const s = states[i]
      const out = c[0] * y + c[1] * s[0] + c[2] * s[1] - c[3] * s[2] - c[4] * s[3]
      s[1] = s[0]
      s[0] = y
      s[3] = s[2]
      s[2] = out
      y = out
    }
    return y
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const masterGain = Math.pow(10, this.p.master / 20)
    const stereo = out.length > 1

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0][i]
      const inR = stereo ? (inp.length > 1 ? inp[1][i] : inp[0][i]) : inL

      const yL = this._processSample(inL, this.stateL) * masterGain

      if (stereo) {
        const yR = this._processSample(inR, this.stateR) * masterGain
        out[0][i] = yL
        out[1][i] = yR
      } else {
        out[0][i] = yL
      }
    }
  }
}
