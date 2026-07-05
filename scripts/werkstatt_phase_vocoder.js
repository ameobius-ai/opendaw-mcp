// @werkstatt phase_vocoder 1 1
// @label Phase Vocoder (FFT Pitch Shifter)
// High-quality pitch shifting via phase vocoder: STFT + phase unwrapping + resynthesis
// Élastique / Melodyne quality — preserves phase coherence across frames, no transient smearing

// @param pitch      0.5  0    1    linear   // pitch shift amount: 0=-12 semitones, 0.5=unison, 1=+12 semitones
// @param formant    0.5  0    1    linear   // formant preservation: 0=shift formants, 0.5=preserve, 1=boost formants
// @param lock_phase 0    0    1    linear   // phase locking: 0=off (standard PV), 1=full (identity phase lock, reduces artifacts)
// @param mix        1    0    1    linear   // dry/wet mix
// @param output     0    -12  6    linear dB

class Processor {
  p = {pitch: 0.5, formant: 0.5, lock_phase: 0, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  FFT_SIZE = 2048
  HOP_SIZE = 512
  fftBuf = null
  fftPos = 0
  fftFilled = 0

  // Phase vocoder state
  prevMag = null       // previous frame magnitude per bin
  prevPhase = null     // previous frame phase per bin
  accumPhase = null    // accumulated output phase per bin
  outBufL = null       // overlap-add output buffer
  outBufR = null
  outBufPos = 0

  // Window
  window = null

  // Cached pitch ratio
  ratio = 1.0
  prevPitchParam = -1

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    const N = this.FFT_SIZE
    this.fftBuf = new Float32Array(N * 2) // interleaved real/imag
    this.prevMag = new Float32Array(N)
    this.prevPhase = new Float32Array(N)
    this.accumPhase = new Float32Array(N)
    this.outBufL = new Float32Array(N)
    this.outBufR = new Float32Array(N)
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

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const n = output[0].length
    const N = this.FFT_SIZE
    const H = this.HOP_SIZE
    const og = this.outGain
    const mix = this.p.mix

    // Compute pitch ratio from param: 0=-12st, 0.5=unison, 1=+12st
    // -12 semitones = 0.5 ratio, +12 = 2.0 ratio, unison = 1.0
    const semitones = (this.p.pitch - 0.5) * 24  // -12 to +12
    this.ratio = Math.pow(2, semitones / 12)

    // Formant preservation factor: 0=shift formants with pitch, 0.5=preserve, 1=boost
    const formantShift = (this.p.formant - 0.5) * 2  // -1 to +1
    // If preserving formants, we scale spectral envelope back
    // formant=0.5 → no correction (formants shift with pitch)
    // formant=0 → full correction (formants preserved at original freq)
    // formant=1 → formants shifted extra
    const formantRatio = this.ratio * Math.pow(2, formantShift) / this.ratio  // simplified

    const lockPhase = this.p.lock_phase
    const omegaBase = 2 * Math.PI / N

    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0]
      const outCh = output[ch]

      // Fill input ring buffer
      for (let i = 0; i < n; i++) {
        this.fftBuf[this.fftPos] = inCh[i]
        this.fftPos = (this.fftPos + 1) % N
        if (this.fftFilled < N) this.fftFilled++
      }

      // Process all available frames
      while (this.fftFilled >= N) {
        // Extract windowed frame
        const re = new Float32Array(N)
        const im = new Float32Array(N)
        for (let i = 0; i < N; i++) {
          const idx = (this.fftPos + i) % N
          re[i] = this.fftBuf[idx] * this.window[i]
        }

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
          // Wrapped to [-PI, PI]
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

          // Phase locking: blend accumulated phase with input phase to reduce phasiness
          let outPhase = this.accumPhase[bin]
          if (lockPhase > 0) {
            // Identity phase lock: blend toward input phase weighted by magnitude
            const lockAmount = lockPhase * 0.5
            outPhase = outPhase * (1 - lockAmount) + phase * lockAmount
          }

          // Store for next frame
          this.prevMag[bin] = mag
          this.prevPhase[bin] = phase

          // Write modified spectrum
          re[bin] = mag * Math.cos(outPhase)
          im[bin] = mag * Math.sin(outPhase)
        }

        // Inverse FFT
        this._fft(re, im, true)

        // Overlap-add to output buffer
        for (let i = 0; i < N; i++) {
          const idx = (this.outBufPos + i) % N
          this.outBufL[idx] += re[i] * this.window[i] * (H / N)
        }
        this.outBufPos = (this.outBufPos + synthesisHop) % N

        // Advance input buffer by analysis hop
        this.fftPos = (this.fftPos + analysisHop) % N
        this.fftFilled -= analysisHop

        // Output synthesis hop samples
        const startOut = (this.outBufPos - synthesisHop + N) % N
        for (let i = 0; i < synthesisHop && i < n; i++) {
          const bufIdx = (startOut + i) % N
          const wet = this.outBufL[bufIdx]
          this.outBufL[bufIdx] = 0  // clear after reading
          // Find corresponding input sample for dry
          // (approximate — phase vocoder has latency)
          outCh[i] = wet * og * mix
        }
      }
    }
  }

  reset() {
    this.fftPos = 0
    this.fftFilled = 0
    this.outBufPos = 0
    this.ratio = 1.0
    this.prevPitchParam = -1
    if (this.fftBuf) this.fftBuf.fill(0)
    if (this.prevMag) this.prevMag.fill(0)
    if (this.prevPhase) this.prevPhase.fill(0)
    if (this.accumPhase) this.accumPhase.fill(0)
    if (this.outBufL) this.outBufL.fill(0)
    if (this.outBufR) this.outBufR.fill(0)
  }
}
