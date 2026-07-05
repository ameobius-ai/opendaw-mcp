// @werkstatt limiter 1 1
// @label Brickwall Limiter
// @param ceiling 0.9 0 1 linear
// @param release 0.3 0 1 linear
// @param lookahead 0.5 0 1 linear
// @param dither 0 0 1 linear
// @param mix 1 0 1 linear

class Processor {
  p = {ceiling: 0.9, release: 0.3, lookahead: 0.5, dither: 0, mix: 1}
  sr = sampleRate
  // Envelope state
  env = 1.0  // current gain (1 = no reduction)
  // Lookahead buffer
  bufL = null
  bufR = null
  bufIdx = 0
  bufLen = 0

  constructor() {
    // Lookahead: 0.5→1ms, 1→5ms
    this.bufLen = Math.floor(this.sr * 0.005)
    this.bufL = new Float32Array(this.bufLen)
    this.bufR = new Float32Array(this.bufLen)
    this.bufIdx = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
    // Resize lookahead buffer if param changed
    if (name === "lookahead") {
      const ms = 0.1 + value * value * 4.9  // 0.1ms → 5ms
      const newLen = Math.max(Math.floor(this.sr * ms / 1000), 1)
      if (newLen !== this.bufLen) {
        this.bufLen = newLen
        this.bufL = new Float32Array(newLen)
        this.bufR = new Float32Array(newLen)
        this.bufIdx = 0
      }
    }
  }

  // TPDF dither — eliminates quantization distortion
  _dither() {
    if (this.p.dither <= 0) return 0
    const r = (Math.random() - 0.5) + (Math.random() - 0.5)
    return r * 0.5 * this.p.dither
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p

    const ceiling = p.ceiling  // 0..1, threshold above which we limit
    // Release: 0→10ms, 1→500ms (logarithmic-ish)
    const releaseMs = 10 + Math.pow(p.release, 2) * 490
    const releaseCoeff = Math.exp(-1 / (this.sr * releaseMs / 1000))

    const stereo = output.length > 1
    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]

    for (let i = 0; i < inL.length; i++) {
      // Write to lookahead buffer
      this.bufL[this.bufIdx] = inL[i]
      if (stereo) this.bufR[this.bufIdx] = inR[i]

      // Detect peak from current input (pre-buffer)
      const peakL = Math.abs(inL[i])
      const peakR = stereo ? Math.abs(inR[i]) : peakL
      const peak = Math.max(peakL, peakR)

      // Compute target gain
      let targetGain = 1.0
      if (peak > ceiling) {
        targetGain = ceiling / Math.max(peak, 1e-10)
      }

      // Instant attack (limiter = instant), smooth release
      if (targetGain < this.env) {
        // Attack: instant grab
        this.env = targetGain
      } else {
        // Release: smooth recovery
        this.env = this.env + (targetGain - this.env) * (1 - releaseCoeff)
      }

      // Read from lookahead buffer (delayed signal so envelope catches peaks)
      const delayedL = this.bufL[this.bufIdx]
      const delayedR = stereo ? this.bufR[this.bufIdx] : delayedL

      // Apply gain + dither
      const wetL = delayedL * this.env + this._dither()
      outL[i] = inL[i] * (1 - p.mix) + wetL * p.mix

      if (stereo) {
        const wetR = delayedR * this.env + this._dither()
        outR[i] = inR[i] * (1 - p.mix) + wetR * p.mix
      }

      // Advance buffer index
      this.bufIdx = (this.bufIdx + 1) % this.bufLen
    }
  }
}
