// @werkstatt tremolo 1 1
// @label Tremolo
// @param rate 5 0.1 20 exp Hz
// @param depth 0.5 0 1 linear
// @param shape 0 0 1 linear
// @param phase 0 0 6.28 linear rad

class Processor {
  p = {rate: 5, depth: 0.5, shape: 0, phase: 0}
  sr = sampleRate
  phase = 0

  constructor() {
    this.phase = 0
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === 'phase') this.phase = value
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const sr = this.sr
    const phaseInc = (2 * Math.PI * p.rate) / sr

    for (let i = 0; i < input[0].length; i++) {
      this.phase += phaseInc
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI

      // Waveform interpolation: 0=sine, 1=square
      const sine = Math.sin(this.phase)
      const square = sine >= 0 ? 1 : -1
      const lfo = sine * (1 - p.shape) + square * p.shape

      // Tremolo gain: 1 - depth * (1 - lfo) / 2
      // lfo ranges -1..1, so (1 - lfo)/2 ranges 0..1
      const gain = 1 - p.depth * (1 - lfo) * 0.5

      if (output.length > 1) {
        const inL = input.length > 1 ? input[0][i] : input[0][i]
        const inR = input.length > 1 ? input[1][i] : input[0][i]
        output[0][i] = inL * gain
        output[1][i] = inR * gain
      } else {
        output[0][i] = input[0][i] * gain
      }
    }
  }
}
