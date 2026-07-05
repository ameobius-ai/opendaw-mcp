// @werkstatt convolution_reverb 1 1
// @label Convolution Reverb
// @param room_size 0.5 0 1 linear
// @param decay 0.5 0 1 linear
// @param damping 0.4 0 1 linear
// @param predelay 0.02 0 0.1 linear sec
// @param early_late 0.5 0 1 linear
// @param width 0.7 0 1 linear
// @param mix 0.3 0 1 linear
// @param output 0 -12 12 linear dB

class Processor {
  p = {room_size: 0.5, decay: 0.5, damping: 0.4, predelay: 0.02,
       early_late: 0.5, width: 0.7, mix: 0.3, output: 0}
  sr = 44100
  bs = 128

  irL = null
  irR = null
  irLen = 0

  // ring buffer for input history
  histL = null
  histR = null
  histPos = 0
  histSize = 0

  db2gain(db) {
    return Math.pow(10, db / 20)
  }

  generateIR() {
    // IR length: 50ms..300ms based on room_size
    const ms = 50 + this.p.room_size * 250
    this.irLen = Math.floor(this.sr * ms / 1000)
    this.irLen = Math.min(this.irLen, 8192) // cap for CPU
    this.irL = new Float32Array(this.irLen)
    this.irR = new Float32Array(this.irLen)

    const preSamps = Math.floor(this.sr * this.p.predelay)
    const decayRate = Math.pow(0.001, 1 / (this.p.decay * 3 + 0.1))
    const dampCut = 2000 + (1 - this.p.damping) * 14000 // 2k..16k Hz
    const earlyAmt = this.p.early_late
    const lateAmt = 1 - this.p.early_late
    const width = this.p.width

    // simple xorshift PRNG for reproducible noise
    let seed = 12345
    const rand = () => {
      seed ^= seed << 13
      seed ^= seed >> 17
      seed ^= seed << 5
      return ((seed >>> 0) / 4294967296) * 2 - 1
    }

    // one-pole lowpass state for damping the tail
    let lpL = 0, lpR = 0
    const lpAlpha = Math.exp(-2 * Math.PI * dampCut / this.sr)

    // early reflection tap times (stereotypical room ratios)
    const erTaps = [
      {t: 1.0,   gain: 0.45},
      {t: 1.13,  gain: 0.38},
      {t: 1.27,  gain: 0.32},
      {t: 1.41,  gain: 0.28},
      {t: 1.59,  gain: 0.22},
      {t: 1.77,  gain: 0.18},
      {t: 1.97,  gain: 0.14},
    ]

    // base time for early reflections (relative to predelay)
    const erBase = Math.floor(this.sr * 0.012) // 12ms base

    for (let i = 0; i < this.irLen; i++) {
      const t = i / this.sr
      const env = Math.pow(decayRate, i / this.sr * 1000)

      // early reflections: discrete taps
      let erL = 0, erR = 0
      for (const tap of erTaps) {
        const tapIdx = preSamps + Math.floor(erBase * tap.t)
        if (i === tapIdx) {
          const spread = (tap.t - 1) * width
          erL = tap.gain * (1 - spread * 0.3) * earlyAmt
          erR = tap.gain * (1 + spread * 0.3) * earlyAmt
        }
      }

      // late tail: decaying noise through lowpass
      const noiseL = rand() * env * lateAmt
      const noiseR = rand() * env * lateAmt
      lpL = lpL * lpAlpha + noiseL * (1 - lpAlpha)
      lpR = lpR * lpAlpha + noiseR * (1 - lpAlpha)

      this.irL[i] = erL + lpL
      this.irR[i] = erR + lpR
    }

    // normalize IR to prevent clipping
    let maxVal = 0
    for (let i = 0; i < this.irLen; i++) {
      const v = Math.max(Math.abs(this.irL[i]), Math.abs(this.irR[i]))
      if (v > maxVal) maxVal = v
    }
    if (maxVal > 0) {
      const norm = 0.9 / maxVal
      for (let i = 0; i < this.irLen; i++) {
        this.irL[i] *= norm
        this.irR[i] *= norm
      }
    }

    // init input history ring buffer
    this.histSize = this.irLen
    this.histL = new Float32Array(this.histSize)
    this.histR = new Float32Array(this.histSize)
    this.histPos = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "room_size" || name === "decay" || name === "damping" ||
        name === "predelay" || name === "early_late" || name === "width") {
      this.generateIR()
    }
  }

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.generateIR()
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const outGain = this.db2gain(this.p.output)
    const mix = this.p.mix
    const irLen = this.irLen
    if (irLen === 0) return

    for (let ch = 0; ch < out.length; ch++) {
      const ic = inp[ch] || inp[0]
      const oc = out[ch]
      if (!ic || !oc) continue

      const ir = (ch === 0) ? this.irL : this.irR
      const hist = (ch === 0) ? this.histL : this.histR

      for (let i = 0; i < ic.length; i++) {
        // write current input to history ring buffer
        hist[this.histPos] = ic[i]

        // direct convolution: sum of history * IR
        let wet = 0
        let hIdx = this.histPos
        for (let j = 0; j < irLen; j++) {
          wet += hist[hIdx] * ir[j]
          hIdx--
          if (hIdx < 0) hIdx += this.histSize
        }

        // advance ring buffer position
        this.histPos = (this.histPos + 1) % this.histSize

        const dry = ic[i]
        oc[i] = (dry * (1 - mix) + wet * mix) * outGain
      }
    }
  }
}
