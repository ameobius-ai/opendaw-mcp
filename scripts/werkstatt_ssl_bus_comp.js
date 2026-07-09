// @werkstatt ssl_bus_comp 1 1
// @label SSL Bus Comp
// SSL G-series bus compressor (the glue compressor)
// VCA-based with smooth gain reduction, signature mix bus sound
// Known for "gluing" a mix together — subtle but transformative
// NOTE: compiles and validates, but processAudio not called in minimal test.
// Works through full produce_ostayus pipeline — needs proper bus routing.
// @param threshold 0.5 0 1 linear
// @param ratio 0.3 0 1 linear
// @param attack 0.3 0 1 linear
// @param release 0.3 0 1 linear
// @param makeup 0.5 0 1 linear
// @param mix 1.0 0 1 linear
// @param auto_release 1.0 0 1 bool

class Processor {
  constructor(sampleRate, blockSize) {
    this.sr = sampleRate || 48000
    this.p = {threshold: 0.5, ratio: 0.3, attack: 0.3, release: 0.3, makeup: 0.5, mix: 1.0, auto_release: 1.0}

    // RMS detector state
    this.rmsWindow = new Float32Array(256)
    this.rmsPos = 0
    this.rmsSum = 0

    // Envelope follower state
    this.env = 1

    // Auto-release state
    this.compressionHistory = 0

    // DC blocker state
    this.dcIn = 0
    this.dcOut = 0

    this._updateCoeffs()
  }

  _updateCoeffs() {
    const attackRaw = this.p.attack
    const releaseRaw = this.p.release

    // Attack: SSL stepped (0.1, 0.3, 1, 3, 10, 30 ms)
    const attackSteps = [0.1, 0.3, 1, 3, 10, 30]
    const attackIdx = Math.min(Math.floor(attackRaw * 6), 5)
    const attackMs = attackSteps[attackIdx]
    this.attackCoeff = Math.exp(-1 / (this.sr * attackMs * 0.001))

    // Release: SSL stepped (0.1, 0.3, 1, 3, 10 sec)
    const releaseSteps = [0.1, 0.3, 1, 3, 10]
    const releaseIdx = Math.min(Math.floor(releaseRaw * 5), 4)
    const releaseMs = releaseSteps[releaseIdx] * 1000
    this.releaseCoeff = Math.exp(-1 / (this.sr * releaseMs * 0.001))
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "attack" || name === "release") this._updateCoeffs()
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const numCh = output.length
    if (numCh === 0) return
    const numFrames = output[0].length
    if (numFrames === 0) return

    const thresholdRaw = this.p.threshold
    const ratioRaw = this.p.ratio
    const makeupRaw = this.p.makeup
    const mix = this.p.mix
    const autoRelease = (this.p.auto_release || 1.0) > 0.5

    // Threshold: -30 to 0 dB
    const thresholdDb = -30 + thresholdRaw * 30
    const thresholdLinear = Math.pow(10, thresholdDb / 20)

    // Ratio: 2:1, 4:1, 10:1
    const ratioSteps = [2, 4, 10]
    const ratioIdx = Math.min(Math.floor(ratioRaw * 3), 2)
    const ratio = ratioSteps[ratioIdx]

    // Makeup: 0 to +24 dB
    const makeupDb = makeupRaw * 24
    const makeupGain = Math.pow(10, makeupDb / 20)

    for (let i = 0; i < numFrames; i++) {
      // Mix to mono for detector
      let inSample = 0
      let chCount = 0
      for (let c = 0; c < numCh; c++) {
        if (input[c]) { inSample += input[c][i]; chCount++ }
      }
      if (chCount > 0) inSample /= chCount

      // RMS detection (256-sample window)
      const oldSample = this.rmsWindow[this.rmsPos]
      const newSquared = inSample * inSample
      this.rmsSum = this.rmsSum - oldSample * oldSample + newSquared
      this.rmsWindow[this.rmsPos] = inSample
      this.rmsPos = (this.rmsPos + 1) % this.rmsWindow.length

      const rms = Math.sqrt(Math.max(this.rmsSum / this.rmsWindow.length, 1e-10))

      // Gain reduction
      let compGain = 1
      if (rms > thresholdLinear) {
        const rmsDb = 20 * Math.log10(rms)
        const overDb = rmsDb - thresholdDb
        const reducedDb = overDb * (1 - 1 / ratio)
        compGain = Math.pow(10, -reducedDb / 20)
      }

      // Auto-release
      let actualReleaseCoeff = this.releaseCoeff
      if (autoRelease) {
        this.compressionHistory = this.compressionHistory * 0.99 + (1 - compGain) * 0.01
        const speedup = 1 + this.compressionHistory * 3
        actualReleaseCoeff = Math.pow(this.releaseCoeff, speedup)
      }

      // Envelope follower
      if (compGain < this.env) {
        this.env = this.attackCoeff * this.env + (1 - this.attackCoeff) * compGain
      } else {
        this.env = actualReleaseCoeff * this.env + (1 - actualReleaseCoeff) * compGain
      }

      // Apply compression + makeup
      const compressed = inSample * this.env * makeupGain

      // Mix dry/wet
      const mixed = inSample * (1 - mix) + compressed * mix

      // DC blocker
      const dcOut = mixed - this.dcIn + 0.995 * this.dcOut
      this.dcIn = mixed
      this.dcOut = dcOut

      // Write to all channels (bus comp is mono-linked)
      for (let c = 0; c < numCh; c++) {
        output[c][i] = dcOut
      }
    }
  }
}
