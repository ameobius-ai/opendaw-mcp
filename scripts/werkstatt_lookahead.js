// @werkstatt lookahead 1 1
// @label Lookahead Compressor
// @param threshold -18 -60 0 linear dB
// @param ratio 4 1 20 linear
// @param attack 0.003 0.001 0.1 exp s
// @param release 0.25 0.01 2 exp s
// @param knee 6 0 12 linear dB
// @param makeup 0 0 24 linear dB
// @param mix 1 0 1 linear

class Processor {
  constructor() {
    this.sr = this.sampleRate;
    // Lookahead buffer
    const laLen = Math.floor(this.sr * 0.01);
    this.lookBuf = new Float32Array(laLen);
    this.lookIdx = 0;
    // Envelope detector
    this.env = 0;
    // DC blocker
    this.dcPrev = 0;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const out = outputs[0];
    const threshold = parameters.threshold[0];
    const ratio = parameters.ratio[0];
    const attackCoef = Math.exp(-1 / (parameters.attack[0] * this.sr));
    const releaseCoef = Math.exp(-1 / (parameters.release[0] * this.sr));
    const knee = parameters.knee[0];
    const makeupLin = Math.pow(10, parameters.makeup[0] / 20);
    const mix = parameters.mix[0];
    const blockSize = out[0] ? out[0].length : 0;

    for (let i = 0; i < blockSize; i++) {
      // Mono detect (sum stereo)
      let inL = input && input[0] ? input[0][i] : 0;
      let inR = input && input[1] ? input[1][i] : inL;
      const mono = (inL + inR) * 0.5;

      // Lookahead: store current, read delayed
      const delayed = this.lookBuf[this.lookIdx];
      this.lookBuf[this.lookIdx] = mono;
      this.lookIdx = (this.lookIdx + 1) % this.lookBuf.length;

      // Envelope follower (peak)
      const absIn = Math.abs(mono);
      const coef = absIn > this.env ? attackCoef : releaseCoef;
      this.env = absIn + (this.env - absIn) * coef;

      // Gain reduction (dB domain, soft knee)
      const envDb = 20 * Math.log10(this.env + 1e-10);
      let gainReduction = 0;
      const kneeStart = threshold - knee * 0.5;
      const kneeEnd = threshold + knee * 0.5;

      if (envDb > kneeEnd) {
        gainReduction = (envDb - threshold) * (1 - 1 / ratio);
      } else if (envDb > kneeStart) {
        // Soft knee: quadratic transition
        const x = envDb - kneeStart;
        const w = knee;
        gainReduction = (1 - 1 / ratio) * (x * x) / (2 * w);
      }

      const gainLin = Math.pow(10, -gainReduction / 20);
      const outGain = gainLin * makeupLin;

      // DC blocker
      const dL = delayed + (inL - this.dcPrev) * 0; // delayed is mono, use per-channel
      this.dcPrev = inL;

      if (out[0]) out[0][i] = inL * (outGain * mix + (1 - mix));
      if (out[1]) out[1][i] = inR * (outGain * mix + (1 - mix));
    }
  }

  paramChanged(name, value) {}
}
