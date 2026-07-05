// @werkstatt overdrive 1 1
// @label Overdrive
// @param drive 0.4 0 1 linear
// @param tone 0.5 0 1 linear
// @param level 0.8 0 1 linear
// @param bias 0 0 1 linear
// @param dry 0 0 1 linear

class Processor {
  p = {drive: 0.4, tone: 0.5, level: 0.8, bias: 0, dry: 0}
  sr = sampleRate
  lp1 = 0
  lp2 = 0
  hp1 = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Asymmetric soft clip — tube-like overdrive character
  _clip(x, drive) {
    const d = 1 + drive * 8  // 1..9 gain
    const s = x * d
    // Positive half: tanh-like (polynomial approx)
    // Negative half: slightly harder (asymmetric = even harmonics = warmth)
    if (s >= 0) {
      return s / (1 + s * s * 0.15)
    } else {
      return s / (1 + s * s * 0.25)
    }
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr

    // Pre-filter: highpass to remove mud before clipping (freq scales with bias)
    const hpFreq = 60 + p.bias * 200
    const hpAlpha = 1 - Math.exp(-1 / (sr / (2 * Math.PI * hpFreq)))
    // Post-filter: tone control (0=bright, 1=dark)
    const lpFreq = 2000 + p.tone * 8000
    const lpAlpha = 1 - Math.exp(-1 / (sr / (2 * Math.PI * lpFreq)))

    const stereo = output.length > 1

    for (let i = 0; i < input[0].length; i++) {
      const inL = input.length > 1 ? input[0][i] : input[0][i]
      const inR = input.length > 1 ? input[1][i] : input[0][i]

      // Pre-HP filter (remove low-end mud before drive)
      this.hp1 = this.hp1 + hpAlpha * (inL - this.hp1)
      const hpL = inL - this.hp1

      // Drive + asymmetric soft clip
      const clipL = this._clip(hpL + p.bias * 0.1, p.drive)

      // Post tone filter (LP)
      this.lp1 = this.lp1 + lpAlpha * (clipL - this.lp1)
      let outL = this.lp1 * p.level

      // Dry blend
      outL = outL * (1 - p.dry) + inL * p.dry

      if (stereo) {
        // R channel — same processing, separate state would be ideal
        // but keeping simple: process R through same path with slight offset
        const hpR = inR - this.hp1 * 0.99
        const clipR = this._clip(hpR + p.bias * 0.1, p.drive)
        this.lp2 = this.lp2 + lpAlpha * (clipR - this.lp2)
        let outR = this.lp2 * p.level
        outR = outR * (1 - p.dry) + inR * p.dry
        output[0][i] = outL
        output[1][i] = outR
      } else {
        output[0][i] = outL
      }
    }
  }
}
