// @apparat wavetable 1 1
// @label Wavetable Synth
// @param pos 0 0 1 linear
// @param pos_lfo_rate 0.5 0.05 20 exp Hz
// @param pos_lfo_depth 0 0 1 linear
// @param detune 0 0 0.5 linear
// @param unison 1 1 7 int
// @param attack 0.005 0.001 2 exp s
// @param decay 0.2 0.01 4 exp s
// @param sustain 0.7 0 1 linear
// @param release 0.3 0.01 4 exp s
// @param volume 0.7 0 1 linear

class Processor {
  p = {pos: 0, pos_lfo_rate: 0.5, pos_lfo_depth: 0, detune: 0, unison: 1, attack: 0.005, decay: 0.2, sustain: 0.7, release: 0.3, volume: 0.7}
  sr = sampleRate
  phase = 0
  lfoPhase = 0
  env = 0
  envState = 0
  noteFreq = 220
  noteOn = false

  // 8 wavetables: sine, tri, saw, square, pulse, double-sine, saw+tri, noise-sine
  _wt(phase, pos) {
    const t = (phase / (2 * Math.PI)) % 1
    const n = 8
    const idx = pos * (n - 1)
    const i0 = Math.floor(idx) % n
    const i1 = (i0 + 1) % n
    const frac = idx - Math.floor(idx)
    const t0 = this._table(i0, t)
    const t1 = this._table(i1, t)
    return t0 * (1 - frac) + t1 * frac
  }

  _table(i, t) {
    switch(i) {
      case 0: return Math.sin(2 * Math.PI * t)
      case 1: return 2 * Math.abs(2 * (t - Math.floor(t + 0.5))) - 1
      case 2: return 2 * (t - Math.floor(t + 0.5))
      case 3: return t < 0.5 ? 1 : -1
      case 4: return t < 0.3 ? 1 : -1
      case 5: return 0.6 * Math.sin(2 * Math.PI * t) + 0.4 * Math.sin(4 * Math.PI * t)
      case 6: return 0.5 * (2 * (t - Math.floor(t + 0.5))) + 0.5 * (2 * Math.abs(2 * (t - Math.floor(t + 0.5))) - 1)
      case 7: return 0.7 * Math.sin(2 * Math.PI * t) + 0.3 * (Math.random() * 2 - 1)
      default: return Math.sin(2 * Math.PI * t)
    }
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  noteOn(freq, velocity) {
    this.noteFreq = freq
    this.noteOn = true
    this.envState = 1
    this.env = 0
    this.phase = 0
  }

  noteOff() {
    this.noteOn = false
    this.envState = 4
  }

  process(output, block) {
    const sr = this.sr
    const pos = this.p.pos
    const lfoRate = this.p.pos_lfo_rate
    const lfoDepth = this.p.pos_lfo_depth
    const detune = this.p.detune
    const unison = Math.max(1, Math.round(this.p.unison))
    const vol = this.p.volume
    const aCoef = Math.exp(-1 / (this.p.attack * sr))
    const dCoef = Math.exp(-1 / (this.p.decay * sr))
    const sLevel = this.p.sustain
    const rCoef = Math.exp(-1 / (this.p.release * sr))

    if (!this._uniPhases || this._uniPhases.length !== unison) {
      this._uniPhases = new Float32Array(unison)
      this._uniDetunes = new Float32Array(unison)
      for (let u = 0; u < unison; u++) {
        this._uniPhases[u] = Math.random() * 2 * Math.PI
        this._uniDetunes[u] = u === 0 ? 0 : ((u - (unison - 1) / 2) / (unison - 1 || 1)) * detune
      }
    }

    for (let i = block.s0; i < block.s1; i++) {
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

      this.lfoPhase += 2 * Math.PI * lfoRate / sr
      if (this.lfoPhase > 2 * Math.PI) this.lfoPhase -= 2 * Math.PI
      const lfo = Math.sin(this.lfoPhase)
      const scanPos = Math.max(0, Math.min(1, pos + lfo * lfoDepth))

      let sample = 0
      for (let u = 0; u < unison; u++) {
        const f = this.noteFreq * (1 + this._uniDetunes[u])
        sample += this._wt(this._uniPhases[u], scanPos)
        this._uniPhases[u] += 2 * Math.PI * f / sr
        if (this._uniPhases[u] > 2 * Math.PI) this._uniPhases[u] -= 2 * Math.PI
      }
      sample = (sample / unison) * this.env * vol
      output[0][i] = sample
      output[1][i] = sample
    }
  }
}
