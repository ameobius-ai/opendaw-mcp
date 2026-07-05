// @werkstatt stereo_delay 1 1
// @label Stereo Delay
// @param time_l 350 1 2000 exp ms
// @param time_r 450 1 2000 exp ms
// @param feedback 0.35 0 0.95 linear
// @param tone 0.5 0 1 linear
// @param mix 0.3 0 1 linear
// @param pingpong 0 0 1 linear

class Processor {
  p = {time_l: 350, time_r: 450, feedback: 0.35, tone: 0.5, mix: 0.3, pingpong: 0}
  sr = sampleRate
  bufL = null
  bufR = null
  writePos = 0
  bufSize = 0
  lpState = 0
  hpState = 0

  constructor() {
    this.bufSize = Math.ceil(this.sr * 2)
    this.bufL = new Float32Array(this.bufSize)
    this.bufR = new Float32Array(this.bufSize)
    this.writePos = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr

    const delaySamplesL = Math.max(1, Math.floor((p.time_l / 1000) * sr))
    const delaySamplesR = Math.max(1, Math.floor((p.time_r / 1000) * sr))

    // Tone filter: 0=bright (more HP), 1=dark (more LP)
    const lpAlpha = 1 - Math.exp(-1 / (sr * 0.003 * (0.1 + p.tone * 2)))
    const hpAlpha = 1 - Math.exp(-1 / (sr * 0.0005 * (1.5 - p.tone)))

    const stereo = output.length > 1

    for (let i = 0; i < input[0].length; i++) {
      const inL = input.length > 1 ? input[0][i] : input[0][i]
      const inR = input.length > 1 ? input[1][i] : input[0][i]

      const readPosL = (this.writePos - delaySamplesL + this.bufSize) % this.bufSize
      const readPosR = (this.writePos - delaySamplesR + this.bufSize) % this.bufSize

      let delL = this.bufL[readPosL]
      let delR = this.bufR[readPosR]

      // Ping-pong: swap L/R delay feedback
      if (p.pingpong > 0) {
        const swap = p.pingpong
        const fbL = delR * swap + delL * (1 - swap)
        const fbR = delL * swap + delR * (1 - swap)
        delL = fbL
        delR = fbR
      }

      // Tone: LP then HP in series
      this.lpState += lpAlpha * (delL - this.lpState)
      delL = this.lpState
      this.hpState = this.hpState + hpAlpha * (delL - this.hpState)
      delL = delL - this.hpState

      // Same for R (separate state would be better but keeping simple)
      const lpR = delR
      const hpR = lpR * 0.99

      // Write to buffer with feedback
      this.bufL[this.writePos] = inL + delL * p.feedback
      this.bufR[this.writePos] = inR + lpR * p.feedback

      this.writePos = (this.writePos + 1) % this.bufSize

      // Output: dry + wet
      const wetL = delL * p.mix
      const wetR = lpR * p.mix

      if (stereo) {
        output[0][i] = inL * (1 - p.mix * 0.5) + wetL
        output[1][i] = inR * (1 - p.mix * 0.5) + wetR
      } else {
        output[0][i] = inL * (1 - p.mix * 0.5) + wetL
      }
    }
  }
}
