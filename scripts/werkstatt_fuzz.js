// @werkstatt fuzz 1 1
// @label Fuzz (Big Muff Pi / Fuzz Face style)
// Hard clipping distortion with octave-up content from full-wave rectification
// + classic Big Muff tone stack (lowpass/highpass blend)

// @param sustain   0.7  0  1   linear   // sustain/gain — controls clipping intensity
// @param tone      0.5  0  1   linear   // tone stack: 0=bass (lowpass), 1=treble (highpass)
// @param octave    0    0  1   linear   // octave-up amount (full-wave rectification blend)
// @param gate      0    0  0.3 linear   // noise gate threshold (reduces fizz on sustained notes)
// @param bias      0    -0.3 0.3 linear // asymmetrical clipping bias (even harmonics)
// @param level     0.5  0  1   linear   // output level
// @param dry       0    0  1   linear   // dry blend (fuzz parallel mix)
// @param output    0    -24 6 linear dB

class Processor {
  p = {sustain: 0.7, tone: 0.5, octave: 0, gate: 0, bias: 0, level: 0.5, dry: 0, output: 0}
  sr = sampleRate

  // Tone stack state (one-pole)
  toneLp = 0   // lowpass state
  toneHp = 0   // highpass state

  // Noise gate
  env = 0
  gateGain = 1

  // Output gain
  outGain = 1

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  _hardClip(x, sustain, bias) {
    // High gain into hard clipping — classic fuzz character
    const gain = 1 + sustain * 50   // 1..51x gain
    let s = x * gain + bias

    // Hard clip to [-1, 1]
    if (s > 1) s = 1
    else if (s < -1) s = -1

    // Extra foldback for extreme settings (Muff-like squash)
    if (sustain > 0.8) {
      if (s > 0.95) s = 0.95 + (s - 0.95) * 0.3
      else if (s < -0.95) s = -0.95 + (s + 0.95) * 0.3
    }

    return s
  }

  _fullWaveRect(x) {
    // Full-wave rectification → octave-up harmonics
    return x < 0 ? -x : x
  }

  process(io, block) {
    const sr = this.sr
    const p = this.p
    const og = this.outGain

    // Tone stack frequencies
    const lpFreq = 800 + (1 - p.tone) * 3000   // 800..3800 Hz lowpass
    const hpFreq = 300 + p.tone * 2500          // 300..2800 Hz highpass
    const lpCoeff = Math.exp(-2 * Math.PI * lpFreq / sr)
    const hpCoeff = Math.exp(-2 * Math.PI * hpFreq / sr)

    // Noise gate coefficients
    const gateThresh = p.gate * p.gate * 0.1   // 0..0.03
    const gateAttack = Math.exp(-1 / (sr * 0.005))   // 5ms attack
    const gateRelease = Math.exp(-1 / (sr * 0.05))    // 50ms release

    const s0 = block.s0
    const s1 = block.s1

    for (let i = s0; i < s1; i++) {
      const inL = io.src[0][i]
      const inR = io.src[1] ? io.src[1][i] : inL
      const mono = (inL + inR) * 0.5

      // --- Noise gate (envelope follower) ---
      const absMono = mono < 0 ? -mono : mono
      if (absMono > this.env) {
        this.env = absMono
      } else {
        this.env = this.env * gateRelease + absMono * (1 - gateRelease)
      }

      if (gateThresh > 0) {
        if (this.env > gateThresh) {
          this.gateGain = this.gateGain * gateAttack + 1 * (1 - gateAttack)
        } else {
          this.gateGain = this.gateGain * gateAttack + 0 * (1 - gateAttack)
        }
      } else {
        this.gateGain = 1
      }

      // --- Hard clip ---
      let clipped = this._hardClip(mono, p.sustain, p.bias)

      // --- Octave-up via full-wave rectification ---
      if (p.octave > 0) {
        const rectified = this._fullWaveRect(clipped)
        // Remove DC from rectified signal (one-pole highpass at 20Hz)
        clipped = clipped * (1 - p.octave) + rectified * p.octave
        // DC blocker
        this._dcBlock = this._dcBlock || 0
        this._dcPrev = this._dcPrev || 0
        const dcOut = clipped - this._dcBlock
        this._dcBlock = this._dcBlock * 0.999 + clipped * 0.001
        clipped = dcOut
      }

      // --- Tone stack (Big Muff style: LP + HP blend) ---
      this.toneLp = this.toneLp * lpCoeff + clipped * (1 - lpCoeff)
      this.toneHp = this.toneHp * hpCoeff + clipped * (1 - hpCoeff)

      // Blend: tone=0 → all lowpass, tone=1 → all highpass
      let toned = this.toneLp * (1 - p.tone) + this.toneHp * p.tone

      // --- Level + gate ---
      toned = toned * p.level * this.gateGain

      // --- Dry blend ---
      const out = toned * (1 - p.dry) + mono * p.dry

      // --- Output ---
      const final = out * og

      io.out[0][i] = final
      io.out[1][i] = final
    }
  }

  _dcBlock = 0
  _dcPrev = 0
}
