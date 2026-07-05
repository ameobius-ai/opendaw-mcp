// @apparat supersaw 1 1
// @label Supersaw
// @param detune 0.15 0 0.5 linear
// @param spread 0.6 0 1 linear
// @param cutoff 0.8 0 1 linear
// @param resonance 0.2 0 1 linear
// @param attack 0.005 0.001 2 exp s
// @param decay 0.2 0.01 4 exp s
// @param sustain 0.8 0 1 linear
// @param release 0.4 0.01 4 exp s
// @param volume 0.7 0 1 linear

class Processor {
  p = {detune: 0.15, spread: 0.6, cutoff: 0.8, resonance: 0.2,
       attack: 0.005, decay: 0.2, sustain: 0.8, release: 0.4, volume: 0.7}
  sr = sampleRate
  noteFreq = 220
  env = 0
  envState = 0

  // 7 voices: fixed sawtooth with character detune pattern
  NUM = 7
  // JP-8000 style detune ratios (cents): -12, -7, -4, 0, +4, +7, +12
  detuneCents = [-12, -7, -4, 0, 4, 7, 12]
  phases = null
  pans = null

  // per-voice state
  _initVoices() {
    this.phases = new Float32Array(this.NUM)
    this.pans = new Float32Array(this.NUM)
    for (let v = 0; v < this.NUM; v++) {
      this.phases[v] = Math.random()
      // pan: center voice = 0, outer voices spread wider
      const norm = (v - (this.NUM - 1) / 2) / ((this.NUM - 1) / 2)
      this.pans[v] = norm * this.p.spread
    }
  }

  // one-pole lowpass state (per channel)
  lpL = 0
  lpR = 0

  _saw(phase) {
    return 2 * (phase - Math.floor(phase + 0.5))
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "spread") {
      // recompute pan positions
      for (let v = 0; v < this.NUM; v++) {
        const norm = (v - (this.NUM - 1) / 2) / ((this.NUM - 1) / 2)
        this.pans[v] = norm * this.p.spread
      }
    }
  }

  noteOn(freq, velocity) {
    this.noteFreq = freq
    this.envState = 1
    this.env = 0
    if (!this.phases) this._initVoices()
    // randomize phases for rich starting texture
    for (let v = 0; v < this.NUM; v++) {
      this.phases[v] = Math.random()
    }
  }

  noteOff() {
    this.envState = 4
  }

  process(output, block) {
    const sr = this.sr
    const detune = this.p.detune
    const vol = this.p.volume
    const aCoef = Math.exp(-1 / (this.p.attack * sr))
    const dCoef = Math.exp(-1 / (this.p.decay * sr))
    const sLevel = this.p.sustain
    const rCoef = Math.exp(-1 / (this.p.release * sr))

    // filter cutoff: exponential mapping 50Hz..16kHz
    const cutHz = 50 * Math.pow(320, this.p.cutoff)
    const cutCoeff = Math.exp(-2 * Math.PI * cutHz / sr)
    const resAmt = this.p.resonance * 0.9

    if (!this.phases) this._initVoices()

    // precompute voice frequencies
    const freqs = new Float32Array(this.NUM)
    for (let v = 0; v < this.NUM; v++) {
      const cents = this.detuneCents[v] * (detune / 0.5)
      freqs[v] = this.noteFreq * Math.pow(2, cents / 1200)
    }

    // equal-power pan: left = cos, right = sin
    const panAngles = new Float32Array(this.NUM)
    for (let v = 0; v < this.NUM; v++) {
      // pan -1..1 → angle 0..PI/2
      panAngles[v] = (this.pans[v] + 1) * 0.25 * Math.PI
    }

    for (let i = block.s0; i < block.s1; i++) {
      // ADSR
      if (this.envState === 1) {
        this.env += (1 - this.env) * (1 - aCoef)
        if (this.env >= 0.999) this.envState = 2
      } else if (this.envState === 2) {
        this.env += (sLevel - this.env) * (1 - dCoef)
        if (Math.abs(this.env - sLevel) < 0.001) this.envState = 3
      } else if (this.envState === 3) {
        this.env = sLevel
      } else if (this.envState === 4) {
        this.env *= rCoef
        if (this.env < 0.0001) this.envState = 0
      }

      // sum 7 detuned saws with per-voice pan
      let left = 0
      let right = 0
      for (let v = 0; v < this.NUM; v++) {
        const s = this._saw(this.phases[v])
        const cl = Math.cos(panAngles[v])
        const cr = Math.sin(panAngles[v])
        left += s * cl
        right += s * cr
        this.phases[v] += freqs[v] / sr
        if (this.phases[v] >= 1) this.phases[v] -= 1
      }
      left /= this.NUM
      right /= this.NUM

      // resonant lowpass (one-pole + feedback)
      const inputL = left * this.env * vol
      const inputR = right * this.env * vol
      this.lpL = this.lpL * cutCoeff + inputL * (1 - cutCoeff)
      this.lpR = this.lpR * cutCoeff + inputR * (1 - cutCoeff)
      // resonance: feed back band-rejected signal
      const resL = (inputL - this.lpL) * resAmt
      const resR = (inputR - this.lpR) * resAmt
      this.lpL += resL * (1 - cutCoeff)
      this.lpR += resR * (1 - cutCoeff)

      output[0][i] = this.lpL
      output[1][i] = this.lpR
    }
  }
}
