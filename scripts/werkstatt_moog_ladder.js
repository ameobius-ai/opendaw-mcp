// @werkstatt moog_ladder 1 1
// @label Moog Ladder Filter
// @param cutoff 800 20 20000 exp Hz
// @param resonance 0.3 0 1 linear
// @param drive 0 0 1 linear
// @param warmth 0 0 1 linear
// @param mode 0 0 2 linear
// @param mix 1 0 1 linear

class Processor {
  p = {cutoff: 800, resonance: 0.3, drive: 0, warmth: 0, mode: 0, mix: 1}
  sr = sampleRate
  // 4 ladder stages (per channel)
  s1L = [0, 0, 0, 0]
  s1R = [0, 0, 0, 0]
  prevL = 0
  prevR = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  _tanh(x) {
    // Fast tanh approximation
    const x2 = x * x
    return x * (27 + x2) / (27 + 9 * x2)
  }

  _processLadder(x, stages, cutoff, res, drive, warmth) {
    // Huovilainen improved Moog ladder — 4 cascaded one-pole LP stages
    // with feedback resonance and thermal noise approximation
    
    const sr = this.sr
    // Frequency compensation (Huovilainen)
    const fc = cutoff / sr
    const wc = Math.min(0.8, fc * 2 * Math.PI)
    
    // Thermal noise + stability factor
    const thermal = 0.00001
    
    // Gains per stage (Huovilainen uses g = 1 - exp(-wc))
    const g = 1 - Math.exp(-wc * 2)
    
    // Feedback with resonance
    const k = res * 4 // 0-4 (self-oscillation at 4)
    
    // Pre-drive
    const input = x * (1 + drive * 3)
    
    // Input into ladder with feedback
    const fb = k * (stages[3] - warmth * stages[0])
    let u = input - fb
    
    // Process 4 stages — each is a one-pole LP with tanh nonlinearity
    // Stage 1
    stages[0] = stages[0] + g * (this._tanh(u - k * stages[3]) - stages[0])
    // Stage 2
    stages[1] = stages[1] + g * (this._tanh(stages[0]) - stages[1])
    // Stage 3
    stages[2] = stages[2] + g * (this._tanh(stages[1]) - stages[2])
    // Stage 4
    stages[3] = stages[3] + g * (this._tanh(stages[2]) - stages[3])
    
    // Mode: 0 = LP (24dB/oct), 1 = HP, 2 = BP
    return stages[3]
  }

  _highpass(x, prev, cutoff) {
    // Simple RC highpass for HP mode
    const sr = this.sr
    const fc = Math.min(0.95, cutoff / (sr * 0.5))
    const a = Math.exp(-2 * Math.PI * fc)
    const hp = a * prev + (1 - a) * x
    return x - hp
  }

  processAudio(inputs, outputs, parameters) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return
    const cutoff = this.p.cutoff
    const res = this.p.resonance
    const drive = this.p.drive
    const warmth = this.p.warmth
    const mode = this.p.mode
    const mix = this.p.mix

    for (let ch = 0; ch < out.length; ch++) {
      const inCh = inp[ch] || inp[0]
      const outCh = out[ch]
      if (!inCh || !outCh) continue

      const stages = ch === 0 ? this.s1L : this.s1R
      const prev = ch === 0 ? this.prevL : this.prevR

      for (let i = 0; i < outCh.length; i++) {
        const dry = inCh[i]
        let filtered

        if (mode < 0.5) {
          // LP — classic Moog 24dB/oct
          filtered = this._processLadder(dry, stages, cutoff, res, drive, warmth)
        } else if (mode < 1.5) {
          // HP — run signal through ladder at low cutoff, subtract from dry
          const lp = this._processLadder(dry, stages, cutoff, res, drive, warmth)
          filtered = dry - lp
        } else {
          // BP — bandpass via cascade: HP then LP at different cutoff
          const hp = this._highpass(dry, prev, cutoff * 0.5)
          filtered = this._processLadder(hp, stages, cutoff, res, drive, warmth)
        }

        outCh[i] = filtered * mix + dry * (1 - mix)
      }

      if (ch === 0) this.prevL = prev
      else this.prevR = prev
    }
  }
}
