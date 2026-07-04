// @werkstatt shimmer 1 1
// @label Shimmer Delay
// @param time 0.25 0.01 1 exp s
// @param feedback 0.55 0 0.95 linear
// @param pitch 12 -12 24 int
// @param shimmer 0.4 0 1 linear
// @param damping 0.3 0 1 linear
// @param mix 0.35 0 1 linear

class Processor {
  constructor() {
    this.sr = this.sampleRate;
    const maxLen = this.sr;
    this.buf = new Float32Array(maxLen * 2);
    this.idx = 0;
    this.pitchPhase = 0;
    this.pitchBuf = new Float32Array(2048);
    this.pitchWriteIdx = 0;
    this.dampState = [0, 0];
  }

  pitchShift(sample, semitones) {
    if (semitones === 0) return sample;
    const ratio = Math.pow(2, semitones / 12);
    this.pitchBuf[this.pitchWriteIdx] = sample;
    this.pitchWriteIdx = (this.pitchWriteIdx + 1) % this.pitchBuf.length;
    this.pitchPhase += ratio;
    if (this.pitchPhase >= this.pitchBuf.length) this.pitchPhase -= this.pitchBuf.length;
    const readIdx = Math.floor(this.pitchPhase);
    const nextIdx = (readIdx + 1) % this.pitchBuf.length;
    const frac = this.pitchPhase - readIdx;
    return this.pitchBuf[readIdx] * (1 - frac) + this.pitchBuf[nextIdx] * frac;
  }

  processAudio(inputs, outputs, parameters) {
    const input = inputs[0];
    const out = outputs[0];
    const delaySamp = Math.floor(parameters.time[0] * this.sr);
    const feedback = parameters.feedback[0];
    const semitones = Math.round(parameters.pitch[0]);
    const shimmerAmt = parameters.shimmer[0];
    const damping = parameters.damping[0];
    const mix = parameters.mix[0];
    const blockSize = out[0] ? out[0].length : 0;
    const maxLen = this.sr;

    for (let i = 0; i < blockSize; i++) {
      for (let c = 0; c < 2; c++) {
        const bufBase = c * maxLen;
        const dry = input && input[c] ? input[c][i] : (input && input[0] ? input[0][i] : 0);
        const readIdx = (this.idx - delaySamp + maxLen) % maxLen;
        const delayed = this.buf[bufBase + readIdx];
        const pitched = this.pitchShift(delayed, semitones);
        const wet = delayed * (1 - shimmerAmt) + pitched * shimmerAmt;
        this.dampState[c] = this.dampState[c] * damping + wet * (1 - damping);
        this.buf[bufBase + this.idx] = dry + this.dampState[c] * feedback;
        if (out[c]) out[c][i] = dry * (1 - mix) + wet * mix;
      }
      this.idx = (this.idx + 1) % maxLen;
    }
  }

  paramChanged(name, value) {}
}
