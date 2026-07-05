// @werkstatt dimension_chorus 1 1
// @label Dimension Chorus
// @param rate_l 0.7 0.05 5 exp
// @param rate_r 1.1 0.05 5 exp
// @param depth 0.35 0 1 linear
// @param center 0.012 0.001 0.05 linear
// @param phase_offset 90 0 360 linear
// @param width 0.8 0 1 linear
// @param brightness 0.5 0 1 linear
// @param mix 0.55 0 1 linear
// @param output 0 0 1 linear

class Processor {
  p = {
    rate_l: 0.7, rate_r: 1.1, depth: 0.35, center: 0.012,
    phase_offset: 90, width: 0.8, brightness: 0.5, mix: 0.55, output: 0,
  }
  sr = 44100
  bs = 128

  // dual delay buffers — no feedback (Dimension D characteristic)
  bufL = null
  bufR = null
  bufLen = 0
  idxL = 0
  idxR = 0

  // independent LFO phases
  phaseL = 0
  phaseR = 0

  // brightness filter state (one-pole lowpass on wet)
  brightStateL = 0
  brightStateR = 0

  initBuffers() {
    this.bufLen = Math.floor(this.sr * 0.08) // max 80ms
    this.bufL = new Float32Array(this.bufLen)
    this.bufR = new Float32Array(this.bufLen)
    this.idxL = 0
    this.idxR = 0
    this.phaseL = 0
    this.phaseR = 0
    this.brightStateL = 0
    this.brightStateR = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  _fracRead(buf, idx, delaySamps) {
    const readPos = ((idx - delaySamps) % this.bufLen + this.bufLen) % this.bufLen
    const i0 = Math.floor(readPos) % this.bufLen
    const i1 = (i0 + 1) % this.bufLen
    const frac = readPos - Math.floor(readPos)
    return buf[i0] * (1 - frac) + buf[i1] * frac
  }

  _brightFilter(input, state) {
    // one-pole lowpass: brightness 0 = dark, 1 = bright
    const cutoff = 0.1 + this.p.brightness * 0.89
    return state + cutoff * (input - state)
  }

  processAudio(inputs, outputs) {
    if (!this.bufL) this.initBuffers()
    const input = inputs[0]
    const output = outputs[0]
    const numFrames = output[0].length

    const rateL = this.p.rate_l
    const rateR = this.p.rate_r
    const depth = this.p.depth
    const centerSamps = this.p.center * this.sr
    const phaseOffsetRad = this.p.phase_offset * Math.PI / 180
    const width = this.p.width
    const mix = this.p.mix
    const outGain = Math.pow(10, this.p.output / 20)

    for (let i = 0; i < numFrames; i++) {
      // advance independent LFOs
      this.phaseL += 2 * Math.PI * rateL / this.sr
      if (this.phaseL > 2 * Math.PI) this.phaseL -= 2 * Math.PI
      this.phaseR += 2 * Math.PI * rateR / this.sr
      if (this.phaseR > 2 * Math.PI) this.phaseR -= 2 * Math.PI

      // triangular LFO (Dimension D uses triangle, not sine)
      const lfoL = 2 * Math.abs(2 * (this.phaseL / (2 * Math.PI) - Math.floor(this.phaseL / (2 * Math.PI) + 0.5))) - 1
      const lfoR = 2 * Math.abs(2 * ((this.phaseR + phaseOffsetRad) / (2 * Math.PI) - Math.floor((this.phaseR + phaseOffsetRad) / (2 * Math.PI) + 0.5))) - 1

      const delayL = centerSamps * (1 + depth * lfoL)
      const delayR = centerSamps * (1 + depth * lfoR)

      // read input — mono sum for delay input (Dimension D sums to mono before modulating)
      let inSample = 0
      if (input && input.length > 0) {
        for (let c = 0; c < input.length; c++) {
          inSample += input[c][i] || 0
        }
        inSample /= input.length
      }

      // write to buffers (no feedback!)
      this.bufL[this.idxL] = inSample
      this.bufR[this.idxR] = inSample
      this.idxL = (this.idxL + 1) % this.bufLen
      this.idxR = (this.idxR + 1) % this.bufLen

      // read modulated delay
      const wetL = this._fracRead(this.bufL, this.idxL, delayL)
      const wetR = this._fracRead(this.bufR, this.idxR, delayR)

      // brightness filter on wet signal
      const filteredL = this._brightFilter(wetL, this.brightStateL)
      this.brightStateL = filteredL
      const filteredR = this._brightFilter(wetR, this.brightStateR)
      this.brightStateR = filteredR

      // stereo width: widen by subtracting a bit of opposite channel
      const widenedL = filteredL * (1 - width * 0.15) + filteredR * width * 0.15
      const widenedR = filteredR * (1 - width * 0.15) + filteredL * width * 0.15

      // dry/wet — Dimension D is fully wet by default but we allow blend
      const dryL = (input && input[0]) ? input[0][i] : 0
      const dryR = (input && input[1]) ? input[1][i] : dryL

      output[0][i] = (dryL * (1 - mix) + widenedL * mix) * outGain
      if (output.length > 1) {
        output[1][i] = (dryR * (1 - mix) + widenedR * mix) * outGain
      }
    }
  }

  reset() {
    if (this.bufL) this.bufL.fill(0)
    if (this.bufR) this.bufR.fill(0)
    this.idxL = 0
    this.idxR = 0
    this.phaseL = 0
    this.phaseR = 0
    this.brightStateL = 0
    this.brightStateR = 0
  }
}
