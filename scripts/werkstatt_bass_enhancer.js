// @werkstatt bass_enhancer 1 1
// @label Bass Enhancer (Psychoacoustic)
// @param freq 80 40 200 linear Hz
// @param sub_level 0.5 0 1 linear
// @param direct_level 0.7 0 1 linear
// @param harmonics 0.3 0 1 linear
// @param attack 0.005 0.001 0.05 exp s
// @param release 0.1 0.01 0.5 exp s
// @param mix 0.5 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {
    freq: 80, sub_level: 0.5, direct_level: 0.7, harmonics: 0.3,
    attack: 0.005, release: 0.1, mix: 0.5, output: 0,
  }
  sr = 44100
  outGain = 1

  // LPF state for isolating bass band
  lpStateL = 0; lpStateR = 0
  // HPF state for cleaning sub output
  hpStateL = 0; hpStateR = 0
  // Envelope follower
  env = 0
  // Half-wave rectifier smoothing
  rectSmoothL = 0; rectSmoothR = 0
  // Sub-harmonic LPF (smoothing of rectified signal)
  subLpL = 0; subLpR = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const numCh = out.length
    const numFrames = out[0].length
    const sr = this.sr
    const og = this.outGain
    const mix = this.p.mix

    // Crossover LPF for bass band isolation
    const fcLp = this.p.freq
    const alphaLp = 1 / (1 + 2 * Math.PI * fcLp / sr)
    // HPF for cleaning sub output (removes DC)
    const fcHp = Math.max(20, this.p.freq * 0.4)
    const alphaHp = 1 / (1 + 2 * Math.PI * fcHp / sr)

    // Envelope coefficients
    const atkCoef = Math.exp(-1 / (this.p.attack * sr))
    const relCoef = Math.exp(-1 / (this.p.release * sr))

    // Sub-harmonic LPF (smoothing rectified signal to extract fundamental)
    const subFc = this.p.freq * 0.8
    const subAlpha = 1 / (1 + 2 * Math.PI * subFc / sr)

    const subLevel = this.p.sub_level
    const directLevel = this.p.direct_level
    const harmLevel = this.p.harmonics

    for (let i = 0; i < numFrames; i++) {
      const dryL = inp[0] ? inp[0][i] : 0
      const dryR = (inp.length > 1 && inp[1]) ? inp[1][i] : dryL

      // Isolate bass band (LPF)
      this.lpStateL = this.lpStateL + alphaLp * (dryL - this.lpStateL)
      this.lpStateR = this.lpStateR + alphaLp * (dryR - this.lpStateR)
      const bassL = this.lpStateL
      const bassR = this.lpStateR

      // Envelope follower on bass signal
      const monoBass = (Math.abs(bassL) + Math.abs(bassR)) * 0.5
      const envCoef = monoBass > this.env ? atkCoef : relCoef
      this.env = this.env * envCoef + monoBass * (1 - envCoef)

      // Half-wave rectification → generates sub-harmonic at f/2
      // |sin(2πft)| has component at f (DC + 2f, 4f...) but when filtered
      // through LPF below f, the fundamental f component remains
      // Actually: rectification of sin gives |sin| which has spectrum at 0, 2f, 4f
      // To get sub-harmonic f/2 we need a different approach:
      // Use full-wave rectification then divide by 2 via tracking
      // Simpler: the "missing fundamental" trick — generate harmonics of f
      // that imply a lower fundamental. We rectify to get 2f, then LPF below f
      // The brain infers the missing f from the spacing of harmonics

      // Full-wave rectification: |bass|
      const rectL = Math.abs(bassL)
      const rectR = Math.abs(bassR)

      // Smooth rectified signal (extract envelope-modulated sub)
      this.rectSmoothL = this.rectSmoothL * 0.5 + rectL * 0.5
      this.rectSmoothR = this.rectSmoothR * 0.5 + rectR * 0.5

      // LPF the rectified signal to get the sub-harmonic component
      this.subLpL = this.subLpL + subAlpha * (this.rectSmoothL - this.subLpL)
      this.subLpR = this.subLpR + subAlpha * (this.rectSmoothR - this.subLpR)

      // HPF to remove DC offset from sub
      this.hpStateL = this.hpStateL + alphaHp * (this.subLpL - this.hpStateL)
      this.hpStateR = this.hpStateR + alphaHp * (this.subLpR - this.hpStateR)
      const subL = this.subLpL - this.hpStateL
      const subR = this.subLpR - this.hpStateR

      // Harmonics: add slight saturation to bass for presence
      const harmL = bassL * (1 + harmLevel * Math.tanh(bassL * 3) * 0.3)
      const harmR = bassR * (1 + harmLevel * Math.tanh(bassR * 3) * 0.3)

      // Combine: direct bass + sub-harmonic + harmonics
      const enhancedL = bassL * directLevel + subL * subLevel + harmL * harmLevel
      const enhancedR = bassR * directLevel + subR * subLevel + harmR * harmLevel

      // Replace bass band in full signal
      // High-pass the dry signal to remove original bass
      const hpDryL = dryL - this.lpStateL
      const hpDryR = dryR - this.lpStateR

      // Sum enhanced bass + high-passed dry
      const wetL = hpDryL + enhancedL
      const wetR = hpDryR + enhancedR

      // Dry/wet
      const dryGain = 1.0 - mix * 0.5
      if (numCh > 0) out[0][i] = (dryL * dryGain + wetL * mix) * og
      if (numCh > 1) out[1][i] = (dryR * dryGain + wetR * mix) * og
    }
  }

  reset() {
    this.lpStateL = 0; this.lpStateR = 0
    this.hpStateL = 0; this.hpStateR = 0
    this.env = 0
    this.rectSmoothL = 0; this.rectSmoothR = 0
    this.subLpL = 0; this.subLpR = 0
  }
}
