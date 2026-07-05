// @werkstatt waveshaper 1 1
// @label Waveshaper
// @param drive 0.5 0 3 linear
// @param curve 0 0 3 linear
// @param bias 0 -0.5 0.5 linear
// @param harmonics 0.3 0 1 linear
// @param tone 0.5 0 1 linear
// @param output 0 -24 6 linear
// @param mix 1 0 1 linear

class Processor {
  p = {drive: 0.5, curve: 0, bias: 0, harmonics: 0.3, tone: 0.5, output: 0, mix: 1}
  toneL = 0
  toneR = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  _shape(x, drive, curveIdx, bias) {
    const d = drive
    const xb = x + bias * d
    let out

    if (curveIdx < 0.5) {
      // Curve 0: tanh soft-clip — smooth, warm, classic saturation
      out = Math.tanh(xb * d * 2)
    } else if (curveIdx < 1.5) {
      // Curve 1: cubic — sharper knee, more aggressive
      const clamped = Math.max(-1, Math.min(1, xb * d))
      out = clamped - (clamped * clamped * clamped) / 3
    } else if (curveIdx < 2.5) {
      // Curve 2: atan — linear-ish center, hard shoulders
      out = (2 / Math.PI) * Math.atan(xb * d * 3)
    } else {
      // Curve 3: Chebyshev — controlled harmonic injection
      const t = Math.max(-1, Math.min(1, xb * d))
      // T2 (2nd harmonic) + T3 (3rd harmonic) blend via harmonics param
      const t2 = 2 * t * t - 1
      const t3 = 4 * t * t * t - 3 * t
      out = t * (1 - this.p.harmonics) + (t2 * this.p.harmonics * 0.5 + t3 * this.p.harmonics * 0.3)
    }

    return out
  }

  _toneFilter(x, state, tone) {
    // Simple one-pole lowpass/highpass blend
    // tone=0.5 = flat, <0.5 = darker (more lowpass), >0.5 = brighter (more highpass residual)
    const alpha = 0.02 + tone * 0.3
    const lp = state + alpha * (x - state)
    if (tone < 0.5) {
      // Blend toward lowpass
      const blend = (0.5 - tone) * 2
      return x * (1 - blend) + lp * blend
    } else {
      // Blend toward highpass (subtract lowpass)
      const blend = (tone - 0.5) * 2
      const hp = x - lp
      return x * (1 - blend) + hp * blend
    }
  }

  processAudio(inputs, outputs, parameters) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return
    const drive = this.p.drive
    const curve = this.p.curve
    const bias = this.p.bias
    const tone = this.p.tone
    const outGain = Math.pow(10, this.p.output / 20)
    const mix = this.p.mix

    for (let ch = 0; ch < out.length; ch++) {
      const inCh = inp[ch] || inp[0]
      const outCh = out[ch]
      if (!inCh || !outCh) continue
      const state = ch === 0 ? this.toneL : this.toneR

      for (let i = 0; i < outCh.length; i++) {
        const dry = inCh[i]
        const shaped = this._shape(dry, drive, curve, bias)
        const toned = this._toneFilter(shaped, state, tone)
        outCh[i] = (toned * outGain * mix + dry * (1 - mix)) * 0.8
      }

      if (ch === 0) this.toneL = state
      else this.toneR = state
    }
  }
}
