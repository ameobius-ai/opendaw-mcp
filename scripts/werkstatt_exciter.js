// @werkstatt exciter 1 1
// @label Harmonic Exciter
// @param freq 0.3 0 1 linear
// @param harmonics 0.5 0 1 linear
// @param drive 0.4 0 1 linear
// @param mix 0.3 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
  p = {freq: 0.3, harmonics: 0.5, drive: 0.4, mix: 0.3, output: 0}

  // State
  hpStateL = 0; hpStateR = 0;   // HPF state (one-pole)
  hpPrevL = 0;  hpPrevR = 0;    // second HPF stage for steeper slope
  outGain = 1;

  paramChanged(name, value) {
    this.p[name] = value;
    if (name === "output") {
      this.outGain = Math.pow(10, value / 20);
    }
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    if (!input || !output) return;

    const freq = this.p.freq;
    const harm = this.p.harmonics;
    const drv = this.p.drive;
    const mix = this.p.mix;
    const og = this.outGain;

    // map freq 0..1 to crossover 800Hz..12000Hz (exponential)
    const fc = 800 * Math.pow(15, freq); // 800 → 12000
    const dt = 1 / this.sampleRate;
    // one-pole HPF coefficient
    const rc = 1 / (2 * Math.PI * fc);
    const alpha = rc / (rc + dt);

    for (let c = 0; c < input.length; c++) {
      const ch = input[c];
      const out = output[c];
      const len = ch.length;

      // stereo-linked state per channel
      let s1 = c === 0 ? this.hpStateL : this.hpStateR;
      let s2 = c === 0 ? this.hpPrevL : this.hpPrevR;
      const hp0 = s1;
      const hp1 = s2;
      const saveC = c;

      for (let i = 0; i < len; i++) {
        const dry = ch[i];

        // two cascaded one-pole HPFs (12 dB/oct)
        const hpOut1 = alpha * (s1 + dry - hp0);
        s1 = hpOut1;
        const hpOut2 = alpha * (s1 + hpOut1 - hp1);
        s2 = hpOut2;

        // high band
        let hi = hpOut2;

        // waveshaping: 3rd-order harmonic generation
        // tanh-like approximation scaled by drive + harmonics amount
        const d = 1 + drv * 4;
        const shaped = hi * d;
        // cubic nonlinearity — adds odd harmonics
        const cubed = shaped * shaped * shaped;
        // mix original hi with harmonics
        let excited = hi + cubed * harm * 0.3;

        // soft clip to prevent runaway
        if (excited > 1) excited = 1;
        if (excited < -1) excited = -1;

        // parallel: dry + excited high band
        const wet = dry + excited * mix;
        out[i] = wet * og;
      }

      // save state
      if (saveC === 0) { this.hpStateL = s1; this.hpPrevL = s2; }
      else { this.hpStateR = s1; this.hpPrevR = s2; }
    }
  }
}
