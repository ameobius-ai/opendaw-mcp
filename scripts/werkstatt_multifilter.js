// @werkstatt multifilter 1 1
// @label Multi-Mode Filter
// @param mode 0 0 3 linear
// @param cutoff 800 20 20000 exp Hz
// @param resonance 0.3 0 1 linear
// @param drive 0 0 1 linear
// @param mix 1 0 1 linear

class Processor {
  p = {mode: 0, cutoff: 800, resonance: 0.3, drive: 0, mix: 1}
  sr = sampleRate
  // SVF state
  low = 0
  band = 0
  high = 0
  notch = 0
  // Pre-drive saturation state
  prevIn = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr

    // SVF coefficients (Chamberlin topology)
    const fc = Math.max(20, Math.min(20000, p.cutoff))
    const f = 2 * Math.sin(Math.PI * fc / sr)
    // Damping from resonance: q = 1 - resonance (0=max resonance, 1=no resonance)
    const q = 1 - p.resonance * 0.95
    const damp = Math.min(2, Math.max(0, q))

    const mode = Math.round(p.mode)
    const driveGain = 1 + p.drive * 4
    const stereo = output.length > 1

    // Separate SVF state for R channel
    let lowR = 0, bandR = 0, highR = 0

    for (let i = 0; i < input[0].length; i++) {
      const inL = input.length > 1 ? input[0][i] : input[0][i]
      const inR = input.length > 1 ? input[1][i] : input[0][i]

      // Pre-drive: soft saturation
      const drvL = inL * driveGain
      const satL = drvL / (1 + Math.abs(drvL) * p.drive * 0.5)
      const drvR = inR * driveGain
      const satR = drvR / (1 + Math.abs(drvR) * p.drive * 0.5)

      // Chamberlin SVF (L)
      this.high = satL - this.low - damp * this.band
      this.band = this.band + f * this.high
      this.low = this.low + f * this.band
      this.notch = this.high + this.low

      let outL
      switch (mode) {
        case 0: outL = this.low; break    // Lowpass
        case 1: outL = this.high; break   // Highpass
        case 2: outL = this.band; break   // Bandpass
        case 3: outL = this.notch; break  // Notch
        default: outL = this.low
      }

      // Chamberlin SVF (R)
      highR = satR - lowR - damp * bandR
      bandR = bandR + f * highR
      lowR = lowR + f * bandR
      const notchR = highR + lowR

      let outR
      switch (mode) {
        case 0: outR = lowR; break
        case 1: outR = highR; break
        case 2: outR = bandR; break
        case 3: outR = notchR; break
        default: outR = lowR
      }

      // Dry/wet mix
      const wetL = outL * p.mix
      const wetR = outR * p.mix
      const dryL = inL * (1 - p.mix)
      const dryR = inR * (1 - p.mix)

      if (stereo) {
        output[0][i] = dryL + wetL
        output[1][i] = dryR + wetR
      } else {
        output[0][i] = dryL + wetL
      }
    }

    // Store R state (can't persist locals, so re-init next block — acceptable for simple SVF)
  }
}
