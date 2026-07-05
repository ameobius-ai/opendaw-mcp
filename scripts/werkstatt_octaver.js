// @werkstatt octaver 1 1
// @label Octaver (Sub-Octave Generator)
// Sub-octave generator — Boss OC-2 / Mu-Tron Octave Divider style
// Zero-crossing flip-flop divides input frequency by 2 (-1 oct) and 4 (-2 oct)
// Envelope follower tracks input amplitude for natural decay

// @param oct1     0.7  0  1   linear   // -1 octave level (flip-flop /2)
// @param oct2     0    0  1   linear   // -2 octave level (flip-flop /4)
// @param direct   0    0  1   linear   // direct (dry) level
// @param smooth   0.3  0  1   linear   // square wave edge smoothing (one-pole lowpass)
// @param track    0.5  0  1   linear   // envelope tracking speed (0=slow, 1=fast)
// @param trigger  0.01 0  0.1 linear   // zero-crossing hysteresis threshold
// @param output   0    -24 6 linear dB

class Processor {
  p = {oct1: 0.7, oct2: 0, direct: 0, smooth: 0.3, track: 0.5, trigger: 0.01, output: 0}
  sr = sampleRate

  // Flip-flop state: toggles on each zero crossing
  flip1 = 0   // -1 octave (divide by 2)
  flip2 = 0   // -2 octave (divide by 4, toggles on flip1 edges)
  prevSign = 0  // previous input sign for zero-crossing detection
  hystState = 0 // hysteresis: 0=below, 1=above

  // Envelope follower
  env = 0
  // Smoothing one-pole lowpass states for each octave
  smooth1 = 0
  smooth2 = 0
  // Output gain cache
  outGain = 1

  paramChanged(name, value) {
    this.p[name] = value
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20)
    }
  }

  process(io, block) {
    const sr = this.sr
    const p = this.p
    const og = this.outGain

    // Envelope follower coefficients
    // track 0→500ms, 1→0.5ms
    const trackMs = 500 * Math.pow(0.001, p.track)
    const envCoeff = Math.exp(-1 / (sr * trackMs * 0.001))

    // Smoothing lowpass coefficient
    // smooth 0→no smoothing (raw square), 1→heavy smoothing
    const smoothHz = 200 + p.smooth * 4800  // 200Hz..5000Hz
    const smoothCoeff = Math.exp(-2 * Math.PI * smoothHz / sr)

    // Hysteresis threshold
    const hyst = p.trigger

    const s0 = block.s0
    const s1 = block.s1

    for (let i = s0; i < s1; i++) {
      const inL = io.src[0][i]
      const inR = io.src[1] ? io.src[1][i] : inL
      const mono = (inL + inR) * 0.5

      // --- Zero-crossing detection with hysteresis ---
      // State machine: track when signal crosses zero with a small dead zone
      let crossed = false
      if (this.hystState === 0) {
        // Below threshold — wait for signal to rise above +hyst
        if (mono > hyst) {
          this.hystState = 1
          crossed = true
        } else if (mono < -hyst) {
          this.hystState = -1
          crossed = true
        }
      } else if (this.hystState === 1) {
        if (mono < -hyst) {
          this.hystState = -1
          crossed = true
        }
      } else if (this.hystState === -1) {
        if (mono > hyst) {
          this.hystState = 1
          crossed = true
        }
      }

      // --- Flip-flop frequency division ---
      if (crossed) {
        // Toggle -1 octave flip-flop
        this.flip1 = 1 - this.flip1
        // Toggle -2 octave flip-flop only on rising edge of flip1
        if (this.flip1 === 1) {
          this.flip2 = 1 - this.flip2
        }
      }

      // --- Envelope follower (peak-hold style) ---
      const absMono = mono < 0 ? -mono : mono
      if (absMono > this.env) {
        this.env = absMono  // fast attack
      } else {
        this.env = this.env * envCoeff + absMono * (1 - envCoeff)
      }

      // --- Generate square waves centered at 0 ---
      // Square wave: +1 or -1, centered
      const sq1 = this.flip1 * 2 - 1   // -1 octave
      const sq2 = this.flip2 * 2 - 1   // -2 octave

      // --- Smooth square waves (one-pole lowpass) ---
      this.smooth1 = this.smooth1 * smoothCoeff + sq1 * (1 - smoothCoeff)
      this.smooth2 = this.smooth2 * smoothCoeff + sq2 * (1 - smoothCoeff)

      // --- Shape with envelope ---
      const envAmt = this.env * 2  // gain compensation for square wave amplitude

      // --- Mix ---
      let out = 0
      out += this.smooth1 * envAmt * p.oct1
      out += this.smooth2 * envAmt * p.oct2
      out += mono * p.direct

      out *= og

      io.out[0][i] = out
      io.out[1][i] = out
    }
  }
}
