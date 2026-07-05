// @werkstatt envelope_follower 1 1
// Envelope follower — tracks input amplitude and outputs control signal
// Used as building block for auto-wah, tremolo depth, ducking, sidechain
//
// @param attack linear 0.001 0.1 0.005   // rise time (fast = percussive, slow = smooth)
// @param release linear 0.01 1.0 0.1     // fall time (fast = staccato, slow = legato)
// @param gain linear 0.5 4.0 1.5         // output gain of control signal
// @param mix linear 0.0 1.0 0.5          // 0=dry, 1=envelope only, 0.5=mixed
//
// Influences: Mooger Fooger MF-101, Korg MS-20 EG, Sherman Filterbank

class Processor {
  paramChanged(name, value) {
    if (name === "attack") this.attackTime = value;
    if (name === "release") this.releaseTime = value;
    if (name === "gain") this.gain = value;
    if (name === "mix") this.mix = value;
    this.recalculate();
  }

  recalculate() {
    const sr = this.sampleRate;
    // Convert time constants to per-sample coefficients
    // alpha = 1 - exp(-1 / (time * sampleRate))
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

      if (ch === 0) {
        // Channel 0: process envelope
        for (let i = 0; i < inCh.length; i++) {
          const sample = inCh[i];
          const abs = Math.abs(sample);

          // Attack/release envelope detection
          if (abs > this.envelope) {
            this.envelope += (abs - this.envelope) * this.attackCoef;
          } else {
            this.envelope += (abs - this.envelope) * this.releaseCoef;
          }

          // Output: mix of dry and envelope
          const env = this.envelope * this.gain;
          outCh[i] = sample * (1 - this.mix) + env * this.mix;
        }
      } else {
        // Other channels: copy processed envelope
        const ref = output[0];
        for (let i = 0; i < inCh.length; i++) {
          outCh[i] = inCh[i] * (1 - this.mix) + (ref[i] - inCh[i] * (1 - this.mix)) * this.mix;
        }
      }
    }
  }

  envelope = 0;
  attackTime = 0.005;
  releaseTime = 0.1;
  gain = 1.5;
  mix = 0.5;
  attackCoef = 0;
  releaseCoef = 0;
  sampleRate = 44100;
  blockSize = 128;
}
