// @werkstatt spring_reverb 1 1
// @label Spring Reverb
// @param decay 0.4 0 1 linear
// @param damp 0.5 0 1 linear
// @param tension 0.5 0 1 linear
// @param boing 0.3 0 1 linear
// @param mix 0.3 0 1 linear

class Processor {
  p = {decay: 0.4, damp: 0.5, tension: 0.5, boing: 0.3, mix: 0.3}
  sr = 44100
  bs = 128

  // 4 dispersive delay lines (springs)
  delays = []
  writePos = [0, 0, 0, 0]
  readPos = [0, 0, 0, 0]
  bufLen = 0

  // transient detection
  prevInput = [0, 0]
  envL = 0
  envR = 0
  chirpPhase = [0, 0]
  chirpFreq = [0, 0]
  chirpEnv = [0, 0]

  initBuffers() {
    this.bufLen = Math.floor(this.sr * 0.1) // max 100ms delay
    this.delays = [
      new Float32Array(this.bufLen),
      new Float32Array(this.bufLen),
      new Float32Array(this.bufLen),
      new Float32Array(this.bufLen),
    ]
    // different delay times for each spring (dispersion)
    const base = 0.02 + this.p.tension * 0.04 // 20-60ms
    const offsets = [1.0, 1.07, 1.13, 1.21] // slightly detuned springs
    this.delTimes = offsets.map(o => Math.floor(this.sr * base * o))
    this.writePos = [0, 0, 0, 0]
    this.readPos = this.delTimes.map(dt => (this.bufLen - dt) % this.bufLen)
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "tension") {
      this.initBuffers()
    }
  }

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.initBuffers()
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const decay = Math.pow(0.001, 1 / (this.p.decay * 4 + 0.01))
    const dampAmt = this.p.damp
    const boingAmt = this.p.boing
    const mix = this.p.mix
    const bufLen = this.bufLen

    // simple one-pole lowpass for damping
    let dampL = 0
    let dampR = 0
    const dampAlpha = 1 - dampAmt * 0.8

    for (let ch = 0; ch < out.length; ch++) {
      const ic = inp[ch] || inp[0]
      const oc = out[ch]
      if (!ic || !oc) continue

      const chIdx = Math.min(ch, 1) // 0 or 1

      for (let i = 0; i < ic.length; i++) {
        const dry = ic[i]

        // transient detection for "boing" effect
        const diff = Math.abs(dry) - Math.abs(this.prevInput[chIdx])
        this.prevInput[chIdx] = dry
        if (diff > 0.05) {
          this.chirpEnv[chIdx] = boingAmt * Math.min(1, diff * 3)
          this.chirpFreq[chIdx] = 200 + diff * 2000 // frequency sweep
          this.chirpPhase[chIdx] = 0
        }

        // generate chirp (transient response)
        let chirpSig = 0
        if (this.chirpEnv[chIdx] > 0.001) {
          const phaseInc = 2 * Math.PI * this.chirpFreq[chIdx] / this.sr
          this.chirpPhase[chIdx] += phaseInc
          chirpSig = Math.sin(this.chirpPhase[chIdx]) * this.chirpEnv[chIdx]
          this.chirpEnv[chIdx] *= 0.999 // decay
          this.chirpFreq[chIdx] *= 0.998 // sweep down
        }

        const inputSig = dry + chirpSig

        // process through 4 dispersive delay lines
        let wetSum = 0
        for (let s = 0; s < 4; s++) {
          // write input + feedback
          const readVal = this.delays[s][this.readPos[s]]
          const writeVal = inputSig + readVal * decay
          this.delays[s][this.writePos[s]] = writeVal

          // advance positions
          this.writePos[s] = (this.writePos[s] + 1) % bufLen
          this.readPos[s] = (this.readPos[s] + 1) % bufLen

          wetSum += readVal * 0.25
        }

        // damping
        if (chIdx === 0) {
          dampL = dampL * dampAlpha + wetSum * (1 - dampAlpha)
          const wet = dampL
          oc[i] = dry * (1 - mix) + wet * mix
        } else {
          dampR = dampR * dampAlpha + wetSum * (1 - dampAlpha)
          const wet = dampR
          oc[i] = dry * (1 - mix) + wet * mix
        }
      }
    }
  }
}
