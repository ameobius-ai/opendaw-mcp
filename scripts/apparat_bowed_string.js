// @apparat bowed_string 1 1
// @label Bowed String (Waveguide + Bow Friction)
// @param bow_pressure 0.5 0 1 linear
// @param bow_speed 0.3 0 1 linear
// @param bow_position 0.3 0 0.5 linear
// @param freq 220 50 2000 exp Hz
// @param brightness 0.5 0 1 linear
// @param body_resonance 0.3 0 1 linear
// @param vibrato_rate 0 0 10 linear Hz
// @param vibrato_depth 0 0 1 linear
// @param volume 0.7 0 1 linear

class Processor {
  p = {bow_pressure: 0.5, bow_speed: 0.3, bow_position: 0.3, freq: 220,
       brightness: 0.5, body_resonance: 0.3, vibrato_rate: 0, vibrato_depth: 0, volume: 0.7}
  sr = 44100

  // Digital waveguide: two delay lines (left-going and right-going waves)
  // Total delay = sr/freq samples, split at bow position
  waveBufL = null
  waveBufR = null
  waveLenL = 0
  waveLenR = 0
  wavePosL = 0
  wavePosR = 0

  // Bow friction state
  bowForce = 0

  // String damping filter (one-pole LP in the waveguide loop)
  dampState = 0

  // Body resonator — 3 simple resonators (formant-like)
  body1_z1 = 0; body1_z2 = 0
  body2_z1 = 0; body2_z2 = 0
  body3_z1 = 0; body3_z2 = 0

  // Vibrato
  vibPhase = 0

  // Previous bow velocity for friction model
  prevVstring = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    this._updateWaveguide(220)
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "freq") {
      this._updateWaveguide(value)
    }
  }

  _updateWaveguide(freq) {
    const totalDelay = Math.max(2, this.sr / Math.max(freq, 20))
    // Bow position splits the string: L = bow to nut, R = bow to bridge
    const bp = this.p ? this.p.bow_position : 0.3
    this.waveLenL = Math.max(1, Math.floor(totalDelay * bp))
    this.waveLenR = Math.max(1, Math.floor(totalDelay * (1 - bp)))
    this.waveBufL = new Float32Array(this.waveLenL)
    this.waveBufR = new Float32Array(this.waveLenR)
    this.wavePosL = 0
    this.wavePosR = 0
  }

  // Bow friction model: velocity-dependent stick-slip
  // When string velocity ≈ bow velocity → sticking (high friction)
  // When string velocity ≠ bow velocity → sliding (low friction)
  // Stribeck curve: friction decreases as relative velocity increases
  _bowFriction(vString, vBow, pressure) {
    const vRel = vString - vBow // relative velocity
    // Stribeck: mu = mu_s * exp(-|vRel|/v_ref) + mu_d
    // Simplified: friction = pressure * (exp(-|vRel| * k) + 0.2)
    const k = 80 // friction sharpness
    const muStatic = 0.8
    const muDynamic = 0.2
    const friction = pressure * (muStatic * Math.exp(-Math.abs(vRel) * k) + muDynamic)
    // Friction force opposes relative motion
    return -friction * Math.sign(vRel) * 0.5
  }

  // One-pole lowpass for string damping (waveguide loop filter)
  _dampFilter(input, brightness) {
    const coeff = 0.5 + brightness * 0.49 // 0.5=dull, 0.99=bright
    this.dampState = this.dampState + (input - this.dampState) * coeff
    return this.dampState
  }

  // Biquad resonator for body
  _resonate(x, z1, z2, freq, q) {
    const w0 = 2 * Math.PI * freq / this.sr
    const alpha = Math.sin(w0) / (2 * q)
    const b0 = alpha
    const b1 = 0
    const b2 = -alpha
    const a0 = 1 + alpha
    const a1 = -2 * Math.cos(w0)
    const a2 = 1 - alpha
    const y = (b0 * x + b2 * z2) / a0 - (a1 * z1 + a2 * z2) / a0
    return [y, y, z1]
  }

  processAudio(inputs, outputs) {
    const output = outputs[0]
    if (!output) return
    const p = this.p
    const outL = output[0]
    const outR = output[1] || output[0]
    const numFrames = outL.length

    // Update waveguide if freq changed
    this._updateWaveguide(p.freq)

    // Vibrato
    const vibRate = p.vibrato_rate
    const vibDepth = p.vibrato_depth * 0.02 // semitones
    const vibInc = 2 * Math.PI * vibRate / this.sr

    // Bow parameters
    const bowVel = (p.bow_speed - 0.5) * 0.4 // bow velocity, centered at 0
    const bowPress = p.bow_pressure * 0.8

    // Body resonator frequencies (violin-like)
    const bodyFreqs = [280, 450, 650]
    const bodyQ = 8

    for (let i = 0; i < numFrames; i++) {
      // Vibrato: modulate frequency
      const vibCents = Math.sin(this.vibPhase) * vibDepth
      const actualFreq = p.freq * Math.pow(2, vibCents / 12)
      // Update waveguide length for vibrato (simplified — just adjust R length)
      const totalDelay = this.sr / actualFreq
      const targetLenR = Math.max(1, Math.floor(totalDelay * (1 - p.bow_position)))
      // Lagrange interpolation would be ideal, but we'll use simple rounding
      this.vibPhase += vibInc

      // --- 1. Read from waveguide ends ---
      // Right-going wave at bow point (from L side, traveling right)
      const waveR = this.waveBufL[this.wavePosL] // wave arriving at bow from nut side
      // Left-going wave at bow point (from R side, traveling left)
      const waveL = this.waveBufR[this.wavePosR] // wave arriving at bow from bridge side

      // String velocity at bow point = waveR - waveL (velocity = right wave - left wave)
      const vString = waveR - waveL
      this.prevVstring = vString

      // --- 2. Bow friction interaction ---
      const frictionForce = this._bowFriction(vString, bowVel, bowPress)

      // New waves injected into both directions from bow point
      // The bow adds a velocity impulse split equally into both waveguides
      const newWaveR = waveR + frictionForce * 0.5
      const newWaveL = waveL - frictionForce * 0.5

      // --- 3. Advance waveguides with damping filter ---
      // Left waveguide: wave travels from bow toward nut, reflects, returns
      // Simple model: delay line + damping filter at the end
      const dampR = this._dampFilter(newWaveR, p.brightness)
      this.wavePosL = (this.wavePosL + 1) % this.waveLenL
      this.waveBufL[this.wavePosL] = dampR // write damped wave back (reflection)

      // Right waveguide: wave travels from bow toward bridge
      const dampL = this._dampFilter(newWaveL, p.brightness)
      this.wavePosR = (this.wavePosR + 1) % this.waveLenR
      this.waveBufR[this.wavePosR] = dampL

      // --- 4. Bridge output: read from right waveguide end (near bridge) ---
      // The bridge pickup is at the end of the R waveguide
      const bridgeOut = this.waveBufR[(this.wavePosR + 1) % this.waveLenR]

      // --- 5. Body resonator ---
      let bodyOut = bridgeOut
      if (p.body_resonance > 0.01) {
        const [b1, bz1, bz2] = this._resonate(bridgeOut, this.body1_z1, this.body1_z2, bodyFreqs[0], bodyQ)
        this.body1_z1 = bz1; this.body1_z2 = bz2
        const [b2, bz1b, bz2b] = this._resonate(b1, this.body2_z1, this.body2_z2, bodyFreqs[1], bodyQ)
        this.body2_z1 = bz1b; this.body2_z2 = bz2b
        const [b3, bz1c, bz2c] = this._resonate(b2, this.body3_z1, this.body3_z2, bodyFreqs[2], bodyQ)
        this.body3_z1 = bz1c; this.body3_z2 = bz2c
        bodyOut = bridgeOut * (1 - p.body_resonance) + b3 * p.body_resonance
      }

      // --- 6. Output ---
      const sample = bodyOut * p.volume * 3 // scale up
      outL[i] = sample
      outR[i] = sample
    }
  }

  noteOn(pitch, velocity) {
    // Convert MIDI pitch to frequency
    const freq = 440 * Math.pow(2, (pitch - 69) / 12)
    this._updateWaveguide(freq)
    // Reset waveguide with small noise to seed oscillation
    for (let i = 0; i < this.waveBufL.length; i++) {
      this.waveBufL[i] = (Math.random() - 0.5) * 0.01 * velocity
    }
    for (let i = 0; i < this.waveBufR.length; i++) {
      this.waveBufR[i] = (Math.random() - 0.5) * 0.01 * velocity
    }
    this.dampState = 0
    this.body1_z1 = 0; this.body1_z2 = 0
    this.body2_z1 = 0; this.body2_z2 = 0
    this.body3_z1 = 0; this.body3_z2 = 0
  }

  reset() {
    if (this.waveBufL) this.waveBufL.fill(0)
    if (this.waveBufR) this.waveBufR.fill(0)
    this.dampState = 0
    this.vibPhase = 0
    this.body1_z1 = 0; this.body1_z2 = 0
    this.body2_z1 = 0; this.body2_z2 = 0
    this.body3_z1 = 0; this.body3_z2 = 0
  }
}
