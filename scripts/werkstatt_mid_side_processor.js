// @werkstatt mid_side_processor 1 1
// Mid/Side processor — encode L/R to M/S, process independently, decode back
// M = (L+R)/2 (center content: vocals, bass, kick)
// S = (L-R)/2 (stereo content: wide instruments, room ambience)
// Independent gain and filter control per channel. Mastering staple.
//
// @param mid_gain 0.0 2.0 1.0 linear  // mid channel gain (1=unity)
// @param side_gain 0.0 2.0 1.0 linear  // side channel gain (1=unity, >1=widen, <1=narrow)
// @param mid_freq 20 2000 200 linear  // mid highpass cutoff (Hz, 0=bypass)
// @param side_freq 100 8000 2000 linear  // side lowpass cutoff (Hz, removes harsh side content)
// @param width 0.0 2.0 1.0 linear  // stereo width (0=mono, 1=original, 2=double wide)
// @param mix 0.0 1.0 1.0 linear  // 0=bypass, 1=full M/S processing
//
// Influences: Brainworx bx_digital, Dangerous MUSIC, SSL X-Phase

class Processor {
  paramChanged(name, value) {
    if (name === "mid_gain") this.midGain = value;
    if (name === "side_gain") this.sideGain = value;
    if (name === "mid_freq") this.midFreq = value;
    if (name === "side_freq") this.sideFreq = value;
    if (name === "width") this.width = value;
    if (name === "mix") this.mixAmount = value;
  }

  prepare(sampleRate, blockSize) {
    this.sampleRate = sampleRate;
    this.blockSize = blockSize;

    // Mid highpass filter state (biquad)
    this.midHpX1 = 0; this.midHpX2 = 0;
    this.midHpY1 = 0; this.midHpY2 = 0;

    // Side lowpass filter state (biquad)
    this.sideLpX1 = 0; this.sideLpX2 = 0;
    this.sideLpY1 = 0; this.sideLpY2 = 0;

    this.updateMidCoeffs();
    this.updateSideCoeffs();
  }

  updateMidCoeffs() {
    if (this.midFreq <= 0) return;
    const w0 = 2 * Math.PI * this.midFreq / this.sampleRate;
    const cosW0 = Math.cos(w0);
    const sinW0 = Math.sin(w0);
    const alpha = sinW0 / (2 * 0.707); // Q=0.707
    // Highpass
    this.midB0 = (1 + cosW0) / 2;
    this.midB1 = -(1 + cosW0);
    this.midB2 = (1 + cosW0) / 2;
    this.midA0 = 1 + alpha;
    this.midA1 = -2 * cosW0;
    this.midA2 = 1 - alpha;
  }

  updateSideCoeffs() {
    if (this.sideFreq <= 0) return;
    const w0 = 2 * Math.PI * this.sideFreq / this.sampleRate;
    const cosW0 = Math.cos(w0);
    const sinW0 = Math.sin(w0);
    const alpha = sinW0 / (2 * 0.707); // Q=0.707
    // Lowpass
    this.sideB0 = (1 - cosW0) / 2;
    this.sideB1 = (1 - cosW0);
    this.sideB2 = (1 - cosW0) / 2;
    this.sideA0 = 1 + alpha;
    this.sideA1 = -2 * cosW0;
    this.sideA2 = 1 - alpha;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];

    if (!input || !input[0] || !input[1]) return;
    if (!output || !output[0] || !output[1]) return;

    const inL = input[0];
    const inR = input[1];
    const outL = output[0];
    const outR = output[1];

    this.updateMidCoeffs();
    this.updateSideCoeffs();

    for (let i = 0; i < inL.length; i++) {
      const l = inL[i];
      const r = inR[i];

      // Encode: M/S
      let mid = (l + r) * 0.5;
      let side = (l - r) * 0.5;

      // Mid highpass
      if (this.midFreq > 0) {
        const midHp = (this.midB0 * mid + this.midB1 * this.midHpX1 + this.midB2 * this.midHpX2
          - this.midA1 * this.midHpY1 - this.midA2 * this.midHpY2) / this.midA0;
        this.midHpX2 = this.midHpX1;
        this.midHpX1 = mid;
        this.midHpY2 = this.midHpY1;
        this.midHpY1 = midHp;
        mid = midHp;
      }

      // Side lowpass
      if (this.sideFreq > 0) {
        const sideLp = (this.sideB0 * side + this.sideB1 * this.sideLpX1 + this.sideB2 * this.sideLpX2
          - this.sideA1 * this.sideLpY1 - this.sideA2 * this.sideLpY2) / this.sideA0;
        this.sideLpX2 = this.sideLpX1;
        this.sideLpX1 = side;
        this.sideLpY2 = this.sideLpY1;
        this.sideLpY1 = sideLp;
        side = sideLp;
      }

      // Independent gain
      mid *= this.midGain;
      side *= this.sideGain * this.width;

      // Decode: L/R
      const newL = mid + side;
      const newR = mid - side;

      // Mix
      outL[i] = newL * this.mixAmount + l * (1 - this.mixAmount);
      outR[i] = newR * this.mixAmount + r * (1 - this.mixAmount);
    }
  }
}
