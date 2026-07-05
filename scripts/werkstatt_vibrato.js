// @werkstatt vibrato 1 1
// @label Pitch Vibrato
// @param rate 5 0.1 20 exp Hz
// @param depth 0.003 0.0005 0.02 linear s
// @param shape 0 0 1 linear
// @param stereo 0.7 0 1 linear

class Processor {
  p = {rate: 5, depth: 0.003, shape: 0, stereo: 0.7}
  sr = sampleRate
  phase = 0

  constructor() {
    this.maxDelay = Math.floor(this.sr * 0.05)
    this.bufL = new Float32Array(this.maxDelay)
    this.bufR = new Float32Array(this.maxDelay)
    this.idxL = 0
    this.idxR = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  process(io, block) {
    const rate = this.p.rate
    const depth = this.p.depth * this.sr
    const shape = this.p.shape
    const stereo = this.p.stereo

    for (let i = block.s0; i < block.s1; i++) {
      this.phase += 2 * Math.PI * rate / this.sr
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI

      const sine = Math.sin(this.phase)
      const tri = 2 * Math.abs(2 * (this.phase / (2 * Math.PI) - Math.floor(this.phase / (2 * Math.PI) + 0.5))) - 1
      const lfo = sine * (1 - shape) + tri * shape

      const lfoL = lfo
      const lfoR = Math.sin(this.phase + Math.PI * stereo)

      const delayL = depth * (1 + lfoL)
      const delayR = depth * (1 + lfoR)

      const readL = ((this.idxL - delayL) % this.maxDelay + this.maxDelay) % this.maxDelay
      const readR = ((this.idxR - delayR) % this.maxDelay + this.maxDelay) % this.maxDelay
      const iL0 = Math.floor(readL) % this.maxDelay
      const iL1 = (iL0 + 1) % this.maxDelay
      const fL = readL - Math.floor(readL)
      const delayedL = this.bufL[iL0] * (1 - fL) + this.bufL[iL1] * fL
      const iR0 = Math.floor(readR) % this.maxDelay
      const iR1 = (iR0 + 1) % this.maxDelay
      const fR = readR - Math.floor(readR)
      const delayedR = this.bufR[iR0] * (1 - fR) + this.bufR[iR1] * fR

      this.bufL[this.idxL] = io.src[0][i]
      this.bufR[this.idxR] = io.src[1][i]
      this.idxL = (this.idxL + 1) % this.maxDelay
      this.idxR = (this.idxR + 1) % this.maxDelay

      io.out[0][i] = delayedL
      io.out[1][i] = delayedR
    }
  }
}
