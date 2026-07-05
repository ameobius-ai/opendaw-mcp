// @werkstatt harmonizer 1 1
// @label Harmonizer
// @param shift1_semi 7 -12 12 linear semi
// @param shift1_cent 0 -50 50 linear cent
// @param shift1_gain 0.5 0 1 linear
// @param shift2_semi -5 -12 12 linear semi
// @param shift2_cent 0 -50 50 linear cent
// @param shift2_gain 0.5 0 1 linear
// @param detune 0.1 0 1 linear
// @param delay 0.03 0 0.2 linear sec
// @param mix 0.4 0 1 linear

class Processor {
  p = {shift1_semi: 7, shift1_cent: 0, shift1_gain: 0.5,
       shift2_semi: -5, shift2_cent: 0, shift2_gain: 0.5,
       detune: 0.1, delay: 0.03, mix: 0.4}
  sr = 44100
  bs = 128

  // Two pitch shifters, each with its own delay buffer
  buf1L = null; buf1R = null
  buf2L = null; buf2R = null
  writePos = 0
  bufSize = 0

  // LFO for detune modulation
  lfoPhase = 0

  constructor() {
    if (this.sampleRate) this.sr = this.sampleRate
    if (this.blockSize) this.bs = this.blockSize
    this.bufSize = Math.ceil(this.sr * 0.3) // 300ms max
    this.buf1L = new Float32Array(this.bufSize)
    this.buf1R = new Float32Array(this.bufSize)
    this.buf2L = new Float32Array(this.bufSize)
    this.buf2R = new Float32Array(this.bufSize)
  }

  paramChanged(name, value) {
    this.p[name] = value
  }

  // Simple pitch shift via delay line modulation (granular-ish)
  // Rate ratio = 2^(semitones/12)
  // We modulate the read position to achieve pitch shifting
  _pitchShift(buf, writePos, bufSize, ratio, detuneMod, delaySamples) {
    // Target read position lags behind write by delaySamples
    // Pitch shift = ratio, so read speed = 1/ratio relative to write
    // readPos moves at writePos - delaySamples * ratio
    const readPos = (writePos - delaySamples * ratio + detuneMod + bufSize * 10) % bufSize
    const idx0 = Math.floor(readPos)
    const idx1 = (idx0 + 1) % bufSize
    const frac = readPos - idx0
    return buf[idx0] * (1 - frac) + buf[idx1] * frac
  }

  processAudio(inputs, outputs) {
    const inp = inputs[0]
    const out = outputs[0]
    if (!inp || !out) return

    const sr = this.sr
    const bufSize = this.bufSize
    const delaySamples = Math.max(1, Math.floor(this.p.delay * sr))
    const detuneAmt = this.p.detune * delaySamples * 0.3

    // Pitch ratios
    const ratio1 = Math.pow(2, (this.p.shift1_semi + this.p.shift1_cent / 100) / 12)
    const ratio2 = Math.pow(2, (this.p.shift2_semi + this.p.shift2_cent / 100) / 12)

    const gain1 = this.p.shift1_gain
    const gain2 = this.p.shift2_gain
    const mix = this.p.mix

    // LFO for detune (slow chorus-like wobble)
    const lfoInc = 2 * Math.PI * 0.5 / sr // 0.5 Hz
    const stereo = out.length > 1

    for (let i = 0; i < out[0].length; i++) {
      const inL = inp[0][i]
      const inR = stereo ? (inp.length > 1 ? inp[1][i] : inp[0][i]) : inL

      // Write to buffers
      this.buf1L[this.writePos] = inL
      this.buf1R[this.writePos] = inR
      this.buf2L[this.writePos] = inL
      this.buf2R[this.writePos] = inR

      // Detune modulation
      const detuneMod = Math.sin(this.lfoPhase) * detuneAmt
      this.lfoPhase += lfoInc
      if (this.lfoPhase > Math.PI * 2) this.lfoPhase -= Math.PI * 2

      // Pitch-shifted reads
      const ps1L = this._pitchShift(this.buf1L, this.writePos, bufSize, ratio1, detuneMod, delaySamples)
      const ps1R = this._pitchShift(this.buf1R, this.writePos, bufSize, ratio1, -detuneMod, delaySamples)
      const ps2L = this._pitchShift(this.buf2L, this.writePos, bufSize, ratio2, -detuneMod, delaySamples)
      const ps2R = this._pitchShift(this.buf2R, this.writePos, bufSize, ratio2, detuneMod, delaySamples)

      this.writePos = (this.writePos + 1) % bufSize

      // Mix: dry + two harmonized voices
      const wetL = ps1L * gain1 + ps2L * gain2
      const wetR = ps1R * gain1 + ps2R * gain2

      out[0][i] = inL * (1 - mix * 0.5) + wetL * mix
      if (stereo) {
        out[1][i] = inR * (1 - mix * 0.5) + wetR * mix
      }
    }
  }
}
