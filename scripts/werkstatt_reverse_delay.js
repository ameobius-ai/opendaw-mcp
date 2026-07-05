// @werkstatt reverse_delay 1 1
// @label Reverse Delay
// @param time 0.4 0.05 2 linear s
// @param feedback 0.35 0 0.85 linear
// @param levels 0.6 0 1 linear
// @param pan 0 -1 1 linear
// @param fade 0.01 0.001 0.1 linear s
// @param damping 0.3 0 0.9 linear
// @param mix 0.35 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {
    time: 0.4, feedback: 0.35, levels: 0.6, pan: 0,
    fade: 0.01, damping: 0.3, mix: 0.35, output: 0,
  }
  sr = 44100
  outGain = 1

  buf = null
  bufLen = 0
  writePos = 0

  // Damping state
  dampState = 0

  // Fade ramps: apply at read boundaries
  fadeSamps = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this.bufLen = Math.floor(this.sr * 2.1)
    this.buf = new Float32Array(this.bufLen)
    this.writePos = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  _dampLp(input) {
    const cutoff = 1.0 - this.p.damping * 0.8
    this.dampState = this.dampState + cutoff * (input - this.dampState)
    return this.dampState
  }

  _pan(sample, pan) {
    const angle = (pan + 1) * 0.785398
    return [sample * Math.cos(angle), sample * Math.sin(angle)]
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const numCh = out.length
    const numFrames = out[0].length
    const sr = this.sr
    const og = this.outGain
    const mix = this.p.mix
    const delaySamps = Math.max(1, Math.min(this.bufLen - 1, Math.floor(this.p.time * sr)))
    const fbLevel = this.p.feedback
    const tapLevel = this.p.levels
    const fadeLen = Math.max(1, Math.floor(this.p.fade * sr))

    for (let i = 0; i < numFrames; i++) {
      // Mono sum input
      let inSample = 0
      if (inp.length > 0) {
        for (let c = 0; c < inp.length; c++) {
          inSample += inp[c][i] || 0
        }
        inSample /= inp.length
      }

      // Read reverse: readPos scans backwards from writePos-1
      // This creates the reverse delay effect
      const readOffset = (this.writePos - delaySamps + this.bufLen) % this.bufLen
      // Scan backwards from readOffset
      // For each sample, we read delaySamps behind writePos, but reversed
      // Simpler: read at readOffset, which is the oldest sample in the delay window
      // and fade it in/out at window boundaries
      let revSample = this.buf[readOffset]

      // Apply fade at window boundaries (when writePos wraps around delaySamps)
      const cyclePos = this.writePos % delaySamps
      let fadeGain = 1.0
      if (cyclePos < fadeLen) {
        fadeGain = cyclePos / fadeLen
      } else if (cyclePos > delaySamps - fadeLen) {
        fadeGain = (delaySamps - cyclePos) / fadeLen
      }
      revSample *= fadeGain

      // Feedback: damped reverse sample goes back into buffer
      const fb = this._dampLp(revSample * fbLevel)
      this.buf[this.writePos] = inSample + fb
      this.writePos = (this.writePos + 1) % this.bufLen

      // Pan the reverse tap
      const [pl, pr] = this._pan(revSample * tapLevel, this.p.pan)

      // Dry/wet
      const dryL = (inp[0]) ? inp[0][i] : 0
      const dryR = (inp.length > 1) ? inp[1][i] : dryL
      const wetL = pl * mix
      const wetR = pr * mix
      const dryGain = 1.0 - mix * 0.5

      if (numCh > 0) out[0][i] = (dryL * dryGain + wetL) * og
      if (numCh > 1) out[1][i] = (dryR * dryGain + wetR) * og
    }
  }

  reset() {
    if (this.buf) this.buf.fill(0)
    this.writePos = 0
    this.dampState = 0
  }
}
