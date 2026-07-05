// @werkstatt flanger 1 1
// @label Stereo Flanger
// @param rate 0.3 0.05 8 exp Hz
// @param depth 0.8 0 3 linear ms
// @param center 1 0.1 10 linear ms
// @param feedback 0.6 -0.95 0.95 linear
// @param mix 0.5 0 1 linear

class Processor {
  p = {rate: 0.3, depth: 0.8, center: 1, feedback: 0.6, mix: 0.5}
  sr = sampleRate
  phase = 0
  bufL = null; bufR = null
  writeIdx = 0
  maxDelay = 0

  constructor() {
    this.maxDelay = Math.floor(this.sr * 0.02)
    this.bufL = new Float32Array(this.maxDelay)
    this.bufR = new Float32Array(this.maxDelay)
    this.writeIdx = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  _readDelay(buf, writeIdx, delaySamples) {
    const n = buf.length
    let readIdx = writeIdx - Math.floor(delaySamples)
    if (readIdx < 0) readIdx += n
    const frac = delaySamples - Math.floor(delaySamples)
    const next = (readIdx + 1) % n
    return buf[readIdx] * (1 - frac) + buf[next] * frac
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr
    const phaseInc = (2 * Math.PI * p.rate) / sr
    const centerSamples = (p.center / 1000) * sr
    const depthSamples = (p.depth / 1000) * sr

    for (let i = 0; i < input.length; i++) {
      this.phase += phaseInc
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI

      const lfo = Math.sin(this.phase)
      const delaySamp = Math.max(1, centerSamples + depthSamples * lfo)

      const inL = input.length > 1 ? input[0][i] : input[0][i]
      const inR = input.length > 1 ? input[1][i] : input[0][i]

      const dlL = this._readDelay(this.bufL, this.writeIdx, delaySamp)
      const dlR = this._readDelay(this.bufR, this.writeIdx, delaySamp)

      this.bufL[this.writeIdx] = inL + dlL * p.feedback
      this.bufR[this.writeIdx] = inR + dlR * p.feedback

      if (output.length > 1) {
        output[0][i] = inL * (1 - p.mix) + dlL * p.mix
        output[1][i] = inR * (1 - p.mix) + dlR * p.mix
      } else {
        output[0][i] = (inL + inR) * 0.5 * (1 - p.mix) + (dlL + dlR) * 0.5 * p.mix
      }

      this.writeIdx = (this.writeIdx + 1) % this.maxDelay
    }
  }
}
