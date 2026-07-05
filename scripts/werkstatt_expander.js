// @werkstatt expander 1 1
// @label Downward Expander
// @param threshold 0.7 0 1 linear
// @param ratio 0.4 0 1 linear
// @param attack 0.1 0 1 linear
// @param release 0.3 0 1 linear
// @param range 0.8 0 1 linear
// @param mix 1 0 1 linear
// @param knee 0.2 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {threshold: 0.7, ratio: 0.4, attack: 0.1, release: 0.3, range: 0.8, mix: 1, knee: 0.2, output: 0}
  sr = 44100
  envL = 0
  envR = 0
  outGain = 1

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  // threshold: 0→0 dB (loudest), 1→-60 dB (quietest) — inverted
  // ratio: 0→1:1 (no expansion), 1→20:1 (near-gate)
  // attack: 0→0.1ms, 1→100ms (logarithmic)
  // release: 0→50ms, 1→500ms (logarithmic)
  // range: 0→0 dB max attenuation, 1→-60 dB max attenuation (cap)
  // knee: 0→hard, 1→wide soft knee

  _dbToGain(db) {
    return Math.pow(10, db / 20)
  }

  _gainToDb(g) {
    return 20 * Math.log10(Math.max(g, 1e-10))
  }

  _msToCoeff(ms) {
    const tau = Math.max(ms / 1000, 1e-6)
    return 1 - Math.exp(-1 / (this.sr * tau))
  }

  // Downward expansion: signals BELOW threshold get attenuated
  // gain_reduction_db = (ratio-1) * (threshold - input) when input < threshold
  // Capped by range (max attenuation)
  _computeGainReduction(inputDb, threshDb, ratioNum, kneeWidth, maxAttenDb) {
    // belowDb = how far below threshold (positive = below)
    const belowDb = threshDb - inputDb
    if (belowDb < -kneeWidth / 2) {
      // Above threshold + knee — no expansion, unity gain
      return 0
    } else if (belowDb > kneeWidth / 2) {
      // Well below threshold — full expansion
      let gr = belowDb * (ratioNum - 1)
      // Cap at max attenuation
      gr = Math.min(gr, maxAttenDb)
      return -gr
    } else {
      // Inside knee — quadratic blend
      const t = (belowDb + kneeWidth / 2) / kneeWidth
      let gr = belowDb * t * (ratioNum - 1) * 0.5
      gr = Math.min(gr, maxAttenDb)
      return -gr
    }
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p

    // Convert params to physical units
    const threshDb = -p.threshold * 60  // 0→0 dB, 1→-60 dB
    const ratioNum = 1 + p.ratio * 19    // 1:1 → 20:1
    const attackMs = 0.1 + Math.pow(p.attack, 3) * 99.9
    const releaseMs = 50 + Math.pow(p.release, 3) * 450
    const maxAttenDb = -p.range * 60     // 0→0 dB, 1→-60 dB max attenuation
    const kneeWidth = p.knee * 12        // 0 → 12 dB soft knee
    const og = this.outGain

    const attackCoeff = this._msToCoeff(attackMs)
    const releaseCoeff = this._msToCoeff(releaseMs)

    const stereo = output.length > 1
    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]

    for (let i = 0; i < inL.length; i++) {
      // Peak detection
      const detL = Math.abs(inL[i])
      const detR = Math.abs(inR[i])
      const det = stereo ? Math.max(detL, detR) : detL

      // Convert to dB
      const detDb = this._gainToDb(det)

      // Compute target gain reduction (dB)
      // Expander: below threshold → attenuate
      // gain reduction is NEGATIVE (attenuation), 0 = unity
      const grDb = this._computeGainReduction(detDb, threshDb, ratioNum, kneeWidth, maxAttenDb)

      // Convert to gain scalar (0..1, where 1=unity, <1=attenuation)
      const targetGain = this._dbToGain(grDb)

      // Smooth envelope: attack for gain decreasing, release for recovering
      let env = stereo ? Math.min(this.envL, this.envR) : this.envL
      if (targetGain < env) {
        // Gain is reducing (signal went below threshold) — attack
        env = env + (targetGain - env) * attackCoeff
      } else {
        // Gain is recovering (signal went above threshold) — release
        env = env + (targetGain - env) * releaseCoeff
      }

      // Apply gain + output + dry/wet
      const wet = inL[i] * env * og
      outL[i] = (inL[i] * (1 - p.mix)) + (wet * p.mix)

      if (stereo) {
        const wetR = inR[i] * env * og
        outR[i] = (inR[i] * (1 - p.mix)) + (wetR * p.mix)
        this.envR = env
      }
      this.envL = env
    }
  }

  reset() {
    this.envL = 0
    this.envR = 0
  }
}
