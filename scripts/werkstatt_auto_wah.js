// @werkstatt auto_wah 1 1
// Auto-wah — envelope-driven resonant filter sweep
// Classic funk/disco quack: filter frequency follows input amplitude
//
// @param attack linear 0.001 0.1 0.005     // envelope rise (fast = snappy quack)
// @param release linear 0.01 1.0 0.15      // envelope fall (slow = vocal, fast = staccato)
// @param min_freq exp 100 2000 400         // lowest filter frequency (Hz)
// @param max_freq exp 500 8000 2000        // highest filter frequency (Hz)
// @param resonance linear 1 20 8           // filter Q (low = gentle, high = vocal quack)
// @param mix linear 0.0 1.0 1.0            // 0=dry, 1=wet only
//
// Influences: Mu-Tron III, Cry Baby Wah, Boss AW-3, Bootsy Collins funk

class Processor {
  paramChanged(name, value) {
    if (name === "attack") this.attackTime = value;
    if (name === "release") this.releaseTime = value;
    if (name === "min_freq") this.minFreq = value;
    if (name === "max_freq") this.maxFreq = value;
    if (name === "resonance") this.resonance = value;
    if (name === "mix") this.mix = value;
    this.recalculate();
  }

  recalculate() {
    const sr = this.sampleRate;
    this.attackCoef = 1 - Math.exp(-1 / (Math.max(0.0001, this.attackTime) * sr));
    this.releaseCoef = 1 - Math.exp(-1 / (Math.max(0.0001, this.releaseTime) * sr));
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    if (!input || !input[0]) return;

    for (let ch = 0; ch < output.length; ch++) {
      const inCh = input[ch] || input[0];
      const outCh = output[ch];

      // State per-channel for stereo
      if (ch >= this.state.length) {
        this.state.push({ envelope: 0, x1: 0, x2: 0, y1: 0, y2: 0 });
      }
      const st = this.state[ch];

      for (let i = 0; i < inCh.length; i++) {
        const sample = inCh[i];
        const abs = Math.abs(sample);

        // Envelope detection
        if (abs > st.envelope) {
          st.envelope += (abs - st.envelope) * this.attackCoef;
        } else {
          st.envelope += (abs - st.envelope) * this.releaseCoef;
        }

        // Map envelope (0-1) to filter frequency (min-max)
        const envNorm = Math.min(1, st.envelope * 2); // scale up
        const freq = this.minFreq + (this.maxFreq - this.minFreq) * envNorm;

        // Biquad bandpass filter (state-variable)
        const w0 = 2 * Math.PI * freq / this.sampleRate;
        const alpha = Math.sin(w0) / (2 * this.resonance);
        const cosw0 = Math.cos(w0);
        const b0 = alpha;
        const b1 = 0;
        const b2 = -alpha;
        const a0 = 1 + alpha;
        const a1 = -2 * cosw0;
        const a2 = 1 - alpha;

        // Normalize
        const nb0 = b0 / a0;
        const nb1 = b1 / a0;
        const nb2 = b2 / a0;
        const na1 = a1 / a0;
        const na2 = a2 / a0;

        // Direct form II transposed
        const xn = sample;
        const yn = nb0 * xn + st.x1;
        st.x1 = nb1 * xn - na1 * yn + st.x2;
        st.x2 = nb2 * xn - na2 * yn;

        outCh[i] = sample * (1 - this.mix) + yn * this.mix;
      }
    }
  }

  attackTime = 0.005;
  releaseTime = 0.15;
  minFreq = 400;
  maxFreq = 2000;
  resonance = 8;
  mix = 1.0;
  attackCoef = 0;
  releaseCoef = 0;
  sampleRate = 44100;
  blockSize = 128;
  state = []; // per-channel filter state
}
