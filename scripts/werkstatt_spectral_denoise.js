// @werkstatt spectral_denoise 1 1
// @label Spectral Denoiser (Noise Floor Subtraction)
// Restoration tool: learns noise floor from low-energy frames, subtracts noise spectrum
// iZotope RX Spectral De-noise / CEDAR DNS / Berouti & Schwartz spectral subtraction (1979)

// @param reduction  0.6  0  1    linear   // noise reduction amount: 0=none, 1=max (-30 dB)
// @param learn_time 0.3  0  1    linear   // noise learning time: 0=fast (0.5s), 1=slow (10s) — accumulates noise profile
// @param oversub    0.5  0  1    linear   // oversubtraction factor: 0=1x, 1=4x (aggressive, more artifacts)
// @param floor      0.2  0  1    linear   // spectral floor: 0=silence, 1=full (prevents musical noise)
// @param smoothing  0.5  0  1    linear   // gain smoothing across bins (reduces musical noise artifacts)
// @param mix        1    0  1    linear   // dry/wet mix
// @param output     0    -12 6  linear dB

class Processor {
  p = {reduction: 0.6, learn_time: 0.3, oversub: 0.5, floor: 0.2, smoothing: 0.5, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  FFT_SIZE = 1024
  HOP_SIZE = 512
  inBuf = null
  inPos = 0
  inFilled = 0
  outBuf = null
  outBufPos = 0
  window = null

  // Noise profile
  noiseMag = null       // accumulated noise magnitude spectrum
  noiseCount = 0        // number of noise frames accumulated
  noiseLearned = false  // true after enough noise frames
  noiseThreshold = 0    // energy threshold for noise frames

  // Per-bin gain (smoothed)
  gainBins = null       // current applied gain per bin
  prevGain = null       // previous frame gain for smoothing

  // Energy tracking for noise detection
  frameEnergy = 0
  noiseFramesTarget = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    const N = this.FFT_SIZE
    this.inBuf = new Float32Array(N)
    this.outBuf = new Float32Array(N)
    this.noiseMag = new Float32Array(N)
    this.gainBins = new Float32Array(N)
    this.prevGain = new Float32Array(N)
    this.window = new Float32Array(N)

    for (let i = 0; i < N; i++) {
      this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (N - 1)))
    }
    this.gainBins.fill(1)
    this.prevGain.fill(1)
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

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const n = output[0].length
    const N = this.FFT_SIZE
    const H = this.HOP_SIZE
    const og = this.outGain
    const mix = this.p.mix

    // Reduction amount: 0→0 dB, 1→-30 dB
    const reductionDb = -this.p.reduction * 30
    const reductionGain = Math.pow(10, reductionDb / 20)

    // Oversubtraction: 1x to 4x
    const oversubFactor = 1 + this.p.oversub * 3

    // Spectral floor: 0→0 (silence), 1→1 (no reduction)
    const floorLevel = this.p.floor

    // Smoothing coefficient
    const smoothCoeff = this.p.smoothing * 0.9

    // Noise learning target: learn_time 0→0.5s, 1→10s
    const learnSeconds = 0.5 + this.p.learn_time * 9.5
    const framesPerSec = this.sr / H
    this.noiseFramesTarget = Math.round(learnSeconds * framesPerSec)

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

        // Compute frame energy
        let energy = 0
        for (let i = 0; i < N; i++) energy += re[i] * re[i]
        energy = Math.sqrt(energy / N)

        // Forward FFT
        this._fft(re, im, false)

        // --- Noise learning phase ---
        // During learning, accumulate noise spectrum from all frames
        // (assuming input is mostly noise during learning period)
        if (this.noiseCount < this.noiseFramesTarget) {
          for (let bin = 0; bin < N / 2; bin++) {
            const mag = Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin])
            this.noiseMag[bin] += mag
          }
          this.noiseCount++
          this.noiseThreshold = Math.max(this.noiseThreshold, energy) // track max noise energy

          if (this.noiseCount >= this.noiseFramesTarget) {
            // Average the accumulated noise magnitudes
            for (let bin = 0; bin < N; bin++) {
              this.noiseMag[bin] /= this.noiseCount
            }
            this.noiseLearned = true
          }

          // During learning, pass through
          for (let bin = 0; bin < N; bin++) {
            re[bin] = 0
            im[bin] = 0
          }
        } else if (this.noiseLearned) {
          // --- Denoising phase ---
          for (let bin = 0; bin < N / 2; bin++) {
            const mag = Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin])
            const phase = Math.atan2(im[bin], re[bin])

            // Noise floor for this bin
            const noiseBin = this.noiseMag[bin] * oversubFactor

            // Spectral subtraction: subtract noise from signal
            let cleanMag = mag - noiseBin

            // Apply reduction amount (partial subtraction)
            cleanMag = mag - (mag - cleanMag) * (1 - reductionGain)

            // Spectral floor: don't go below floorLevel * mag
            const minMag = mag * floorLevel
            if (cleanMag < minMag) cleanMag = minMag

            // Half-wave rectification
            if (cleanMag < 0) cleanMag = 0

            // Compute gain (cleanMag / mag)
            const gain = mag > 1e-10 ? cleanMag / mag : 1

            // Smoothing: blend with previous frame's gain
            const smoothedGain = this.prevGain[bin] + (gain - this.prevGain[bin]) * (1 - smoothCoeff)
            this.prevGain[bin] = smoothedGain
            this.gainBins[bin] = smoothedGain

            // Apply gain
            re[bin] = mag * smoothedGain * Math.cos(phase)
            im[bin] = mag * smoothedGain * Math.sin(phase)
          }

          // Mirror to upper half (conjugate symmetry)
          for (let bin = N / 2; bin < N; bin++) {
            const mirror = N - bin
            re[bin] = re[mirror]
            im[bin] = -im[mirror]
          }
        }

        // Inverse FFT
        this._fft(re, im, true)

        // Overlap-add
        for (let i = 0; i < N; i++) {
          const idx = (this.outBufPos + i) % N
          this.outBuf[idx] += re[i] * this.window[i] * (H / N)
        }

        // Advance
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
    this.noiseCount = 0
    this.noiseLearned = false
    this.noiseThreshold = 0
    if (this.inBuf) this.inBuf.fill(0)
    if (this.outBuf) this.outBuf.fill(0)
    if (this.noiseMag) this.noiseMag.fill(0)
    if (this.gainBins) this.gainBins.fill(1)
    if (this.prevGain) this.prevGain.fill(1)
  }
}
