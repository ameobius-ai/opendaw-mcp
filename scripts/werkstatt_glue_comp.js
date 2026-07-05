// @werkstatt glue_compressor 1 1
// @label Glue Compressor (SSL Bus Style)
// Bus compressor for gluing groups together — SSL G-buss style
// Fixed ratio options, slow release, auto makeup gain, warm VCA character
// Use on drum bus, vocal bus, or master bus for cohesive "glued" sound

// @param threshold  -10  -40  0   linear dB   // Threshold: where comp kicks in. -10 = gentle, -25 = aggressive
// @param ratio       2    1    4   int          // Ratio: 2 = gentle glue, 4 = hard pump. SSL bus = 2 or 4
// @param attack     10    3    30  linear       // Attack: 10ms = SSL default, 3ms = catch peaks, 30ms = let transients through
// @param release    100   50   400 linear       // Release: 100ms = SSL default, 50ms = snappy, 400ms = smooth
// @param mix         1    0    1   linear       // Dry/wet mix for parallel compression
// @param warmth      0.3  0    1   linear       // VCA warmth: adds subtle even harmonics for analog character
// @param output      0    -12  6   linear dB    // Output gain (auto-makeup is applied separately)

class Processor {
  p = {threshold: -10, ratio: 2, attack: 10, release: 100, mix: 1, warmth: 0.3, output: 0}
  sr = 44100
  outGain = 1

  // Envelope detector (peak detector with attack/release)
  env = 0
  makeupGain = 1

  // Warmth (subtle saturation)
  warmthState = 0

  paramChanged(name, value) {
    if (name === 'threshold') this.p.threshold = value
    if (name === 'ratio') this.p.ratio = Math.round(value)
    if (name === 'attack') this.p.attack = value
    if (name === 'release') this.p.release = value
    if (name === 'warmth') this.p.warmth = value
    if (name === 'output') {
      this.p.output = value
      this.outGain = Math.pow(10, value / 20)
    }
    // Auto makeup: compensate for gain reduction at threshold
    if (name === 'threshold' || name === 'ratio') {
      // Estimate makeup: gain reduction at 0dB input = ratio-dependent
      const ratio = this.p.ratio
      const thresh = this.p.threshold
      // At 0dB input, gain reduction = (0 - thresh) * (1 - 1/ratio)
      const gr = Math.max(0, (0 - thresh)) * (1 - 1/ratio)
      this.makeupGain = Math.pow(10, gr / 20)
    }
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    if (input.length < 1) return

    const threshold = this.p.threshold
    const ratio = this.p.ratio
    const attackMs = this.p.attack
    const releaseMs = this.p.release
    const mix = this.p.mix
    const warmth = this.p.warmth
    const outGain = this.outGain
    const makeup = this.makeupGain

    // Attack/release coefficients (per-sample)
    const attackCoef = Math.exp(-1 / (attackMs * 0.001 * this.sr))
    const releaseCoef = Math.exp(-1 / (releaseMs * 0.001 * this.sr))

    const numCh = input.length
    const numFrames = input[0].length

    for (let i = 0; i < numFrames; i++) {
      // Peak detect across all channels
      let maxSample = 0
      for (let ch = 0; ch < numCh; ch++) {
        const s = Math.abs(input[ch][i])
        if (s > maxSample) maxSample = s
      }

      // Convert to dB
      const inputDb = 20 * Math.log10(maxSample + 1e-10)

      // Envelope follower
      if (inputDb > this.env) {
        this.env = attackCoef * this.env + (1 - attackCoef) * inputDb
      } else {
        this.env = releaseCoef * this.env + (1 - releaseCoef) * inputDb
      }

      // Gain reduction
      let gr = 0
      if (this.env > threshold) {
        const over = this.env - threshold
        gr = over * (1 - 1/ratio)
      }

      // Gain in linear
      const gainLinear = Math.pow(10, -gr / 20) * makeup * outGain

      // Apply to all channels
      for (let ch = 0; ch < numCh; ch++) {
        const dry = input[ch][i]
        const wet = dry * gainLinear

        // Warmth: subtle even-harmonic saturation (soft clip)
        let warm = wet
        if (warmth > 0) {
          this.warmthState = 0.99 * this.warmthState + 0.01 * wet
          warm = wet + warmth * 0.15 * Math.tanh(wet - this.warmthState) * 2
        }

        // Dry/wet mix
        output[ch][i] = dry * (1 - mix) + warm * mix
      }
    }
  }
}
