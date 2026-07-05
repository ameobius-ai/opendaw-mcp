// @werkstatt transient 1 1
// @label Transient Shaper
// @param attack 0.5 0 1 linear
// @param sustain 0.5 0 1 linear
// @param mix 1 0 1 linear
// @param output 0 -24 6 linear dB

class Processor {
  p = {attack: 0.5, sustain: 0.5, mix: 1, output: 0}

  // State — dual envelope followers (fast for transient, slow for sustain)
  envFastL = 0; envFastR = 0;
  envSlowL = 0; envSlowR = 0;
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

    const atkAmt = this.p.attack;     // 0..1, 0.5 = neutral
    const susAmt = this.p.sustain;   // 0..1, 0.5 = neutral
    const mix = this.p.mix;
    const og = this.outGain;

    // fast envelope: ~5ms for transient detection
    const fastAtk = Math.exp(-1 / (0.001 * this.sampleRate));
    const fastRel = Math.exp(-1 / (0.005 * this.sampleRate));
    // slow envelope: ~80ms for sustain detection
    const slowAtk = Math.exp(-1 / (0.003 * this.sampleRate));
    const slowRel = Math.exp(-1 / (0.08 * this.sampleRate));

    // gain amounts: 0.5 = neutral (1x), 0 = -12dB, 1 = +12dB
    const atkGain = Math.pow(10, (atkAmt - 0.5) * 24 / 20); // -12..+12 dB
    const susGain = Math.pow(10, (susAmt - 0.5) * 24 / 20);

    for (let c = 0; c < input.length; c++) {
      const ch = input[c];
      const out = output[c];
      const len = ch.length;

      let ef = c === 0 ? this.envFastL : this.envFastR;
      let es = c === 0 ? this.envSlowL : this.envSlowR;
      const saveC = c;

      for (let i = 0; i < len; i++) {
        const dry = ch[i];
        const absDry = Math.abs(dry);

        // fast envelope (transient)
        if (absDry > ef) ef = fastAtk * ef + (1 - fastAtk) * absDry;
        else ef = fastRel * ef + (1 - fastRel) * absDry;

        // slow envelope (sustain)
        if (absDry > es) es = slowAtk * es + (1 - slowAtk) * absDry;
        else es = slowRel * es + (1 - slowRel) * absDry;

        // transient component = fast - slow (clipped to >=0)
        const transient = Math.max(0, ef - es);
        // sustain component = slow
        const sustain = es;

        // gain factors
        const tGain = transient > 0.0001 ? atkGain : 1;
        const sGain = sustain > 0.0001 ? susGain : 1;

        // apply: split signal into transient and sustain portions
        // transient portion scales with (ef-es)/ef ratio
        const transientRatio = ef > 0.0001 ? transient / ef : 0;
        const sustainRatio = ef > 0.0001 ? sustain / ef : 1;

        const processed = dry * (transientRatio * tGain + sustainRatio * sGain);

        // parallel dry/wet
        out[i] = (dry + (processed - dry) * mix) * og;
      }

      if (saveC === 0) { this.envFastL = ef; this.envSlowL = es; }
      else { this.envFastR = ef; this.envSlowR = es; }
    }
  }
}
