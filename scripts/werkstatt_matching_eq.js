// @werkstatt matching_eq 1 1
// @label Matching EQ (Spectral Balance Corrector)
// Adaptive EQ: analyzes input spectrum, compares to reference target, auto-corrects tonal balance
// iZotope Ozone EQ Match / FabFilter Pro-Q spectrum grab style

// @param target     0    0  1    linear   // reference target: 0=pink noise (equal energy/octave), 0.5=flat, 1=brown noise (emphasize lows)
// @param match_amt  0.7  0  1    linear   // match amount: 0=pass through, 1=full spectral match
// @param smooth     0.5  0  1    linear   // spectral smoothing of correction curve (0=detailed, 1=smooth broadband)
// @param adapt_rate 0.3  0  1    linear   // adaptation speed: 0=very slow (stable), 1=fast (reactive)
// @param tilt       0.5  0  1    linear   // additional tilt: 0=darker, 0.5=neutral, 1=brighter
// @param mix        1    0  1    linear   // dry/wet mix
// @param output     0    -12 6  linear dB

class Processor {
  p = {target: 0, match_amt: 0.7, smooth: 0.5, adapt_rate: 0.3, tilt: 0.5, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  FFT_SIZE = 1024
  HOP_SIZE = 512
  inBuf = null
  inPos = 0
  inFilled = 0
  outBufL = null
  outBufR = null
  outBufPos = 0
  window = null

  // Long-term average spectrum (LTAS) of input
  ltasMag = null       // accumulated magnitude spectrum
  ltasCount = 0        // number of frames accumulated

  // Correction gain curve (smoothed, per-bin)
  gainCurve = null     // current applied gain per bin
  targetGain = null    // target gain per bin (from LTAS comparison)

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    const N = this.FFT_SIZE
    this.inBuf = new Float32Array(N)
    this.outBufL = new Float32Array(N)
    this.outBufR = new Float32Array(N)
    this.window = new Float32Array(N)
    this.ltasMag = new Float32Array(N)
    this.gainCurve = new Float32Array(N)
    this.targetGain = new Float32Array(N)

    for (let i = 0; i < N; i++) {
      this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (N - 1)))
    }
    // Initialize gain curve to 1 (flat)
    this.gainCurve.fill(1)
    this.targetGain.fill(1)
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // In-place radix-2 FFT
  _fft(re, im, inverse) {
    const N = re.length
    let j = 0
    for (let i = 0; i < N - 1; i++) {
      if (i < j) {
        let t = re[i]; re[i] = re[j]; re[j] = t
        t = im[i]; im[i] = im[j]; im[j] = t
      }
      let k = N >> 1
      while (k <= j) { j -= k; k >>= 1 }
      j += k
    }

    for (let len = 2; len <= N; len <<= 1) {
      const halfLen = len >> 1
      const ang = (inverse ? 2 : -2) * Math.PI / len
      const wRe = Math.cos(ang)
      const wIm = Math.sin(ang)
      for (let i = 0; i < N; i += len) {
        let curRe = 1, curIm = 0
        for (let k = 0; k < halfLen; k++) {
          const tRe = curRe * re[i + k + halfLen] - curIm * im[i + k + halfLen]
          const tIm = curRe * im[i + k + halfLen] + curIm * re[i + k + halfLen]
          re[i + k + halfLen] = re[i + k] - tRe
          im[i + k + halfLen] = im[i + k] - tIm
          re[i + k] += tRe
          im[i + k] += tIm
          const newRe = curRe * wRe - curIm * wIm
          curIm = curRe * wIm + curIm * wRe
          curRe = newRe
        }
      }
    }

    if (inverse) {
      for (let i = 0; i < N; i++) {
        re[i] /= N
        im[i] /= N
      }
    }
  }

  // Compute reference target magnitude for a given bin
  // target=0: pink noise (-3 dB/octave from DC)
  // target=0.5: flat (white noise, equal energy per Hz)
  // target=1: brown noise (-6 dB/octave, emphasize lows)
  _targetMag(bin, N) {
    const freq = bin * this.sr / N
    if (freq < 1) return 1

    const pinkSlope = 1 / Math.sqrt(freq)         // -3 dB/oct
    const whiteSlope = 1                            // flat
    const brownSlope = 1 / freq                     // -6 dB/oct

    // Interpolate between targets
    const t = this.p.target
    if (t < 0.5) {
      // pink → white
      const f = t * 2  // 0→1
      return pinkSlope * (1 - f) + whiteSlope * f
    } else {
      // white → brown
      const f = (t - 0.5) * 2  // 0→1
      return whiteSlope * (1 - f) + brownSlope * f
    }
  }

  // Compute the correction gain curve from LTAS vs target
  _computeGainCurve(N) {
    const matchAmt = this.p.match_amt
    const smoothAmt = this.p.smooth
    const tiltAmt = (this.p.tilt - 0.5) * 2  // -1 to +1

    // Compute raw correction: target / actual (in magnitude domain)
    const rawGain = new Float32Array(N)
    for (let bin = 1; bin < N / 2; bin++) {
      const actual = this.ltasMag[bin] / Math.max(1, this.ltasCount)
      if (actual < 1e-10) {
        rawGain[bin] = 1
        continue
      }
      const target = this._targetMag(bin, N)
      // Gain = (target / actual) ^ matchAmt
      // matchAmt=0 → gain=1 (no correction), matchAmt=1 → full correction
      const ratio = target / actual
      rawGain[bin] = Math.pow(ratio, matchAmt)
    }

    // Apply tilt: boost highs or lows
    for (let bin = 1; bin < N / 2; bin++) {
      const freqRatio = bin / (N / 2)  // 0=DC, 1=Nyquist
      const tiltGain = Math.pow(2, tiltAmt * 3 * (freqRatio - 0.5))  // ±3 dB at extremes
      rawGain[bin] *= tiltGain
    }

    // Clamp extreme gains
    for (let bin = 0; bin < N; bin++) {
      rawGain[bin] = Math.max(0.1, Math.min(10, rawGain[bin]))
    }

    // Smoothing: moving average across bins
    const smoothSize = 1 + Math.round(smoothAmt * 30)  // 1 to 31 bins
    const smoothed = new Float32Array(N)
    for (let bin = 0; bin < N / 2; bin++) {
      let sum = 0, count = 0
      for (let i = -smoothSize; i <= smoothSize; i++) {
        const idx = bin + i
        if (idx >= 0 && idx < N / 2) {
          sum += rawGain[idx]
          count++
        }
      }
      smoothed[bin] = sum / count
    }
    // Mirror to upper half (conjugate symmetry for real signal)
    for (let bin = N / 2; bin < N; bin++) {
      smoothed[bin] = smoothed[N - bin]
    }

    // Store as target
    for (let bin = 0; bin < N; bin++) {
      this.targetGain[bin] = smoothed[bin]
    }
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const n = output[0].length
    const N = this.FFT_SIZE
    const H = this.HOP_SIZE
    const og = this.outGain
    const mix = this.p.mix

    // Adaptation coefficient: 0=very slow, 1=fast
    const adaptCoeff = 0.001 + this.p.adapt_rate * 0.05

    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0]
      const outCh = output[ch]

      // Fill input ring buffer
      for (let i = 0; i < n; i++) {
        this.inBuf[this.inPos] = inCh[i]
        this.inPos = (this.inPos + 1) % N
        if (this.inFilled < N) this.inFilled++
      }

      // Process frames
      while (this.inFilled >= N) {
        // Extract windowed frame
        const re = new Float32Array(N)
        const im = new Float32Array(N)
        for (let i = 0; i < N; i++) {
          const idx = (this.inPos + i) % N
          re[i] = this.inBuf[idx] * this.window[i]
        }

        // Forward FFT
        this._fft(re, im, false)

        // Accumulate LTAS (magnitude only, mono)
        if (ch === 0) {
          for (let bin = 0; bin < N / 2; bin++) {
            const mag = Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin])
            this.ltasMag[bin] += mag
          }
          this.ltasCount++

          // Recompute gain curve every 16 frames
          if (this.ltasCount % 16 === 0) {
            this._computeGainCurve(N)
          }
        }

        // Smoothly approach target gain
        for (let bin = 0; bin < N; bin++) {
          this.gainCurve[bin] += (this.targetGain[bin] - this.gainCurve[bin]) * adaptCoeff
          // Apply gain to this frame
          const g = this.gainCurve[bin]
          re[bin] *= g
          im[bin] *= g
        }

        // Inverse FFT
        this._fft(re, im, true)

        // Overlap-add
        for (let i = 0; i < N; i++) {
          const idx = (this.outBufPos + i) % N
          this.outBufL[idx] += re[i] * this.window[i] * (H / N)
        }

        // Advance
        this.outBufPos = (this.outBufPos + H) % N
        this.inPos = (this.inPos + H) % N
        this.inFilled -= H
      }

      // Output
      for (let i = 0; i < n; i++) {
        const wet = this.outBufL[this.outBufPos % N]
        this.outBufL[this.outBufPos % N] = 0
        this.outBufPos = (this.outBufPos + 1) % N
        const dry = inCh[i]
        outCh[i] = (dry * (1 - mix) + wet * mix) * og
      }
    }
  }

  reset() {
    this.inPos = 0
    this.inFilled = 0
    this.outBufPos = 0
    this.ltasCount = 0
    if (this.inBuf) this.inBuf.fill(0)
    if (this.outBufL) this.outBufL.fill(0)
    if (this.outBufR) this.outBufR.fill(0)
    if (this.ltasMag) this.ltasMag.fill(0)
    if (this.gainCurve) this.gainCurve.fill(1)
    if (this.targetGain) this.targetGain.fill(1)
  }
}
