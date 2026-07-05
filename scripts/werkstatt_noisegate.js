// @werkstatt noisegate 1 1
// @label Noise Gate
// @param threshold -45 -80 -10 linear dB
// @param attack 0.002 0.0005 0.05 exp s
// @param hold 0.05 0.01 1 linear s
// @param release 0.15 0.01 2 exp s
// @param range -60 -100 0 linear dB

class Processor {
  p = {threshold: -45, attack: 0.002, hold: 0.05, release: 0.15, range: -60}
  sr = sampleRate
  env = 0
  gateState = 0  // 0=closed, 1=open
  holdCounter = 0

  constructor() {}

  paramChanged(name, value) {
    this.p[name] = value
  }

  _dbToGain(db) {
    return Math.pow(10, db / 20)
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr

    const threshGain = this._dbToGain(p.threshold)
    const rangeGain = this._dbToGain(p.range)
    const attackCoef = Math.exp(-1 / (p.attack * sr))
    const releaseCoef = Math.exp(-1 / (p.release * sr))
    const holdSamples = Math.floor(p.hold * sr)

    for (let i = 0; i < input[0].length; i++) {
      const inL = input.length > 1 ? input[0][i] : input[0][i]
      const inR = input.length > 1 ? input[1][i] : input[0][i]
      const mono = (Math.abs(inL) + Math.abs(inR)) * 0.5

      // Envelope follower
      if (mono > this.env) {
        this.env = mono
      } else {
        this.env = this.env * 0.999 + mono * 0.001
      }

      // Gate state machine
      if (this.env > threshGain) {
        this.gateState = 1
        this.holdCounter = holdSamples
      } else if (this.holdCounter > 0) {
        this.holdCounter--
      } else {
        this.gateState = 0
      }

      // Smooth gain
      const targetGain = this.gateState ? 1 : rangeGain
      const coef = this.gateState ? attackCoef : releaseCoef
      let currentGain = this._currentGain || 0
      currentGain = currentGain * coef + targetGain * (1 - coef)
      this._currentGain = currentGain

      if (output.length > 1) {
        output[0][i] = inL * currentGain
        output[1][i] = inR * currentGain
      } else {
        output[0][i] = (inL + inR) * 0.5 * currentGain
      }
    }
  }

  _currentGain = 0
}
