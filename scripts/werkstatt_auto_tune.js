// @werkstatt auto_tune 1 1
// @label Auto-Tune (Pitch Correction)
// Pitch detection via autocorrelation + snap-to-scale correction + time-domain pitch shifting
// Cher "Believe" / T-Pain style — retune speed controls hard (robot) vs soft (natural) correction

// @param key        0    0  11 int      // scale root: 0=C, 1=C#, ..., 11=B
// @param scale      0    0  6  int      // 0=chromatic, 1=major, 2=minor, 3=dorian, 4=mixolydian, 5=pentatonic minor, 6=blues
// @param retune     0.5  0  1  linear   // retune speed: 0=slow (natural), 1=fast (hard/auto-tune effect)
// @param strength   1    0  1  linear   // correction strength: 0=none, 1=full snap
// @param detune     0    0  1  linear   // pitch shift offset in cents: 0=0, 1=+50 cents
// @param mix        1    0  1  linear   // dry/wet mix
// @param output     0    -12 6 linear dB

class Processor {
  p = {key: 0, scale: 0, retune: 0.5, strength: 1, detune: 0, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Pitch detection buffer (autocorrelation)
  PD_SIZE = 2048
  pdBuf = null      // circular input buffer for pitch detection
  pdPos = 0
  pdFilled = 0
  detectedFreq = 0
  detectedPitch = -1  // MIDI note (float)
  pdCounter = 0
  pdPeriod = 0        // detected period in samples

  // Pitch shifter: overlap-add granular
  PS_GRAIN = 256
  psInBuf = null      // input ring buffer
  psInPos = 0
  psOutBuf = null     // output overlap buffer
  psOutPos = 0
  psRatio = 1.0       // current pitch ratio
  psTargetRatio = 1.0
  psWindow = null

  // Scale intervals
  SCALES = [
    [0,1,2,3,4,5,6,7,8,9,10,11],                    // chromatic
    [0,2,4,5,7,9,11],                                // major
    [0,2,3,5,7,10,12],                               // natural minor
    [0,2,3,5,7,9,11],                                // dorian
    [0,2,4,5,7,9,10],                                // mixolydian
    [0,3,5,7,10,12],                                 // minor pentatonic
    [0,3,5,6,7,10,12],                               // blues
  ]

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._init()
  }

  _init() {
    this.pdBuf = new Float32Array(this.PD_SIZE)
    this.psInBuf = new Float32Array(this.PS_GRAIN * 4)
    this.psOutBuf = new Float32Array(this.PS_GRAIN * 4)
    this.psWindow = new Float32Array(this.PS_GRAIN)
    for (let i = 0; i < this.PS_GRAIN; i++) {
      this.psWindow[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (this.PS_GRAIN - 1)))
    }
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // Frequency to MIDI note (float)
  _freqToMidi(freq) {
    return 69 + 12 * Math.log2(freq / 440)
  }

  // MIDI note to frequency
  _midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12)
  }

  // Snap MIDI note to nearest scale degree
  _snapToScale(midiFloat) {
    const root = Math.round(this.p.key) % 12
    const scaleIdx = Math.round(this.p.scale) % 7
    const intervals = this.SCALES[scaleIdx]
    const noteInOctave = ((Math.round(midiFloat) - root) % 12 + 12) % 12

    // Find nearest scale note
    let bestDist = 12
    let bestOffset = 0
    for (let i = 0; i < intervals.length; i++) {
      const dist = Math.abs(midiFloat - (Math.floor(midiFloat / 12) * 12 + root + intervals[i]))
      const wrappedDist = Math.min(
        Math.abs(((noteInOctave - intervals[i]) % 12 + 12) % 12),
        12 - Math.abs(((noteInOctave - intervals[i]) % 12 + 12) % 12)
      )
      if (wrappedDist < bestDist) {
        bestDist = wrappedDist
        bestOffset = intervals[i]
      }
    }

    // Build target note: same octave as input + nearest scale note
    const octave = Math.floor(midiFloat / 12)
    let target = octave * 12 + (root + bestOffset) % 12
    // Handle wrap: if target is too far, try adjacent octave
    while (target < midiFloat - 6) target += 12
    while (target > midiFloat + 6) target -= 12
    return target
  }

  // Autocorrelation pitch detection
  // Returns frequency in Hz, or 0 if no pitch found
  _detectPitch() {
    const buf = this.pdBuf
    const N = this.PD_SIZE
    const filled = this.pdFilled
    if (filled < 256) return 0

    // Normalize
    let rms = 0
    for (let i = 0; i < N; i++) rms += buf[i] * buf[i]
    rms = Math.sqrt(rms / N)
    if (rms < 0.001) return 0  // silence

    // Autocorrelation: find period
    // Search range: 60 Hz to 1200 Hz
    const minLag = Math.floor(this.sr / 1200)
    const maxLag = Math.floor(this.sr / 60)
    if (maxLag >= N) maxLag = N - 1

    let bestLag = 0
    let bestCorr = 0
    let prevCorr = 0

    for (let lag = minLag; lag <= maxLag; lag++) {
      let corr = 0
      for (let i = 0; i < N - lag; i++) {
        corr += buf[i] * buf[i + lag]
      }
      corr /= (N - lag)

      // Normalized correlation
      corr /= (rms * rms + 1e-10)

      // Peak detection: look for local maxima
      if (corr > bestCorr && corr > 0.1) {
        // Check it's a local peak (not just monotonically rising)
        if (corr >= prevCorr) {
          bestCorr = corr
          bestLag = lag
        }
      }
      prevCorr = corr
    }

    if (bestLag === 0 || bestCorr < 0.1) return 0

    // Parabolic interpolation for sub-sample accuracy
    if (bestLag > minLag && bestLag < maxLag) {
      let y1 = 0, y2 = 0, y3 = 0
      for (let i = 0; i < N - bestLag + 1; i++) y2 += buf[i] * buf[i + bestLag]
      for (let i = 0; i < N - bestLag; i++) y1 += buf[i] * buf[i + bestLag - 1]
      for (let i = 0; i < N - bestLag - 1; i++) y3 += buf[i] * buf[i + bestLag + 1]
      const denom = (y1 - 2 * y2 + y3)
      if (Math.abs(denom) > 1e-10) {
        const offset = 0.5 * (y1 - y3) / denom
        bestLag = bestLag + Math.max(-1, Math.min(1, offset))
      }
    }

    return this.sr / bestLag
  }

  // Granular pitch shift: overlap-add with Hann window
  // Reads from psInBuf at rate psRatio, writes to psOutBuf
  _pitchShiftBlock(input, output, n) {
    const inBuf = this.psInBuf
    const outBuf = this.psOutBuf
    const grain = this.PS_GRAIN
    const win = this.psWindow
    const inLen = inBuf.length
    const outLen = outBuf.length
    const ratio = this.psRatio

    for (let i = 0; i < n; i++) {
      // Write input to ring buffer
      inBuf[this.psInPos] = input[i]
      this.psInPos = (this.psInPos + 1) % inLen

      // Read from input buffer at pitch-shifted rate
      // The read pointer advances by ratio per output sample
      // We use a fixed grain: read grain samples starting from psInPos - grain
      // then write to output with windowing

      // Simple approach: linear interpolation read from ring buffer
      // readPos advances by ratio
      if (!this._readPos) this._readPos = 0
      const readIdx = Math.floor(this._readPos)
      const frac = this._readPos - readIdx
      const s0 = inBuf[(this.psInPos - grain + readIdx + inLen * 2) % inLen]
      const s1 = inBuf[(this.psInPos - grain + readIdx + 1 + inLen * 2) % inLen]
      const shifted = s0 + (s1 - s0) * frac

      // Overlap-add with windowing
      outBuf[this.psOutPos] += shifted * win[this._grainPos]
      this._grainPos = (this._grainPos + 1) % grain
      if (this._grainPos === 0) {
        // Reset overlap region for next grain
        const startOverlap = this.psOutPos
        for (let j = 0; j < grain; j++) {
          outBuf[(startOverlap + j) % outLen] = 0
        }
        this.psOutPos = startOverlap
      }

      output[i] = outBuf[this.psOutPos]
      this.psOutPos = (this.psOutPos + 1) % outLen

      this._readPos += ratio
      if (this._readPos >= inLen) this._readPos -= inLen
    }
  }

  // Simplified granular pitch shift using PSOLA-like approach
  _processPitchShift(input, output, n) {
    const ratio = this.psRatio
    const inBuf = this.psInBuf
    const inLen = inBuf.length
    const win = this.psWindow
    const grain = this.PS_GRAIN

    for (let i = 0; i < n; i++) {
      // Store input
      inBuf[this.psInPos] = input[i]
      this.psInPos = (this.psInPos + 1) % inLen

      // Output: linear interpolation from ring buffer at read position
      if (this._readPos === undefined) this._readPos = 0
      const ri = Math.floor(this._readPos)
      const rf = this._readPos - ri
      // Read from behind write pointer by grain size to avoid reading uninitialized
      const base = (this.psInPos - grain + inLen) % inLen
      const s0 = inBuf[(base + ri) % inLen]
      const s1 = inBuf[(base + ri + 1) % inLen]
      output[i] = s0 + (s1 - s0) * rf

      this._readPos += ratio
      // Keep read pointer within a grain length behind write pointer
      if (this._readPos >= grain) {
        this._readPos -= grain
      }
    }
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const n = output[0].length
    const og = this.outGain
    const mix = this.p.mix
    const retune = this.p.retune

    // Smoothly approach target pitch ratio
    // retune 0 = 0.001 per sample (slow), 1 = 0.1 per sample (instant)
    const retuneCoeff = 0.001 + 0.099 * retune

    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0]
      const outCh = output[ch]

      // 1. Fill pitch detection buffer (mono, use channel 0)
      if (ch === 0) {
        for (let i = 0; i < n; i++) {
          this.pdBuf[this.pdPos] = inCh[i]
          this.pdPos = (this.pdPos + 1) % this.PD_SIZE
          if (this.pdFilled < this.PD_SIZE) this.pdFilled++
        }

        // Run pitch detection every N samples
        this.pdCounter += n
        if (this.pdCounter >= 256) {
          this.pdCounter = 0
          const freq = this._detectPitch()
          if (freq > 0) {
            this.detectedFreq = freq
            this.detectedPitch = this._freqToMidi(freq)
            // Snap to scale
            const targetNote = this._snapToScale(this.detectedPitch + this.p.detune * 0.5)
            // Apply strength
            const correctedNote = this.detectedPitch * (1 - this.p.strength) + targetNote * this.p.strength
            // Compute pitch ratio
            const targetFreq = this._midiToFreq(correctedNote)
            this.psTargetRatio = targetFreq / freq
          } else {
            // No pitch: pass through
            this.psTargetRatio = 1.0
          }
        }

        // Smooth ratio interpolation
        this.psRatio += (this.psTargetRatio - this.psRatio) * retuneCoeff
      }

      // 2. Pitch shift
      this._processPitchShift(inCh, outCh, n)

      // 3. Mix + output gain
      for (let i = 0; i < n; i++) {
        const dry = inCh[i]
        const wet = outCh[i]
        outCh[i] = (dry * (1 - mix) + wet * mix) * og
      }
    }
  }

  // Reset state for new voice
  reset() {
    this.pdPos = 0
    this.pdFilled = 0
    this.pdCounter = 0
    this.detectedFreq = 0
    this.detectedPitch = -1
    this.psInPos = 0
    this.psOutPos = 0
    this.psRatio = 1.0
    this.psTargetRatio = 1.0
    this._readPos = 0
    this._grainPos = 0
    this.pdBuf.fill(0)
    this.psInBuf.fill(0)
    this.psOutBuf.fill(0)
  }
}
