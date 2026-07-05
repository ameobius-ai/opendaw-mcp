// @werkstatt stereowidth 1 1
// @label Stereo Width (M/S)
// @param width 0.5 0 1.5 linear
// @param lowTrim 0 0 1 linear
// @param lowFreq 0.2 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
  p = {width: 0.5, lowTrim: 0, lowFreq: 0.2, mix: 1, output: 0}

  // State — one-pole smoother for low-band gain
  sSmoothL = 0; sSmoothR = 0;
  prevSideL = 0; prevSideR = 0;
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
    if (!input || !output || input.length < 2) return;

    const inL = input[0];
    const inR = input[1];
    const outL = output[0];
    const outR = output[1];
    const len = inL.length;

    const width = this.p.width;        // 0=mono, 0.5=neutral, 1.5=wide
    const lowTrim = this.p.lowTrim;    // 0=no trim, 1=full mono below crossover
    const mix = this.p.mix;
    const og = this.outGain;

    // lowFreq 0..1 → 50..500 Hz crossover
    const fc = 50 * Math.pow(10, this.p.lowFreq * 1); // 50..500 Hz
    const dt = 1 / this.sampleRate;
    const rc = 1 / (2 * Math.PI * fc);
    const alpha = dt / (rc + dt); // one-pole LP coefficient

    for (let i = 0; i < len; i++) {
      const dryL = inL[i];
      const dryR = inR[i];

      // M/S encode
      const mid = (dryL + dryR) * 0.5;
      const side = (dryL - dryR) * 0.5;

      // one-pole LPF on side signal to detect low-freq content
      const sideLowL = alpha * side + (1 - alpha) * this.prevSideL;
      this.prevSideL = sideLowL;

      // compute low-band gain reduction
      const sideLowMag = Math.abs(sideLowL);
      // smooth it
      this.sSmoothL = this.sSmoothL * 0.99 + sideLowMag * 0.01;
      const lowEnergy = this.sSmoothL;

      // lowTrim: reduce side in low frequencies (mono bass)
      // gain = 1 - lowTrim * (energy-weighted factor)
      const lowGain = 1 - lowTrim * Math.min(1, lowEnergy * 10);

      // apply width to side
      const processedSide = side * width * lowGain;

      // M/S decode
      const wetL = mid + processedSide;
      const wetR = mid - processedSide;

      // parallel dry/wet
      outL[i] = (dryL + (wetL - dryL) * mix) * og;
      outR[i] = (dryR + (wetR - dryR) * mix) * og;
    }
  }
}
