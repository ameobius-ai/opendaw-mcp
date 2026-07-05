// @werkstatt maximizer 1 1
// @label Loudness Maximizer
// @param ceiling -1 -6 0 linear dB
// @param release 50 5 500 linear ms
// @param lookahead 1 0 1 linear ms
// @param dither 0.5 0 1 linear
// @param stereo_link 1 0 1 linear
// @param mix 1 0 1 linear

class Processor {
  p = {ceiling: -1, release: 50, lookahead: 1, dither: 0.5, stereo_link: 1, mix: 1}

  // Lookahead delay buffer
  delaySize = 64  // max ~1.5ms at 44100
  delayBufL = new Float32Array(64)
  delayBufR = new Float32Array(64)
  delayPos = 0

  // Envelope state
  envL = 0
  envR = 0
  maxEnv = 0

  // DC blocker for dither noise
  dcL = 0
  dcR = 0

  // Dither state (LFSR — TPDF)
  lfsr = 0x12345
  prevDithL = 0
  prevDithR = 0

  ceilGain = 0.891  // -1 dB
  relCoef = 0.999
  lookSamples = 44  // ~1ms at 44100

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "ceiling") {
      this.ceilGain = Math.pow(10, value / 20)
    }
    if (name === "release") {
      // release coefficient: time constant in samples
      const sr = this.sampleRate || 44100
      const ms = value
      const samples = sr * ms / 1000
      this.relCoef = Math.exp(-1 / samples)
    }
    if (name === "lookahead") {
      const sr = this.sampleRate || 44100
      this.lookSamples = Math.max(1, Math.min(63, Math.round(sr * value / 1000)))
    }
  }

  _dither() {
    // TPDF dither via LFSR
    this.lfsr = (this.lfsr << 1) | (((this.lfsr >> 0) ^ (this.lfsr >> 1) ^ (this.lfsr >> 3) ^ (this.lfsr >> 12)) & 1)
    this.lfsr &= 0xFFFF
    const r = (this.lfsr / 0xFFFF) * 2 - 1  // -1..1
    return r
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const inL = input[0]
    const inR = input[1] || input[0]
    const outL = output[0]
    const outR = output[1] || output[0]
    if (!inL || !outL) return

    const n = inL.length
    const ceil = this.ceilGain
    const relCoef = this.relCoef
    const lookS = this.lookSamples
    const sterLink = this.p.stereo_link
    const mix = this.p.mix
    const dithAmt = this.p.dither

    for (let i = 0; i < n; i++) {
      // Push into lookahead delay
      const dryL = inL[i]
      const dryR = inR[i]
      this.delayBufL[this.delayPos] = dryL
      this.delayBufR[this.delayPos] = dryR

      // Read delayed sample
      const readPos = (this.delayPos - lookS + 64) % 64
      const delayL = this.delayBufL[readPos]
      const delayR = this.delayBufR[readPos]

      // Detect peak (with lookahead — scan buffer ahead)
      let peak = 0
      for (let j = 0; j <= lookS; j++) {
        const p = (this.delayPos - j + 64) % 64
        const sL = Math.abs(this.delayBufL[p])
        const sR = Math.abs(this.delayBufR[p])
        const mx = sterLink > 0.5 ? Math.max(sL, sR) : Math.max(sL, sR)
        if (mx > peak) peak = mx
      }

      // Envelope follower — fast attack, slow release
      if (peak > this.maxEnv) {
        this.maxEnv = peak
      } else {
        this.maxEnv = this.maxEnv * relCoef + peak * (1 - relCoef)
      }

      // Calculate gain reduction
      let gain = 1
      if (this.maxEnv > ceil) {
        gain = ceil / this.maxEnv
      }

      // Apply gain to delayed signal
      let procL = delayL * gain
      let procR = delayR * gain

      // Hard ceiling (ISP protection)
      if (procL > ceil) procL = ceil
      if (procL < -ceil) procL = -ceil
      if (procR > ceil) procR = ceil
      if (procR < -ceil) procR = -ceil

      // TPDF dither
      if (dithAmt > 0) {
        const d1L = this._dither()
        const d2L = this._dither()
        const tpdfL = (d1L - this.prevDithL) * dithAmt * 0.5
        this.prevDithL = d1L
        procL += tpdfL * (ceil / 10)  // scale dither to signal level

        const d1R = this._dither()
        const d2R = this._dither()
        const tpdfR = (d1R - this.prevDithR) * dithAmt * 0.5
        this.prevDithR = d1R
        procR += tpdfR * (ceil / 10)
      }

      // Mix
      outL[i] = procL * mix + dryL * (1 - mix)
      outR[i] = procR * mix + dryR * (1 - mix)

      this.delayPos = (this.delayPos + 1) % 64
    }
  }
}
