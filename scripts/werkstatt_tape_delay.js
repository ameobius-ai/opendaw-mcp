// @werkstatt tape_delay 1 1
// @label Tape Delay
// @param time 0.3 0.02 1 linear
// @param feedback 0.4 0 0.95 linear
// @param wow 0.2 0 1 linear
// @param flutter 0.3 0 1 linear
// @param saturation 0.3 0 1 linear
// @param mix 0.35 0 1 linear

class Processor {
  p = {time: 0.3, feedback: 0.4, wow: 0.2, flutter: 0.3, saturation: 0.3, mix: 0.35}
  sr = 44100
  bs = 128

  bufLen = 0
  bufL = null
  bufR = null
  writePos = 0
  readPosL = 0
  readPosR = 0

  // LFOs for wow (slow) and flutter (fast)
  wowPhase = 0
  flutterPhase = 0

  // saturation state
  satStateL = 0
  satStateR = 0

  initBuffers() {
    this.bufLen = Math.floor(this.sr * 1.5) // max 1.5s delay
    this.bufL = new Float32Array(this.bufLen)
    this.bufR = new Float32Array(this.bufLen)
    this.writePos = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.initBuffers()
  }

  // Tape saturation (soft clip in feedback path)
  _tapeSat(x, drive) {
    const k = 1 + drive * 4
    return Math.tanh(x * k) / k
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const bufLen = this.bufLen
    const baseDelay = Math.max(1, Math.floor(this.p.time * sr))
    const fb = this.p.feedback
    const wowAmt = this.p.wow * 0.003 // up to 0.3% pitch wobble (slow)
    const flutterAmt = this.p.flutter * 0.001 // up to 0.1% pitch wobble (fast)
    const satAmt = this.p.saturation
    const mix = this.p.mix

    const wowInc = 2 * Math.PI * 0.5 / sr // 0.5 Hz wow
    const flutterInc = 2 * Math.PI * 15 / sr // 15 Hz flutter

    for (let ch = 0; ch < out.length; ch++) {
      const ic = inp[ch] || inp[0]
      const oc = out[ch]
      if (!ic || !oc) continue

      const buf = ch === 0 ? this.bufL : this.bufR
      let satState = ch === 0 ? this.satStateL : this.satStateR

      for (let i = 0; i < ic.length; i++) {
        // Advance LFOs (shared across channels for stereo coherence)
        if (ch === 0) {
          this.wowPhase += wowInc
          this.flutterPhase += flutterInc
        }

        // Modulated delay time
        const wowMod = Math.sin(this.wowPhase) * wowAmt
        const flutterMod = Math.sin(this.flutterPhase) * flutterAmt
        const modDelay = baseDelay * (1 + wowMod + flutterMod)

        // Fractional delay read
        const readPos = (this.writePos - modDelay + bufLen * 2) % bufLen
        const idx0 = Math.floor(readPos)
        const idx1 = (idx0 + 1) % bufLen
        const frac = readPos - idx0
        const delayed = buf[idx0] * (1 - frac) + buf[idx1] * frac

        // Saturation in feedback path
        const saturated = this._tapeSat(delayed * fb, satAmt)
        satState = saturated

        // Write input + saturated feedback
        const dry = ic[i]
        buf[this.writePos] = dry + saturated

        // Advance write position (shared across channels)
        if (ch === 0) {
          this.writePos = (this.writePos + 1) % bufLen
        }

        // Dry/wet
        oc[i] = dry * (1 - mix) + delayed * mix
      }

      if (ch === 0) this.satStateL = satState
      else this.satStateR = satState
    }
  }
}
