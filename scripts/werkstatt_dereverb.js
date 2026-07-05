// @werkstatt dereverb 1 1
// @label De-Reverb (Reverb Tail Suppression)
// Restoration tool: removes room reverb from dry signal by detecting and suppressing reverb tails
// iZotope RX De-reverb / Accusonus ERA De-reverb style

// @param reduction   0.5  0  1    linear   // reverb reduction amount: 0=none, 1=max (-24 dB)
// @param decay_est   0.3  0  1    linear   // decay estimation speed: 0=fast (100ms), 1=slow (2s)
// @param sensitivity 0.5  0  1    linear   // transient detection sensitivity: 0=low (only loud), 1=high (subtle too)
// @param bands       0.5  0  1    linear   // frequency band count: 0=4 bands, 1=16 bands
// @param preserve    0.7  0  1    linear   // direct signal preservation: 0=aggressive (may cut signal), 1=safe (preserve transients)
// @param mix         1    0  1    linear   // dry/wet mix
// @param output      0    -12 6  linear dB

class Processor {
  p = {reduction: 0.5, decay_est: 0.3, sensitivity: 0.5, bands: 0.5, preserve: 0.7, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Configuration
  MAX_BANDS = 16
  FFT_SIZE = 1024
  HOP_SIZE = 512

  inBuf = null
  inPos = 0
  inFilled = 0
  outBuf = null
  outBufPos = 0
  window = null

  // Per-band state
  numBands = 8
  bandEdges = null     // frequency bin boundaries for each band

  // Per-band envelope followers
  fastEnv = null       // fast envelope (tracks direct signal)
  slowEnv = null       // slow envelope (tracks reverb tail)
  decayCoeff = null    // per-band decay coefficient (estimated reverb decay rate)
  bandGain = null      // per-band gain applied to suppress reverb
  prevGain = null      // smoothed gain
  tailActive = null    // per-band: true when in tail (after transient)
  tailCounter = null   // frames since last transient per band

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    const N = this.FFT_SIZE
    this.inBuf = new Float32Array(N)
    this.outBuf = new Float32Array(N)
    this.window = new Float32Array(N)

    this.fastEnv = new Float32Array(this.MAX_BANDS)
    this.slowEnv = new Float32Array(this.MAX_BANDS)
    this.decayCoeff = new Float32Array(this.MAX_BANDS)
    this.bandGain = new Float32Array(this.MAX_BANDS)
    this.prevGain = new Float32Array(this.MAX_BANDS)
    this.tailActive = new Uint8Array(this.MAX_BANDS)
    this.tailCounter = new Int32Array(this.MAX_BANDS)
    this.bandEdges = new Int32Array(this.MAX_BANDS + 1)

    for (let i = 0; i < N; i++) {
      this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (N - 1)))
    }
    this.bandGain.fill(1)
    this.prevGain.fill(1)
    this.decayCoeff.fill(0.99)
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

  _updateBandEdges(N) {
    // Logarithmic band spacing
    const minBin = 2
    const maxBin = N / 2
    this.numBands = Math.max(4, Math.round(4 + this.p.bands * 12))
    for (let b = 0; b <= this.numBands; b++) {
      const ratio = b / this.numBands
      this.bandEdges[b] = Math.round(minBin * Math.pow(maxBin / minBin, ratio))
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

    const reductionDb = -this.p.reduction * 24
    const reductionGain = Math.pow(10, reductionDb / 20)

    // Decay estimation speed: 0→fast (100ms), 1→slow (2s)
    const decayMs = 100 + this.p.decay_est * 1900
    const decayTau = decayMs / 1000
    const slowCoeff = Math.exp(-1 / (this.sr * decayTau / (H / this.sr)))

    // Transient sensitivity
    const transThresh = 1.5 + (1 - this.p.sensitivity) * 2  // 1.5x to 3.5x energy jump
    const preserveAmt = this.p.preserve

    // Update band edges if needed
    this._updateBandEdges(N)

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
        const re = new Float32Array(N)
        const im = new Float32Array(N)
        for (let i = 0; i < N; i++) {
          const idx = (this.inPos + i) % N
          re[i] = this.inBuf[idx] * this.window[i]
        }

        // Forward FFT
        this._fft(re, im, false)

        // Per-band processing
        for (let b = 0; b < this.numBands; b++) {
          const binStart = this.bandEdges[b]
          const binEnd = this.bandEdges[b + 1]

          // Compute band energy
          let bandMag = 0
          for (let bin = binStart; bin < binEnd && bin < N / 2; bin++) {
            bandMag += Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin])
          }
          bandMag /= Math.max(1, binEnd - binStart)

          // Fast envelope (tracks direct signal)
          const fastCoeff = 0.3  // fast attack
          if (bandMag > this.fastEnv[b]) {
            this.fastEnv[b] = bandMag
          } else {
            this.fastEnv[b] *= 0.85
          }

          // Slow envelope (tracks reverb tail)
          this.slowEnv[b] = this.slowEnv[b] * slowCoeff + bandMag * (1 - slowCoeff)

          // Transient detection: fast env jumps above slow env by threshold
          const energyRatio = this.slowEnv[b] > 1e-10 ? this.fastEnv[b] / this.slowEnv[b] : 1
          if (energyRatio > transThresh) {
            // Transient detected — direct signal
            this.tailActive[b] = 0
            this.tailCounter[b] = 0
            // Update decay estimate based on how fast slow env was rising
          } else {
            this.tailActive[b] = 1
            this.tailCounter[b]++
          }

          // Compute gain: suppress tail, preserve direct signal
          let targetGain = 1
          if (this.tailActive[b] && this.tailCounter[b] > 2) {
            // In tail — reduce
            // Amount of reduction depends on how much the tail dominates
            const tailDominance = 1 - Math.min(1, this.fastEnv[b] / (this.slowEnv[b] + 1e-10))
            targetGain = 1 - tailDominance * (1 - reductionGain) * (1 - preserveAmt * 0.5)
          }

          // Smooth gain
          this.prevGain[b] = this.prevGain[b] * 0.8 + targetGain * 0.2
          const gain = this.prevGain[b]

          // Apply gain to all bins in this band
          for (let bin = binStart; bin < binEnd && bin < N / 2; bin++) {
            re[bin] *= gain
            im[bin] *= gain
          }
        }

        // Mirror to upper half (conjugate symmetry)
        for (let bin = N / 2; bin < N; bin++) {
          const mirror = N - bin
          re[bin] = re[mirror]
          im[bin] = -im[mirror]
        }

        // Inverse FFT
        this._fft(re, im, true)

        // Overlap-add
        for (let i = 0; i < N; i++) {
          const idx = (this.outBufPos + i) % N
          this.outBuf[idx] += re[i] * this.window[i] * (H / N)
        }

        this.outBufPos = (this.outBufPos + H) % N
        this.inPos = (this.inPos + H) % N
        this.inFilled -= H
      }

      // Output
      for (let i = 0; i < n; i++) {
        const wet = this.outBuf[this.outBufPos % N]
        this.outBuf[this.outBufPos % N] = 0
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
    if (this.inBuf) this.inBuf.fill(0)
    if (this.outBuf) this.outBuf.fill(0)
    if (this.fastEnv) this.fastEnv.fill(0)
    if (this.slowEnv) this.slowEnv.fill(0)
    if (this.bandGain) this.bandGain.fill(1)
    if (this.prevGain) this.prevGain.fill(1)
    if (this.tailActive) this.tailActive.fill(0)
    if (this.tailCounter) this.tailCounter.fill(0)
    if (this.decayCoeff) this.decayCoeff.fill(0.99)
  }
}
