// @werkstatt analog_delay 1 1
// @label Analog BBD Delay
// @param time 250 10 1000 linear ms
// @param feedback 0.35 0 0.95 linear
// @param mix 0.3 0 1 linear
// @param modulation 0.2 0 1 linear
// @param clock 0.5 0 1 linear
// @param saturation 0.3 0 1 linear
// @param tone 0.6 0 1 linear
// @param stereo 0.2 0 1 linear

class Processor {
  p = {time: 250, feedback: 0.35, mix: 0.3, modulation: 0.2, clock: 0.5, saturation: 0.3, tone: 0.6, stereo: 0.2}
  
  // Delay buffer
  bufL = new Float32Array(131072)
  bufR = new Float32Array(131072)
  bufPos = 0
  bufLen = 131072
  
  // LFO for modulation
  lfoPhase = 0
  
  // BBD clock filter (sample-and-hold reconstruction)
  bbdL = 0; bbdR = 0
  bbdClockL = 0; bbdClockR = 0
  bbdCounter = 0
  
  // Saturation state
  satL = 0; satR = 0
  
  // Tone filter (lowpass for wet signal)
  toneLpL = 0; toneLpR = 0
  toneHpL = 0; toneHpR = 0
  
  paramChanged(name, value) {
    this.p[name] = value
  }
  
  _tanh(x) {
    if (x > 3) return 1
    if (x < -3) return -1
    return x * (27 + x * x) / (27 + 9 * x * x)
  }
  
  process(io, block) {
    const sr = this.sampleRate || 44100
    const delaySamples = this.p.time * 0.001 * sr
    const fb = this.p.feedback
    const wetMix = this.p.mix
    const modDepth = this.p.modulation * 0.15 * delaySamples
    const modRate = 0.5  // Hz
    const clockRate = this.p.clock  // 0=full rate, 1=max downsample
    const satAmt = 1 + this.p.saturation * 3
    const toneCoeff = this.p.tone * 0.8 + 0.1
    const stereoOffset = this.p.stereo * sr * 0.01  // up to 10ms stereo offset
    
    this.bbdCounter = 0
    
    for (let i = block.s0; i < block.s1; i++) {
      // --- LFO modulation ---
      this.lfoPhase += (modRate * 2 * Math.PI) / sr
      const mod = Math.sin(this.lfoPhase) * modDepth
      
      // --- Read from delay buffer with interpolation ---
      const readPosL = (this.bufPos - delaySamples - mod + this.bufLen) % this.bufLen
      const readPosR = (this.bufPos - delaySamples - mod - stereoOffset + this.bufLen) % this.bufLen
      
      const idx0L = Math.floor(readPosL)
      const fracL = readPosL - idx0L
      const idx1L = (idx0L + 1) % this.bufLen
      const delL = this.bufL[idx0L] * (1 - fracL) + this.bufL[idx1L] * fracL
      
      const idx0R = Math.floor(readPosR)
      const fracR = readPosR - idx0R
      const idx1R = (idx0R + 1) % this.bufLen
      const delR = this.bufR[idx0R] * (1 - fracR) + this.bufR[idx1R] * fracR
      
      // --- BBD clock simulation (sample-rate reduction) ---
      // BBD chips sample at a clock rate; lower clock = more aliasing/grain
      const bbdThreshold = 1 - clockRate * 0.8
      this.bbdCounter += bbdThreshold
      if (this.bbdCounter >= 1) {
        this.bbdCounter -= 1
        this.bbdL = delL
        this.bbdR = delR
      }
      // Smooth BBD output (analog reconstruction filter)
      this.bbdClockL = this.bbdClockL * 0.7 + this.bbdL * 0.3
      this.bbdClockR = this.bbdClockR * 0.7 + this.bbdR * 0.3
      
      // --- Saturation (analog warmth) ---
      this.satL = this._tanh(this.bbdClockL * satAmt) / this._tanh(satAmt)
      this.satR = this._tanh(this.bbdClockR * satAmt) / this._tanh(satAmt)
      
      // --- Tone filter (bandpass-ish: lowpass + highpass) ---
      this.toneLpL = this.toneLpL * (1 - toneCoeff) + this.satL * toneCoeff
      this.toneLpR = this.toneLpR * (1 - toneCoeff) + this.satR * toneCoeff
      this.toneHpL = this.toneHpL * 0.99 + (this.satL - this.toneLpL) * 0.01
      this.toneHpR = this.toneHpR * 0.99 + (this.satR - this.toneLpR) * 0.01
      const tonedL = this.toneLpL
      const tonedR = this.toneLpR
      
      // --- Write to buffer (input + feedback) ---
      this.bufL[this.bufPos] = io.src[0][i] + tonedL * fb
      this.bufR[this.bufPos] = io.src[1][i] + tonedR * fb
      this.bufPos = (this.bufPos + 1) % this.bufLen
      
      // --- Mix ---
      io.dst[0][i] = io.src[0][i] * (1 - wetMix) + tonedL * wetMix
      io.dst[1][i] = io.src[1][i] * (1 - wetMix) + tonedR * wetMix
    }
  }
}
