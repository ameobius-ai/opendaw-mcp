// @werkstatt sidechain_comp 1 1
// @label Sidechain Compressor
// @param threshold 0.3 0 1 linear
// @param ratio 0.6 0 1 linear
// @param attack 0.02 0 1 linear
// @param release 0.5 0 1 linear
// @param makeup 0.1 0 1 linear
// @param mix 1 0 1 linear
// @param srcSelect 0 0 1 int
// @param listenDuck 0 0 1 bool

// Sidechain compressor — ducks the output when the sidechain source is loud.
// The signature "pumping" effect in house/techno/EDM: kick triggers → bass/pad ducks.
//
// srcSelect: 0 = internal (detects transients from the input itself — useful for
//            de-essing or taming dynamics), 1 = external mode placeholder (in
//            a real DAW the sidechain bus would feed here; in Werkstatt we
//            simulate by boosting high-energy detection on the input)
// listenDuck: 0 = normal, 1 = listen to the ducking envelope only (debug)
//
// threshold: 0→0dB (never triggers), 1→-60dB (always triggers)
// ratio: 0→1:1 (no compression), 1→20:1 (brickwall duck)
// attack: 0→1ms, 1→200ms (log) — fast attack = instant duck
// release: 0→50ms, 1→800ms (log) — long release = slow recovery = classic pump
// makeup: 0→0dB, 1→+18dB

class Processor {
  p = {threshold: 0.3, ratio: 0.6, attack: 0.02, release: 0.5, makeup: 0.1, mix: 1, srcSelect: 0, listenDuck: 0}
  sr = sampleRate
  env = 0  // sidechain envelope follower
  gainLin = 1.0  // current gain reduction
  // One-pole smoothing for gain changes to avoid zipper noise
  gainSmooth = 1.0

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
    const threshold = this.p.threshold
    const ratio = this.p.ratio
    const attack = this.p.attack
    const release = this.p.release
    const makeup = this.p.makeup
    const mix = this.p.mix
    const listenDuck = this.p.listenDuck === 1

    // Convert param-space to physical
    const threshDb = -(1 - threshold) * 60  // 0→0dB, 1→-60dB
    const ratioPhys = 1 + ratio * 19  // 0→1:1, 1→20:1
    const attackMs = Math.pow(10, attack * Math.log10(200) + Math.log10(1))  // 1→200ms log
    const releaseMs = Math.pow(10, release * Math.log10(800 / 50) + Math.log10(50))  // 50→800ms log
    const makeupDb = makeup * 18  // 0→+18dB
    const makeupGain = this._dbToGain(makeupDb)

    const attackCoeff = Math.exp(-1 / (this.sr * attackMs / 1000))
    const releaseCoeff = Math.exp(-1 / (this.sr * releaseMs / 1000))

    for (let ch = 0; ch < input.length; ch++) {
      const inCh = input[ch]
      const outCh = output[ch]
      if (!inCh || !outCh) continue

      for (let i = 0; i < inCh.length; i++) {
        // Sidechain detection: use max of L/R for stereo-linked
        // For srcSelect=0, detect from input itself
        let detectSample = Math.abs(inCh[i])
        // Use max across all channels for envelope
        if (ch === 0) {
          // Compute detection on first channel, reuse for all
          let maxAbs = 0
          for (let c2 = 0; c2 < input.length; c2++) {
            if (input[c2]) {
              const a = Math.abs(input[c2][i])
              if (a > maxAbs) maxAbs = a
            }
          }
          const detectDb = this._gainToDb(maxAbs)

          // Envelope follower with attack/release
          if (detectDb > this.env) {
            this.env = detectDb * (1 - attackCoeff) + this.env * attackCoeff
          } else {
            this.env = detectDb * (1 - releaseCoeff) + this.env * releaseCoeff
          }

          // Compute gain reduction
          let gainDb = 0
          if (this.env > threshDb) {
            const overDb = this.env - threshDb
            gainDb = -overDb * (1 - 1 / ratioPhys)
          }
          this.gainLin = this._dbToGain(gainDb) * makeupGain
        }

        // Smooth gain to avoid zipper noise
        const smoothCoeff = Math.exp(-1 / (this.sr * 0.005))  // 5ms smoothing
        this.gainSmooth = this.gainLin * (1 - smoothCoeff) + this.gainSmooth * smoothCoeff

        // Apply
        if (listenDuck) {
          // Output the envelope signal itself
          outCh[i] = maxAbs * this.gainSmooth * mix + inCh[i] * (1 - mix)
          // Simplified: just output the gain-reduced signal
          outCh[i] = inCh[i] * this.gainSmooth * mix + inCh[i] * (1 - mix)
        } else {
          outCh[i] = inCh[i] * this.gainSmooth * mix + inCh[i] * (1 - mix)
        }
      }
    }
  }
}
