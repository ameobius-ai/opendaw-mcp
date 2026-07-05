// @werkstatt gated_reverb 1 1
// @label Gated Reverb (80s Drum)
// @param decay 0.5 0.1 0.9 linear
// @param predelay 0.01 0 0.15 linear s
// @param damping 0.4 0 1 linear
// @param width 0.7 0 1 linear
// @param threshold 0.02 0.001 0.3 linear
// @param hold 0.08 0.01 0.5 linear s
// @param release 0.04 0.005 0.3 linear s
// @param mix 0.4 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {
    decay: 0.5, predelay: 0.01, damping: 0.4, width: 0.7,
    threshold: 0.02, hold: 0.08, release: 0.04,
    mix: 0.4, output: 0,
  }
  sr = 44100
  outGain = 1

  // Gate state
  env = 0
  gateOpen = false
  holdCounter = 0
  gateGain = 1

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate

    // Schroeder reverb: 4 comb + 2 allpass per channel
    const combMsL = [29.7, 37.1, 41.1, 43.7]
    const combMsR = [30.1, 36.5, 41.7, 43.3]
    const apMsL = [5.0, 1.7]
    const apMsR = [4.8, 1.9]

    this.combsL = combMsL.map(ms => this._mkComb(Math.floor(this.sr * ms / 1000)))
    this.combsR = combMsR.map(ms => this._mkComb(Math.floor(this.sr * ms / 1000)))
    this.apsL = apMsL.map(ms => this._mkAp(Math.floor(this.sr * ms / 1000)))
    this.apsR = apMsR.map(ms => this._mkAp(Math.floor(this.sr * ms / 1000)))

    const pdLen = Math.floor(this.sr * 0.15)
    this.pdBufL = new Float32Array(pdLen)
    this.pdBufR = new Float32Array(pdLen)
    this.pdIdx = 0
    this.pdLen = pdLen
  }

  _mkComb(n) {
    return {buf: new Float32Array(n), idx: 0, len: n, damp: 0}
  }

  _mkAp(n) {
    return {buf: new Float32Array(n), idx: 0, len: n}
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  _combProcess(c, input, decay, damping) {
    const fb = c.buf[c.idx]
    c.damp = c.damp * damping + fb * (1 - damping)
    c.buf[c.idx] = input + c.damp * decay
    c.idx = (c.idx + 1) % c.len
    return c.damp
  }

  _apProcess(a, input) {
    const delayed = a.buf[a.idx]
    a.buf[a.idx] = input + delayed * 0.7
    a.idx = (a.idx + 1) % a.len
    return delayed - input * 0.7
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out || inp.length < 2) return

    const inL = inp[0]
    const inR = inp[1]
    const outL = out[0]
    const outR = out[1]
    const len = inL.length

    const decay = this.p.decay
    const pdSamp = Math.floor(this.p.predelay * this.sr)
    const damping = this.p.damping
    const width = this.p.width
    const mix = this.p.mix
    const og = this.outGain
    const threshold = this.p.threshold
    const holdSamples = Math.floor(this.p.hold * this.sr)
    const releaseCoef = Math.exp(-1 / (this.p.release * this.sr))
    const envDecay = Math.exp(-1 / (0.003 * this.sr))

    for (let i = 0; i < len; i++) {
      const dryL = inL[i]
      const dryR = inR[i]

      // --- Envelope follower on DRY input (gate detection) ---
      const monoAbs = (Math.abs(dryL) + Math.abs(dryR)) * 0.5
      if (monoAbs > this.env) {
        this.env = monoAbs
      } else {
        this.env *= envDecay
      }

      // --- Gate state machine ---
      if (this.env > threshold) {
        this.gateOpen = true
        this.holdCounter = holdSamples
      } else if (this.holdCounter > 0) {
        this.holdCounter--
      } else {
        this.gateOpen = false
      }

      // Gate gain: open=1, closed=0 (exponential release)
      const target = this.gateOpen ? 1 : 0
      this.gateGain = this.gateGain * releaseCoef + target * (1 - releaseCoef)

      // --- Predelay ---
      const pdReadL = (this.pdIdx - pdSamp + this.pdLen) % this.pdLen
      const pdReadR = pdReadL
      const pdOutL = this.pdBufL[pdReadL]
      const pdOutR = this.pdBufR[pdReadR]
      this.pdBufL[this.pdIdx] = dryL
      this.pdBufR[this.pdIdx] = dryR
      this.pdIdx = (this.pdIdx + 1) % this.pdLen

      // --- Schroeder reverb ---
      let wetL = pdOutL
      for (let k = 0; k < this.combsL.length; k++) {
        wetL += this._combProcess(this.combsL[k], pdOutL, decay, damping)
      }
      for (let k = 0; k < this.apsL.length; k++) {
        wetL = this._apProcess(this.apsL[k], wetL)
      }

      let wetR = pdOutR
      for (let k = 0; k < this.combsR.length; k++) {
        wetR += this._combProcess(this.combsR[k], pdOutR, decay, damping)
      }
      for (let k = 0; k < this.apsR.length; k++) {
        wetR = this._apProcess(this.apsR[k], wetR)
      }

      // M/S width
      const mid = (wetL + wetR) * 0.5
      const side = (wetL - wetR) * 0.5 * width
      const wL = mid + side
      const wR = mid - side

      // Apply gate to reverb output
      const gatedL = wL * this.gateGain
      const gatedR = wR * this.gateGain

      // Dry/wet mix
      outL[i] = (dryL + (gatedL - dryL) * mix) * og
      outR[i] = (dryR + (gatedR - dryR) * mix) * og
    }
  }
}
