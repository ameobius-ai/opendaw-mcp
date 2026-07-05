// @werkstatt scratch 1 1
// @label Scratch
// @param depth 0.5 0 1 linear amount
// @param rate 2 0.5 10 linear Hz
// @param pullback 0.3 0 1 linear
// @param friction 0.7 0 1 linear
// @param wow 0.02 0 0.1 linear
// @param flutter 0.05 0 0.3 linear
// @param flutter_rate 8 2 30 linear Hz
// @param crackle 0 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 12 linear dB

class Processor {
  p = {depth: 0.5, rate: 2, pullback: 0.3, friction: 0.7,
       wow: 0.02, flutter: 0.05, flutter_rate: 8,
       crackle: 0, mix: 1, output: 0}
  sr = 44100
  bs = 128

  // Circular delay buffer
  bufL = null
  bufR = null
  bufSize = 0
  writePos = 0
  readPos = 0

  // LFO phases
  scratchPhase = 0
  wowPhase = 0
  flutterPhase = 0

  // Velocity for physics-based scratch
  velocity = 1
  targetVelocity = 1

  // Crackle state
  crackleCounter = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.bufSize = Math.ceil(this.sr * 1.0) // 1 second buffer
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
    const stereo = out.length > 1
    const mix = this.p.mix
    const outGain = Math.pow(10, this.p.output / 20)
    const depth = this.p.depth
    const rate = this.p.rate
    const pullback = this.p.pullback
    const friction = this.p.friction
    const wowAmt = this.p.wow
    const flutterAmt = this.p.flutter
    const flutterRate = this.p.flutter_rate
    const crackleAmt = this.p.crackle

    const scratchInc = 2 * Math.PI * rate / sr
    const wowInc = 2 * Math.PI * 0.5 / sr // 0.5 Hz wow
    const flutterInc = 2 * Math.PI * flutterRate / sr

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0] ? inp[0][i] : 0
      const inR = stereo && inp.length > 1 && inp[1] ? inp[1][i] : inL

      // Write to buffer
      this.bufL[this.writePos] = inL
      this.bufR[this.writePos] = inR
      this.writePos = (this.writePos + 1) % this.bufSize

      // Scratch LFO: triangle wave for back-and-forth
      const sPhase = this.scratchPhase
      const triWave = 2 * Math.abs(2 * (sPhase / (2 * Math.PI) - Math.floor(sPhase / (2 * Math.PI) + 0.5))) - 1
      this.scratchPhase += scratchInc
      if (this.scratchPhase > Math.PI * 2) this.scratchPhase -= Math.PI * 2

      // Target velocity from scratch pattern
      // depth controls how far the readhead moves
      // pullback adds a backward "yank" at the start of each cycle
      const scratchShape = triWave * depth
      const pullbackShape = Math.sin(sPhase) * pullback * depth
      this.targetVelocity = 1 + scratchShape - pullbackShape

      // Physics: friction causes velocity to lag behind target
      const frictionCoeff = friction * 0.95 + 0.05
      this.velocity = this.velocity * frictionCoeff + this.targetVelocity * (1 - frictionCoeff)

      // Wow & flutter (pitch wobble)
      this.wowPhase += wowInc
      this.flutterPhase += flutterInc
      const wow = Math.sin(this.wowPhase) * wowAmt
      const flutter = Math.sin(this.flutterPhase) * flutterAmt
      const pitchMod = 1 + wow + flutter

      // Combined read speed
      const readSpeed = this.velocity * pitchMod

      // Read from buffer at variable speed
      this.readPos += readSpeed
      while (this.readPos < 0) this.readPos += this.bufSize
      while (this.readPos >= this.bufSize) this.readPos -= this.bufSize

      // Linear interpolation
      const idx0 = Math.floor(this.readPos)
      const idx1 = (idx0 + 1) % this.bufSize
      const frac = this.readPos - idx0
      const outL = this.bufL[idx0] * (1 - frac) + this.bufL[idx1] * frac
      const outR = this.bufR[idx0] * (1 - frac) + this.bufR[idx1] * frac

      // Crackle (random pops)
      let crackleVal = 0
      if (crackleAmt > 0) {
        this.crackleCounter++
        if (this.crackleCounter > Math.floor(sr * 0.01 * (1 + Math.random() * 3))) {
          this.crackleCounter = 0
          crackleVal = (Math.random() * 2 - 1) * crackleAmt * (0.5 + Math.random() * 0.5)
        }
      }

      const wetL = (outL + crackleVal) * outGain
      const wetR = (outR + crackleVal) * outGain

      out[0][i] = inL * (1 - mix) + wetL * mix
      if (stereo) {
        out[1][i] = inR * (1 - mix) + wetR * mix
      }
    }
  }
}
