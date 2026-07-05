// @werkstatt looper 1 1
// @label Looper
// @param loop_length 2 0.5 30 linear sec
// @param feedback 0.8 0 1 linear
// @param overdub 1 0 1 linear
// @param play_mode 0 0 2 linear type
// @param speed 1 0.25 4 linear x
// @param reverse_mode 0 0 1 linear bool
// @param monitor 0 0 1 linear
// @param fade_edges 0.01 0 0.1 linear sec
// @param mix 1 0 1 linear
// @param output 0 -12 12 linear dB

class Processor {
  p = {loop_length: 2, feedback: 0.8, overdub: 1, play_mode: 0,
       speed: 1, reverse_mode: 0, monitor: 0, fade_edges: 0.01,
       mix: 1, output: 0}
  sr = 44100
  bs = 128

  // Loop buffer (stereo)
  bufL = null
  bufR = null
  bufSize = 0
  loopSamples = 0

  // Positions
  writePos = 0
  readPos = 0

  // State: 0=record, 1=play, 2=overdub
  state = 0
  stateSamples = 0
  hasLooped = false

  // Fade edge state
  fadeSamples = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.bufSize = Math.ceil(this.sr * 30) // 30 sec max
    this.bufL = new Float32Array(this.bufSize)
    this.bufR = new Float32Array(this.bufSize)
    this.loopSamples = Math.floor(this.p.loop_length * this.sr)
    this.fadeSamples = Math.max(1, Math.floor(this.p.fade_edges * this.sr))
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "loop_length") {
      this.loopSamples = Math.floor(value * this.sr)
    }
    if (name === "fade_edges") {
      this.fadeSamples = Math.max(1, Math.floor(value * this.sr))
    }
  }

  // Crossfade at loop boundaries to avoid clicks
  _fadeGain(pos, len, fadeLen) {
    if (fadeLen <= 0) return 1
    // Fade in at start, fade out at end
    const fadeIn = Math.min(1, pos / fadeLen)
    const fadeOut = Math.min(1, (len - pos) / fadeLen)
    return Math.max(0, Math.min(fadeIn, fadeOut))
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const stereo = out.length > 1
    const mix = this.p.mix
    const outGain = Math.pow(10, this.p.output / 20)
    const fbAmt = this.p.feedback
    const odAmt = this.p.overdub
    const speed = this.p.speed
    const reverse = this.p.reverse_mode > 0.5
    const monitor = this.p.monitor
    const playMode = Math.floor(this.p.play_mode)
    const ls = Math.max(1, this.loopSamples)
    const fadeLen = this.fadeSamples

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0] ? inp[0][i] : 0
      const inR = stereo && inp.length > 1 && inp[1] ? inp[1][i] : inL

      // Determine state
      // playMode: 0 = auto (record then play/overdub), 1 = play, 2 = overdub
      let currentState = this.state
      if (playMode === 0) {
        // Auto: record first loop, then overdub
        if (!this.hasLooped && this.stateSamples >= ls) {
          this.hasLooped = true
          this.state = 2 // overdub
          currentState = 2
          this.stateSamples = 0
        }
      } else if (playMode === 1) {
        currentState = 1 // play only
      } else if (playMode === 2) {
        currentState = 2 // overdub
      }

      // Read from loop buffer
      let readIdx;
      if (reverse) {
        readIdx = (this.writePos - Math.floor(this.readPos) + ls + this.bufSize * 10) % ls
      } else {
        readIdx = Math.floor(this.readPos) % ls
      }
      const readIdxNext = (readIdx + 1) % ls
      const frac = this.readPos - Math.floor(this.readPos)
      const playL = this.bufL[readIdx] * (1 - frac) + this.bufL[readIdxNext] * frac
      const playR = this.bufR[readIdx] * (1 - frac) + this.bufR[readIdxNext] * frac

      // Apply fade at loop edges
      const fadePos = reverse ? (ls - Math.floor(this.readPos) % ls) : (Math.floor(this.readPos) % ls)
      const fadeG = this._fadeGain(fadePos, ls, fadeLen)

      // State-dependent processing
      let writeL, writeR
      if (currentState === 0) {
        // Record: write input directly, no feedback
        writeL = inL
        writeR = inR
      } else if (currentState === 2) {
        // Overdub: mix existing buffer content (× feedback) + new input (× overdub)
        writeL = playL * fbAmt + inL * odAmt
        writeR = playR * fbAmt + inR * odAmt
      } else {
        // Play: buffer unchanged, no new recording
        writeL = playL * fbAmt
        writeR = playR * fbAmt
      }

      // Write to buffer
      const wIdx = this.writePos % ls
      this.bufL[wIdx] = writeL
      this.bufR[wIdx] = writeR

      // Advance positions
      this.writePos = (this.writePos + 1) % ls
      this.readPos += speed
      while (this.readPos >= ls) this.readPos -= ls
      while (this.readPos < 0) this.readPos += ls

      this.stateSamples++

      // Output: loop playback + optional input monitor
      const wetL = playL * fadeG * outGain
      const wetR = playR * fadeG * outGain
      const monL = inL * monitor
      const monR = inR * monitor

      out[0][i] = (wetL + monL) * mix + inL * (1 - mix) * 0
      if (stereo) {
        out[1][i] = (wetR + monR) * mix + inR * (1 - mix) * 0
      }
    }
  }
}
