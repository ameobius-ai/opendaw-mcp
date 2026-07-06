// @werkstatt cassette_sim 1 1
// @label Cassette Tape Simulator
// @param age 0.3 0 1 linear
// @param wow 0.2 0 1 linear
// @param flutter 0.3 0 1 linear
// @param hiss 0.15 0 1 linear
// @param saturation 0.4 0 1 linear
// @param loss 0.3 0 1 linear
// @param mix 0.85 0 1 linear
// @param output -2 -24 6 linear dB

class Processor {
  p = {age: 0.3, wow: 0.2, flutter: 0.3, hiss: 0.15, saturation: 0.4, loss: 0.3, mix: 0.85, output: -2}
  
  // Wow/flutter LFO state
  wowPhase = 0
  flutterPhase = 0
  wowPhase2 = 0
  wowDepth = 0
  flutterDepth = 0
  
  // Tape delay buffer (for wow/flutter pitch modulation via interpolation)
  bufL = new Float32Array(2048)
  bufR = new Float32Array(2048)
  bufPos = 0
  bufLen = 2048
  
  // Hiplast noise state
  hissState = 0
  
  // Head bump (low-frequency resonance)
  bumpL = 0; bumpR = 0; bumpLp = 0; bumpRp = 0
  
  // High-frequency loss (tape head gap effect)
  lossLpL = 0; lossLpR = 0
  
  // DC blocker
  dcL = 0; dcR = 0
  
  paramChanged(name, value) {
    this.p[name] = value
  }
  
  _tanh(x) {
    if (x > 3) return 1
    if (x < -3) return -1
    return x * (27 + x * x) / (27 + 9 * x * x)
  }
  
  // Pseudo-random noise (fractal)
  _noise() {
    this.hissState = (this.hissState * 1103515245 + 12345) & 0x7fffffff
    return (this.hissState / 0x3fffffff) - 1.0
  }
  
  process(io, block) {
    const outGain = Math.pow(10, this.p.output / 20)
    const satAmt = 1 + this.p.saturation * 5
    const ageAmt = this.p.age
    const wowRate = 0.5 + ageAmt * 1.5  // 0.5-2 Hz wow
    const flutterRate = 13 + ageAmt * 20  // 13-33 Hz flutter
    const wowGain = this.p.wow * 0.003  // max 3ms modulation
    const flutterGain = this.p.flutter * 0.0008  // max 0.8ms modulation
    const hissAmt = this.p.hiss * 0.04
    const lossFreq = 1 - this.p.loss * 0.7  // tape head gap lowpass coefficient
    const wetMix = this.p.mix
    const sr = this.sampleRate || 44100
    
    for (let i = block.s0; i < block.s1; i++) {
      // --- Wow & flutter: LFO-driven pitch modulation ---
      // Wow = slow speed variation (~0.5-2 Hz)
      // Flutter = faster flutter (~13-33 Hz)
      this.wowPhase += (wowRate * 2 * Math.PI) / sr
      this.wowPhase2 += (wowRate * 0.37 * 2 * Math.PI) / sr  // second wow partial
      this.flutterPhase += (flutterRate * 2 * Math.PI) / sr
      
      const wowMod = Math.sin(this.wowPhase) * 0.7 + Math.sin(this.wowPhase2) * 0.3
      const flutterMod = Math.sin(this.flutterPhase) * 0.6 + Math.sin(this.flutterPhase * 2.7) * 0.4
      
      // Combined delay modulation (in samples)
      const delayMod = wowMod * wowGain * sr + flutterMod * flutterGain * sr
      const readPos = (this.bufPos - 64 - delayMod + this.bufLen) % this.bufLen
      const idx0 = Math.floor(readPos)
      const frac = readPos - idx0
      const idx1 = (idx0 + 1) % this.bufLen
      
      // Write input to buffer
      this.bufL[this.bufPos] = io.src[0][i]
      this.bufR[this.bufPos] = io.src[1][i]
      this.bufPos = (this.bufPos + 1) % this.bufLen
      
      // Read with linear interpolation (wow/flutter pitch shift)
      const wowL = this.bufL[idx0] * (1 - frac) + this.bufL[idx1] * frac
      const wowR = this.bufR[idx0] * (1 - frac) + this.bufR[idx1] * frac
      
      // --- Tape saturation (asymmetric soft clipping) ---
      const satL = this._tanh(wowL * satAmt) / this._tanh(satAmt)
      const satR = this._tanh(wowR * satAmt) / this._tanh(satAmt)
      
      // --- Head bump (low-frequency resonance boost ~80 Hz) ---
      const bumpFreq = 80 / sr * 2 * Math.PI
      this.bumpL = this.bumpL + bumpFreq * (satL - this.bumpLp)
      this.bumpLp = this.bumpLp + bumpFreq * this.bumpL
      this.bumpR = this.bumpR + bumpFreq * (satR - this.bumpRp)
      this.bumpRp = this.bumpRp + bumpFreq * this.bumpR
      const bumpedL = satL + this.bumpLp * 0.3 * ageAmt
      const bumpedR = satR + this.bumpRp * 0.3 * ageAmt
      
      // --- High-frequency loss (tape head gap effect) ---
      this.lossLpL = this.lossLpL * lossFreq + bumpedL * (1 - lossFreq)
      this.lossLpR = this.lossLpR * lossFreq + bumpedR * (1 - lossFreq)
      const lossyL = bumpedL * (1 - this.p.loss * 0.5) + this.lossLpL * this.p.loss * 0.5
      const lossyR = bumpedR * (1 - this.p.loss * 0.5) + this.lossLpR * this.p.loss * 0.5
      
      // --- Tape hiss (pink-ish noise) ---
      const hissL = this._noise() * hissAmt
      const hissR = this._noise() * hissAmt
      const noisyL = lossyL + hissL
      const noisyR = lossyR + hissR
      
      // --- DC blocker ---
      this.dcL = this.dcL * 0.9999 + noisyL * 0.0001
      this.dcR = this.dcR * 0.9999 + noisyR * 0.0001
      const cleanL = noisyL - this.dcL
      const cleanR = noisyR - this.dcR
      
      // --- Mix + output ---
      io.dst[0][i] = (io.src[0][i] * (1 - wetMix) + cleanL * wetMix) * outGain
      io.dst[1][i] = (io.src[1][i] * (1 - wetMix) + cleanR * wetMix) * outGain
    }
  }
}
