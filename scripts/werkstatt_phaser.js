// @werkstatt phaser 1 1
// @label Phaser
// @param rate 0.3 0.05 8 exp Hz
// @param depth 0.5 0 1 linear
// @param feedback 0.3 0 0.9 linear
// @param stages 4 2 8 int
// @param mix 0.5 0 1 linear

class Processor {
  constructor() {
    this.sr = this.sampleRate;
    this.phase = 0;
    // Allpass states for up to 8 stages, stereo
    this.apStates = [];
    for (let c = 0; c < 2; c++) {
      this.apStates.push(new Array(8).fill(0).map(() => ({z1: 0, z2: 0})));
    }
  }

  // 2nd-order allpass for phasing (shifts 0..pi sweep)
  allpass2(x, state, freq) {
    // Coefficients from frequency
    const w = 2 * Math.PI * freq / this.sr;
    const c = Math.cos(w);
    const tanw = Math.tan(w / 2);
    const b0 = (1 - tanw) / (1 + tanw);
    const a1 = -2 * c * (1 - tanw) / (1 + tanw);

    const y = b0 * x + state.z1 - state.z2 * b0;
    state.z2 = state.z1;
    state.z1 = x - a1 * y;
    return y;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const out = outputs[0];
    const rate = parameters.rate[0];
    const depth = parameters.depth[0];
    const feedback = parameters.feedback[0];
    const stages = Math.round(parameters.stages[0]);
    const mix = parameters.mix[0];
    const blockSize = out[0] ? out[0].length : 0;

    for (let i = 0; i < blockSize; i++) {
      this.phase += 2 * Math.PI * rate / this.sr;
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI;

      // LFO sweeps 200..8000 Hz
      const lfo = (Math.sin(this.phase) + 1) * 0.5;
      const sweepFreq = 200 + depth * 7800 * lfo;

      const nch = Math.min(out.length, 2);
      for (let c = 0; c < nch; c++) {
        const inCh = input && input[c] ? input[c] : (input && input[0] ? input[0][i] : 0);
        let sample = inCh;
        const fbBuf = this.apStates[c];

        // Feedback loop
        let fbSample = sample + this._fb[c] * feedback;

        // Cascade allpass stages
        for (let s = 0; s < stages; s++) {
          fbSample = this.allpass2(fbSample, fbBuf[s], sweepFreq);
        }

        this._fb = this._fb || [0, 0];
        this._fb[c] = fbSample;

        if (out[c]) out[c][i] = inCh * (1 - mix) + fbSample * mix;
      }
    }
  }

  paramChanged(name, value) {}
}
