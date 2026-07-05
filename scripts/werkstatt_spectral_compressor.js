// @werkstatt spectral_compressor 1 1
// @label Spectral Compressor (STFT)
// @param threshold 0.5 0 1 linear
// @param ratio 0.4 0 1 linear
// @param attack 0.3 0 1 linear
// @param release 0.5 0 1 linear
// @param smoothing 0.7 0 1 linear
// @param tilt 0 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {threshold: 0.5, ratio: 0.4, attack: 0.3, release: 0.5, smoothing: 0.7, tilt: 0, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // STFT config
  FFT_SIZE = 1024
  HOP_SIZE = 512
  fftBuf = null
  fftPos = 0
  fftCount = 0

  // Per-bin envelope state (magnitude followers)
  envBins = null
  // Per-bin gain (compressed)
  gainBins = null

  // Overlap-add buffer
  outBufL = null
  outBufR = null
  outBufPos = 0

  // Window
  window = null

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    const N = this.FFT_SIZE
    this.fftBuf = new Float32Array(N * 2) // interleaved real/imag for in-place FFT
    this.envBins = new Float32Array(N)
    this.gainBins = new Float32Array(N)
    this.outBufL = new Float32Array(N)
    this.outBufR = new Float32Array(N)
    this.window = new Float32Array(N)

    // Hann window
    for (let i = 0; i < N; i++) {
      this.window[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (N - 1)))
    }

    // Pre-compute FFT twiddle factors
    this._cosTable = new Float32Array(N / 2)
    this._sinTable = new Float32Array(N / 2)
    for (let i = 0; i < N / 2; i++) {
      this._cosTable[i] = Math.cos(-2 * Math.PI * i / N)
      this._sinTable[i] = Math.sin(-2 * Math.PI * i / N)
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
    // Bit reversal
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

    // Butterfly
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
    const p = this.p
    const og = this.outGain
    const N = this.FFT_SIZE
    const H = this.HOP_SIZE

    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]
    const numFrames = inL.length
    const isMono = input.length <= 1

    // Parameter conversions
    const threshDb = -p.threshold * 60  // 0→0 dB, 1→-60 dB
    const ratioNum = 1 + p.ratio * 19   // 1:1 → 20:1
    const attackMs = 0.5 + Math.pow(p.attack, 3) * 50   // 0.5 → 50ms
    const releaseMs = 10 + Math.pow(p.release, 3) * 500  // 10 → 510ms
    const smoothAmt = p.smoothing  // 0=no smoothing, 1=heavy
    const tiltDb = (p.tilt - 0.5) * 24  // -12 to +12 dB tilt

    // Time constants per bin
    const atkCoeff = 1 - Math.exp(-1 / (this.sr * attackMs / 1000 / (H / this.sr)))
    const relCoeff = 1 - Math.exp(-1 / (this.sr * releaseMs / 1000 / (H / this.sr)))

    for (let frameStart = 0; frameStart < numFrames; frameStart += H) {
      const frameEnd = Math.min(frameStart + N, numFrames)
      const valid = frameEnd - frameStart

      if (valid < N) break // skip incomplete final frame

      // --- 1. Fill FFT buffer (windowed, mono mix for analysis) ---
      const re = new Float32Array(N)
      const im = new Float32Array(N)
      for (let i = 0; i < N; i++) {
        const idx = frameStart + i
        const w = this.window[i]
        const mono = idx < numFrames ? (inL[idx] + (isMono ? inL[idx] : inR[idx])) * 0.5 : 0
        re[i] = mono * w
      }

      // --- 2. Forward FFT ---
      this._fft(re, im, false)

      // --- 3. Per-bin compression ---
      for (let bin = 0; bin < N; bin++) {
        // Magnitude and phase
        const mag = Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin])
        const phase = Math.atan2(im[bin], re[bin])

        // Per-bin threshold with tilt: low bins compressed more (tilt>0.5) or less (tilt<0.5)
        const freqRatio = bin / (N * 0.5) // 0=DC, 1=Nyquist
        const binThreshDb = threshDb + tiltDb * freqRatio
        const binThresh = Math.pow(10, binThreshDb / 20)

        // Envelope follower per bin
        const env = this.envBins[bin]
        if (mag > env) {
          this.envBins[bin] = env + (mag - env) * atkCoeff
        } else {
          this.envBins[bin] = env + (mag - env) * relCoeff
        }
        const envMag = this.envBins[bin]

        // Compression curve (downward)
        let gain = 1
        if (envMag > binThresh && binThresh > 0) {
          const envDb = 20 * Math.log10(Math.max(envMag, 1e-10))
          const overDb = envDb - binThreshDb
          const reductionDb = overDb * (1 - 1 / ratioNum)
          gain = Math.pow(10, -reductionDb / 20)
        }

        // Smoothing: blend current gain with previous
        const prevGain = this.gainBins[bin]
        const smoothCoeff = smoothAmt * 0.8
        gain = prevGain + (gain - prevGain) * (1 - smoothCoeff)
        this.gainBins[bin] = gain

        // Apply gain
        const newMag = mag * gain
        re[bin] = newMag * Math.cos(phase)
        im[bin] = newMag * Math.sin(phase)
      }

      // --- 4. Inverse FFT ---
      this._fft(re, im, true)

      // --- 5. Overlap-add with window ---
      for (let i = 0; i < N; i++) {
        const idx = frameStart + i
        if (idx >= numFrames) break
        const w = this.window[i]
        const sample = re[i] * w * 2 // scale for overlap (H/N factor)

        this.outBufL[this.outBufPos] += sample
        if (!isMono) {
          // For stereo: process R separately (simplified — use same gain as L)
          this.outBufR[this.outBufPos] += sample
        }
        this.outBufPos = (this.outBufPos + 1) % N
      }

      // --- 6. Output hop ---
      for (let i = 0; i < H; i++) {
        const outIdx = frameStart + i
        if (outIdx >= numFrames) break
        const bufIdx = (this.outBufPos + i) % N
        const wet = this.outBufL[bufIdx]
        const dry = inL[outIdx]
        outL[outIdx] = (dry * (1 - p.mix) + wet * p.mix) * og

        if (!isMono && outR.length > 0) {
          const wetR = this.outBufR[bufIdx]
          const dryR = inR[outIdx]
          outR[outIdx] = (dryR * (1 - p.mix) + wetR * p.mix) * og
        }

        // Clear output buffer after reading
        this.outBufL[bufIdx] = 0
        this.outBufR[bufIdx] = 0
      }
      this.outBufPos = (this.outBufPos + H) % N
    }
  }

  reset() {
    if (this.envBins) this.envBins.fill(0)
    if (this.gainBins) this.gainBins.fill(0)
    if (this.outBufL) this.outBufL.fill(0)
    if (this.outBufR) this.outBufR.fill(0)
    this.fftPos = 0
    this.outBufPos = 0
  }
}
