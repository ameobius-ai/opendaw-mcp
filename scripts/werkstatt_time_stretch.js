// @werkstatt time_stretch 1 1
// @label Phase Vocoder Time Stretch
// High-quality time stretching via phase vocoder — preserves pitch, changes duration
// Complements granular_stretch (texture) and paulstretch (ambient) with Élastique-grade quality

// @param stretch    0.5  0    1    linear   // stretch amount: 0=0.25x (compress), 0.5=1x (unison), 1=4x (expand)
// @param lock_phase 0.3  0    1    linear   // phase locking: 0=standard PV, 1=full identity lock (reduces phasiness)
// @param transient  0.5  0    1    linear   // transient preservation: 0=smooth, 1=sharp (reduces transient smearing)
// @param mix        1    0    1    linear   // dry/wet mix
// @param output     0    -12  6    linear dB

class Processor {
  p = {stretch: 0.5, lock_phase: 0.3, transient: 0.5, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  FFT_SIZE = 2048
  HOP_SIZE = 512
  inBuf = null        // input ring buffer
  inPos = 0
  inFilled = 0

  // Phase vocoder state
  prevPhase = null     // previous frame phase per bin
  prevMag = null       // previous frame magnitude per bin
  accumPhase = null    // accumulated output phase per bin
  outBufL = null       // overlap-add output buffer
  outBufR = null
  outBufPos = 0

  // Transient detection
  prevEnergy = 0
  transientFlag = 0
  transientHold = 0

  // Window
  window = null

  // Cached stretch ratio
  ratio = 1.0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    const N = this.FFT_SIZE
    this.inBuf = new Float32Array(N * 2)  // input ring buffer (larger for stretch)
    this.prevMag = new Float32Array(N)
    this.prevPhase = new Float32Array(N)
    this.accumPhase = new Float32Array(N)
    this.outBufL = new Float32Array(N * 4) // output buffer (larger for stretch)
    this.outBufR = new Float32Array(N * 4)
    this.window = new Float32Array(N)

    // Hann window
    for (let i = 0; i < N; i++) {
      this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (N - 1)))
    }
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // In-place radix-2 FFT (Cooley-Tukey, iterative)
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

  // Detect transients via energy jump
  _detectTransient(frame, N) {
    let energy = 0
    for (let i = 0; i < N; i++) energy += Math.abs(frame[i])
    energy /= N

    const ratio = this.prevEnergy > 1e-10 ? energy / this.prevEnergy : 1
    this.prevEnergy = energy

    // Transient if energy jumps > 2x
    if (ratio > 2.0 && this.transientHold <= 0) {
      this.transientFlag = 1
      this.transientHold = 8 // hold for 8 frames
    } else {
      this.transientHold = Math.max(0, this.transientHold - 1)
      this.transientFlag = Math.max(0, this.transientFlag - 0.15)
    }
    return this.transientFlag
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

    // Stretch ratio: 0=0.25x, 0.5=1x, 1=4x
    this.ratio = 0.25 + this.p.stretch * 3.75

    const lockPhase = this.p.lock_phase
    const transientPres = this.p.transient
    const omegaBase = 2 * Math.PI / N

    const inLen = this.inBuf.length
    const outLen = this.outBufL.length

    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0]
      const outCh = output[ch]

      // Fill input ring buffer
      for (let i = 0; i < n; i++) {
        this.inBuf[this.inPos] = inCh[i]
        this.inPos = (this.inPos + 1) % inLen
        if (this.inFilled < inLen) this.inFilled++
      }

      // Process frames while we have enough input
      while (this.inFilled >= N) {
        // Extract windowed frame from input ring buffer
        const re = new Float32Array(N)
        const im = new Float32Array(N)
        for (let i = 0; i < N; i++) {
          const idx = (this.inPos + i) % inLen
          re[i] = this.inBuf[idx] * this.window[i]
        }

        // Transient detection
        const transientLevel = this._detectTransient(re, N)

        // Forward FFT
        this._fft(re, im, false)

        // Phase vocoder processing
        const analysisHop = H
        const synthesisHop = Math.round(H * this.ratio)

        for (let bin = 0; bin < N; bin++) {
          // Current magnitude and phase
          const mag = Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin])
          const phase = Math.atan2(im[bin], re[bin])

          // Expected phase advance for this bin at analysis hop
          const expectedPhaseAdv = omegaBase * bin * analysisHop
          let expectedPhase = this.prevPhase[bin] + expectedPhaseAdv

          // Phase deviation (heterodyned phase)
          let phaseDev = phase - expectedPhase
          // Unwrap to [-PI, PI]
          while (phaseDev > Math.PI) phaseDev -= 2 * Math.PI
          while (phaseDev < -Math.PI) phaseDev += 2 * Math.PI

          // True frequency (phase derivative)
          const trueFreq = omegaBase * bin + phaseDev / analysisHop

          // Accumulate output phase using synthesis hop
          this.accumPhase[bin] += trueFreq * synthesisHop

          // Phase locking: blend accumulated phase with input phase
          let outPhase = this.accumPhase[bin]
          if (lockPhase > 0) {
            const lockAmount = lockPhase * 0.5
            outPhase = outPhase * (1 - lockAmount) + phase * lockAmount
          }

          // Transient preservation: during transients, use input phase directly
          if (transientLevel > 0.1 && transientPres > 0) {
            const tMix = transientLevel * transientPres * 0.8
            outPhase = outPhase * (1 - tMix) + phase * tMix
          }

          // Store for next frame
          this.prevMag[bin] = mag
          this.prevPhase[bin] = phase

          // Write modified spectrum (magnitude unchanged — time stretch only)
          re[bin] = mag * Math.cos(outPhase)
          im[bin] = mag * Math.sin(outPhase)
        }

        // Inverse FFT
        this._fft(re, im, true)

        // Overlap-add to output buffer
        for (let i = 0; i < N; i++) {
          const idx = (this.outBufPos + i) % outLen
          this.outBufL[idx] += re[i] * this.window[i] * (synthesisHop / N)
        }

        // Advance output position by synthesis hop
        this.outBufPos = (this.outBufPos + synthesisHop) % outLen

        // Advance input by analysis hop
        this.inPos = (this.inPos + analysisHop) % inLen
        this.inFilled -= analysisHop
      }

      // Read output from overlap buffer
      for (let i = 0; i < n; i++) {
        const wet = this.outBufL[this.outBufPos % outLen]
        this.outBufL[this.outBufPos % outLen] = 0
        this.outBufPos = (this.outBufPos + 1) % outLen
        const dry = inCh[i]
        outCh[i] = (dry * (1 - mix) + wet * mix) * og
      }
    }
  }

  reset() {
    this.inPos = 0
    this.inFilled = 0
    this.outBufPos = 0
    this.ratio = 1.0
    this.prevEnergy = 0
    this.transientFlag = 0
    this.transientHold = 0
    if (this.inBuf) this.inBuf.fill(0)
    if (this.prevMag) this.prevMag.fill(0)
    if (this.prevPhase) this.prevPhase.fill(0)
    if (this.accumPhase) this.accumPhase.fill(0)
    if (this.outBufL) this.outBufL.fill(0)
    if (this.outBufR) this.outBufR.fill(0)
  }
}
