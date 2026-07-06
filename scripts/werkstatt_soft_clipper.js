// @werkstatt soft_clipper 1 1
// @label Soft Clipper
// @param ceiling 0.9 0 1 linear
// @param drive 0.3 0 1 linear
// @param curve 0.5 0 1 linear
// @param mix 1 0 1 linear
// @param outGain 0 0 1 linear

// Soft clipper — saturating limiter with musical clipping curve.
// Unlike a hard limiter (brickwall), soft clipping rounds off peaks
// progressively, adding harmonic richness while preventing digital clipping.
// Used on drum buses, mix buses, masters, and 808s for loudness without
// harshness. SSL G-bus style, FabFilter Pro-L style, Klanghelm DC1A style.
//
// ceiling: 0→0dB, 1→-0.1dB — the soft ceiling threshold
// drive: 0→0dB, 1→+18dB — input gain before clipping
// curve: 0→hard (tanh), 1→soft (cubic) — clipping character
// mix: dry/wet
// outGain: 0→0dB, 1→+6dB — output trim after clipping

class Processor {
  p = {ceiling: 0.9, drive: 0.3, curve: 0.5, mix: 1, outGain: 0}
  sr = sampleRate

  paramChanged(name, value) {
    this.p[name] = value
  }

  _dbToGain(db) {
    if (db <= -120) return 0
    return Math.pow(10, db / 20)
  }

  // Tanh approximation (cubic soft clip)
  _tanh(x) {
    const x2 = x * x
    return x * (27 + x2) / (27 + 9 * x2)
  }

  // Cubic soft clip
  _cubic(x) {
    if (x > 1) return 2 / 3
    if (x < -1) return -2 / 3
    return x - x * x * x / 3
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const ceiling = this.p.ceiling
    const driveDb = this.p.drive * 18
    const driveGain = this._dbToGain(driveDb)
    const curveMix = this.p.curve
    const outGainDb = this.p.outGain * 6
    const outTrim = this._dbToGain(outGainDb)
    const mix = this.p.mix

    // Ceiling in linear: 0→0 (silence), 1→~0.89 (-1dBFS)
    // Map ceiling param to linear threshold
    const ceilingLin = 0.01 + ceiling * 0.98  // 0.01 to 0.99
    const invCeiling = 1 / ceilingLin

    for (let ch = 0; ch < input.length; ch++) {
      const inCh = input[ch]
      const outCh = output[ch]
      if (!inCh || !outCh) continue

      for (let i = 0; i < inCh.length; i++) {
        const x = inCh[i]
        // Drive
        const driven = x * driveGain
        // Normalize to ceiling
        const normalized = driven * invCeiling
        // Blend between tanh (hard-ish) and cubic (soft)
        const tanhOut = this._tanh(normalized)
        const cubicOut = this._cubic(normalized)
        const clipped = tanhOut * (1 - curveMix) + cubicOut * curveMix
        // Back to original scale
        const processed = clipped * ceilingLin * outTrim
        // Mix
        outCh[i] = processed * mix + x * (1 - mix)
      }
    }
  }
}
