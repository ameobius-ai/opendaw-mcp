// @werkstatt de_plosive 1 1
// De-plosive — adaptive highpass for removing plosive bursts (P, B, T) from vocals
// Detects low-frequency transient bursts and dynamically applies highpass filtering
// only when plosive energy is detected. Clean vocal passes through untouched.
//
// @param threshold 0.05 0.5 0.15 linear  // detection threshold (lower = more sensitive)
// @param freq 80 300 150 linear  // highpass cutoff frequency (Hz) when active
// @param attack 0.001 0.02 0.003 linear  // filter engagement speed (fast = catches burst start)
// @param release 0.05 0.5 0.15 linear  // filter release speed (slow = natural recovery)
// @param q 0.5 4.0 1.2 linear  // filter resonance (higher = steeper cut)
// @param mix 0.0 1.0 1.0 linear  // 0=bypass, 1=full de-plosive
//
// Influences: Waves DeBreath, iZotope RX De-plosive, SPL De-esser adaptive mode

class Processor {
  paramChanged(name, value) {
    if (name === "threshold") this.threshold = value;
    if (name === "freq") this.cutoffFreq = value;
    if (name === "attack") this.attackTime = value;
    if (name === "release") this.releaseTime = value;
    if (name === "q") this.qFactor = value;
    if (name === "mix") this.mixAmount = value;
  }

  prepare(sampleRate, blockSize) {
    this.sampleRate = sampleRate;
    this.blockSize = blockSize;

    // Detection band: low-frequency energy (20-100 Hz) where plosives live
    this.detectPrev = 0;
    this.detectEnv = 0;

    // Filter engagement level (0 = bypass, 1 = full filter)
    this.filterEngage = 0;

    // Highpass filter state (biquad)
    this.hpX1 = 0; this.hpX2 = 0;
    this.hpY1 = 0; this.hpY2 = 0;

    this.updateCoeffs();
  }

  updateCoeffs() {
    const w0 = 2 * Math.PI * this.cutoffFreq / this.sampleRate;
    const cosW0 = Math.cos(w0);
    const sinW0 = Math.sin(w0);
    const alpha = sinW0 / (2 * this.qFactor);

    // Highpass biquad coefficients
    this.b0 = (1 + cosW0) / 2;
    this.b1 = -(1 + cosW0);
    this.b2 = (1 + cosW0) / 2;
    this.a0 = 1 + alpha;
    this.a1 = -2 * cosW0;
    this.a2 = 1 - alpha;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];

    if (!input || !input[0]) return;

    const sr = this.sampleRate;
    const attackCoeff = Math.exp(-1 / (this.attackTime * sr));
    const releaseCoeff = Math.exp(-1 / (this.releaseTime * sr));
    const detectAttack = Math.exp(-1 / (0.001 * sr));
    const detectRelease = Math.exp(-1 / (0.05 * sr));

    // Re-update coeffs if freq changed (cheap)
    this.updateCoeffs();

    for (let ch = 0; ch < input.length; ch++) {
      const inCh = input[ch];
      const outCh = output[ch];
      if (!inCh || !outCh) continue;

      // Per-channel filter state
      let x1 = ch === 0 ? this.hpX1 : this.hpX1;
      let x2 = ch === 0 ? this.hpX2 : this.hpX2;
      let y1 = ch === 0 ? this.hpY1 : this.hpY1;
      let y2 = ch === 0 ? this.hpY2 : this.hpY2;

      for (let i = 0; i < inCh.length; i++) {
        const sample = inCh[i];

        // Detection: low-frequency content via simple one-pole lowpass at 100Hz
        const detectLp = 0.99 * this.detectPrev + 0.01 * Math.abs(sample);
        this.detectPrev = detectLp;

        // Envelope of low-frequency energy
        if (detectLp > this.detectEnv) {
          this.detectEnv = detectLp * (1 - detectAttack) + this.detectEnv * detectAttack;
        } else {
          this.detectEnv = detectLp * (1 - detectRelease) + this.detectEnv * detectRelease;
        }

        // Plosive detection: if low-freq energy exceeds threshold, engage filter
        const plosiveDetected = this.detectEnv > this.threshold ? 1 : 0;

        // Smooth filter engagement
        if (plosiveDetected) {
          this.filterEngage = 1 * (1 - attackCoeff) + this.filterEngage * attackCoeff;
        } else {
          this.filterEngage = 0 * (1 - releaseCoeff) + this.filterEngage * releaseCoeff;
        }

        // Apply highpass filter (biquad)
        const hpOut = (this.b0 * sample + this.b1 * x1 + this.b2 * x2
          - this.a1 * y1 - this.a2 * y2) / this.a0;
        x2 = x1;
        x1 = sample;
        y2 = y1;
        y1 = hpOut;

        // Crossfade between dry and filtered based on engagement level
        const filtered = sample * (1 - this.filterEngage) + hpOut * this.filterEngage;

        // Mix
        outCh[i] = filtered * this.mixAmount + sample * (1 - this.mixAmount);
      }

      // Save state for first channel
      if (ch === 0) {
        this.hpX1 = x1; this.hpX2 = x2;
        this.hpY1 = y1; this.hpY2 = y2;
      }
    }
  }
}
