// @werkstatt distortion_pedal 1 1
// @label Distortion Pedal (DS-1/Rat style)
// @param drive 0.5 0 1 linear
// @param tone 0.5 0 1 linear
// @param level 0.7 0 1 linear
// @param character 0.3 0 1 linear
// @param mix 1.0 0 1 linear

class Processor {
  p = {drive: 0.5, tone: 0.5, level: 0.7, character: 0.3, mix: 1.0}
  
  // Pre-distortion highpass (removes mud before clipping)
  hpL = 0; hpR = 0
  hpLpL = 0; hpLpR = 0
  
  // Post-distortion tone stack (active EQ: bass cut, mid scoop, treble boost)
  toneLpL = 0; toneLpR = 0  // bass
  toneHpL = 0; toneHpR = 0  // treble
  toneMidL = 0; toneMidR = 0  // mid band
  
  // DC blocker
  dcL = 0; dcR = 0
  
  paramChanged(name, value) {
    this.p[name] = value
  }
  
  // Hard clipping with soft knee transition
  _clip(x, amt) {
    const threshold = 1 - amt * 0.7
    if (Math.abs(x) < threshold) return x
    const sign = x < 0 ? -1 : 1
    const over = Math.abs(x) - threshold
    const clipped = threshold + over * (1 - amt * 0.8)
    return sign * Math.min(clipped, 1.0)
  }
  
  process(io, block) {
    const sr = this.sampleRate || 44100
    const driveAmt = 1 + this.p.drive * 20
    const tonePos = this.p.tone
    const levelAmt = this.p.level * 1.5
    const charAmt = this.p.character  // 0=DS-1 (scoop), 1=Rat (mid hump)
    const wetMix = this.p.mix
    
    // Pre-distortion highpass (~200 Hz, removes mud)
    const hpFreq = 200 / sr * 2 * Math.PI
    // Tone stack frequencies
    const bassFreq = 250 / sr * 2 * Math.PI
    const midFreq = 1000 / sr * 2 * Math.PI
    const trebFreq = 3000 / sr * 2 * Math.PI
    
    for (let i = block.s0; i < block.s1; i++) {
      const inL = io.src[0][i]
      const inR = io.src[1][i]
      
      // --- Pre-distortion highpass ---
      this.hpLpL = this.hpLpL + hpFreq * (inL - this.hpLpL)
      this.hpLpR = this.hpLpR + hpFreq * (inR - this.hpLpR)
      this.hpL = inL - this.hpLpL
      this.hpR = inR - this.hpLpR
      
      // --- Distortion (hard clipping with drive) ---
      const distL = this._clip(this.hpL * driveAmt, this.p.drive)
      const distR = this._clip(this.hpR * driveAmt, this.p.drive)
      
      // --- Tone stack (active EQ) ---
      // Bass: lowpass
      this.toneLpL = this.toneLpL + bassFreq * (distL - this.toneLpL)
      this.toneLpR = this.toneLpR + bassFreq * (distR - this.toneLpR)
      // Treble: highpass via difference
      this.toneHpL = this.toneHpL + trebFreq * (distL - this.toneHpL)
      this.toneHpR = this.toneHpR + trebFreq * (distR - this.toneHpR)
      const trebL = distL - this.toneHpL
      const trebR = distR - this.toneHpR
      // Mid: bandpass
      this.toneMidL = this.toneMidL + midFreq * (distL - this.toneMidL)
      this.toneMidR = this.toneMidR + midFreq * (distR - this.toneMidR)
      const midL = distL - this.toneMidL - this.toneLpL
      const midR = distR - this.toneMidR - this.toneLpR
      
      // Mix tone: character controls mid scoop vs mid hump
      // tone controls bass/treble balance
      const bassGain = (1 - tonePos) * 1.2
      const trebGain = tonePos * 1.5
      const midGain = charAmt < 0.5 ? (1 - charAmt * 2) * 0.3 : (charAmt - 0.5) * 2 * 1.5
      
      let outL = this.toneLpL * bassGain + midL * midGain + trebL * trebGain
      let outR = this.toneLpR * bassGain + midR * midGain + trebR * trebGain
      
      // --- Level ---
      outL *= levelAmt
      outR *= levelAmt
      
      // --- DC blocker ---
      this.dcL = this.dcL * 0.9999 + outL * 0.0001
      this.dcR = this.dcR * 0.9999 + outR * 0.0001
      outL -= this.dcL
      outR -= this.dcR
      
      // --- Mix ---
      io.dst[0][i] = inL * (1 - wetMix) + outL * wetMix
      io.dst[1][i] = inR * (1 - wetMix) + outR * wetMix
    }
  }
}
