// @werkstatt vowel_morph 1 1
// @label Vowel Morph (Formant Shifter)
// Morphs between 5 vowels (A, E, I, O, U) via dual resonant bandpass filters
// Vowel positions interpolated smoothly — creates talking/talking-bass effects
// Use on vocals, synth leads, bass for "wow" / vocal-like character

// @param vowel   0.0  0 1   linear   // Vowel position: 0=A, 0.25=E, 0.5=I, 0.75=O, 1=U
// @param morph   0    0 1   linear   // Auto-morph LFO amount (0=static, 1=full auto-sweep)
// @param rate    0.5  0.1 5 linear   // Auto-morph rate (Hz, 0.1=slow, 5=fast chatter)
// @param reso    0.7  0 1   linear   // Formant resonance (0=subtle, 1=sharp vowel)
// @param tilt    0    -1 1  linear   // Spectral tilt: -1=darker (softer), 0=neutral, 1=brighter
// @param mix     1    0 1   linear   // Dry/wet mix
// @param output  0   -12 6  linear dB

class Processor {
  p = {vowel: 0, morph: 0, rate: 0.5, reso: 0.7, tilt: 0, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // Vowel formant table: F1, F2, F3 (Hz) for A, E, I, O, U
  // Source: classic speech synthesis formant data
  VOWELS = [
    [800, 1150, 2900],   // A (ah) — low F1, mid F2
    [400, 1700, 2600],   // E (eh) — mid F1, high F2
    [300, 2200, 3000],   // I (ee) — low F1, high F2
    [450, 800, 2800],    // O (oh) — mid F1, low F2
    [350, 600, 2700],    // U (oo) — low F1, very low F2
  ]

  // Two resonant bandpass filters (biquad)
  f1 = {x1: 0, x2: 0, y1: 0, y2: 0}
  f2 = {x1: 0, x2: 0, y1: 0, y2: 0}
  f3 = {x1: 0, x2: 0, y1: 0, y2: 0}

  // Spectral tilt (one-pole lowpass/highpass)
  tiltState = 0

  // LFO phase
  lfoPhase = 0

  paramChanged(name, value) {
    if (name === 'output') {
      this.p.output = value
      this.outGain = Math.pow(10, value / 20)
    }
    if (name === 'vowel') this.p.vowel = value
    if (name === 'morph') this.p.morph = value
    if (name === 'rate') this.p.rate = value
    if (name === 'reso') this.p.reso = value
    if (name === 'tilt') this.p.tilt = value
    if (name === 'mix') this.p.mix = value
  }

  _interpVowel(pos) {
    // pos: 0-1, map to 5 vowels (0-4)
    const idx = pos * 4 // 0 to 4
    const i0 = Math.floor(idx) % 5
    const i1 = (i0 + 1) % 5
    const frac = idx - Math.floor(idx)
    const f1 = this.VOWELS[i0][0] * (1 - frac) + this.VOWELS[i1][0] * frac
    const f2 = this.VOWELS[i0][1] * (1 - frac) + this.VOWELS[i1][1] * frac
    const f3 = this.VOWELS[i0][2] * (1 - frac) + this.VOWELS[i1][2] * frac
    return [f1, f2, f3]
  }

  _setBiquadBP(state, freq, Q) {
    const w0 = 2 * Math.PI * freq / this.sr
    const alpha = Math.sin(w0) / (2 * Q)
    const cosw = Math.cos(w0)
    const b0 = alpha
    const b1 = 0
    const b2 = -alpha
    const a0 = 1 + alpha
    const a1 = -2 * cosw
    const a2 = 1 - alpha
    state.b0 = b0 / a0
    state.b1 = b1 / a0
    state.b2 = b2 / a0
    state.a1 = a1 / a0
    state.a2 = a2 / a0
  }

  _processBiquad(state, x) {
    const y = state.b0 * x + state.b1 * state.x1 + state.b2 * state.x2
                  - state.a1 * state.y1 - state.a2 * state.y2
    state.x2 = state.x1
    state.x1 = x
    state.y2 = state.y1
    state.y1 = y
    return y
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    if (input.length < 1) return

    const vowel = this.p.vowel
    const morph = this.p.morph
    const rate = this.p.rate
    const reso = this.p.reso
    const tilt = this.p.tilt
    const mix = this.p.mix
    const outGain = this.outGain

    const Q = 5 + reso * 30 // Q 5-35
    const numCh = input.length
    const numFrames = input[0].length
    const lfoInc = 2 * Math.PI * rate / this.sr

    for (let i = 0; i < numFrames; i++) {
      // Auto-morph LFO (sine)
      this.lfoPhase += lfoInc
      const lfoVal = Math.sin(this.lfoPhase) * 0.5 + 0.5 // 0-1
      const vowelPos = (vowel + morph * lfoVal * 4) % 1 // wrap

      // Get interpolated formant frequencies
      const [freq1, freq2, freq3] = this._interpVowel(vowelPos)

      // Update biquad coefficients (per-sample for smooth morph)
      this._setBiquadBP(this.f1, freq1, Q)
      this._setBiquadBP(this.f2, freq2, Q)
      this._setBiquadBP(this.f3, freq3, Q)

      for (let ch = 0; ch < numCh; ch++) {
        const dry = input[ch][i]
        let wet = this._processBiquad(this.f1, dry)
        wet = this._processBiquad(this.f2, wet)
        wet = this._processBiquad(this.f3, wet)

        // Spectral tilt
        if (tilt > 0) {
          // Brighten: highpass emphasis
          this.tiltState = 0.999 * this.tiltState + 0.001 * wet
          wet = wet + tilt * (wet - this.tiltState) * 2
        } else if (tilt < 0) {
          // Darken: lowpass
          this.tiltState = 0.997 * this.tiltState + 0.003 * wet
          wet = wet * (1 + tilt) + this.tiltState * (-tilt)
        }

        // Dry/wet + output gain
        output[ch][i] = (dry * (1 - mix) + wet * mix) * outGain
      }
    }
  }
}
