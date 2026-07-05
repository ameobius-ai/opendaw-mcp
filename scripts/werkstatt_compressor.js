// @werkstatt compressor 1 1
// @label Compressor
// @param threshold 0.5 0 1 linear
// @param ratio 0.4 0 1 linear
// @param attack 0.1 0 1 linear
// @param release 0.3 0 1 linear
// @param makeup 0 0 1 linear
// @param mix 1 0 1 linear
// @param knee 0.2 0 1 linear

class Processor {
  p = {threshold: 0.5, ratio: 0.4, attack: 0.1, release: 0.3, makeup: 0, mix: 1, knee: 0.2}
  sr = sampleRate
  // Per-channel envelope state
  envL = 0
  envR = 0

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Convert param-space to physical units
  // threshold: 0→0 dB (loudest), 1→-60 dB (quietest) — inverted so "high" = more compression
  // ratio: 0→1:1, 1→20:1
  // attack: 0→0.1ms, 1→100ms (logarithmic)
  // release: 0→50ms, 1→500ms (logarithmic)
  // makeup: 0→0 dB, 1→+24 dB
  // knee: 0→hard, 1→wide soft knee

  _dbToGain(db) {
    return Math.pow(10, db / 20)
  }

  _gainToDb(g) {
    return 20 * Math.log10(Math.max(g, 1e-10))
  }

  _msToCoeff(ms) {
    // Time constant for one-pole smoother
    // tau = ms/1000, alpha = 1 - exp(-1/(sr*tau))
    const tau = Math.max(ms / 1000, 1e-6)
    return 1 - Math.exp(-1 / (this.sr * tau))
  }

  _computeGain(inputDb, threshDb, ratioNum, kneeWidth) {
    // Soft-knee compression curve
    // kneeWidth in dB (0 = hard knee)
    const overDb = inputDb - threshDb
    if (overDb < -kneeWidth / 2) {
      // Below knee — no compression
      return 0
    } else if (overDb > kneeWidth / 2) {
      // Above knee — full compression
      return -overDb * (1 - 1 / ratioNum)
    } else {
      // Inside knee — quadratic blend
      const t = (overDb + kneeWidth / 2) / kneeWidth
      const reduction = overDb * t * (1 - 1 / ratioNum) * 0.5
      return -reduction
    }
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p

    // Convert params to physical units
    const threshDb = -p.threshold * 60  // 0→0 dB, 1→-60 dB
    const ratioNum = 1 + p.ratio * 19    // 1:1 → 20:1
    const attackMs = 0.1 + Math.pow(p.attack, 3) * 99.9  // ~0.1ms → 100ms
    const releaseMs = 50 + Math.pow(p.release, 3) * 450   // 50ms → 500ms
    const makeupDb = p.makeup * 24        // 0 → +24 dB
    const kneeWidth = p.knee * 12         // 0 → 12 dB soft knee
    const makeupGain = this._dbToGain(makeupDb)

    const attackCoeff = this._msToCoeff(attackMs)
    const releaseCoeff = this._msToCoeff(releaseMs)

    const stereo = output.length > 1
    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]

    for (let i = 0; i < inL.length; i++) {
      // Peak detection (absolute value)
      const detL = Math.abs(inL[i])
      const detR = Math.abs(inR[i])
      const det = stereo ? Math.max(detL, detR) : detL

      // Convert to dB
      const detDb = this._gainToDb(det)

      // Compute target gain reduction (dB)
      const grDb = this._computeGain(detDb, threshDb, ratioNum, kneeWidth)

      // Convert reduction dB to gain scalar
      const targetGain = this._dbToGain(grDb)

      // Smooth envelope: attack for decreasing gain, release for recovering
      let env = stereo ? Math.min(this.envL, this.envR) : this.envL
      if (targetGain < env) {
        // Gain is reducing — use attack
        env = env + (targetGain - env) * attackCoeff
      } else {
        // Gain is recovering — use release
        env = env + (targetGain - env) * releaseCoeff
      }

      // Apply gain + makeup + dry/wet
      const wet = inL[i] * env * makeupGain
      outL[i] = (inL[i] * (1 - p.mix)) + (wet * p.mix)

      if (stereo) {
        const wetR = inR[i] * env * makeupGain
        outR[i] = (inR[i] * (1 - p.mix)) + (wetR * p.mix)
        this.envR = env
      }
      this.envL = env
    }
  }
}
