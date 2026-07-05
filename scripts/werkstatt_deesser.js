// @werkstatt deesser 1 1
// @label De-Esser
// @param freq 0.4 0 1 linear
// @param threshold 0.5 0 1 linear
// @param ratio 0.4 0 1 linear
// @param attack 0.3 0 1 linear
// @param release 0.4 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
  p = {freq: 0.4, threshold: 0.5, ratio: 0.4, attack: 0.3, release: 0.4, mix: 1, output: 0}

  // State
  hpS1L = 0; hpS2L = 0;   // Linkwitz-Riley HPF state L
  hpS1R = 0; hpS2R = 0;   // Linkwitz-Riley HPF state R
  envL = 0; envR = 0;     // envelope follower
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
    const thr = this.p.threshold;
    const ratio = this.p.ratio;
    const atk = this.p.attack;
    const rel = this.p.release;
    const mix = this.p.mix;
    const og = this.outGain;

    // map freq 0..1 to crossover 2kHz..12kHz (exponential)
    const fc = 2000 * Math.pow(6, freq); // 2000 → 12000
    const dt = 1 / this.sampleRate;
    const wc = 2 * Math.PI * fc * dt;
    // 2nd-order Linkwitz-Riley HPF coefficients
    const cosw = Math.cos(wc);
    const sinw = Math.sin(wc);
    const alpha = sinw / 0.707; // Q=0.707 for LR4
    const b0 = (1 + cosw) / 2, b1 = -(1 + cosw), b2 = (1 + cosw) / 2;
    const a0 = 1 + alpha, a1 = -2 * cosw, a2 = 1 - alpha;
    const nb0 = b0 / a0, nb1 = b1 / a0, nb2 = b2 / a0;
    const na1 = a1 / a0, na2 = a2 / a0;

    // envelope time constants (mapped from 0..1)
    const atkT = Math.pow(10, atk * 2 - 3) * this.sampleRate; // 0.001s..1s
    const relT = Math.pow(10, rel * 2 - 2) * this.sampleRate; // 0.01s..10s
    const atkC = Math.exp(-1 / atkT);
    const relC = Math.exp(-1 / relT);

    // threshold mapped 0..1 to -40..0 dB
    const thrLin = Math.pow(10, (thr * 40 - 40) / 20);
    // ratio mapped 0..1 to 1:1..10:1
    const ratioVal = 1 + ratio * 9;

    for (let c = 0; c < input.length; c++) {
      const ch = input[c];
      const out = output[c];
      const len = ch.length;

      let s1 = c === 0 ? this.hpS1L : this.hpS1R;
      let s2 = c === 0 ? this.hpS2L : this.hpS2R;
      let env = c === 0 ? this.envL : this.envR;
      const saveC = c;

      for (let i = 0; i < len; i++) {
        const dry = ch[i];

        // 2nd-order HPF to isolate sibilance band
        const hpOut = nb0 * dry + nb1 * (s1) + nb2 * (s2) - na1 * (s1) - na2 * (s2);
        s2 = s1;
        s1 = dry;

        // envelope follower on high band
        const absHp = Math.abs(hpOut);
        if (absHp > env) {
          env = atkC * env + (1 - atkC) * absHp;
        } else {
          env = relC * env + (1 - relC) * absHp;
        }

        // gain reduction
        let gain = 1;
        if (env > thrLin) {
          const over = env / thrLin;
          const reduced = Math.pow(over, 1 / ratioVal);
          gain = thrLin * reduced / env;
        }

        // apply gain reduction to high band only, recombine
        const reducedHi = hpOut * gain;
        const lowBand = dry - hpOut; // everything below crossover
        let processed = lowBand + reducedHi;

        // parallel dry/wet
        const wet = dry + (processed - dry) * mix;
        out[i] = wet * og;
      }

      if (saveC === 0) { this.hpS1L = s1; this.hpS2L = s2; this.envL = env; }
      else { this.hpS1R = s1; this.hpS2R = s2; this.envR = env; }
    }
  }
}
