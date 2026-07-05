// @werkstatt comb_filter 1 1
// @label Comb Filter
// @param freq 500 10 8000 exp Hz
// @param feedback 0.7 -0.99 0.99 linear
// @param damping 0.3 0 1 linear
// @param mix 0.5 0 1 linear
// @param polarity 0 0 1 linear

class Processor {
  p = {freq: 500, feedback: 0.7, damping: 0.3, mix: 0.5, polarity: 0}
  sr = 44100
  bs = 128

  bufL = null
  bufR = null
  writePos = 0
  bufSize = 0
  dampStateL = 0
  dampStateR = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.bufSize = Math.ceil(this.sr * 0.5) // max 500ms delay
    this.bufL = new Float32Array(this.bufSize)
    this.bufR = new Float32Array(this.bufSize)
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const bufSize = this.bufSize
    const delaySamples = Math.max(1, Math.floor(sr / Math.max(1, this.p.freq)))
    const fb = this.p.feedback
    const dampAmt = this.p.damping
    const mix = this.p.mix
    const polarity = this.p.polarity > 0.5 ? -1 : 1

    const stereo = out.length > 1

    // Damping LP coefficient
    const dampAlpha = 1 - Math.exp(-1 / (sr * 0.001 * (0.1 + dampAmt * 10)))

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0][i]
      const inR = stereo ? (inp.length > 1 ? inp[1][i] : inp[0][i]) : inL

      // Read delayed sample
      const readPos = (this.writePos - delaySamples + bufSize) % bufSize
      let delL = this.bufL[readPos]
      let delR = this.bufR[readPos]

      // Apply damping (one-pole LP in feedback path)
      this.dampStateL += dampAlpha * (delL - this.dampStateL)
      delL = this.dampStateL
      this.dampStateR += dampAlpha * (delR - this.dampStateR)
      delR = this.dampStateR

      // Write input + feedback (polarity selects positive or negative comb)
      this.bufL[this.writePos] = inL + delL * fb * polarity
      this.bufR[this.writePos] = inR + delR * fb * polarity

      this.writePos = (this.writePos + 1) % bufSize

      // Output: dry + wet
      out[0][i] = inL * (1 - mix) + delL * mix
      if (stereo) {
        out[1][i] = inR * (1 - mix) + delR * mix
      }
    }
  }
}
