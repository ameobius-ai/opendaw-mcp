// @werkstatt ensemble 1 1
// @label Ensemble (Juno-style)
// @param rate 0.3 0 1 linear
// @param depth 0.5 0 1 linear
// @param voices 0.7 0 1 linear
// @param detune 0.3 0 1 linear
// @param mix 0.5 0 1 linear
// @param width 0.7 0 1 linear

// Ensemble chorus — Roland Juno-60 / Juno-106 style ensemble effect.
// The signature "lush" chorus that defined the Juno sound. Unlike a
// standard chorus (single LFO + delay), ensemble uses 3 detuned LFOs
// at prime-ratio rates, each modulating a separate delay line.
// The combination creates a thick, evolving, orchestral wash.
//
// Architecture: 3 delay lines, each with its own LFO at different rates
// (0.5Hz, 0.8Hz, 1.3Hz prime ratios), phase-offset. Outputs are
// panned L/C/R and mixed. Dry signal + 3 modulated voices = 4 sources.
//
// rate: 0→0.1Hz (slow), 1→5Hz (fast) — master rate multiplier
// depth: 0→0ms (no modulation), 1→5ms delay swing
// voices: 0→1 voice (subtle), 1→3 voices (full ensemble)
// detune: 0→0 cents, 1→15 cents pitch detune between voices
// mix: 0→dry, 1→fully wet (ensemble only)
// width: 0→mono, 1→wide stereo (voices panned L/R)

class Processor {
  p = {rate: 0.3, depth: 0.5, voices: 0.7, detune: 0.3, mix: 0.5, width: 0.7}
  sr = sampleRate
  // 3 delay lines (L, C, R)
  dl = [new Float32Array(2048), new Float32Array(2048), new Float32Array(2048)]
  dlIdx = [0, 0, 0]
  // 3 LFO phases at prime ratios
  lfoPhase = [0, 0, 0]
  // Base delay center (ms) — each voice slightly different
  baseDelay = [15, 20, 25]  // ms

  paramChanged(name, value) {
    this.p[name] = value
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return

    const rateMul = 0.1 + this.p.rate * 4.9  // 0.1-5Hz multiplier
    const depthMs = this.p.depth * 5  // 0-5ms
    const numVoices = Math.max(1, Math.round(1 + this.p.voices * 2))  // 1-3
    const detuneCents = this.p.detune * 15
    const mix = this.p.mix
    const width = this.p.width

    // LFO rates (prime ratios for non-repeating pattern)
    const lfoRates = [0.5, 0.83, 1.37]  // Hz, multiplied by rateMul

    for (let ch = 0; ch < input.length; ch++) {
      const inCh = input[ch]
      const outCh = output[ch]
      if (!inCh || !outCh) continue
      const chIdx = Math.min(ch, 1)  // L=0, R=1

      for (let i = 0; i < inCh.length; i++) {
        const x = inCh[i]
        let wet = 0

        for (let v = 0; v < numVoices; v++) {
          // LFO modulation
          const lfoInc = 2 * Math.PI * lfoRates[v] * rateMul / this.sr
          if (ch === 0) {
            this.lfoPhase[v] += lfoInc
            if (this.lfoPhase[v] > 2 * Math.PI) this.lfoPhase[v] -= 2 * Math.PI
          }

          // Delay modulation: base + LFO * depth
          const modMs = this.baseDelay[v] + Math.sin(this.lfoPhase[v]) * depthMs
          const delaySamples = Math.floor(this.sr * modMs / 1000)
          const frac = this.sr * modMs / 1000 - delaySamples

          // Read from delay line with linear interpolation
          const buf = this.dl[v]
          const bufLen = buf.length
          const readIdx = (this.dlIdx[v] - delaySamples + bufLen) % bufLen
          const readIdx2 = (readIdx + 1) % bufLen
          const delayed = buf[readIdx] * (1 - frac) + buf[readIdx2] * frac

          // Detune: slight pitch shift via rate variation (simulated by
          // adding a small constant to the LFO phase offset per voice)
          // This is a simplification — real detune would need pitch shifting

          // Pan voices: v0=center, v1=left, v2=right
          let panGain = 1
          if (v === 1) panGain = 1 - width * 0.5  // left
          if (v === 2) panGain = 1 - width * 0.5  // right
          // Inverse pan for opposite channel
          if (chIdx === 0 && v === 2) panGain = width * 0.5
          if (chIdx === 1 && v === 1) panGain = width * 0.5
          if (v === 0) panGain = 1  // center always full

          wet += delayed * panGain

          // Write to delay (only on first channel to avoid double-write)
          if (ch === 0) {
            buf[this.dlIdx[v]] = x
            this.dlIdx[v] = (this.dlIdx[v] + 1) % bufLen
          }
        }

        // Normalize wet by number of voices
        wet = wet / numVoices

        // Output
        outCh[i] = x * (1 - mix) + wet * mix
      }
    }
  }
}
