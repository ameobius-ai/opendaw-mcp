// @werkstatt tube_saturator 1 1
// @label Tube Saturator
// @param drive 0.3 0 1 linear
// @param warmth 0.5 0 1 linear
// @param bias 0.3 -0.5 0.5 linear
// @param tone 0.5 0 1 linear
// @param output 0 0 1 linear
// @param mix 0.8 0 1 linear

class Processor {
  p = {drive: 0.3, warmth: 0.5, bias: 0.3, tone: 0.5, output: 0, mix: 0.8}
  toneStateL = 0
  toneStateR = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Asymmetrical waveshaper — tube-like even harmonic generation
  // Combines shifted tanh (even harmonics) with symmetric soft-clip (odd harmonics)
  _waveshape(x, drive, warmth, bias) {
    // Asymmetric bias shifts the operating point → even harmonics
    const biased = x + bias * drive
    // Even harmonic component (warmth-controlled)
    const even = Math.tanh(biased * drive * 2) * 0.5
    // Odd harmonic component (symmetric soft-clip)
    const odd = Math.tanh(x * drive * 3) * 0.5
    // Blend: warmth controls even/odd balance
    return even * warmth + odd * (1 - warmth)
  }

  // One-pole lowpass for tone control (warmth/brightness)
  _toneFilter(x, state, cutoff) {
    const a = cutoff
    state = state * (1 - a) + x * a
    return state
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const drive = 1 + this.p.drive * 8 // 1-9x gain
    const warmth = this.p.warmth
    const bias = this.p.bias
    const toneCut = 0.1 + this.p.tone * 0.8 // 0.1 (dark) to 0.9 (bright)
    const outGain = Math.pow(10, this.p.output * 0.3) // 0 to ~2x
    const mix = this.p.mix

    for (let ch = 0; ch < out.length; ch++) {
      const ic = inp[ch] || inp[0]
      const oc = out[ch]
      if (!ic || !oc) continue

      let state = ch === 0 ? this.toneStateL : this.toneStateR

      for (let i = 0; i < ic.length; i++) {
        const dry = ic[i]
        // Waveshape
        let wet = this._waveshape(dry, drive, warmth, bias)
        // Tone filter (post-saturation lowpass for warmth)
        wet = this._toneFilter(wet, state, toneCut)
        state = wet
        // Output gain
        wet *= outGain
        // Dry/wet
        oc[i] = dry * (1 - mix) + wet * mix
      }

      if (ch === 0) this.toneStateL = state
      else this.toneStateR = state
    }
  }
}
