// @werkstatt reverb 1 1
// @label Plate Reverb
// @param decay 0.4 0.1 0.95 linear
// @param predelay 0.02 0 0.2 linear s
// @param damping 0.5 0 1 linear
// @param width 0.8 0 1 linear
// @param mix 0.3 0 1 linear

class Processor {
  constructor() {
    // Schroeder reverb: 4 comb filters + 2 allpass
    this.sr = this.sampleRate;
    this.combs = [];
    const combTimes = [29.7, 37.1, 41.1, 43.7]; // ms
    for (let i = 0; i < 4; i++) {
      const len = Math.floor(this.sr * combTimes[i] / 1000);
      this.combs.push({buf: new Float32Array(len), idx: 0, len});
    }
    this.allpasses = [];
    const apTimes = [5.0, 1.7]; // ms
    for (let i = 0; i < 2; i++) {
      const len = Math.floor(this.sr * apTimes[i] / 1000);
      this.allpasses.push({buf: new Float32Array(len), idx: 0, len});
    }
    this.predelayBuf = new Float32Array(Math.floor(this.sr * 0.2));
    this.predelayIdx = 0;
    this.dampState = 0;
    this.dampPrev = 0;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const out = outputs[0];
    const decay = parameters.decay[0];
    const predelaySamp = Math.floor(parameters.predelay[0] * this.sr);
    const damping = parameters.damping[0];
    const width = parameters.width[0];
    const mix = parameters.mix[0];

    const nch = out.length;
    for (let c = 0; c < nch; c++) {
      const inCh = input && input[c] ? input[c] : null;
      const outCh = out[c];
      for (let i = 0; i < outCh.length; i++) {
        const dry = inCh ? inCh[i] : 0;

        // Predelay
        const pdIdx = (this.predelayIdx - predelaySamp + this.predelayBuf.length) % this.predelayBuf.length;
        const pdOut = this.predelayBuf[pdIdx];
        this.predelayBuf[this.predelayIdx] = dry;
        this.predelayIdx = (this.predelayIdx + 1) % this.predelayBuf.length;

        // Comb filters
        let wet = pdOut;
        for (let k = 0; k < this.combs.length; k++) {
          const comb = this.combs[k];
          const feedback = comb.buf[comb.idx];
          const filtered = feedback * (1 - damping) + this.dampPrev * damping;
          this.dampPrev = filtered;
          comb.buf[comb.idx] = pdOut + filtered * decay;
          wet += filtered;
        }

        // Allpass filters
        for (let k = 0; k < this.allpasses.length; k++) {
          const ap = this.allpasses[k];
          const delayed = ap.buf[ap.idx];
          ap.buf[ap.idx] = wet + delayed * 0.7;
          wet = delayed - wet * 0.7;
          ap.idx = (ap.idx + 1) % ap.len;
        }

        // Stereo width (cross-mix on channel 1)
        let sample = wet;
        if (c === 1) {
          // narrow stereo by mixing opposite channel
          sample = sample * (1 - width * 0.5);
        } else {
          sample = sample * (0.5 + width * 0.5);
        }

        outCh[i] = dry * (1 - mix) + sample * mix;
      }
    }
  }

  paramChanged(name, value) {}
}
