// @werkstatt multitap_delay 1 1
// @label Multitap Delay
// @param tap1_time 0.25 0.02 1 linear
// @param tap1_level 0.7 0 1 linear
// @param tap1_pan -0.5 -1 1 linear
// @param tap1_fb 0.3 0 0.9 linear
// @param tap2_time 0.375 0.02 1 linear
// @param tap2_level 0.55 0 1 linear
// @param tap2_pan 0.5 -1 1 linear
// @param tap2_fb 0 0 0.9 linear
// @param tap3_time 0.5 0.02 1 linear
// @param tap3_level 0.4 0 1 linear
// @param tap3_pan -0.2 -1 1 linear
// @param tap3_fb 0 0 0.9 linear
// @param tap4_time 0.75 0.02 1 linear
// @param tap4_level 0.25 0 1 linear
// @param tap4_pan 0.2 -1 1 linear
// @param tap4_fb 0 0 0.9 linear
// @param spread 0 0 1 linear
// @param damping 0.3 0 0.9 linear
// @param mix 0.4 0 1 linear
// @param output 0 0 1 linear

class Processor {
  p = {
    tap1_time: 0.25, tap1_level: 0.7, tap1_pan: -0.5, tap1_fb: 0.3,
    tap2_time: 0.375, tap2_level: 0.55, tap2_pan: 0.5, tap2_fb: 0,
    tap3_time: 0.5, tap3_level: 0.4, tap3_pan: -0.2, tap3_fb: 0,
    tap4_time: 0.75, tap4_level: 0.25, tap4_pan: 0.2, tap4_fb: 0,
    spread: 0, damping: 0.3, mix: 0.4, output: 0,
  }
  sr = 44100
  bs = 128

  bufLen = 0
  buf = null
  writePos = 0

  // damping one-pole lowpass state
  dampStateL = 0
  damptStateR = 0

  // spread LFO
  spreadPhase = 0

  initBuffer() {
    this.bufLen = Math.floor(this.sr * 1.2)
    this.buf = new Float32Array(this.bufLen)
    this.writePos = 0
    this.dampStateL = 0
    this.damptStateR = 0
    this.spreadPhase = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  _tapDelaySamples(tapIdx) {
    const times = [this.p.tap1_time, this.p.tap2_time, this.p.tap3_time, this.p.tap4_time]
    let t = times[tapIdx]
    // spread modulates tap times slightly for stereo width
    if (this.p.spread > 0) {
      const modPhase = this.spreadPhase + tapIdx * 1.5708
      t *= 1.0 + this.p.spread * 0.15 * Math.sin(modPhase)
    }
    return Math.max(1, Math.min(this.bufLen - 1, Math.floor(t * this.sr)))
  }

  _readTap(delaySamps) {
    const readPos = (this.writePos - delaySamps + this.bufLen) % this.bufLen
    return this.buf[readPos]
  }

  _pan(sample, pan) {
    // equal-power pan: pan = -1 (L), 0 (C), 1 (R)
    const angle = (pan + 1) * 0.785398 // 0..pi/2
    return [sample * Math.cos(angle), sample * Math.sin(angle)]
  }

  _dampLp(input) {
    const cutoff = 1.0 - this.p.damping * 0.8
    this.dampStateL = this.dampStateL + cutoff * (input - this.dampStateL)
    return this.dampStateL
  }

  processAudio(inputs, outputs) {
    if (!this.buf) this.initBuffer()
    const input = inputs[0]
    const output = outputs[0]
    const numCh = output.length
    const numFrames = output[0].length

    for (let i = 0; i < numFrames; i++) {
      // read input (mono sum if stereo)
      let inSample = 0
      if (input && input.length > 0) {
        for (let c = 0; c < input.length; c++) {
          inSample += input[c][i] || 0
        }
        inSample /= input.length
      }

      // read all 4 taps
      const taps = []
      let fbSum = 0
      for (let t = 0; t < 4; t++) {
        const delay = this._tapDelaySamples(t)
        const s = this._readTap(delay)
        taps.push(s)
        // feedback: only taps with fb > 0 feed back into the buffer
        const fbVals = [this.p.tap1_fb, this.p.tap2_fb, this.p.tap3_fb, this.p.tap4_fb]
        fbSum += s * fbVals[t]
      }

      // damping on feedback path
      fbSum = this._dampLp(fbSum)

      // write input + damped feedback into buffer
      this.buf[this.writePos] = inSample + fbSum
      this.writePos = (this.writePos + 1) % this.bufLen

      // sum taps with levels and pan into output
      let outL = 0, outR = 0
      const levels = [this.p.tap1_level, this.p.tap2_level, this.p.tap3_level, this.p.tap4_level]
      const pans = [this.p.tap1_pan, this.p.tap2_pan, this.p.tap3_pan, this.p.tap4_pan]
      for (let t = 0; t < 4; t++) {
        const tapSig = taps[t] * levels[t]
        const [pl, pr] = this._pan(tapSig, pans[t])
        outL += pl
        outR += pr
      }

      // advance spread LFO
      this.spreadPhase += 0.0008

      // dry/wet
      const dryL = (input && input[0]) ? input[0][i] : 0
      const dryR = (input && input[1]) ? input[1][i] : dryL
      const wetL = outL * this.p.mix
      const wetR = outR * this.p.mix
      const dryGain = 1.0 - this.p.mix * 0.5

      const outGain = Math.pow(10, this.p.output / 20)
      if (numCh > 0) output[0][i] = (dryL * dryGain + wetL) * outGain
      if (numCh > 1) output[1][i] = (dryR * dryGain + wetR) * outGain
    }
  }

  reset() {
    if (this.buf) this.buf.fill(0)
    this.writePos = 0
    this.dampStateL = 0
    this.damptStateR = 0
    this.spreadPhase = 0
  }
}
