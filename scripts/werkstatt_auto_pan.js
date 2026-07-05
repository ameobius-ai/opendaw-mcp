// @werkstatt auto_pan 1 1
// @label Auto-Pan
// @param rate 2 0.1 20 exp Hz
// @param depth 0.7 0 1 linear
// @param shape 0 0 1 linear
// @param phase 0 0 360 linear deg
// @param width 1 0 1 linear
// @param offset 0 -1 1 linear

class Processor {
  p = {rate: 2, depth: 0.7, shape: 0, phase: 0, width: 1, offset: 0}
  sr = 44100
  bs = 128
  phasePos = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Waveform morph: 0=sine, 0.5=triangle, 1=square
  _waveform(phase, shape) {
    const s = shape
    // Sine to triangle morph (0 to 0.5)
    if (s < 0.5) {
      const t = s * 2 // 0..1
      const sine = Math.sin(phase)
      const tri = (2 / Math.PI) * Math.asin(Math.sin(phase))
      return sine * (1 - t) + tri * t
    }
    // Triangle to square morph (0.5 to 1)
    const t = (s - 0.5) * 2 // 0..1
    const tri = (2 / Math.PI) * Math.asin(Math.sin(phase))
    const sq = Math.sign(Math.sin(phase))
    return tri * (1 - t) + sq * t
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const rate = this.p.rate
    const depth = this.p.depth
    const shape = this.p.shape
    const width = this.p.width
    const offset = this.p.offset
    const phaseOffset = this.p.phase * Math.PI / 180

    const inc = 2 * Math.PI * rate / sr
    const stereo = out.length > 1

    for (let i = 0; i < out[0].length; i++) {
      const wave = this._waveform(this.phasePos + phaseOffset, shape)
      this.phasePos += inc
      if (this.phasePos > Math.PI * 2) this.phasePos -= Math.PI * 2

      // Pan position: -1 = full left, 0 = center, +1 = full right
      const pan = wave * depth * width + offset
      // Clamp
      const panClamped = Math.max(-1, Math.min(1, pan))

      // Equal-power pan law
      const angleL = (Math.max(0, -panClamped) + 1) * Math.PI / 4 // 0..pi/2
      const angleR = (Math.max(0, panClamped) + 1) * Math.PI / 4
      const gainL = Math.cos(angleL)
      const gainR = Math.cos(angleR)

      // When pan > 0 (right): reduce L, full R
      // When pan < 0 (left): full L, reduce R
      const gL = panClamped > 0 ? gainL * (1 - panClamped * 0.5) : gainL
      const gR = panClamped < 0 ? gainR * (1 + panClamped * 0.5) : gainR

      const inL = inp[0][i]
      const inR = stereo ? (inp.length > 1 ? inp[1][i] : inp[0][i]) : inL

      if (stereo) {
        // Auto-pan: distribute input across L/R based on pan position
        const mono = (inL + inR) * 0.5
        out[0][i] = inL * (1 - depth) + mono * gL * depth
        out[1][i] = inR * (1 - depth) + mono * gR * depth
      } else {
        // Mono output: just modulate amplitude
        out[0][i] = inL * (0.5 + 0.5 * wave * depth)
      }
    }
  }
}
