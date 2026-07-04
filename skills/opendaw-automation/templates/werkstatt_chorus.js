// @werkstatt chorus 1 1
// @label Stereo Chorus
// @param rate 0.5 0.05 5 exp Hz
// @param depth 0.3 0 1 linear
// @param center 0.015 0.001 0.05 linear s
// @param feedback 0.2 0 0.9 linear
// @param mix 0.5 0 1 linear

class Processor {
  constructor() {
    this.sr = this.sampleRate;
    this.maxDelay = Math.floor(this.sr * 0.05);
    this.bufL = new Float32Array(this.maxDelay);
    this.bufR = new Float32Array(this.maxDelay);
    this.idxL = 0;
    this.idxR = 0;
    this.phase = 0;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const out = outputs[0];
    const rate = parameters.rate[0];
    const depth = parameters.depth[0];
    const center = parameters.center[0] * this.sr;
    const feedback = parameters.feedback[0];
    const mix = parameters.mix[0];
    const blockSize = out[0] ? out[0].length : 0;

    for (let i = 0; i < blockSize; i++) {
      this.phase += 2 * Math.PI * rate / this.sr;
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI;
      const lfoL = Math.sin(this.phase);
      const lfoR = Math.sin(this.phase + Math.PI / 2);
      const delayL = center + depth * center * lfoL;
      const delayR = center + depth * center * lfoR;
      const readL = this.idxL - delayL + this.maxDelay;
      const readR = this.idxR - delayR + this.maxDelay;
      const iL0 = Math.floor(readL) % this.maxDelay;
      const iL1 = (iL0 + 1) % this.maxDelay;
      const fL = readL - Math.floor(readL);
      const delayedL = this.bufL[iL0] * (1 - fL) + this.bufL[iL1] * fL;
      const iR0 = Math.floor(readR) % this.maxDelay;
      const iR1 = (iR0 + 1) % this.maxDelay;
      const fR = readR - Math.floor(readR);
      const delayedR = this.bufR[iR0] * (1 - fR) + this.bufR[iR1] * fR;
      const dryL = input && input[0] ? input[0][i] : 0;
      const dryR = input && input[1] ? input[1][i] : dryL;
      this.bufL[this.idxL] = dryL + delayedL * feedback;
      this.bufR[this.idxR] = dryR + delayedR * feedback;
      this.idxL = (this.idxL + 1) % this.maxDelay;
      this.idxR = (this.idxR + 1) % this.maxDelay;
      if (out[0]) out[0][i] = dryL * (1 - mix) + delayedL * mix;
      if (out[1]) out[1][i] = dryR * (1 - mix) + delayedR * mix;
    }
  }

  paramChanged(name, value) {}
}
