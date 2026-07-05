// @werkstatt tape_stop 1 1
// @label Tape Stop
// Exponential slow-down to full stop with corresponding pitch drop.
// DJ Screw, trap intros, lo-fi hip-hop tape stop effect.

// @param stop_time   0.8  0.1  5   exp     s   // time to reach full stop
// @param trigger     1    0  1   linear       // 1=trigger stop, 0=pass-through
// @param restart     0    0  1   linear       // 1=restart from stopped state
// @param curve       2    0.5 8 linear        // exponential curve (1=linear, 2=classic tape, 8=hard stop)
// @param wow         0.01 0 0.05 linear       // wow flutter during slowdown
// @param flutter     0.005 0 0.02 linear      // flutter amplitude
// @param flutter_rate 6  2 20 linear Hz       // flutter rate
// @param mix         1    0 1 linear          // wet/dry mix
// @param output      0   -12 12 linear dB     // output gain

class Processor {
  p = {stop_time: 0.8, trigger: 1, restart: 0, curve: 2, wow: 0.01,
       flutter: 0.005, flutter_rate: 6, mix: 1, output: 0}
  sr = sampleRate

  // Circular buffer for pitch-shifted readback
  buf = null
  bufSize = 0
  writePos = 0
  readPos = 0

  // State machine: 0=playing, 1=stopping, 2=stopped
  state = 0
  // Speed: 1.0 = normal, 0.0 = stopped
  speed = 1.0
  // Elapsed time in current state
  stateTime = 0
  // LFO phase for flutter
  flutterPhase = 0
  // Output gain
  outGain = 1

  constructor() {
    this.bufSize = Math.ceil(this.sr * 2)  // 2 second buffer
    this.buf = new Float32Array(this.bufSize)
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
    if (name === "trigger" && value > 0.5 && this.state === 0) {
      this.state = 1
      this.stateTime = 0
    }
    if (name === "restart" && value > 0.5 && this.state === 2) {
      this.state = 0
      this.speed = 1.0
      this.stateTime = 0
    }
  }

  process(io, block) {
    const sr = this.sr
    const p = this.p
    const og = this.outGain

    const flutterCoeff = 2 * Math.PI * p.flutter_rate / sr
    const stopSamples = p.stop_time * sr

    const s0 = block.s0
    const s1 = block.s1

    for (let i = s0; i < s1; i++) {
      const inL = io.src[0][i]
      const inR = io.src[1] ? io.src[1][i] : inL
      const mono = (inL + inR) * 0.5

      // Write to buffer
      this.buf[this.writePos] = mono
      this.writePos = (this.writePos + 1) % this.bufSize

      // State machine
      if (this.state === 1) {
        // Stopping: exponential speed decay
        this.stateTime++
        const t = this.stateTime / stopSamples
        if (t >= 1.0) {
          this.state = 2
          this.speed = 0
        } else {
          // Exponential: speed = (1 - t)^curve
          this.speed = Math.pow(1.0 - t, p.curve)
          // Clamp to avoid clicks at very low speeds
          if (this.speed < 0.001) this.speed = 0.001
        }
      }

      // Flutter (wow + flutter) — adds pitch wobble during slowdown
      this.flutterPhase += flutterCoeff
      const flutterAmt = Math.sin(this.flutterPhase) * p.flutter
      const wowAmt = (Math.sin(this.flutterPhase * 0.3) + 1) * p.wow * 0.5
      const speedMod = this.speed * (1 + flutterAmt + wowAmt)

      // Read from buffer at current speed (fractional read)
      this.readPos += speedMod
      if (this.readPos >= this.bufSize) this.readPos -= this.bufSize
      if (this.readPos < 0) this.readPos += this.bufSize

      const r0 = Math.floor(this.readPos)
      const r1 = (r0 + 1) % this.bufSize
      const frac = this.readPos - r0
      const wet = this.buf[r0] * (1 - frac) + this.buf[r1] * frac

      // Mix
      const out = wet * p.mix + mono * (1 - p.mix)
      const final = out * og

      io.out[0][i] = final
      io.out[1][i] = final
    }
  }
}
