// @werkstatt binaural 1 1
// @label Binaural Spatial Panner
// @param azimuth 0 -180 180 linear
// @param elevation 0 -90 90 linear
// @param distance 1 0.1 10 exp
// @param head_size 0.5 0 1 linear
// @param room 0.3 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -12 6 linear dB

class Processor {
  p = {azimuth: 0, elevation: 0, distance: 1, head_size: 0.5, room: 0.3, mix: 1, output: 0}
  sr = 44100
  outGain = 1

  // ITD delay buffers — fractional delay per channel
  delayBufL = new Float32Array(64)
  delayBufR = new Float32Array(64)
  writePos = 0
  readPosL = 0
  readPosR = 0
  delaySamplesL = 0
  delaySamplesR = 0

  // ILD — frequency-dependent level via one-pole smoothing
  ildStateL = 0
  ildStateR = 0

  // Pinna/elevation spectral notches — 2 peaking filters per channel
  pinna1L_z1 = 0; pinna1L_z2 = 0
  pinna2L_z1 = 0; pinna2L_z2 = 0
  pinna1R_z1 = 0; pinna1R_z2 = 0
  pinna2R_z1 = 0; pinna2R_z2 = 0

  // Simple reverb for room/distance — 2 combs + 1 allpass
  comb1 = new Float32Array(1686); comb1p = 0
  comb2 = new Float32Array(2400); comb2p = 0
  ap1 = new Float32Array(523); ap1p = 0

  // LCG for reverb decorrelation
  _rng = 12345

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
  }

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
    if (name === "azimuth" || name === "head_size") {
      this._updateITD()
    }
  }

  _updateITD() {
    // Woodworth formula: ITD = (r/c) * (theta + sin(theta))
    // r = head radius (head_size * 0.0875m, average 8.75cm)
    // c = 343 m/s, theta = azimuth in radians
    const azRad = this.p.azimuth * Math.PI / 180
    const r = this.p.head_size * 0.0875
    const c = 343
    const itd = (r / c) * (azRad + Math.sin(azRad)) // seconds
    const itdSamples = Math.abs(itd * this.sr)

    // Cap at buffer size
    const maxDelay = 60 // ~1.3ms at 44.1k, enough for max ITD
    const capped = Math.min(itdSamples, maxDelay)

    if (azRad >= 0) {
      // Sound from right → left channel delayed
      this.delaySamplesR = 0
      this.delaySamplesL = capped
    } else {
      this.delaySamplesL = 0
      this.delaySamplesR = capped
    }
  }

  _rand() {
    this._rng = (this._rng * 1103515245 + 12345) & 0x7fffffff
    return this._rng / 0x7fffffff
  }

  // One-pole filter for ILD — frequency-dependent attenuation
  // High frequencies attenuated more on the shadowed ear
  _onePole(input, state, coeff) {
    const out = state + (input - state) * coeff
    return out
  }

  // Peaking biquad for pinna elevation notches
  _biquadPeak(x, z1, z2, freq, gain, q) {
    const w0 = 2 * Math.PI * freq / this.sr
    const alpha = Math.sin(w0) / (2 * q)
    const A = Math.pow(10, gain / 40)
    const b0 = 1 + alpha * A
    const b1 = -2 * Math.cos(w0)
    const b2 = 1 - alpha * A
    const a0 = 1 + alpha / A
    const a1 = -2 * Math.cos(w0)
    const a2 = 1 - alpha / A
    const y = (b0 * x + b1 * z1 + b2 * z2) / a0
    const newZ1 = x - a1 * z1 / a0 - a2 * z2 / a0
    const newZ2 = z1
    return [y, newZ1, newZ2]
  }

  _readDelay(buf, writePos, delaySamp) {
    const readPos = (writePos - delaySamp + buf.length) % buf.length
    const idx0 = Math.floor(readPos)
    const frac = readPos - idx0
    const idx1 = (idx0 + 1) % buf.length
    return buf[idx0] * (1 - frac) + buf[idx1] * frac
  }

  _comb(buf, pos, input, feedback) {
    const out = buf[pos]
    buf[pos] = input + out * feedback
    return out
  }

  _allpass(buf, pos, input, feedback) {
    const out = buf[pos]
    buf[pos] = input + out * feedback
    return out * -feedback + input
  }

  processAudio(inputs, outputs) {
    const input = inputs[0]
    const output = outputs[0]
    if (!input || !output) return
    const p = this.p
    const og = this.outGain

    const inL = input[0]
    const inR = input.length > 1 ? input[1] : input[0]
    const outL = output[0]
    const outR = output[1] || output[0]
    const numFrames = inL.length

    // Azimuth in radians
    const azRad = p.azimuth * Math.PI / 180
    const absAz = Math.abs(azRad)

    // ILD: frequency-dependent level difference
    // Low frequencies: minimal ILD (sound diffracts around head)
    // High frequencies: up to -15 dB at 90° (head shadow)
    // Using one-pole HF detection for level attenuation
    const ildMax = Math.sin(absAz) * 0.82 // ~-15 dB at 90°
    const ildCoeff = 0.15 // smoothing for ILD changes

    // Elevation pinna notch frequencies (simplified HRTF)
    // Higher elevation → notch moves up in frequency
    const elev = p.elevation
    const pinnaNotch1 = 6000 + elev * 30 // ~6kHz at 0°, ~8.7kHz at 90°
    const pinnaNotch2 = 9000 + elev * 25 // ~9kHz at 0°, ~11.3kHz at 90°
    const pinnaGain = -6 - Math.abs(elev) * 0.04 // deeper notches at extreme elevation

    // Distance attenuation: 1/distance + air absorption (HF rolloff with distance)
    const distAtten = 1 / Math.max(p.distance, 0.1)
    const airAbsorb = p.distance > 1 ? Math.min((p.distance - 1) * 0.03, 0.5) : 0

    // Room/reverb amount increases with distance (more reflections at far distance)
    const roomAmount = p.room * Math.min(p.distance / 3, 1) * 0.4

    // Stereo-link: convert mono to stereo if needed
    const isMono = input.length <= 1

    for (let i = 0; i < numFrames; i++) {
      // Input signal (mono or stereo)
      let sigL = inL[i]
      let sigR = isMono ? inL[i] : inR[i]

      // --- 1. ITD (Interaural Time Difference) ---
      // Write to delay buffers
      this.delayBufL[this.writePos] = sigL
      this.delayBufR[this.writePos] = sigR

      // Read with fractional delay
      if (this.delaySamplesL > 0) {
        sigL = this._readDelay(this.delayBufL, this.writePos, this.delaySamplesL)
      }
      if (this.delaySamplesR > 0) {
        sigR = this._readDelay(this.delayBufR, this.writePos, this.delaySamplesR)
      }
      this.writePos = (this.writePos + 1) % this.delayBufL.length

      // --- 2. ILD (Interaural Level Difference) ---
      // Split into LF (minimal ILD) and HF (max ILD) components
      const hfL = sigL - this._onePole(sigL, this.ildStateL, 0.02)
      this.ildStateL = this.ildStateL + (sigL - this.ildStateL) * 0.02
      const hfR = sigR - this._onePole(sigR, this.ildStateR, 0.02)
      this.ildStateR = this.ildStateR + (sigR - this.ildStateR) * 0.02

      if (azRad >= 0) {
        // Sound from right → attenuate left HF
        sigL = (sigL - hfL) + hfL * (1 - ildMax)
        sigR = sigR // right unaffected
      } else {
        // Sound from left → attenuate right HF
        sigR = (sigR - hfR) + hfR * (1 - ildMax)
        sigL = sigL
      }

      // --- 3. Pinna elevation notches ---
      // Only on the ear facing the sound (contralateral gets more notching)
      const earFactor = absAz / Math.PI // 0=front, 1=behind
      const notchDepth = 1 + earFactor * 0.5

      let [pl1, pn1L_z1, pn1L_z2] = this._biquadPeak(sigL, this.pinna1L_z1, this.pinna1L_z2,
        pinnaNotch1, pinnaGain * notchDepth, 2)
      this.pinna1L_z1 = pn1L_z1; this.pinna1L_z2 = pn1L_z2
      let [pl2, pn2L_z1, pn2L_z2] = this._biquadPeak(pl1, this.pinna2L_z1, this.pinna2L_z2,
        pinnaNotch2, pinnaGain * notchDepth * 0.8, 2)
      this.pinna2L_z1 = pn2L_z1; this.pinna2L_z2 = pn2L_z2
      sigL = pl2

      let [pr1, pn1R_z1, pn1R_z2] = this._biquadPeak(sigR, this.pinna1R_z1, this.pinna1R_z2,
        pinnaNotch1, pinnaGain * notchDepth, 2)
      this.pinna1R_z1 = pn1R_z1; this.pinna1R_z2 = pn1R_z2
      let [pr2, pn2R_z1, pn2R_z2] = this._biquadPeak(pr1, this.pinna2R_z1, this.pinna2R_z2,
        pinnaNotch2, pinnaGain * notchDepth * 0.8, 2)
      this.pinna2R_z1 = pn2R_z1; this.pinna2R_z2 = pn2R_z2
      sigR = pr2

      // --- 4. Distance attenuation + air absorption ---
      sigL *= distAtten
      sigR *= distAtten

      // Air absorption: simple HF rolloff with distance
      if (airAbsorb > 0) {
        const hfAbsorbL = sigL - this._onePole(sigL, this.ildStateL, 0.01)
        this.ildStateL = this.ildStateL + (sigL - this.ildStateL) * 0.01
        sigL -= hfAbsorbL * airAbsorb

        const hfAbsorbR = sigR - this._onePole(sigR, this.ildStateR, 0.01)
        this.ildStateR = this.ildStateR + (sigR - this.ildStateR) * 0.01
        sigR -= hfAbsorbR * airAbsorb
      }

      // --- 5. Room reverb (distance-dependent) ---
      if (roomAmount > 0.01) {
        const revIn = (sigL + sigR) * 0.5 * roomAmount
        const c1 = this._comb(this.comb1, this.comb1p, revIn, 0.84)
        this.comb1p = (this.comb1p + 1) % this.comb1.length
        const c2 = this._comb(this.comb2, this.comb2p, revIn, 0.78)
        this.comb2p = (this.comb2p + 1) % this.comb2.length
        const rev = this._allpass(this.ap1, this.ap1p, c1 + c2, 0.7)
        this.ap1p = (this.ap1p + 1) % this.ap1.length

        // Decorrelate left/right reverb
        const revL = rev * (0.9 + this._rand() * 0.2)
        const revR = rev * (0.9 + this._rand() * 0.2)
        sigL += revL * roomAmount
        sigR += revR * roomAmount
      }

      // --- 6. Dry/wet + output gain ---
      const dryL = inL[i]
      const dryR = isMono ? inL[i] : inR[i]
      outL[i] = (dryL * (1 - p.mix) + sigL * p.mix) * og
      outR[i] = (dryR * (1 - p.mix) + sigR * p.mix) * og
    }
  }

  reset() {
    this.delayBufL.fill(0)
    this.delayBufR.fill(0)
    this.comb1.fill(0)
    this.comb2.fill(0)
    this.ap1.fill(0)
    this.ildStateL = 0
    this.ildStateR = 0
    this.pinna1L_z1 = 0; this.pinna1L_z2 = 0
    this.pinna2L_z1 = 0; this.pinna2L_z2 = 0
    this.pinna1R_z1 = 0; this.pinna1R_z2 = 0
    this.pinna2R_z1 = 0; this.pinna2R_z2 = 0
    this.writePos = 0
  }
}
