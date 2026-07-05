// @werkstatt rotary_speaker 1 1
// @label Rotary Speaker (Leslie)
// @param speed 0.3 0 1 linear
// @param depth 0.5 0 1 linear
// @param crossover 800 200 4000 exp Hz
// @param horn_level 0.7 0 1 linear
// @param rotor_level 0.5 0 1 linear
// @param acceleration 0.3 0 1 linear
// @param mix 1 0 1 linear

class Processor {
  p = {speed: 0.3, depth: 0.5, crossover: 800, horn_level: 0.7, rotor_level: 0.5, acceleration: 0.3, mix: 1}
  sr = sampleRate

  // Horn rotor state (high freq rotor)
  hornPhaseL = 0
  hornPhaseR = 0
  hornAmplitudeL = 0
  hornAmplitudeR = 0
  hornCurrentRate = 0

  // Rotor state (low freq rotor)
  rotorPhaseL = 0
  rotorPhaseR = 0
  rotorCurrentRate = 0

  // Crossover filter state (simple one-pole)
  lpStateL = 0
  lpStateR = 0

  // Delay buffer for Doppler effect
  delayBufL = null
  delayBufR = null
  delayWritePos = 0
  delayMaxLen = 256

  paramChanged(name, value) {
    this.p[name] = value
  }

  _init() {
    if (!this.delayBufL) {
      this.delayBufL = new Float32Array(this.delayMaxLen)
      this.delayBufR = new Float32Array(this.delayMaxLen)
    }
  }

  processAudio(inputs, outputs, parameters) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return
    this._init()

    const sr = this.sr
    const p = this.p

    // Target rates: speed=0 → slow (~48 RPM = 0.8 Hz), speed=1 → fast (~400 RPM = 6.67 Hz)
    const slowRate = 0.8
    const fastRate = 6.67
    const targetHornRate = slowRate + (fastRate - slowRate) * p.speed
    // Rotor spins slower than horn (typical Leslie: horn 6.67 Hz fast, rotor 6 Hz fast)
    const targetRotorRate = targetHornRate * 0.7

    // Acceleration: how fast rate changes (0 = instant, 1 = slow ramp)
    const accelFactor = 1 - p.acceleration * 0.95
    this.hornCurrentRate += (targetHornRate - this.hornCurrentRate) * accelFactor * 0.001
    this.rotorCurrentRate += (targetRotorRate - this.rotorCurrentRate) * accelFactor * 0.001

    const hornOmega = 2 * Math.PI * this.hornCurrentRate / sr
    const rotorOmega = 2 * Math.PI * this.rotorCurrentRate / sr

    // Crossover coefficient
    const fc = Math.min(0.49, p.crossover / (sr * 0.5))
    const lpAlpha = Math.exp(-2 * Math.PI * fc)

    // Doppler delay range (depth controls modulation amount)
    const maxDelay = Math.floor(0.003 * sr * p.depth) // up to 3ms at depth=1
    const minDelay = 1

    for (let i = 0; i < out[0].length; i++) {
      // Get input (mono or stereo)
      const inL = (inp[0] && inp[0][i]) || 0
      const inR = (inp[1] && inp[1][i]) || inL
      const inMono = (inL + inR) * 0.5

      // Crossover split
      this.lpStateL += (1 - lpAlpha) * (inL - this.lpStateL)
      this.lpStateR += (1 - lpAlpha) * (inR - this.lpStateR)
      const lowL = this.lpStateL
      const lowR = this.lpStateR
      const highL = inL - lowL
      const highR = inR - lowR

      // Advance phases
      this.hornPhaseL += hornOmega
      this.hornPhaseR += hornOmega + Math.PI // opposite phase for stereo
      this.rotorPhaseL += rotorOmega
      this.rotorPhaseR += rotorOmega + Math.PI

      // --- Horn (high rotor): Doppler pitch shift + amplitude modulation ---
      // Doppler delay: cos(phase) controls delay amount
      const hornDelayL = Math.floor(minDelay + (maxDelay * 0.5 + maxDelay * 0.5 * Math.cos(this.hornPhaseL)))
      const hornDelayR = Math.floor(minDelay + (maxDelay * 0.5 + maxDelay * 0.5 * Math.cos(this.hornPhaseR)))

      // Write to delay buffer (mono high signal)
      this.delayBufL[this.delayWritePos] = highL
      this.delayBufR[this.delayWritePos] = highR

      // Read with Doppler delay
      const readPosL = (this.delayWritePos - hornDelayL + this.delayMaxLen) % this.delayMaxLen
      const readPosR = (this.delayWritePos - hornDelayR + this.delayMaxLen) % this.delayMaxLen
      const dopplerL = this.delayBufL[readPosL]
      const dopplerR = this.delayBufR[readPosR]

      // Amplitude modulation (rotor directivity)
      const ampModL = (1 + Math.cos(this.hornPhaseL)) * 0.5
      const ampModR = (1 + Math.cos(this.hornPhaseR)) * 0.5
      const hornOutL = dopplerL * ampModL * p.horn_level * (1 + p.depth)
      const hornOutR = dopplerR * ampModR * p.horn_level * (1 + p.depth)

      this.delayWritePos = (this.delayWritePos + 1) % this.delayMaxLen

      // --- Rotor (low rotor): amplitude modulation only (no Doppler for bass) ---
      const rotorAmpL = (1 + Math.cos(this.rotorPhaseL)) * 0.5
      const rotorAmpR = (1 + Math.cos(this.rotorPhaseR)) * 0.5
      const rotorOutL = lowL * (0.5 + rotorAmpL * 0.5) * p.rotor_level
      const rotorOutR = lowR * (0.5 + rotorAmpR * 0.5) * p.rotor_level

      // Mix: horn + rotor
      const wetL = hornOutL + rotorOutL
      const wetR = hornOutR + rotorOutR

      // Dry/wet
      if (out[0]) out[0][i] = wetL * p.mix + inL * (1 - p.mix)
      if (out[1]) out[1][i] = wetR * p.mix + inR * (1 - p.mix)
    }
  }
}
