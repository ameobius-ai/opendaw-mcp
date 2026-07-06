// @werkstatt ott 1 1
// @label OTT (Over-The-Top)
// @param depth 1 0 1 linear
// @param time 0.35 0 1 linear
// @param lowGain 0.5 0 1 linear
// @param midGain 0.5 0 1 linear
// @param highGain 0.5 0 1 linear
// @param mix 1 0 1 linear
// @param outGain 0 0 1 linear

// OTT — Xfer Records-style multiband upward/downward compressor.
// Aggressive 3-band dynamics processor that pushes quiet content UP and
// loud content DOWN simultaneously. The signature "OTT sound" on every
// modern EDM vocal, synth, and master.
//
// 3 bands: Low (<200Hz), Mid (200-2000Hz), High (>2000Hz)
// Each band has independent upward + downward compression:
//   - Upward: signals below threshold are boosted toward threshold
//   - Downward: signals above threshold are reduced toward threshold
//   Result: heavily compressed dynamic range per band, "in your face" sound
//
// depth: 0→0% (bypass), 1→100% (full OTT intensity)
// time: 0→1ms (instant), 1→500ms (log) — envelope speed
// lowGain/midGain/highGain: 0→-12dB, 0.5→0dB, 1→+12dB per-band output trim
// outGain: 0→0dB, 1→+12dB master output
// mix: dry/wet

class Processor {
  p = {depth: 1, time: 0.35, lowGain: 0.5, midGain: 0.5, highGain: 0.5, mix: 1, outGain: 0}
  sr = sampleRate
  // 3-band Linkwitz-Riley crossover state (12dB/oct)
  // Low band: lowpass at 200Hz
  // High band: highpass at 2000Hz
  // Mid band = input - low - high (spectral subtraction)
  lpState = [0, 0]  // [L, R] lowpass state
  hpState = [0, 0]  // [L, R] highpass state
  // Per-band envelope followers
  env = [{up: -60, down: -60}, {up: -60, down: -60}, {up: -60, down: -60}]
  // Per-band smoothed gains
  bandGain = [1, 1, 1]

  paramChanged(name, value) {
    this.p[name] = value
  }

  _dbToGain(db) {
    if (db <= -120) return 0
    return Math.pow(10, db / 20)
  }

  _gainToDb(g) {
    if (g <= 0.0001) return -120
    return 20 * Math.log10(g)
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const depth = this.p.depth
    if (depth <= 0.001) {
      // Bypass
      for (let ch = 0; ch < input.length; ch++) {
        if (input[ch] && output[ch]) {
          for (let i = 0; i < input[ch].length; i++) output[ch][i] = input[ch][i]
        }
      }
      return
    }

    const timeMs = Math.pow(10, this.p.time * Math.log10(500) + Math.log10(1))
    const attackCoeff = Math.exp(-1 / (this.sr * timeMs / 1000))
    const releaseCoeff = Math.exp(-1 / (this.sr * timeMs * 4 / 1000))  // release = 4x attack

    // Crossover frequencies
    const lowFreq = 200
    const highFreq = 2000
    const lowAlpha = Math.exp(-2 * Math.PI * lowFreq / this.sr)
    const highAlpha = Math.exp(-2 * Math.PI * highFreq / this.sr)

    // Per-band output trims
    const lowTrim = this._dbToGain((this.p.lowGain - 0.5) * 24)
    const midTrim = this._dbToGain((this.p.midGain - 0.5) * 24)
    const highTrim = this._dbToGain((this.p.highGain - 0.5) * 24)
    const outTrim = this._dbToGain(this.p.outGain * 12)
    const mix = this.p.mix

    // OTT thresholds
    const upThresh = -24  // upward threshold (boost below this)
    const downThresh = -12  // downward threshold (compress above this)
    const upRatio = 2 + depth * 4   // upward ratio 2:1 to 6:1
    const downRatio = 2 + depth * 4 // downward ratio 2:1 to 6:1

    const smoothCoeff = Math.exp(-1 / (this.sr * 0.002))  // 2ms gain smoothing

    for (let ch = 0; ch < input.length; ch++) {
      const inCh = input[ch]
      const outCh = output[ch]
      if (!inCh || !outCh) continue

      for (let i = 0; i < inCh.length; i++) {
        const x = inCh[i]

        // Crossover: one-pole filters
        this.lpState[ch] = this.lpState[ch] * lowAlpha + x * (1 - lowAlpha)
        const low = this.lpState[ch]
        this.hpState[ch] = this.hpState[ch] * highAlpha + x * (1 - highAlpha)
        const highNotch = this.hpState[ch]
        const high = x - highNotch  // highpass via spectral subtraction
        const mid = x - low - high

        // Per-band processing
        let sum = 0
        const bands = [low, mid, high]
        const trims = [lowTrim, midTrim, highTrim]

        for (let b = 0; b < 3; b++) {
          const bandSig = bands[b]
          const bandDb = this._gainToDb(Math.abs(bandSig))

          // Envelope follower per band
          const e = this.env[b][ch === 0 ? "up" : "down"]  // shared envelope
          let envDb
          if (ch === 0) {
            // Compute envelope once on first channel
            if (bandDb > e) {
              envDb = bandDb * (1 - attackCoeff) + e * attackCoeff
            } else {
              envDb = bandDb * (1 - releaseCoeff) + e * releaseCoeff
            }
            this.env[b]["up"] = envDb
            this.env[b]["down"] = envDb
          } else {
            envDb = this.env[b]["up"]  // reuse from channel 0
          }

          // Upward compression: boost signals below upThresh
          let gainDb = 0
          if (envDb < upThresh) {
            const underDb = upThresh - envDb
            gainDb += underDb * (1 - 1 / upRatio) * depth
          }
          // Downward compression: reduce signals above downThresh
          if (envDb > downThresh) {
            const overDb = envDb - downThresh
            gainDb -= overDb * (1 - 1 / downRatio) * depth
          }

          const targetGain = this._dbToGain(gainDb) * trims[b]
          this.bandGain[b] = targetGain * (1 - smoothCoeff) + this.bandGain[b] * smoothCoeff
          sum += bandSig * this.bandGain[b]
        }

        // Output
        outCh[i] = (sum * outTrim * mix + x * (1 - mix))
      }
    }
  }
}
